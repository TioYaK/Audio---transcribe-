
"""
Worker de processamento de transcrições.
Gerencia a fila de tarefas e coordena o pipeline de transcrição.
"""
import asyncio
from time import perf_counter
import os
from app import crud
from app.database import SessionLocal
from app.core.config import logger
from app.core.queue import task_queue
from app.core.services import whisper_service

# Métricas
from app.core.metrics import (
    record_transcription,
    record_error,
    file_size_bytes,
    audio_duration_seconds
)


def process_transcription(task_id: str, file_path: str, options: dict = {}):
    """Processa uma tarefa de transcrição de áudio."""
    background_db = SessionLocal()
    task_store = crud.TaskStore(background_db)
    
    try:
        logger.info(f"Iniciando processamento da tarefa {task_id}")
        
        # VALIDAÇÃO: Verificar se o arquivo existe antes de processar
        if not os.path.exists(file_path):
            error_msg = f"Arquivo não encontrado: {file_path} (excluído ou movido)"
            logger.error(f"Tarefa {task_id} falhou: {error_msg}")
            task_store.update_status(task_id, "failed", error_message=error_msg)
            
            # MÉTRICAS: Registrar erro
            record_error('file_not_found', 'transcription')
            record_transcription('error', 0)
            return
        
        # MÉTRICAS: Registrar tamanho do arquivo
        file_size = os.path.getsize(file_path)
        file_size_bytes.observe(file_size)
        
        task_store.update_status(task_id, "processing")
        
        start_ts = perf_counter()
        
        # PERFORMANCE: Redução de ruído desativada para velocidade
        # Usar arquivo original diretamente
        cleaned_audio_path = file_path
        logger.info(f"Usando arquivo de áudio (sem redução de ruído): {cleaned_audio_path}")
        
        def update_prog(pct):
            task_store.update_progress(task_id, pct)
        
        # Buscar Regras de Análise
        rules = []
        try:
            from app.models import AnalysisRule
            active_rules = background_db.query(AnalysisRule).filter(AnalysisRule.is_active == True).all()
            rules = [{'category': r.category, 'keywords': r.keywords} for r in active_rules]
        except Exception as e:
            logger.warning(f"Não foi possível buscar regras de análise: {e}")

        result = whisper_service.process_task(cleaned_audio_path, options=options, progress_callback=update_prog, rules=rules)
        processing_time = perf_counter() - start_ts
        
        # MÉTRICAS: Registrar duração do áudio
        audio_duration_seconds.observe(result.get("duration", 0))
        
        # Obter texto original
        original_text = result.get("text", "")
        
        # PERFORMANCE: Correção ortográfica desativada para velocidade
        # Whisper já produz transcrições de alta qualidade
        logger.info(f"Correção ortográfica: DESATIVADA (otimização de performance)")
        
        # Salvar Resultado
        task_store.save_result(
            task_id=task_id,
            text=original_text,
            language=result.get("language", "unknown"),
            duration=result.get("duration", 0.0),
            processing_time=processing_time,
            summary=result.get("summary"),
            topics=result.get("topics")
        )
        
        logger.info(f"Tarefa {task_id} concluída com sucesso.")
        
        # MÉTRICAS: Registrar transcrição bem-sucedida
        record_transcription(
            status='success',
            duration=processing_time,
            model=options.get('model', 'medium'),
            device='cuda' if 'cuda' in str(options.get('device', 'cuda')) else 'cpu'
        )
        
        # LIMPEZA: Liberar RAM e memória GPU após conclusão da tarefa
        try:
            from app.utils.memory_cleanup import cleanup_after_task
            cleanup_after_task(task_id, clear_gpu=True)
        except Exception as e:
            logger.warning(f"Limpeza pós-tarefa falhou: {e}")

    except Exception as e:
        processing_time = perf_counter() - start_ts
        logger.error(f"Tarefa {task_id} falhou: {e}")
        task_store.update_status(task_id, "failed", error_message=str(e))
        
        # MÉTRICAS: Registrar transcrição com falha
        record_transcription('error', processing_time)
        record_error('processing_error', 'transcription')
    finally:
        background_db.close()


# task_consumer não é mais necessário com RQ
# A função process_transcription é chamada diretamente pelo worker RQ
