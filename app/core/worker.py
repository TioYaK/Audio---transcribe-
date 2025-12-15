
import asyncio
from time import perf_counter
import os
from app import crud
from app.database import SessionLocal
from app.core.config import logger
from app.core.queue import task_queue
from app.core.services import whisper_service
from app.core.services import spell_checker
from app.services.noise_reduction import reduce_noise

# Import metrics
from app.core.metrics import (
    record_transcription,
    record_error,
    file_size_bytes,
    audio_duration_seconds
)

def process_transcription(task_id: str, file_path: str, options: dict = {}):
    background_db = SessionLocal()
    task_store = crud.TaskStore(background_db)
    
    try:
        logger.info(f"Starting processing for task {task_id}")
        
        # VALIDATION: Check if file exists before processing
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path} (deleted or moved)"
            logger.error(f"Task {task_id} failed: {error_msg}")
            task_store.update_status(task_id, "failed", error_message=error_msg)
            
            # METRICS: Record error
            record_error('file_not_found', 'transcription')
            record_transcription('error', 0)
            return
        
        # METRICS: Record file size
        file_size = os.path.getsize(file_path)
        file_size_bytes.observe(file_size)
        
        task_store.update_status(task_id, "processing")
        
        start_ts = perf_counter()
        
        # Apply noise reduction before transcription
        logger.info(f"Applying noise reduction to {file_path}")
        cleaned_audio_path = reduce_noise(file_path)
        logger.info(f"Using audio file: {cleaned_audio_path}")
        
        def update_prog(pct):
            task_store.update_progress(task_id, pct)
        
        # Fetch Rules
        rules = []
        try:
            # We need models here. 
            # app.core.worker imports crud, but we can do raw query or use crud if we add it.
            # Raw query for simplicity to avoid circular dep if crud depends on models.
            from app.models import AnalysisRule
            active_rules = background_db.query(AnalysisRule).filter(AnalysisRule.is_active == True).all()
            rules = [{'category': r.category, 'keywords': r.keywords} for r in active_rules]
        except Exception as e:
            logger.warning(f"Could not fetch analysis rules: {e}")

        result = whisper_service.process_task(cleaned_audio_path, options=options, progress_callback=update_prog, rules=rules)
        processing_time = perf_counter() - start_ts
        
        # METRICS: Record audio duration
        audio_duration_seconds.observe(result.get("duration", 0))
        
        # Get original text
        original_text = result.get("text", "")
        
        # Apply spell correction
        corrected_text = None
        try:
            logger.info(f"Applying spell correction for task {task_id}...")
            corrected_text = spell_checker.correct_text(original_text)
            logger.info(f"Spell correction completed for task {task_id}")
        except Exception as e:
            logger.warning(f"Spell correction failed for task {task_id}: {e}")
            corrected_text = original_text  # Fallback to original
        
        # Save Result
        task_store.save_result(
            task_id=task_id,
            text=original_text,
            language=result.get("language", "unknown"),
            duration=result.get("duration", 0.0),
            processing_time=processing_time,
            summary=result.get("summary"),
            topics=result.get("topics")
        )
        
        # Save corrected text separately
        if corrected_text and corrected_text != original_text:
            task = task_store.get_task(task_id)
            if task:
                task.result_text_corrected = corrected_text
                background_db.commit()
                logger.info(f"Saved corrected text for task {task_id}")
        
        logger.info(f"Task {task_id} completed successfully.")
        
        # METRICS: Record successful transcription
        record_transcription(
            status='success',
            duration=processing_time,
            model=options.get('model', 'medium'),
            device='cuda' if 'cuda' in str(options.get('device', 'cuda')) else 'cpu'
        )
        
        # CLEANUP: Free RAM and GPU memory after task completion
        try:
            from app.utils.memory_cleanup import cleanup_after_task
            cleanup_after_task(task_id, clear_gpu=True)
        except Exception as e:
            logger.warning(f"Post-task cleanup failed: {e}")

    except Exception as e:
        processing_time = perf_counter() - start_ts
        logger.error(f"Task {task_id} failed: {e}")
        task_store.update_status(task_id, "failed", error_message=str(e))
        
        # METRICS: Record failed transcription
        record_transcription('error', processing_time)
        record_error('processing_error', 'transcription')
    finally:
        background_db.close()

# task_consumer is no longer needed with RQ
# The process_transcription function is called directly by the RQ worker process
