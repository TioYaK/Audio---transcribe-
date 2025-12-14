
import asyncio
from time import perf_counter
from app import crud
from app.database import SessionLocal
from app.core.config import logger
from app.core.queue import task_queue
from app.core.services import whisper_service
from app.core.services import spell_checker
from app.services.noise_reduction import reduce_noise

def process_transcription(task_id: str, file_path: str, options: dict = {}):
    background_db = SessionLocal()
    task_store = crud.TaskStore(background_db)
    
    try:
        logger.info(f"Starting processing for task {task_id}")
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

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        task_store.update_status(task_id, "failed", error_message=str(e))
    finally:
        background_db.close()

# task_consumer is no longer needed with RQ
# The process_transcription function is called directly by the RQ worker process
