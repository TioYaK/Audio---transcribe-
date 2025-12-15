"""
Custom RQ Worker with Memory Management
Prevents OOM by monitoring memory usage during job execution
"""
import psutil
import signal
import sys
from rq import Worker
from rq.job import Job
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CustomWorker(Worker):
    """
    Custom RQ Worker with enhanced memory management and graceful shutdown
    """
    
    def __init__(self, *args, max_memory_mb: int = 3500, max_jobs: int = 100, **kwargs):
        """
        Initialize custom worker
        
        Args:
            max_memory_mb: Maximum memory in MB before rejecting jobs (default: 3.5GB)
            max_jobs: Maximum jobs before worker restart (default: 100)
        """
        # Store max_jobs before passing to parent
        self.max_jobs = max_jobs
        super().__init__(*args, **kwargs)
        self.max_memory_mb = max_memory_mb
        self.jobs_processed = 0
        
        # Setup graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown on SIGTERM/SIGINT"""
        logger.info(f"🛑 Received signal {signum}, shutting down gracefully...")
        self.request_stop()
    
    def execute_job(self, job: Job, queue) -> bool:
        """
        Execute job with memory monitoring
        
        Args:
            job: RQ Job instance
            queue: Queue instance
            
        Returns:
            bool: True if job executed successfully
        """
        try:
            # Check memory before execution
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.max_memory_mb:
                error_msg = f"Memory limit exceeded: {memory_mb:.2f}MB > {self.max_memory_mb}MB"
                logger.error(f"❌ {error_msg}")
                
                job.set_status('failed')
                job.meta['error'] = error_msg
                job.meta['memory_mb'] = memory_mb
                job.save()
                
                return False
            
            # Log job start
            logger.info(
                f"▶️  Starting job {job.id} | "
                f"Memory: {memory_mb:.2f}MB | "
                f"Jobs processed: {self.jobs_processed}/{self.max_jobs}"
            )
            
            # Execute job
            result = super().execute_job(job, queue)
            
            # Update counter
            self.jobs_processed += 1
            
            # Log completion
            memory_after = process.memory_info().rss / 1024 / 1024
            logger.info(
                f"✅ Completed job {job.id} | "
                f"Memory: {memory_after:.2f}MB | "
                f"Delta: {memory_after - memory_mb:+.2f}MB"
            )
            
            # Check if max jobs reached
            if self.jobs_processed >= self.max_jobs:
                logger.warning(
                    f"⚠️  Max jobs reached ({self.max_jobs}), "
                    "worker will restart after current job"
                )
                self.request_stop()
            
            return result
            
        except Exception as e:
            logger.exception(f"❌ Error executing job {job.id}: {e}")
            job.set_status('failed')
            job.meta['error'] = str(e)
            job.save()
            return False
    
    def work(self, *args, **kwargs):
        """Override work method to add startup logging"""
        logger.info(
            f"🚀 Worker started | "
            f"Max Memory: {self.max_memory_mb}MB | "
            f"Max Jobs: {self.max_jobs}"
        )
        return super().work(*args, **kwargs)


def main():
    """Main entry point for custom worker"""
    import os
    from redis import Redis
    
    # Get Redis connection using secrets
    try:
        from app.core.secrets import get_redis_url
        redis_url = get_redis_url()
    except Exception as e:
        logger.warning(f"Failed to load Redis URL from secrets, using fallback: {e}")
        # Fallback: build from environment
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_db = os.getenv("REDIS_DB", "0")
        
        # Try to read password from secret file
        try:
            with open("/run/secrets/redis_password", "r") as f:
                redis_password = f.read().strip()
        except:
            redis_password = os.getenv("REDIS_PASSWORD", "")
        
        redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
    
    redis_conn = Redis.from_url(redis_url)
    
    # Create worker
    worker = CustomWorker(
        ['transcription_tasks'],
        connection=redis_conn,
        max_memory_mb=int(os.getenv('WORKER_MAX_MEMORY_MB', '3500')),
        max_jobs=int(os.getenv('WORKER_MAX_JOBS', '100'))
    )
    
    # Start worker
    worker.work(with_scheduler=True, burst=False)


if __name__ == '__main__':
    main()
