
import logging
import os
import pickle
import hashlib
from typing import List, Optional

logger = logging.getLogger(__name__)

class DiarizationService:
    def __init__(self, device: str = "cpu"):
        self.device = device
        self.embedding_model = None
        
    def diarize(self, audio_path: str, segments) -> List[int]:
        """
        Performs speaker diarization on the segments.
        Returns a list of speaker IDs corresponding to each segment.
        """
        # Lazy Loading
        try:
            import torch
            import torchaudio
            from speechbrain.inference.speaker import EncoderClassifier
            import numpy as np
            from sklearn.cluster import AgglomerativeClustering
            from sklearn.preprocessing import normalize
        except ImportError:
            logger.warning("Diarization dependencies missing.")
            return [0] * len(segments)

        # Cache check using hash
        cache_path = self._get_cache_path(audio_path, len(segments))
        if os.path.exists(cache_path):
             # Basic validity check could go here
            return self._load_cache(cache_path, len(segments))

        return self._compute_diarization(audio_path, segments, cache_path)

    def _get_cache_path(self, audio_path, seg_len):
        h = hashlib.md5()
        h.update(f"{audio_path}_{seg_len}".encode()) # Include seg_len in hash to invalidate if segments change
        hash_id = h.hexdigest()
        return os.path.join("/home/appuser/.cache/embeddings", f"{hash_id}.pkl")

    def _load_cache(self, path, expected_len):
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
                labels = data.get('labels')
                if labels and len(labels) == expected_len:
                    logger.info("Loaded diarization from cache.")
                    return labels
        except (IOError, pickle.UnpicklingError, EOFError, KeyError) as e:
            logger.debug(f"Cache load failed for {path}: {e}")
        except Exception as e:
            logger.warning(f"Unexpected cache error: {e}")
        return None

    def _compute_diarization(self, audio_path, segments, cache_path):
        import torch
        import torchaudio
        from speechbrain.inference.speaker import EncoderClassifier
        import numpy as np
        from sklearn.cluster import AgglomerativeClustering
        from sklearn.preprocessing import normalize
        
        logger.info(f"Starting IMPROVED Diarization on {self.device.upper()}...")
        
        try:
            # Init Model
            if not self.embedding_model:
                # Map 'cuda' to 'cuda' and 'cpu' to 'cpu'
                run_opts = {"device": "cuda"} if self.device == "cuda" and torch.cuda.is_available() else {"device": "cpu"}
                
                self.embedding_model = EncoderClassifier.from_hparams(
                    source="speechbrain/spkrec-ecapa-voxceleb", 
                    savedir="/home/appuser/.cache/speechbrain_checkpoints",
                    run_opts=run_opts
                )
            
            # Load Audio (Torchaudio is faster and handles resampling)
            wav, fs = torchaudio.load(audio_path)
            
            # Convert to Mono
            if wav.shape[0] > 1:
                wav = wav.mean(dim=0, keepdim=True)
                
            # Resample if needed (SpeechBrain expects 16k)
            if fs != 16000:
                resampler = torchaudio.transforms.Resample(fs, 16000).to(wav.device)
                wav = resampler(wav)
                fs = 16000

            # Move to device
            if self.device == "cuda" and torch.cuda.is_available():
                wav = wav.cuda()
                
            embeddings = []
            valid_indices = []
            segment_energies = []
            
            # Compute Embeddings
            for i, seg in enumerate(segments):
                # Convert time to samples
                start = int(seg.start * fs)
                end = int(seg.end * fs)
                
                # Skip very short segments (<0.3s) - increased from 0.2s
                if end - start < 4800:  # 0.3s at 16kHz
                    continue
                
                # Verify bounds
                if start >= wav.shape[1]: continue
                end = min(end, wav.shape[1])
                
                # Extract crop
                crop = wav[:, start:end]
                
                # Calculate energy (RMS) to filter out silence/noise
                energy = torch.sqrt(torch.mean(crop ** 2)).item()
                
                # Skip segments with very low energy (likely silence)
                if energy < 0.01:  # Threshold for silence detection
                    continue
                
                # Encode
                # encode_batch expects (batch, time)
                # Ensure no grad
                with torch.no_grad():
                    emb = self.embedding_model.encode_batch(crop)
                    # Result is (batch, 1, emb_dim) -> squeeze to (emb_dim)
                    emb = emb.squeeze().cpu().numpy()
                    
                embeddings.append(emb)
                valid_indices.append(i)
                segment_energies.append(energy)
                
            if len(embeddings) < 2:
                logger.info("Not enough segments for clustering.")
                return [0] * len(segments)
                
            # Clustering Logic
            X = np.array(embeddings)
            
            # 1. Normalize (Cosine Similarity Prep)
            X_norm = normalize(X) 
            
            # 2. Agglomerative Clustering with IMPROVED Distance Threshold
            # CRITICAL CHANGE: Lowered from 0.8 to 0.5 for better speaker separation
            # Threshold 0.5 -> Cosine Sim ~0.875 (Good separation between speakers)
            # This prevents merging different speakers
            
            clusterer = AgglomerativeClustering(
                n_clusters=None,
                metric='euclidean',
                linkage='ward', 
                distance_threshold=0.5  # IMPROVED: Lowered from 0.8 to 0.5
            )
            
            labels = clusterer.fit_predict(X_norm)
            
            # Map back to original segments
            final_labels = [-1] * len(segments)
            for idx, lbl in zip(valid_indices, labels):
                final_labels[idx] = int(lbl)
                
            # 3. IMPROVED Smoothing (Post-Processing)
            # Use sliding window majority vote (window size 5)
            window_size = 5
            smoothed_labels = final_labels.copy()
            
            for j in range(len(final_labels)):
                # Get window around current position
                start_idx = max(0, j - window_size // 2)
                end_idx = min(len(final_labels), j + window_size // 2 + 1)
                window = final_labels[start_idx:end_idx]
                
                # Filter out -1 (invalid)
                valid_window = [l for l in window if l != -1]
                
                if valid_window:
                    # Majority vote
                    from collections import Counter
                    most_common = Counter(valid_window).most_common(1)[0][0]
                    smoothed_labels[j] = most_common

            # 4. Fill remaining -1 with forward fill
            last_known = 0
            for j in range(len(smoothed_labels)):
                if smoothed_labels[j] != -1:
                    last_known = smoothed_labels[j]
                else:
                    smoothed_labels[j] = last_known
            
            # Cache Result
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, 'wb') as f:
                pickle.dump({'labels': smoothed_labels}, f)
                
            num_speakers = len(set(smoothed_labels))
            logger.info(f"Diarization Complete. Detected {num_speakers} speakers (IMPROVED).")
            
            return smoothed_labels
            
        except Exception as e:
            logger.error(f"Diarization error: {e}", exc_info=True)
            return [0] * len(segments)
