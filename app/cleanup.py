import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import List

from .config import settings, logger
from .database import SessionLocal
from .models import TranscriptionTask
from . import crud

async def cleanup_old_files():
    """
    Periodically checks for old files and tasks to clean up.
    Also archives old transcriptions (>30 days) automatically.
    """
    while True:
        try:
            logger.info("Running cleanup task...")
            
            # 1. Archive old tasks (>30 days) - they stay in reports but hidden from main listing
            db = SessionLocal()
            try:
                task_store = crud.TaskStore(db)
                archived_count = task_store.archive_old_tasks(days=30)
                if archived_count > 0:
                    logger.info(f"Auto-archived {archived_count} tasks older than 30 days")
            finally:
                db.close()
            
            # 2. Clean upload directory orphaned files (files not in DB or just old files)
            cleanup_time = datetime.utcnow() - timedelta(hours=settings.CLEANUP_AFTER_HOURS)
            now = time.time()
            max_age_seconds = settings.CLEANUP_AFTER_HOURS * 3600
            
            count = 0
            if os.path.exists(settings.UPLOAD_DIR):
                for filename in os.listdir(settings.UPLOAD_DIR):
                    file_path = os.path.join(settings.UPLOAD_DIR, filename)
                    if os.path.isfile(file_path):
                        file_age = now - os.path.getmtime(file_path)
                        if file_age > max_age_seconds:
                            try:
                                os.remove(file_path)
                                count += 1
                                logger.debug(f"Deleted old file: {file_path}")
                            except Exception as e:
                                logger.error(f"Error deleting {file_path}: {e}")
            
            if count > 0:
                logger.info(f"Cleanup finished. Removed {count} orphaned files.")
            
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            
        # Run every hour
        await asyncio.sleep(3600)
