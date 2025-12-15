"""
Advanced metrics for Mirror.ia transcription service.
Provides business, performance, and infrastructure metrics.
"""

from prometheus_client import Counter, Histogram, Gauge, Info
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# BUSINESS METRICS (Métricas de Negócio)
# ============================================================================

# Transcrições
transcriptions_total = Counter(
    'transcriptions_total',
    'Total number of transcriptions',
    ['status', 'model', 'device', 'user_type']
)

transcription_duration = Histogram(
    'transcription_duration_seconds',
    'Time taken to transcribe audio',
    buckets=[5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 300]
)

file_size_bytes = Histogram(
    'file_size_bytes',
    'Size of uploaded audio files',
    buckets=[1e6, 5e6, 10e6, 25e6, 50e6, 100e6, 200e6, 500e6]  # 1MB to 500MB
)

audio_duration_seconds = Histogram(
    'audio_duration_seconds',
    'Duration of audio files',
    buckets=[30, 60, 120, 300, 600, 1200, 1800, 3600]  # 30s to 1h
)

# ============================================================================
# CACHE METRICS (Métricas de Cache)
# ============================================================================

cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['cache_type', 'operation', 'result']  # transcription/analysis, get/set, hit/miss
)

cache_size_bytes = Gauge(
    'cache_size_bytes',
    'Current cache size in bytes',
    ['cache_type']
)

cache_entries = Gauge(
    'cache_entries',
    'Number of entries in cache',
    ['cache_type']
)

cache_hit_rate = Gauge(
    'cache_hit_rate_percent',
    'Cache hit rate percentage',
    ['cache_type']
)

# ============================================================================
# QUEUE METRICS (Métricas de Fila)
# ============================================================================

queue_size = Gauge(
    'queue_size',
    'Number of tasks in queue'
)

queue_wait_time = Histogram(
    'queue_wait_seconds',
    'Time tasks spend waiting in queue',
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

active_tasks = Gauge(
    'active_tasks',
    'Number of tasks currently being processed'
)

# ============================================================================
# WORKER METRICS (Métricas de Workers)
# ============================================================================

active_workers = Gauge(
    'active_workers',
    'Number of active workers'
)

worker_tasks_total = Counter(
    'worker_tasks_total',
    'Total tasks processed by worker',
    ['worker_id', 'status']
)

worker_uptime_seconds = Gauge(
    'worker_uptime_seconds',
    'Worker uptime in seconds',
    ['worker_id']
)

# ============================================================================
# RESOURCE METRICS (Métricas de Recursos)
# ============================================================================

gpu_utilization_percent = Gauge(
    'gpu_utilization_percent',
    'GPU utilization percentage'
)

gpu_memory_used_bytes = Gauge(
    'gpu_memory_used_bytes',
    'GPU memory used in bytes'
)

gpu_memory_total_bytes = Gauge(
    'gpu_memory_total_bytes',
    'Total GPU memory in bytes'
)

gpu_temperature_celsius = Gauge(
    'gpu_temperature_celsius',
    'GPU temperature in Celsius'
)

ram_usage_bytes = Gauge(
    'ram_usage_bytes',
    'RAM usage in bytes'
)

disk_usage_bytes = Gauge(
    'disk_usage_bytes',
    'Disk usage in bytes',
    ['path']
)

disk_total_bytes = Gauge(
    'disk_total_bytes',
    'Total disk space in bytes',
    ['path']
)

# ============================================================================
# ERROR METRICS (Métricas de Erros)
# ============================================================================

errors_total = Counter(
    'errors_total',
    'Total number of errors',
    ['error_type', 'component']
)

# ============================================================================
# ANALYSIS METRICS (Métricas de Análise)
# ============================================================================

analysis_duration = Histogram(
    'analysis_duration_seconds',
    'Time taken to analyze text',
    buckets=[0.1, 0.5, 1, 2, 5, 10, 20]
)

analysis_total = Counter(
    'analysis_total',
    'Total number of analyses',
    ['status']
)

# ============================================================================
# APPLICATION INFO (Informações da Aplicação)
# ============================================================================

app_info = Info('app', 'Application information')
app_info.info({
    'version': '2.2',
    'environment': 'production',
    'features': 'cache_redis,memory_cleanup,advanced_metrics'
})

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def record_transcription(status: str, duration: float, model: str = "medium", 
                        device: str = "cuda", user_type: str = "regular"):
    """
    Record transcription metrics.
    
    Args:
        status: 'success' or 'error'
        duration: Time in seconds
        model: Whisper model used
        device: 'cuda' or 'cpu'
        user_type: 'admin' or 'regular'
    """
    transcriptions_total.labels(
        status=status,
        model=model,
        device=device,
        user_type=user_type
    ).inc()
    
    if status == 'success':
        transcription_duration.observe(duration)


def record_cache_operation(cache_type: str, operation: str, result: str):
    """
    Record cache operation.
    
    Args:
        cache_type: 'transcription' or 'analysis'
        operation: 'get' or 'set'
        result: 'hit' or 'miss' (for get), 'success' or 'error' (for set)
    """
    cache_operations_total.labels(
        cache_type=cache_type,
        operation=operation,
        result=result
    ).inc()


def record_error(error_type: str, component: str):
    """
    Record error.
    
    Args:
        error_type: Type of error (e.g., 'file_not_found', 'gpu_oom')
        component: Component where error occurred (e.g., 'transcription', 'analysis')
    """
    errors_total.labels(
        error_type=error_type,
        component=component
    ).inc()


def update_resource_metrics():
    """
    Update system resource metrics.
    Should be called periodically (e.g., every 30s).
    """
    try:
        import psutil
        
        # RAM
        mem = psutil.virtual_memory()
        ram_usage_bytes.set(mem.used)
        
        # Disk
        disk = psutil.disk_usage('/app')
        disk_usage_bytes.labels(path='/app').set(disk.used)
        disk_total_bytes.labels(path='/app').set(disk.total)
        
    except ImportError:
        logger.debug("psutil not available for resource metrics")
    except Exception as e:
        logger.warning(f"Failed to update resource metrics: {e}")
    
    try:
        import torch
        
        if torch.cuda.is_available():
            # GPU memory
            allocated = torch.cuda.memory_allocated()
            reserved = torch.cuda.memory_reserved()
            
            gpu_memory_used_bytes.set(allocated)
            
            # GPU utilization (requires nvidia-ml-py3)
            try:
                import pynvml
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_utilization_percent.set(util.gpu)
                
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                gpu_temperature_celsius.set(temp)
                
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpu_memory_total_bytes.set(mem_info.total)
                
                pynvml.nvmlShutdown()
            except ImportError:
                logger.debug("pynvml not available for GPU metrics")
            except Exception as e:
                logger.debug(f"Failed to get GPU metrics: {e}")
                
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Failed to update GPU metrics: {e}")


def update_queue_metrics(redis_conn):
    """
    Update queue metrics from Redis.
    
    Args:
        redis_conn: Redis connection
    """
    try:
        # Get queue size
        size = redis_conn.llen('rq:queue:transcription_tasks')
        queue_size.set(size)
        
    except Exception as e:
        logger.warning(f"Failed to update queue metrics: {e}")


# ============================================================================
# INITIALIZATION
# ============================================================================

logger.info("✓ Advanced metrics initialized")
