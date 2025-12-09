import logging
import concurrent.futures
import os
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

class WhisperService:
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        """
        Initializes the Whisper model.
        
        Args:
            model_size: Size of the model (tiny, base, small, medium, large)
            device: Device to run on (cpu, cuda)
            compute_type: Quantization type (int8, float16, etc.)
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        # Load model immediately to fail fast if there are issues
        self.load_model()

    def load_model(self):
        try:
            logger.info(f"Loading Whisper model: {self.model_size} on {self.device}...")
            # download_root can be specified if needed, but we rely on environment/defaults
            # which we mapped to /root/.cache/huggingface in docker-compose
            self.model = WhisperModel(
                self.model_size, 
                device=self.device, 
                compute_type=self.compute_type,
                # Enable Flash Attention 2 if on CUDA (requires matching compute capability, usually safe on 4060)
                flash_attention=True if self.device == "cuda" else False,
                cpu_threads=4
            )
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise e
        
        # Initialize Batched Pipeline for GPU
        if self.device == "cuda":
            try:
                from faster_whisper import BatchedInferencePipeline
                self.batched_model = BatchedInferencePipeline(model=self.model)
                logger.info("BatchedInferencePipeline initialized for GPU acceleration.")
            except ImportError:
                logger.warning("BatchedInferencePipeline not available. Using standard inference.")
                self.batched_model = None
            except Exception as e:
                logger.warning(f"Failed to initialize BatchedInferencePipeline: {e}")
                self.batched_model = None

    def preprocess_audio(self, input_path: str) -> str:
        """
        Applies noise reduction (Bandpass 200-3400Hz) and normalization.
        Returns path to processed file (temp).
        """
        import subprocess
        import uuid
        
        output_path = f"{input_path}_proc_{uuid.uuid4().hex[:6]}.wav"
        
        # Phone band filter + Normalization
        # highpass=f=200,lowpass=f=3400: Typical voice band
        command = [
            "ffmpeg", "-y", "-i", input_path,
            "-af", "highpass=f=200,lowpass=f=3400,loudnorm",
            "-ar", "16000", "-ac", "1", # Convert to mono 16k for Whisper
            output_path
        ]
        
        try:
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg preprocessing failed: {e}")
            return input_path # Fallback to original

    def transcribe(self, audio_file_path: str) -> dict:
        """
        Transcribes audio. Applies preprocessing first.
        """
        if not self.model:
            raise RuntimeError("Model not loaded")

        if not os.path.exists(audio_file_path):
             raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        # Preprocess first (Noise Reduction)
        processed_path = self.preprocess_audio(audio_file_path)
        final_path = processed_path if processed_path != audio_file_path else audio_file_path
        
        try:
            if hasattr(self, 'batched_model') and self.batched_model:
                 segments, info = self.batched_model.transcribe(final_path, batch_size=16)
            else:
                 segments, info = self.model.transcribe(final_path, beam_size=5)
            
            # Format text with timestamps
            formatted_lines = []
            for segment in segments:
                start = segment.start
                # Simple formatting
                mm = int(start // 60)
                ss = int(start % 60)
                time_str = f"[{mm:02d}:{ss:02d}]"
                formatted_lines.append(f"{time_str} {segment.text.strip()}")

            full_text = "\n".join(formatted_lines)
            
            return {
                "text": full_text,
                "language": info.language,
                "duration": info.duration
            }
        except Exception as e:
            logger.error(f"Error during transcription of {audio_file_path}: {e}")
            raise e
        finally:
            # Cleanup processed file
            if processed_path != audio_file_path and os.path.exists(processed_path):
                try:
                    os.remove(processed_path)
                except: pass

    async def transcribe_async(self, audio_file_path: str):
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self.transcribe, audio_file_path)

    def _get_speaker_embedding(self, audio_path: str, segments):
        """
        Extracts embeddings for each segment using SpeechBrain.
        """
        try:
            import torchaudio
            import torch
            from speechbrain.inference.speakers import EncoderClassifier
            import numpy as np
            from sklearn.cluster import KMeans

            # Load model (cached)
            # Use 'cpu' or 'cuda' for torch
            run_opts = {"device": "cuda"} if self.device == "cuda" else {"device": "cpu"}
            classifier = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb", 
                savedir="/root/.cache/speechbrain_checkpoints",
                run_opts=run_opts
            )

            # Load full audio
            signal, fs = torchaudio.load(audio_path)
            
            # Resample if needed (ECAPA expects 16k)
            if fs != 16000:
                resampler = torchaudio.transforms.Resample(fs, 16000)
                signal = resampler(signal)
            
            # Ensure mono for embedding extraction (use first channel)
            if signal.shape[0] > 1:
                signal = signal[0:1, :]

            embeddings = []
            valid_indices = []

            for i, seg in enumerate(segments):
                # Calculate sample indices (16k sample rate)
                start_sample = int(seg.start * 16000)
                end_sample = int(seg.end * 16000)
                
                # Check bounds
                if end_sample > signal.shape[1]: end_sample = signal.shape[1]
                if start_sample >= end_sample: continue # Skip invalid

                # Crop
                crop = signal[:, start_sample:end_sample]
                
                # Skip very short segments (<0.5s) to avoid noise
                if crop.shape[1] < 8000: 
                    embeddings.append(None)
                    continue

                # Encode
                emb = classifier.encode_batch(crop)
                # Ensure numpy array
                emb_np = emb.squeeze().cpu().numpy()
                embeddings.append(emb_np)
                valid_indices.append(i)

            # Clustering
            # Filter None
            clean_embs = [e for e in embeddings if e is not None]
            
            if len(clean_embs) < 2:
                # Not enough data to cluster
                return [0] * len(segments)
            
            # Matrix
            X = np.array(clean_embs)
            
            # 2 Speakers
            kmeans = KMeans(n_clusters=min(2, len(clean_embs)), random_state=0, n_init=10)
            labels = kmeans.fit_predict(X)
            
            # Map back to all segments
            final_labels = []
            label_idx = 0
            for i in range(len(segments)):
                if embeddings[i] is None:
                    final_labels.append(-1) # Unknown
                else:
                    final_labels.append(labels[label_idx])
                    label_idx += 1
            
            return final_labels

        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            return None # Fallback

    def transcribe(self, audio_file_path: str) -> dict:
        """
        Transcribes audio with Diarization and Preprocessing.
        """
        if not self.model:
            raise RuntimeError("Model not loaded")

        if not os.path.exists(audio_file_path):
             raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        # Preprocess (Noise Reduction)
        processed_path = self.preprocess_audio(audio_file_path)
        final_path = processed_path if processed_path != audio_file_path else audio_file_path
        
        try:
            # 1. Transcribe
            if hasattr(self, 'batched_model') and self.batched_model:
                 segments_gen, info = self.batched_model.transcribe(final_path, batch_size=16)
            else:
                 segments_gen, info = self.model.transcribe(final_path, beam_size=5)
            
            # Consume generator
            segments = list(segments_gen)
            
            # 2. Diarization (Token-Free via SpeechBrain)
            # Only run if we have segments
            speaker_labels = [0] * len(segments)
            if len(segments) > 0:
                logger.info("Starting Diarization...")
                # Pass ORIGINAL file (better quality than processed?) or processed?
                # Processed has noise reduction, likely better for embeddings.
                labels = self._get_speaker_embedding(final_path, segments)
                if labels:
                    speaker_labels = labels

            # 3. Format Output
            formatted_lines = []
            current_speaker = None
            
            # Speaker Map (0 -> Pessoa 1, 1 -> Pessoa 2)
            # Try to guess who is who? Impossible without profile.
            # Just label consistently.
            
            for i, segment in enumerate(segments):
                start = segment.start
                mm = int(start // 60)
                ss = int(start % 60)
                time_str = f"[{mm:02d}:{ss:02d}]"
                
                spk_idx = speaker_labels[i]
                if spk_idx == -1:
                    spk_tag = "[?]"
                else:
                    spk_tag = f"[Pessoa {spk_idx + 1}]"
                
                formatted_lines.append(f"{time_str} {spk_tag}: {segment.text.strip()}")

            full_text = "\n".join(formatted_lines)
            
            return {
                "text": full_text,
                "language": info.language,
                "duration": info.duration
            }
        except Exception as e:
            logger.error(f"Error during transcription of {audio_file_path}: {e}")
            raise e
        finally:
            if processed_path != audio_file_path and os.path.exists(processed_path):
                try: os.remove(processed_path)
                except: pass
