
import os
import logging
from redis import Redis
from rq import Queue
from app.core.config import settings

logger = logging.getLogger(__name__)

class TaskQueue:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.queue = None
        self._init_queue()

    def _init_queue(self):
        try:
            self.redis_conn = Redis.from_url(self.redis_url)
            self.queue = Queue("transcription_tasks", connection=self.redis_conn, default_timeout=3600)
            logger.info(f"RQ Queue initialized: {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to initialize RQ: {e}. Tasks will fail!")
            # In a real enterprise app, we might want to crash or fallback, 
            # but for now we'll just log error as fallback to memory is tricky with RQ pattern change

    async def put(self, item):
        """
        Enqueue a task for the worker.
        Item: (task_id, file_path, options)
        """
        task_id, file_path, options = item
        
        if self.queue:
            # We enqueue the function reference string to avoid circular imports here if possible,
            # but RQ usually needs the function. 
            # We imported 'app.core.worker' inside the worker process, but here we specify the path.
            job = self.queue.enqueue(
                "app.core.worker.process_transcription",
                args=(task_id, file_path, options),
                job_id=task_id, # Use same ID for tracking
                retry=None # Configurable
            )
            logger.info(f"Task {task_id} enqueued to RQ. Job ID: {job.id}")
        else:
            logger.error(f"Queue not initialized! Task {task_id} lost.")

    # get() and task_done() are no longer needed for RQ as the worker handles pulling
    # We keep them if existing code relies on them, but we should refactor usages.
    # The 'main.py' used to call consume, now it won't.

# Global Instance
task_queue = TaskQueue()
