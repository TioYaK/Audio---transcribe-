
import asyncio
import os
import json
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class TaskQueue:
    def __init__(self):
        self._memory_queue = asyncio.Queue()
        self.redis = None
        self.use_redis = False
        self._init_redis()

    def _init_redis(self):
        redis_url = os.getenv("REDIS_URL")
        # redis_url = "redis://localhost" # For testing locally if needed
        if redis_url:
            try:
                import redis.asyncio as redis
                self.redis = redis.from_url(redis_url)
                self.use_redis = True
                logger.info(f"Queue initialized with Redis: {redis_url}")
            except ImportError:
                logger.warning("Redis dependencies missing. Using memory queue.")

    async def put(self, item):
        """
        Item: (task_id, file_path, options)
        """
        if self.use_redis:
            # Serialize
            data = json.dumps(item)
            await self.redis.rpush("transcription_tasks", data)
        else:
            await self._memory_queue.put(item)
            
    async def get(self):
        if self.use_redis:
            # Blocking pop
            # blpop returns (key, value)
            key, value = await self.redis.blpop("transcription_tasks")
            if value:
                return json.loads(value)
        else:
            return await self._memory_queue.get()
            
    def task_done(self):
        # Redis doesn't explicitly need task_done for RPUSH/BLPOP pattern 
        # unless using reliable queue pattern (RPOPLPUSH).
        # For simple FIFO, we just ignore.
        if not self.use_redis:
            self._memory_queue.task_done()

# Global Instance
task_queue = TaskQueue()
