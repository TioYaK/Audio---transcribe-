
import logging
import os
from faster_whisper import WhisperModel, BatchedInferencePipeline
from app.services.audio import AudioProcessor
from app.services.analysis import BusinessAnalyzer

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Serviço principal de transcrição de áudio usando Whisper."""
    
    def __init__(self, settings):
        self.settings = settings
        self.model = None
        self.batched_model = None
        self._load_model()
        
        # Sub-serviços
        self.audio_processor = AudioProcessor()
        self.analyzer = BusinessAnalyzer()

    def _load_model(self):
        """Carrega o modelo Whisper conforme configurações."""
        try:
            logger.info(f"Carregando Whisper: {self.settings.WHISPER_MODEL} ({self.settings.DEVICE})")
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
                    logger.info("Pipeline em lote habilitado.")
                except:
                    logger.warning("Pipeline em lote falhou. Usando padrão.")
        except Exception as e:
            logger.error(f"Falha ao carregar modelo: {e}")
            raise e

    def process_task(self, file_path: str, options: dict = {}, progress_callback=None, rules: list = None):
        """
        Orquestra o pipeline completo com cache distribuído:
        1. Verificar cache de transcrição
        2. Otimizar áudio (se necessário)
        3. Transcrever (se não em cache)
        4. Verificar cache de análise
        5. Analisar (se não em cache)
        """
        from app.services.cache_service import cache_service
        
        # 1. VERIFICAR CACHE DE TRANSCRIÇÃO
        cached_transcription = cache_service.get_transcription(file_path, options)
        if cached_transcription:
            logger.info(f"✓ Usando transcrição em cache para {os.path.basename(file_path)}")
            full_text = cached_transcription['text']
            info_dict = cached_transcription['info']
        else:
            # 2. Otimizar áudio
            optimized_path = self.audio_processor.enhance_audio(file_path)
            
            # 3. Transcrever
            segments, info = self._transcribe_audio(optimized_path, progress_callback)
            
            # 4. Formatar (sem diarização, sem timestamps)
            full_text = self._format_output(segments, [], False)
            
            # Armazenar info
            info_dict = {
                'language': info.language,
                'duration': info.duration
            }
            
            # Salvar transcrição no cache
            cache_service.set_transcription(
                file_path,
                {'text': full_text, 'info': info_dict},
                options,
                ttl=86400  # 24 horas
            )
            
            # Limpar arquivo otimizado
            if optimized_path != file_path and os.path.exists(optimized_path):
                try:
                    os.remove(optimized_path)
                    logger.debug(f"Arquivo temporário removido: {optimized_path}")
                except Exception as e:
                    logger.warning(f"Falha ao limpar {optimized_path}: {e}")
        
        # 5. VERIFICAR CACHE DE ANÁLISE
        cached_analysis = cache_service.get_analysis(full_text, rules)
        if cached_analysis:
            logger.info(f"✓ Usando análise em cache")
            analysis = cached_analysis
        else:
            # 6. Analisar
            analysis = self.analyzer.analyze(full_text, rules=rules)
            
            # Salvar análise no cache
            cache_service.set_analysis(
                full_text,
                analysis,
                rules,
                ttl=604800  # 7 dias
            )
        
        return {
            "text": full_text,
            "language": info_dict.get('language', 'unknown'),
            "duration": info_dict.get('duration', 0.0),
            "summary": analysis.get("summary"),
            "topics": analysis.get("topics")
        }

    def _transcribe_audio(self, path, cb):
        """Realiza a transcrição do áudio usando Whisper."""
        if self.batched_model:
            # Modelo em lote requer VAD ou clip_timestamps
            # Usando VAD com parâmetros menos agressivos
            segments, info = self.batched_model.transcribe(
                path, 
                batch_size=16, 
                word_timestamps=True,
                vad_filter=True,
                vad_parameters={
                    "threshold": 0.3,  # Menor = menos agressivo (padrão 0.5)
                    "min_speech_duration_ms": 100,  # Mínimo mais curto (padrão 250)
                    "min_silence_duration_ms": 1000,  # Silêncio maior para cortar (padrão 2000)
                    "speech_pad_ms": 200  # Mais preenchimento ao redor da fala (padrão 400)
                }
            )
        else:
            segments, info = self.model.transcribe(
                path, 
                beam_size=5, 
                language="pt", 
                vad_filter=False,  # Desabilitado: modelo padrão não precisa
                word_timestamps=True
            )
        
        # Coletar para progresso (faster-whisper retorna gerador)
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
        """Formata a saída da transcrição."""
        lines = []
        for i, seg in enumerate(segments):
            parts = []
            
            # Timestamp
            if use_timestamps:
                m = int(seg.start // 60)
                s = int(seg.start % 60)
                parts.append(f"[{m:02d}:{s:02d}]")
                
            # Falante
            if speakers and i < len(speakers):
                lbl = speakers[i]
                parts.append(f"[Pessoa {lbl+1}]" if lbl >= 0 else "[?]")
                
            parts.append(seg.text.strip())
            lines.append(" ".join(parts))
            
        return "\n".join(lines)
