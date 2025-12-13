
import logging
import os
import pickle
import hashlib
from typing import List, Optional

logger = logging.getLogger(__name__)

class DiarizationService:
    def __init__(self):
        self.embedding_model = None
        
    def diarize(self, audio_path: str, segments) -> List[int]:
        """
        Performs speaker diarization on the segments.
        Returns a list of speaker IDs corresponding to each segment.
        """
        # Lazy Loading
        try:
            import torch
            from speechbrain.inference.speaker import EncoderClassifier
            import numpy as np
            from sklearn.cluster import AgglomerativeClustering
            import soundfile as sf
        except ImportError:
            logger.warning("Diarization dependencies missing.")
            return [0] * len(segments)

        cache_path = self._get_cache_path(audio_path)
        if os.path.exists(cache_path):
            return self._load_cache(cache_path, len(segments))

        return self._compute_diarization(audio_path, segments, cache_path)

    def _get_cache_path(self, audio_path):
        # Hash text
        h = hashlib.md5()
        h.update(audio_path.encode())
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
        except: pass
        return None

    def _compute_diarization(self, audio_path, segments, cache_path):
        import torch
        from speechbrain.inference.speaker import EncoderClassifier
        import numpy as np
        from sklearn.cluster import AgglomerativeClustering
        import soundfile as sf
        
        logger.info("Starting Diarization (CPU)...")
        
        if not self.embedding_model:
             self.embedding_model = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb", 
                savedir="/home/appuser/.cache/speechbrain_checkpoints",
                run_opts={"device": "cpu"}
            )
        
        # Load Audio (Soundfile)
        try:
            signal, fs = sf.read(audio_path)
            if len(signal.shape) > 1: signal = signal[:, 0] # Mono
            if fs != 16000:
                # Basic resample fallback if not 16k?
                # Ideally AudioProcessor ensures 16k.
                pass 
            
            signal_t = torch.tensor(signal).float()
            
            embeddings = []
            valid_indices = []
            
            for i, seg in enumerate(segments):
                start = int(seg.start * fs)
                end = int(seg.end * fs)
                if end - start < 3200: continue # <0.2s
                
                crop = signal_t[start:end].unsqueeze(0)
                emb = self.embedding_model.encode_batch(crop)
                embeddings.append(emb.squeeze().numpy())
                valid_indices.append(i)
                
            if len(embeddings) < 2:
                return [0] * len(segments)
                
            # Clustering
            X = np.array(embeddings)
            # Normalize?
            clusterer = AgglomerativeClustering(n_clusters=2) # Simple 2 speakers
            labels = clusterer.fit_predict(X)
            
            final_labels = [-1] * len(segments)
            for idx, lbl in zip(valid_indices, labels):
                final_labels[idx] = int(lbl)
                
            # Cache
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, 'wb') as f:
                pickle.dump({'labels': final_labels}, f)
                
            return final_labels
            
        except Exception as e:
            logger.error(f"Diarization error: {e}")
            return [0] * len(segments)
