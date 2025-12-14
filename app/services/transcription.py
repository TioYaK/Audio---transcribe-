
import logging
import os
from faster_whisper import WhisperModel, BatchedInferencePipeline
from app.services.audio import AudioProcessor
from app.services.diarization import DiarizationService
from app.services.analysis import BusinessAnalyzer

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self, settings):
        self.settings = settings
        self.model = None
        self.batched_model = None
        self._load_model()
        
        # Sub-services
        self.audio_processor = AudioProcessor()
        self.diarizer = DiarizationService(device=self.settings.DEVICE)
        self.analyzer = BusinessAnalyzer()

    def _load_model(self):
        try:
            logger.info(f"Loading Whisper: {self.settings.WHISPER_MODEL} ({self.settings.DEVICE})")
            content_root = os.environ.get('HF_HOME', '/home/appuser/.cache/huggingface')
            
            self.model = WhisperModel(
                self.settings.WHISPER_MODEL,
                device=self.settings.DEVICE,
                compute_type=self.settings.COMPUTE_TYPE,
                download_root=content_root
            )
            
            if self.settings.DEVICE == "cuda":
                try:
                    self.batched_model = BatchedInferencePipeline(model=self.model)
                    logger.info("Batched Pipeline enabled.")
                except:
                    logger.warning("Batched Pipeline failed. Using standard.")
        except Exception as e:
            logger.error(f"Model load failed: {e}")
            raise e

    def process_task(self, file_path: str, options: dict = {}, progress_callback=None, rules: list = None):
        """
        Orchestrates the full pipeline:
        1. Audio Optimize
        2. Transcribe
        3. Diarize
        4. Analyze
        """
        # 1. Optimize
        optimized_path = self.audio_processor.enhance_audio(file_path)
        
        # 2. Transcribe
        segments, info = self._transcribe_audio(optimized_path, progress_callback)
        
        # 3. Diarize (Re-enabled with improved clustering)
        use_diarization = options.get('diarization', True)
        speaker_labels = []
        if use_diarization:
             speaker_labels = self.diarizer.diarize(optimized_path, segments)
        
        # 4. Format (timestamps disabled)
        full_text = self._format_output(segments, speaker_labels, False)  # No timestamps
        
        # 5. Analyze
        analysis = self.analyzer.analyze(full_text, rules=rules)
        
        # Cleanup (AFTER diarization and analysis)
        if optimized_path != file_path and os.path.exists(optimized_path):
            try:
                os.remove(optimized_path)
                logger.info(f"Cleaned up temporary file: {optimized_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {optimized_path}: {e}")
            
        return {
            "text": full_text,
            "language": info.language,
            "duration": info.duration,
            "summary": analysis.get("summary"),
            "topics": analysis.get("topics")
        }

    def _transcribe_audio(self, path, cb):
        if self.batched_model:
            # Batched model requires VAD or clip_timestamps
            # Using VAD with less aggressive parameters
            segments, info = self.batched_model.transcribe(
                path, 
                batch_size=16, 
                word_timestamps=True,
                vad_filter=True,
                vad_parameters={
                    "threshold": 0.3,  # Lower = less aggressive (default 0.5)
                    "min_speech_duration_ms": 100,  # Shorter minimum (default 250)
                    "min_silence_duration_ms": 1000,  # Longer silence needed to cut (default 2000)
                    "speech_pad_ms": 200  # More padding around speech (default 400)
                }
            )
        else:
            segments, info = self.model.transcribe(
                path, 
                beam_size=5, 
                language="pt", 
                vad_filter=False,  # Disabled: standard model doesn't need it
                word_timestamps=True
            )
            
        # Collect for progress (simplification: faster-whisper is generator, 
        # so we iterate to consume and calculate progress if duration known)
        # BUT standard transcribe doesn't give info until generator starts? 
        # Actually faster-whisper returns (generator, info).
        
        results = []
        total_dur = info.duration or 1.0
        
        for seg in segments:
            results.append(seg)
            if cb:
                pct = int((seg.end / total_dur) * 100)
                cb(min(99, pct))
        
        if cb: cb(100)
        return results, info

    def _format_output(self, segments, speakers, use_timestamps):
        lines = []
        for i, seg in enumerate(segments):
            parts = []
            
            # Timestamp
            if use_timestamps:
                m = int(seg.start // 60)
                s = int(seg.start % 60)
                parts.append(f"[{m:02d}:{s:02d}]")
                
            # Speaker
            if speakers and i < len(speakers):
                lbl = speakers[i]
                parts.append(f"[Pessoa {lbl+1}]" if lbl >= 0 else "[?]")
                
            parts.append(seg.text.strip())
            lines.append(" ".join(parts))
            
        return "\n".join(lines)
