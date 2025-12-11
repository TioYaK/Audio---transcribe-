import logging
import concurrent.futures
import os
from faster_whisper import WhisperModel

# CRITICAL: Patch torchaudio BEFORE any speechbrain imports
# This must be at module level to work
try:
    import torchaudio
    if not hasattr(torchaudio, 'list_audio_backends'):
        torchaudio.list_audio_backends = lambda: []
except ImportError:
    pass

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
                # Disabled due to "not supported" error reported by user
                flash_attention=False,
                cpu_threads=4
            )
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise e
        
        
        # Disable Batched Pipeline to save GPU memory (prevents OOM on 8GB GPUs)
        self.batched_model = None
        logger.info("Using standard inference (batching disabled to prevent OOM).")

    def enhance_audio(self, input_path: str) -> str:
        """
        Enhances audio quality:
        1. Standardize (FFmpeg)
        2. Remove Noise (noisereduce)
        3. Remove Silence (pydub)
        4. Normalize (pydub)
        Returns path to enhanced file.
        """
        import subprocess
        import uuid
        import numpy as np
        from scipy.io import wavfile
        import noisereduce as nr
        from pydub import AudioSegment, effects
        from pydub.silence import split_on_silence
        
        # Temp paths
        temp_wav = f"{input_path}_temp_{uuid.uuid4().hex[:6]}.wav"
        final_output = f"{input_path}_enhanced_{uuid.uuid4().hex[:6]}.wav"
        
        try:
            logger.info("Starting Audio Enhancement Pipeline...")
            
            # 1. Standardize processing (Convert to Mono 16kHz WAV)
            # We assume input might be mp3/m4a/etc, so we convert to wav first
            command = [
                "ffmpeg", "-y", "-i", input_path,
                "-ar", "16000", "-ac", "1", 
                temp_wav
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 2. Noise Reduction (Spectral Gating)
            # Load data
            rate, data = wavfile.read(temp_wav)
            # Perform noise reduction
            # stationary=False (default) assumes noise changes, but for general background hiss, stationary=True is faster/better?
            # We'll use default with conservative settings to avoid 'underwater' artifact
            reduced_noise = nr.reduce_noise(y=data, sr=rate, prop_decrease=0.75, n_std_thresh_stationary=1.5)
            
            # Write back for Pydub
            wavfile.write(temp_wav, rate, reduced_noise)
            
            # 3. Silence Removal & Normalization
            audio = AudioSegment.from_wav(temp_wav)
            
            # Normalize first (Peak normalization)
            audio = effects.normalize(audio)
            
            # Remove long silences (>800ms)
            logger.info("Removing silence...")
            chunks = split_on_silence(
                audio,
                min_silence_len=800,
                silence_thresh=audio.dBFS - 16, # -16dB relative to peak
                keep_silence=400 # Keep 400ms to sound natural
            )
            
            if chunks:
                logger.info(f"Silence removal: reduced from {len(audio)}ms to {sum(len(c) for c in chunks)}ms")
                combined = chunks[0]
                for chunk in chunks[1:]:
                    combined += chunk
                audio = combined
            else:
                logger.warning("No logic chunks found after silence split, keeping original.")

            # Final export
            audio.export(final_output, format="wav")
            
            # Cleanup temp
            if os.path.exists(temp_wav): os.remove(temp_wav)
            
            logger.info(f"Audio enhancement complete: {final_output}")
            return final_output

        except Exception as e:
            logger.error(f"Audio enhancement failed: {e}", exc_info=True)
            # Cleanup
            if os.path.exists(temp_wav): os.remove(temp_wav)
            return input_path # Fallback to original


    def transcribe(self, audio_file_path: str, options: dict = {}) -> dict:
        """
        Transcribes audio. Applies preprocessing first.
        options: {'timestamp': bool, 'diarization': bool}
        """
        if not self.model:
            raise RuntimeError("Model not loaded")

        if not os.path.exists(audio_file_path):
             raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        # Preprocess first (Noise Reduction & Enhancement)
        processed_path = self.enhance_audio(audio_file_path)
        
        # Audio Replacement: Overwrite original with processed audio
        if processed_path != audio_file_path:
             try:
                 import shutil
                 # Move/Overwrite logic
                 shutil.move(processed_path, audio_file_path)
                 logger.info(f"Overwrote original file {audio_file_path} with processed version.")
             except Exception as e:
                 logger.error(f"Failed to overwrite original file: {e}")
                 # If move fails, try to use processed_path if exists, else original
                 if os.path.exists(processed_path):
                     pass # Continue using processed_path
                 else:
                     processed_path = audio_file_path
        
        # Now processed_path points to the audio we want to transcribe
        # But wait, if we moved it, processed_path no longer exists at old location
        # processed_path IS audio_file_path now.
        final_path = audio_file_path
        
        try:
            if hasattr(self, 'batched_model') and self.batched_model:
                 segments, info = self.batched_model.transcribe(final_path, batch_size=16)
            else:
                 segments, info = self.model.transcribe(final_path, beam_size=5)
            
            # Consume generator
            segments = list(segments)
            
            # 2. Diarization
            speaker_labels = [0] * len(segments)
            use_diarization = False # options.get('diarization', True) # Temporarily disabled
            
            if len(segments) > 0 and use_diarization:
                logger.info("Starting Diarization...")
                labels = self._get_speaker_embedding(final_path, segments)
                if labels:
                    speaker_labels = labels

            # 3. Format Output
            formatted_lines = []
            
            for i, segment in enumerate(segments):
                use_timestamp = options.get('timestamp', True)
                
                start = segment.start
                mm = int(start // 60)
                ss = int(start % 60)
                # Never show [00:00] - only show timestamp if enabled AND not zero
                if use_timestamp and (mm > 0 or ss > 0):
                    time_str = f"[{mm:02d}:{ss:02d}]"
                else:
                    time_str = ""

                spk_tag = ""
                if use_diarization:
                    spk_idx = speaker_labels[i]
                    if spk_idx == -1:
                        spk_tag = "[?]"
                    else:
                        spk_tag = f"[Pessoa {spk_idx + 1}]"
                
                # DEBUG: Log first segment to verify logic
                if i == 0:
                    logger.info(f"First segment: use_timestamp={use_timestamp}, mm={mm}, ss={ss}, time_str='{time_str}', spk_tag='{spk_tag}'")
                # Combine parts: [Time] [Speaker]: Text
                # Filter empty parts
                parts = [p for p in [time_str, spk_tag] if p]
                prefix = " ".join(parts)
                if prefix:
                     formatted_lines.append(f"{prefix}: {segment.text.strip()}")
                else:
                     formatted_lines.append(segment.text.strip())

            full_text = "\n".join(formatted_lines)
            
            # 4. Generate AI Analysis
            analysis = self.generate_analysis(full_text)
            
            return {
                "text": full_text,
                "language": info.language,
                "duration": info.duration,
                "summary": analysis.get("summary"),
                "topics": analysis.get("topics")
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
        Runs on CPU to avoid allocating VRAM alongside Whisper.
        """
        try:
            import torch
            from speechbrain.inference.speaker import EncoderClassifier
            import numpy as np
            from sklearn.cluster import AgglomerativeClustering
            
            # Force CPU for embedding model to prevent OOM
            run_opts = {"device": "cpu"} 
            
            logger.info(f"Loading SpeechBrain embedding model on CPU...")
            classifier = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb", 
                savedir="/root/.cache/speechbrain_checkpoints",
                run_opts=run_opts
            )

            # Load full audio using soundfile directly (bypass torchaudio backend issues)
            import soundfile as sf
            
            try:
                data, samplerate = sf.read(audio_path)
                # Ensure float32
                if data.dtype != 'float32':
                    data = data.astype('float32')
                
                signal = torch.from_numpy(data)
                
                # Handle shapes: (frames, channels) -> (channels, frames)
                if signal.ndim == 1:
                    signal = signal.unsqueeze(0) # (1, frames)
                else:
                    signal = signal.t()
                    
                fs = samplerate
                
            except Exception as e:
                logger.error(f"Soundfile load failed: {e}")
                # Last resort fallback
                signal, fs = torchaudio.load(audio_path)

            # Resample if needed (ECAPA expects 16k)
            if fs != 16000:
                resampler = torchaudio.transforms.Resample(fs, 16000)
                signal = resampler(signal)
            
            # Ensure mono for embedding extraction (use first channel)
            if signal.shape[0] > 1:
                signal = signal[0:1, :]

            embeddings = []
            
            logger.info(f"Extracting embeddings for {len(segments)} segments...")

            for i, seg in enumerate(segments):
                # Calculate sample indices (16k sample rate)
                start_sample = int(seg.start * 16000)
                end_sample = int(seg.end * 16000)
                
                # Check bounds
                if end_sample > signal.shape[1]: end_sample = signal.shape[1]
                if start_sample >= end_sample: continue # Skip invalid

                # Crop
                crop = signal[:, start_sample:end_sample]
                
                # Skip very short segments (<0.2s) to avoid noise
                if crop.shape[1] < 3200: 
                    embeddings.append(None)
                    continue

                # Encode
                try:
                    emb = classifier.encode_batch(crop)
                    # Ensure numpy array
                    emb_np = emb.squeeze().cpu().numpy()
                    embeddings.append(emb_np)
                except Exception as e:
                    logger.warning(f"Failed to encode segment {i}: {e}")
                    embeddings.append(None)

            # Clustering
            # Filter None
            clean_embs = [e for e in embeddings if e is not None]
            
            # DEBUG: Detailed embedding stats
            logger.info(f"Embedding stats: Total Segments={len(segments)}, Valid Embeddings={len(clean_embs)}")
            
            if len(clean_embs) < 2:
                logger.warning(f"Not enough valid embeddings for clustering (Found {len(clean_embs)}). Audio might be too short or silent.")
                return [0] * len(segments)
            
            # Matrix
            X = np.array(clean_embs)
            
            # Use AgglomerativeClustering with Cosine Similarity (better for embeddings)
            # distance_threshold is heuristic; 0.7-0.9 usually works for ECAPA-TDNN cosine distance
            # shorter distance = strictly same speaker. larger = loose.
            # However, since we want to force distinct speakers if possible, we can stick to n_clusters
            # But the user complains about merging. 
            # Let's try n_clusters=2 fixed first given the usecase often implies 2 speakers, 
            # OR use logic to find best k. Sticking to 2 for stability as requested "diferenciar pessoas"
            
            try:
                # Normalizing embeddings helps cosine distance metrics
                from sklearn.preprocessing import normalize
                X_norm = normalize(X)
                
                # Linkage=average works well for speaker clustering
                clusterer = AgglomerativeClustering(n_clusters=2, metric='cosine', linkage='average')
                labels = clusterer.fit_predict(X_norm)
                
                # DEBUG: Cluster distribution
                unique, counts = np.unique(labels, return_counts=True)
                dist = dict(zip(unique, counts))
                logger.info(f"Cluster distribution: {dist}") # e.g. {0: 50, 1: 40} -> Good separation
                
            except Exception as e:
                logger.error(f"Clustering failed: {e}. Fallback to single speaker.")
                return [0] * len(segments)

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

        except ImportError as e:
             logger.error(f"Missing dependency for diarization: {e}. Check requirements.")
             return None
        except Exception as e:
            logger.error(f"Diarization CRASHED: {e}", exc_info=True)
            return None # Fallback



    def generate_analysis(self, text: str) -> dict:
        """
        Generates summary and topics using local NLP (Sumy + Scikit-learn).
        """
        logger.info(f"Starting AI Analysis. Text length: {len(text) if text else 0}")
        if not text or len(text) < 50:
             logger.warning("Text too short for analysis (<50 chars).")
             return {"summary": "Texto muito curto para análise.", "topics": ""}

        try:
            # Lazy imports
            logger.info("Importing NLP libraries...")
            import nltk
            from sumy.parsers.plaintext import PlaintextParser
            from sumy.nlp.tokenizers import Tokenizer
            from sumy.summarizers.lsa import LsaSummarizer
            from sumy.nlp.stemmers import Stemmer
            from sumy.utils import get_stop_words
            from sklearn.feature_extraction.text import TfidfVectorizer

            # Resources Check
            try:
                nltk.data.find('tokenizers/punkt')
                nltk.data.find('tokenizers/punkt_tab')
            except LookupError:
                logger.warning("Downloading missing NLTK resources...")
                nltk.download('punkt', quiet=True)
                nltk.download('punkt_tab', quiet=True)
            
            try:
                 nltk.data.find('corpora/stopwords')
            except LookupError:
                 nltk.download('stopwords', quiet=True)

            LANGUAGE = "portuguese"
            
            # 1. Summary (LSA)
            logger.info("Generating Summary (LSA)...")
            parser = PlaintextParser.from_string(text, Tokenizer(LANGUAGE))
            stemmer = Stemmer(LANGUAGE)
            summarizer = LsaSummarizer(stemmer)
            summarizer.stop_words = get_stop_words(LANGUAGE)
            
            summary_sentences = summarizer(parser.document, 3) # Top 3
            summary = " ".join([str(s) for s in summary_sentences])
            logger.info(f"Summary generated: {summary[:50]}...")
            
            # 2. Topics (TF-IDF Keywords)
            logger.info("Extracting Topics (TF-IDF)...")
            pt_stopwords = nltk.corpus.stopwords.words('portuguese')
            # Add common Filler words
            pt_stopwords.extend(['então', 'assim', 'aí', 'coisa', 'gente', 'né', 'tá'])
            
            vectorizer = TfidfVectorizer(stop_words=pt_stopwords, max_features=8)
            vectorizer.fit_transform([text])
            feature_names = vectorizer.get_feature_names_out()
            
            topics = ", ".join(feature_names)
            logger.info(f"Topics extracted: {topics}")
            
            return {"summary": summary, "topics": topics}

        except Exception as e:
            logger.error(f"AI Analysis failed at step: {e}", exc_info=True)
            return {"summary": "Erro na geração do resumo.", "topics": ""}
