"""
Worker Health Check Module
Provides comprehensive health checking for RQ workers
"""
import logging
from datetime import datetime, timedelta
from typing import List
from redis import Redis
from rq import Worker, Queue
from rq.job import Job

logger = logging.getLogger(__name__)


def check_worker_health(redis_conn: Redis, max_stuck_time_minutes: int = 30) -> bool:
    """
    Comprehensive worker health check.
    
    Checks:
    1. Redis connection
    2. Active workers exist
    3. No stuck jobs (running > max_stuck_time_minutes)
    
    Args:
        redis_conn: Redis connection instance
        max_stuck_time_minutes: Maximum time a job can run before considered stuck
        
    Returns:
        True if healthy, False otherwise
    """
    try:
        # 1. Check Redis connection
        if not redis_conn.ping():
            logger.error("❌ Redis connection failed")
            return False
        
        # 2. Check if workers are registered
        workers = Worker.all(connection=redis_conn)
        if not workers:
            logger.warning("⚠️ No workers registered in Redis")
            return False
        
        # Count active workers
        active_workers = [w for w in workers if w.state == 'busy' or w.state == 'idle']
        logger.info(f"✅ Found {len(active_workers)} active workers")
        
        # 3. Check for stuck jobs
        stuck_threshold = datetime.now() - timedelta(minutes=max_stuck_time_minutes)
        stuck_jobs: List[Job] = []
        
        for queue_name in ['default', 'high', 'low']:
            try:
                queue = Queue(queue_name, connection=redis_conn)
                started_jobs = queue.started_job_registry.get_job_ids()
                
                for job_id in started_jobs:
                    job = Job.fetch(job_id, connection=redis_conn)
                    if job.started_at and job.started_at < stuck_threshold:
                        stuck_jobs.append(job)
                        logger.warning(
                            f"⚠️ Stuck job detected: {job.id} "
                            f"(started {job.started_at}, running for "
                            f"{(datetime.now() - job.started_at).seconds // 60} minutes)"
                        )
            except Exception as e:
                logger.warning(f"⚠️ Error checking queue '{queue_name}': {e}")
        
        if stuck_jobs:
            logger.error(f"❌ Found {len(stuck_jobs)} stuck jobs")
            return False
        
        logger.info("✅ Worker health check passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Health check failed with exception: {e}")
        return False


def get_worker_stats(redis_conn: Redis) -> dict:
    """Get worker statistics for monitoring"""
    try:
        workers = Worker.all(connection=redis_conn)
        
        stats = {
            "total_workers": len(workers),
            "busy_workers": len([w for w in workers if w.state == 'busy']),
            "idle_workers": len([w for w in workers if w.state == 'idle']),
            "queues": {}
        }
        
        for queue_name in ['default', 'high', 'low']:
            try:
                queue = Queue(queue_name, connection=redis_conn)
                stats["queues"][queue_name] = {
                    "pending": len(queue),
                    "started": queue.started_job_registry.count,
                    "finished": queue.finished_job_registry.count,
                    "failed": queue.failed_job_registry.count
                }
            except Exception as e:
                logger.warning(f"Error getting stats for queue '{queue_name}': {e}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting worker stats: {e}")
        return {}
