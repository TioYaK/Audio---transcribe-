
import logging
import os
import pickle
import hashlib
import time
from typing import List, Optional, Tuple, Dict
from collections import OrderedDict, Counter
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Force SpeechBrain to use soundfile backend (avoids torchaudio warnings)
os.environ['SPEECHBRAIN_AUDIO_BACKEND'] = 'soundfile'


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    labels: List[int]
    num_speakers: int
    silhouette_score: float
    timestamp: float
    audio_hash: str


class LRUCacheWithTTL:
    """
    LRU Cache with Time-To-Live (TTL) support.
    Automatically evicts old entries and maintains size limit.
    """
    def __init__(self, max_size: int = 100, ttl_seconds: int = 86400):
        """
        Args:
            max_size: Maximum number of entries
            ttl_seconds: Time to live in seconds (default: 24h)
        """
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.hits = 0
        self.misses = 0
        
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from cache if valid"""
        if key in self.cache:
            entry = self.cache[key]
            
            # Check TTL
            if time.time() - entry.timestamp < self.ttl_seconds:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                self.hits += 1
                return entry
            else:
                # Expired, remove
                del self.cache[key]
                logger.debug(f"Cache entry expired: {key}")
        
        self.misses += 1
        return None
    
    def set(self, key: str, entry: CacheEntry):
        """Add entry to cache"""
        # Remove oldest if at capacity
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            logger.debug(f"Cache evicted oldest: {oldest_key}")
        
        self.cache[key] = entry
        self.cache.move_to_end(key)
    
    def clear_expired(self):
        """Manually clear all expired entries"""
        current_time = time.time()
        expired_keys = [
            k for k, v in self.cache.items() 
            if current_time - v.timestamp >= self.ttl_seconds
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"Cleared {len(expired_keys)} expired cache entries")
    
    def get_stats(self) -> Dict[str, any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "ttl_seconds": self.ttl_seconds
        }


class DiarizationService:
    """
    Optimized Speaker Diarization Service with:
    - LRU Cache with TTL
    - Automatic speaker detection (2-6 speakers)
    - Silhouette score optimization
    - Energy-based filtering
    - Smoothing with majority vote
    """
    
    def __init__(self, device: str = "cpu", cache_size: int = 100, cache_ttl: int = 86400):
        """
        Args:
            device: 'cpu' or 'cuda'
            cache_size: Maximum cache entries (default: 100)
            cache_ttl: Cache TTL in seconds (default: 24h)
        """
        self.device = device
        self.embedding_model = None
        
        # Initialize LRU Cache with TTL
        self.cache = LRUCacheWithTTL(max_size=cache_size, ttl_seconds=cache_ttl)
        
        # Statistics
        self.total_diarizations = 0
        self.total_cache_hits = 0
        
    def diarize(self, audio_path: str, segments, min_speakers: int = 2, max_speakers: int = 6) -> List[int]:
        """
        Performs speaker diarization on the segments.
        
        Args:
            audio_path: Path to audio file
            segments: List of transcription segments
            min_speakers: Minimum number of speakers to detect (default: 2)
            max_speakers: Maximum number of speakers to detect (default: 6)
            
        Returns:
            List of speaker IDs corresponding to each segment
        """
        # Lazy Loading
        try:
            import torch
            import torchaudio
            from speechbrain.inference.speaker import EncoderClassifier
            import numpy as np
            from sklearn.cluster import AgglomerativeClustering
            from sklearn.preprocessing import normalize
            from sklearn.metrics import silhouette_score
        except ImportError as e:
            logger.warning(f"Diarization dependencies missing: {e}")
            return [0] * len(segments)

        self.total_diarizations += 1
        
        # Generate cache key
        cache_key = self._get_cache_key(audio_path, len(segments), min_speakers, max_speakers)
        
        # Check cache
        cached_entry = self.cache.get(cache_key)
        if cached_entry:
            self.total_cache_hits += 1
            logger.info(
                f"✓ Cache HIT! Speakers: {cached_entry.num_speakers}, "
                f"Score: {cached_entry.silhouette_score:.3f} "
                f"(Hit rate: {self.cache.hits}/{self.total_diarizations})"
            )
            return cached_entry.labels

        logger.info(f"Cache MISS. Computing diarization... (Cache stats: {self.cache.get_stats()})")
        
        # Compute diarization
        labels, num_speakers, score = self._compute_diarization(
            audio_path, segments, min_speakers, max_speakers
        )
        
        # Cache result
        audio_hash = self._get_file_hash(audio_path)
        cache_entry = CacheEntry(
            labels=labels,
            num_speakers=num_speakers,
            silhouette_score=score,
            timestamp=time.time(),
            audio_hash=audio_hash
        )
        self.cache.set(cache_key, cache_entry)
        
        return labels
    
    def _get_cache_key(self, audio_path: str, num_segments: int, min_speakers: int, max_speakers: int) -> str:
        """Generate cache key from audio path and parameters"""
        # Use file hash + parameters for cache key
        file_hash = self._get_file_hash(audio_path)
        key = f"{file_hash}_{num_segments}_{min_speakers}_{max_speakers}"
        return key
    
    def _get_file_hash(self, audio_path: str) -> str:
        """Get MD5 hash of file for cache invalidation"""
        h = hashlib.md5()
        
        # Hash file metadata (faster than hashing entire file)
        stat = os.stat(audio_path)
        h.update(f"{audio_path}_{stat.st_size}_{stat.st_mtime}".encode())
        
        return h.hexdigest()[:16]  # Use first 16 chars for shorter keys

    def _compute_diarization(
        self, 
        audio_path: str, 
        segments, 
        min_speakers: int, 
        max_speakers: int
    ) -> Tuple[List[int], int, float]:
        """
        Compute diarization with automatic speaker detection.
        
        Returns:
            Tuple of (labels, num_speakers, silhouette_score)
        """
        import torch
        import torchaudio
        from speechbrain.inference.speaker import EncoderClassifier
        import numpy as np
        from sklearn.cluster import AgglomerativeClustering
        from sklearn.preprocessing import normalize
        from sklearn.metrics import silhouette_score
        
        logger.info(f"Starting OPTIMIZED Diarization on {self.device.upper()}...")
        start_time = time.time()
        
        try:
            # 1. Initialize Model (lazy loading)
            if not self.embedding_model:
                run_opts = {
                    "device": "cuda" if self.device == "cuda" and torch.cuda.is_available() else "cpu"
                }
                
                self.embedding_model = EncoderClassifier.from_hparams(
                    source="speechbrain/spkrec-ecapa-voxceleb", 
                    savedir="/home/appuser/.cache/speechbrain_checkpoints",
                    run_opts=run_opts
                )
                logger.info(f"Loaded embedding model on {run_opts['device']}")
            
            # 2. Load and preprocess audio
            wav, fs = self._load_audio(audio_path)
            
            # 3. Extract embeddings
            embeddings, valid_indices, energies = self._extract_embeddings(wav, fs, segments)
            
            if len(embeddings) < min_speakers:
                logger.warning(f"Not enough segments ({len(embeddings)}) for {min_speakers} speakers.")
                return [0] * len(segments), 1, 0.0
            
            # 4. Cluster with automatic speaker detection
            labels, num_speakers, score = self._cluster_speakers(
                embeddings, valid_indices, min_speakers, max_speakers
            )
            
            # 5. Map back to all segments
            final_labels = self._map_to_segments(labels, valid_indices, len(segments))
            
            # 6. Post-process: smoothing
            smoothed_labels = self._smooth_labels(final_labels)
            
            elapsed = time.time() - start_time
            logger.info(
                f"✓ Diarization Complete in {elapsed:.2f}s. "
                f"Detected {num_speakers} speakers (score: {score:.3f})"
            )
            
            return smoothed_labels, num_speakers, score
            
        except Exception as e:
            logger.error(f"Diarization error: {e}", exc_info=True)
            return [0] * len(segments), 1, 0.0
    
    def _load_audio(self, audio_path: str):
        """Load and preprocess audio file"""
        import torch
        import torchaudio
        import soundfile as sf
        
        # Load using soundfile
        audio_data, fs = sf.read(audio_path)
        
        # Convert to torch tensor
        wav = torch.from_numpy(audio_data).float()
        
        # Ensure 2D shape (channels, samples)
        if wav.ndim == 1:
            wav = wav.unsqueeze(0)
        else:
            wav = wav.T
        
        # Convert to Mono
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)
        
        # Resample to 16kHz if needed
        if fs != 16000:
            resampler = torchaudio.transforms.Resample(fs, 16000).to(wav.device)
            wav = resampler(wav)
            fs = 16000
        
        # Move to device
        if self.device == "cuda" and torch.cuda.is_available():
            wav = wav.cuda()
        
        return wav, fs
    
    def _extract_embeddings(self, wav, fs: int, segments):
        """Extract speaker embeddings from segments"""
        import torch
        
        embeddings = []
        valid_indices = []
        energies = []
        
        MIN_SEGMENT_DURATION = 0.3  # seconds
        MIN_ENERGY_THRESHOLD = 0.01  # RMS threshold for silence
        
        for i, seg in enumerate(segments):
            # Convert time to samples
            start = int(seg.start * fs)
            end = int(seg.end * fs)
            
            # Skip very short segments
            if end - start < int(MIN_SEGMENT_DURATION * fs):
                continue
            
            # Verify bounds
            if start >= wav.shape[1]:
                continue
            end = min(end, wav.shape[1])
            
            # Extract segment
            crop = wav[:, start:end]
            
            # Calculate energy (RMS)
            energy = torch.sqrt(torch.mean(crop ** 2)).item()
            
            # Skip low-energy segments (silence)
            if energy < MIN_ENERGY_THRESHOLD:
                continue
            
            # Extract embedding
            with torch.no_grad():
                emb = self.embedding_model.encode_batch(crop)
                emb = emb.squeeze().cpu().numpy()
            
            embeddings.append(emb)
            valid_indices.append(i)
            energies.append(energy)
        
        logger.info(f"Extracted {len(embeddings)} valid embeddings from {len(segments)} segments")
        return embeddings, valid_indices, energies
    
    def _cluster_speakers(
        self, 
        embeddings: List, 
        valid_indices: List[int],
        min_speakers: int, 
        max_speakers: int
    ) -> Tuple[List[int], int, float]:
        """
        Cluster embeddings with automatic speaker detection.
        
        Returns:
            Tuple of (labels, optimal_num_speakers, best_silhouette_score)
        """
        import numpy as np
        from sklearn.cluster import AgglomerativeClustering
        from sklearn.preprocessing import normalize
        from sklearn.metrics import silhouette_score
        
        X = np.array(embeddings)
        
        # Normalize for cosine similarity
        X_norm = normalize(X)
        
        # Determine clustering range
        max_possible = min(max_speakers, len(embeddings))
        min_possible = min(min_speakers, max_possible)
        
        if max_possible < min_possible:
            logger.warning(f"Not enough embeddings for clustering. Using single speaker.")
            return [0] * len(embeddings), 1, 0.0
        
        best_n_clusters = min_possible
        best_score = -1
        best_labels = None
        
        logger.info(f"Testing clustering: {min_possible} to {max_possible} speakers")
        
        # Try different numbers of clusters
        for n in range(min_possible, max_possible + 1):
            try:
                # Agglomerative clustering with cosine metric
                clusterer = AgglomerativeClustering(
                    n_clusters=n,
                    metric='cosine',
                    linkage='average'
                )
                test_labels = clusterer.fit_predict(X_norm)
                
                # Calculate silhouette score
                if len(set(test_labels)) > 1:
                    score = silhouette_score(X_norm, test_labels, metric='cosine')
                else:
                    score = 0.0
                
                logger.info(f"  n={n}: score={score:.3f}, unique={len(set(test_labels))}")
                
                # Update best if score improved
                if score > best_score:
                    best_score = score
                    best_n_clusters = n
                    best_labels = test_labels
                    
            except Exception as e:
                logger.warning(f"  n={n} failed: {e}")
                continue
        
        # Fallback if no valid clustering
        if best_labels is None:
            logger.warning("All clustering attempts failed. Using default.")
            clusterer = AgglomerativeClustering(
                n_clusters=min_possible, 
                metric='cosine', 
                linkage='average'
            )
            best_labels = clusterer.fit_predict(X_norm)
            best_n_clusters = min_possible
            best_score = 0.0
        
        logger.info(f"✓ Selected {best_n_clusters} speakers (score: {best_score:.3f})")
        
        return best_labels.tolist(), best_n_clusters, best_score
    
    def _map_to_segments(self, labels: List[int], valid_indices: List[int], total_segments: int) -> List[int]:
        """Map cluster labels back to all segments"""
        final_labels = [-1] * total_segments
        
        for idx, label in zip(valid_indices, labels):
            final_labels[idx] = int(label)
        
        return final_labels
    
    def _smooth_labels(self, labels: List[int], window_size: int = 5) -> List[int]:
        """
        Smooth labels using sliding window majority vote.
        Also fills gaps with forward fill.
        """
        smoothed = labels.copy()
        
        # 1. Majority vote smoothing
        for i in range(len(labels)):
            start_idx = max(0, i - window_size // 2)
            end_idx = min(len(labels), i + window_size // 2 + 1)
            window = labels[start_idx:end_idx]
            
            # Filter out invalid (-1)
            valid_window = [l for l in window if l != -1]
            
            if valid_window:
                most_common = Counter(valid_window).most_common(1)[0][0]
                smoothed[i] = most_common
        
        # 2. Forward fill for remaining gaps
        last_known = 0
        for i in range(len(smoothed)):
            if smoothed[i] != -1:
                last_known = smoothed[i]
            else:
                smoothed[i] = last_known
        
        return smoothed
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics"""
        stats = self.cache.get_stats()
        stats.update({
            "total_diarizations": self.total_diarizations,
            "total_cache_hits": self.total_cache_hits,
            "overall_hit_rate": f"{(self.total_cache_hits / self.total_diarizations * 100) if self.total_diarizations > 0 else 0:.1f}%"
        })
        return stats
    
    def clear_cache(self):
        """Clear all cache entries"""
        self.cache.cache.clear()
        logger.info("Cache cleared")
    
    def clear_expired_cache(self):
        """Clear only expired cache entries"""
        self.cache.clear_expired()
