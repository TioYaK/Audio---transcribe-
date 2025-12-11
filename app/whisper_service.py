import logging
import concurrent.futures
import os
from faster_whisper import WhisperModel, BatchedInferencePipeline

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
        self.embedding_model = None # Cache for Diarization Model
        
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
        
        
        # Enable Batched Pipeline if on GPU for massive speedup
        if self.device == "cuda":
            try:
                logger.info("Initializing Batched Inference Pipeline for GPU acceleration...")
                self.batched_model = BatchedInferencePipeline(model=self.model)
            except Exception as e:
                logger.warning(f"Could not initialize Batched Pipeline: {e}. Fallback to standard.")
                self.batched_model = None
        else:
            self.batched_model = None
            logger.info("Using standard inference (CPU or Batching disabled).")

    def enhance_audio(self, input_path: str) -> str:
        """
        Enhances audio quality (Optimized for Speed):
        1. Standardize (FFmpeg) -> 16kHz Mono
        2. Normalize (FFmpeg loudnorm) - Fast and effective
        
        Removed 'noisereduce' and 'pydub' silence removal as they are 
        CPU bottlenecks. Whisper's native VAD handles silence much faster.
        """
        import subprocess
        import uuid
        
        # Temp paths
        final_output = f"{input_path}_opt_{uuid.uuid4().hex[:6]}.wav"
        
        try:
            logger.info("Starting Optimized Audio Pipeline (FFmpeg only)...")
            
            # Single pass FFmpeg: Convert to WAV 16k Mono AND Normalize
            # -ar 16000: Resample to 16k (Whisper native)
            # -ac 1: Mono
            # -af loudnorm: EBU R128 Loudness Normalization (better than peak)
            command = [
                "ffmpeg", "-y", "-i", input_path,
                "-ar", "16000", 
                "-ac", "1",
                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", 
                final_output
            ]
            
            # Run fast C++ binary
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            logger.info(f"Audio optimization complete: {final_output}")
            return final_output

        except Exception as e:
            logger.error(f"Audio enhancement failed: {e}", exc_info=True)
            return input_path # Fallback to original


    def transcribe(self, audio_file_path: str, options: dict = {}, progress_callback: callable = None) -> dict:
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
                 # Standard inference
                 segments, info = self.model.transcribe(
                     final_path, 
                     beam_size=5,
                     language="pt", # Force Portuguese to correct casing/spelling
                     vad_filter=True, # Remove silence hallucinations
                     initial_prompt="Conversa telefônica bancária sobre oferta de título de capitalização Bradesco. Termos: reais, agência, conta, senhor, senhora, autoriza."
                 )
            
            # Real-time progress tracking
            collected_segments = []
            total_duration = info.duration or 1.0 # Avoid division by zero
            
            for segment in segments:
                collected_segments.append(segment)
                # Update progress
                if progress_callback:
                    current_pct = int((segment.end / total_duration) * 100)
                    # Limit to 99% until fully done
                    progress_callback(min(99, current_pct))
                    
            segments = collected_segments
            if progress_callback: progress_callback(100)
            
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
            
            # Load model only if not cached
            if not self.embedding_model:
                logger.info(f"Loading SpeechBrain embedding model on CPU (First run)...")
                self.embedding_model = EncoderClassifier.from_hparams(
                    source="speechbrain/spkrec-ecapa-voxceleb", 
                    savedir="/root/.cache/speechbrain_checkpoints",
                    run_opts=run_opts
                )
            classifier = self.embedding_model

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
        Enhanced for Banking/Telemarketing context (Bradesco, Capitalização).
        """
        logger.info(f"Starting AI Analysis. Text length: {len(text) if text else 0}")
        if not text or len(text) < 50:
             logger.warning("Text too short for analysis (<50 chars).")
             return {"summary": "Texto muito curto para análise.", "topics": ""}

        try:
            # Lazy imports
            logger.info("Importing NLP libraries...")
            import nltk
            import re
            from sumy.parsers.plaintext import PlaintextParser
            from sumy.nlp.tokenizers import Tokenizer
            # Switch to LexRank - usually better for key sentence extraction in conversations
            from sumy.summarizers.lex_rank import LexRankSummarizer 
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
            
            # --- 1. Hybrid Context-Aware Summary ---
            logger.info("Generating Summary (LexRank + KW)...")
            parser = PlaintextParser.from_string(text, Tokenizer(LANGUAGE))
            stemmer = Stemmer(LANGUAGE)
            summarizer = LexRankSummarizer(stemmer)
            summarizer.stop_words = get_stop_words(LANGUAGE)
            
            # A. Standard Extraction (Stats)
            # Increase count slightly to 4
            lex_sentences = summarizer(parser.document, 4)
            final_sentences = list(lex_sentences)
            
            # B. Critical Context Injection (Heuristic)
            # Look for specific transactional sentences often missed by LSA/LexRank
            critical_keywords = [
                "bradesco", "capitalização", "título", "sorteio", 
                "autoriza", "confirma", "valor", "reais", "desconto", 
                "parcela", "seguro", "proposta", "aceito", "não quero"
            ]
            
            # Get all sentences from document to scan
            # (parser.document.sentences returns a tuple of sentences)
            all_sentences = [s for s in parser.document.sentences]
            
            # Heuristic: Find first 2 sentences containing critical keywords that aren't already in summary
            added_critical = 0
            existing_indices = {s._text for s in final_sentences} # Use text hash or content
            
            for sent in all_sentences:
                if added_critical >= 2: break # Limit extras
                txt_lower = sent._text.lower()
                
                # Check for currency specifically (R$ 20,00 etc)
                has_money = bool(re.search(r'r\$\s?\d+', txt_lower))
                
                if has_money or any(k in txt_lower for k in critical_keywords):
                    if sent._text not in existing_indices:
                        # Append to explicit list
                        final_sentences.append(sent)
                        existing_indices.add(sent._text)
                        added_critical += 1
            
            # Sort sentences by appearance order to maintain conversation flow
            # Sumy sentences have no simple index, but we can match with original list
            # Optim: fast mapping
            sent_map = {s._text: i for i, s in enumerate(all_sentences)}
            final_sentences.sort(key=lambda s: sent_map.get(s._text, 0))

            summary = " ".join([str(s) for s in final_sentences])
            logger.info(f"Summary generated: {summary[:50]}...")
            
            # --- 2. Topics (TF-IDF) ---
            logger.info("Extracting Topics (TF-IDF)...")
            pt_stopwords = nltk.corpus.stopwords.words('portuguese')
            # Add fillers and common verbiage
            pt_stopwords.extend([
                'então', 'assim', 'aí', 'coisa', 'gente', 'né', 'tá', 'bom', 'sim', 'não',
                'pode', 'vamos', 'agora', 'senhor', 'senhora', 'falar', 'ligação'
            ])
            
            # Boost specific domain words in vectorizer? 
            # TF-IDF naturally handles frequent words, but we can ensure max_features captures enough
            vectorizer = TfidfVectorizer(stop_words=pt_stopwords, max_features=10) # Increased to 10
            
            try:
                vectorizer.fit_transform([text])
                feature_names = vectorizer.get_feature_names_out()
                topics = ", ".join(feature_names)
            except ValueError:
                # Can happen if empty vocab after stop words
                topics = "Sem tópicos relevantes"
                
            logger.info(f"Topics extracted: {topics}")
            
            return {"summary": summary, "topics": topics}

        except Exception as e:
            logger.error(f"AI Analysis failed at step: {e}", exc_info=True)
            return {"summary": "Erro na geração do resumo.", "topics": ""}
