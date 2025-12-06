import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import List

from .config import settings, logger
from .database import SessionLocal
from .models import TranscriptionTask

async def cleanup_old_files():
    """
    Periodically checks for old files and tasks to clean up.
    """
    while True:
        try:
            logger.info("Running cleanup task...")
            
            # Cleanup thresholds
            cleanup_time = datetime.utcnow() - timedelta(hours=settings.CLEANUP_AFTER_HOURS)
            
            # Database cleanup (optional: usually we keep metadata effectively forever, but let's say we clean up files)
            # Strategy: Find completed or failed tasks older than threshold and remove their files.
            # We might want to keep the DB record but mark file as deleted?
            # Or just delete everything.
            # Design doc says "Remove temporary files after configurable period".
            
            # 1. Clean upload directory orphaned files (files not in DB or just old files)
            # Simple approach: Check file modification time.
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
                logger.info(f"Cleanup finished. Removed {count} files.")
            
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            
        # Run every hour
        await asyncio.sleep(3600)

