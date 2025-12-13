
import asyncio
from time import perf_counter
from app import crud
from app.database import SessionLocal
from app.core.config import logger
from app.core.queue import task_queue
from app.core.services import whisper_service

def process_transcription(task_id: str, file_path: str, options: dict = {}):
    background_db = SessionLocal()
    task_store = crud.TaskStore(background_db)
    
    try:
        logger.info(f"Starting processing for task {task_id}")
        task_store.update_status(task_id, "processing")
        
        start_ts = perf_counter()
        
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

        result = whisper_service.process_task(file_path, options=options, progress_callback=update_prog, rules=rules)
        processing_time = perf_counter() - start_ts
        
        # Save Result
        task_store.save_result(
            task_id=task_id,
            text=result.get("text", ""),
            language=result.get("language", "unknown"),
            duration=result.get("duration", 0.0),
            processing_time=processing_time,
            summary=result.get("summary"),
            topics=result.get("topics")
        )
        logger.info(f"Task {task_id} completed successfully.")

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        task_store.update_status(task_id, "failed", error_message=str(e))
    finally:
        background_db.close()

async def task_consumer():
    while True:
        try:
            item = await task_queue.get()
            if len(item) == 3:
                task_id, file_path, options = item
            else:
                 task_id, file_path = item
                 options = {}
                 
            # Run blocking transcription in a separate thread
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, process_transcription, task_id, file_path, options)
            
            task_queue.task_done()
        except Exception as e:
            logger.error(f"Worker crashed: {e}")
            await asyncio.sleep(1) # Prevent busy loop if crash
