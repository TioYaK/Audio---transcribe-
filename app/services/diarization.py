
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
        
        logger.info(f"Starting Diarization on {self.device.upper()}...")
        
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
            
            # Compute Embeddings
            for i, seg in enumerate(segments):
                # Convert time to samples
                start = int(seg.start * fs)
                end = int(seg.end * fs)
                
                # Skip very short segments (<0.2s) helps reducing noise clustering
                if end - start < 3200: 
                    continue
                
                # Verify bounds
                if start >= wav.shape[1]: continue
                end = min(end, wav.shape[1])
                
                # Extract crop
                crop = wav[:, start:end]
                
                # Encode
                # encode_batch expects (batch, time)
                # Ensure no grad
                with torch.no_grad():
                    emb = self.embedding_model.encode_batch(crop)
                    # Result is (batch, 1, emb_dim) -> squeeze to (emb_dim)
                    emb = emb.squeeze().cpu().numpy()
                    
                embeddings.append(emb)
                valid_indices.append(i)
                
            if len(embeddings) < 2:
                logger.info("Not enough segments for clustering.")
                return [0] * len(segments)
                
            # Clustering Logic
            X = np.array(embeddings)
            
            # 1. Normalize (Cosine Similarity Prep)
            X_norm = normalize(X) 
            
            # 2. Agglomerative Clustering with Distance Threshold (Auto Speaker Count)
            # Threshold Tuning:
            # Vectors are normalized to unit length.
            # Euclidean Distance = sqrt(2 * (1 - Cosine_Similarity))
            # 
            # Threshold 1.5 -> Cosine Sim -0.125 (Merges almost everything) -> BAD
            # Threshold 0.8 -> Cosine Sim 0.68  (Reasonable for distinct speakers)
            # Threshold 0.6 -> Cosine Sim 0.82  (Very strict, might split same person)
            
            clusterer = AgglomerativeClustering(
                n_clusters=None,
                metric='euclidean',
                linkage='ward', 
                distance_threshold=0.8 # TIGHTENED from 1.5 to 0.8 to force separation
            )
            
            # Alternate approach: If user wants specific count, we could swap params.
            # But currently we want "Best possible auto".
            
            labels = clusterer.fit_predict(X_norm)
            
            # Map back to original segments
            final_labels = [-1] * len(segments)
            for idx, lbl in zip(valid_indices, labels):
                final_labels[idx] = int(lbl)
                
            # 3. Smoothing (Post-Processing)
            # Algorithm: Rolling majority vote or simple neighbor fix
            # Simple: If A B A -> A A A
            for j in range(1, len(final_labels) - 1):
                prev = final_labels[j-1]
                curr = final_labels[j]
                next_l = final_labels[j+1]
                
                if prev != -1 and next_l != -1 and prev == next_l and curr != prev:
                    final_labels[j] = prev

            # Fill -1 (skipped short segments) with nearest neighbor
            # Forward pass
            last_known = 0
            for j in range(len(final_labels)):
                if final_labels[j] != -1:
                    last_known = final_labels[j]
                else:
                    final_labels[j] = last_known
            
            # Cache Result
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, 'wb') as f:
                pickle.dump({'labels': final_labels}, f)
                
            num_speakers = len(set(final_labels))
            logger.info(f"Diarization Complete. Detected {num_speakers} speakers.")
            
            return final_labels
            
        except Exception as e:
            logger.error(f"Diarization error: {e}", exc_info=True)
            return [0] * len(segments)
