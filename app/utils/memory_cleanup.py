"""
Utility module for memory and resource cleanup.
Ensures low resource usage after task completion or cache clearing.
"""

import gc
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def clear_memory(clear_gpu: bool = True, force: bool = False):
    """
    Clear RAM and optionally GPU memory.
    
    Args:
        clear_gpu: If True, also clear GPU memory (CUDA cache)
        force: If True, force aggressive garbage collection
    
    Returns:
        dict with memory stats before and after cleanup
    """
    stats = {
        "ram_cleared": False,
        "gpu_cleared": False,
        "collections_run": 0
    }
    
    try:
        # 1. Python garbage collection
        if force:
            # Aggressive: collect all generations
            collected = gc.collect(2)  # Full collection
            stats["collections_run"] = 3
        else:
            # Normal: collect generation 0
            collected = gc.collect(0)
            stats["collections_run"] = 1
        
        stats["ram_cleared"] = True
        logger.info(f"RAM cleanup: Collected {collected} objects, {stats['collections_run']} generations")
        
        # 2. GPU memory cleanup (if CUDA available)
        if clear_gpu:
            try:
                import torch
                if torch.cuda.is_available():
                    # Clear CUDA cache
                    torch.cuda.empty_cache()
                    
                    # Synchronize to ensure all operations are complete
                    torch.cuda.synchronize()
                    
                    stats["gpu_cleared"] = True
                    
                    # Get memory stats
                    allocated = torch.cuda.memory_allocated() / 1024**2  # MB
                    reserved = torch.cuda.memory_reserved() / 1024**2    # MB
                    
                    logger.info(
                        f"GPU cleanup: Cache cleared. "
                        f"Allocated: {allocated:.1f}MB, Reserved: {reserved:.1f}MB"
                    )
                else:
                    logger.debug("GPU cleanup skipped: CUDA not available")
            except ImportError:
                logger.debug("GPU cleanup skipped: PyTorch not installed")
            except Exception as e:
                logger.warning(f"GPU cleanup failed: {e}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Memory cleanup error: {e}")
        return stats


def get_memory_usage():
    """
    Get current memory usage statistics.
    
    Returns:
        dict with RAM and GPU memory usage
    """
    stats = {
        "ram": {},
        "gpu": {}
    }
    
    try:
        # RAM usage (process-level)
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()
        
        stats["ram"] = {
            "rss_mb": mem_info.rss / 1024**2,  # Resident Set Size
            "vms_mb": mem_info.vms / 1024**2,  # Virtual Memory Size
        }
    except ImportError:
        logger.debug("psutil not installed, RAM stats unavailable")
    except Exception as e:
        logger.warning(f"Failed to get RAM stats: {e}")
    
    try:
        # GPU usage
        import torch
        if torch.cuda.is_available():
            stats["gpu"] = {
                "allocated_mb": torch.cuda.memory_allocated() / 1024**2,
                "reserved_mb": torch.cuda.memory_reserved() / 1024**2,
                "device_name": torch.cuda.get_device_name(0)
            }
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Failed to get GPU stats: {e}")
    
    return stats


def cleanup_after_task(task_id: str, clear_gpu: bool = True):
    """
    Cleanup memory after task completion.
    
    Args:
        task_id: Task ID for logging
        clear_gpu: Whether to clear GPU memory
    """
    logger.info(f"Running post-task cleanup for {task_id}")
    
    # Get memory before cleanup
    before = get_memory_usage()
    
    # Clear memory
    stats = clear_memory(clear_gpu=clear_gpu, force=False)
    
    # Get memory after cleanup
    after = get_memory_usage()
    
    # Log results
    if before.get("ram") and after.get("ram"):
        ram_freed = before["ram"]["rss_mb"] - after["ram"]["rss_mb"]
        logger.info(f"Task {task_id} cleanup: RAM freed ~{ram_freed:.1f}MB")
    
    if before.get("gpu") and after.get("gpu"):
        gpu_freed = before["gpu"]["allocated_mb"] - after["gpu"]["allocated_mb"]
        logger.info(f"Task {task_id} cleanup: GPU freed ~{gpu_freed:.1f}MB")
    
    return stats


def cleanup_on_cache_clear(cache_type: str = "all"):
    """
    Aggressive cleanup when admin clears cache.
    
    Args:
        cache_type: Type of cache being cleared ('diarization', 'all', etc.)
    """
    logger.info(f"Running aggressive cleanup for cache clear: {cache_type}")
    
    # Get memory before
    before = get_memory_usage()
    
    # Aggressive cleanup
    stats = clear_memory(clear_gpu=True, force=True)
    
    # Additional cleanup: unload unused models if possible
    try:
        import torch
        if torch.cuda.is_available():
            # Force garbage collection of CUDA tensors
            for obj in gc.get_objects():
                try:
                    if torch.is_tensor(obj):
                        del obj
                except:
                    pass
            
            # Clear cache again after deleting tensors
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
    except:
        pass
    
    # Final garbage collection
    gc.collect(2)
    
    # Get memory after
    after = get_memory_usage()
    
    # Log results
    logger.info(f"Cache clear cleanup complete:")
    if before.get("ram") and after.get("ram"):
        ram_freed = before["ram"]["rss_mb"] - after["ram"]["rss_mb"]
        logger.info(f"  RAM: {before['ram']['rss_mb']:.1f}MB → {after['ram']['rss_mb']:.1f}MB (freed ~{ram_freed:.1f}MB)")
    
    if before.get("gpu") and after.get("gpu"):
        gpu_freed = before["gpu"]["allocated_mb"] - after["gpu"]["allocated_mb"]
        logger.info(f"  GPU: {before['gpu']['allocated_mb']:.1f}MB → {after['gpu']['allocated_mb']:.1f}MB (freed ~{gpu_freed:.1f}MB)")
    
    return {
        "before": before,
        "after": after,
        "stats": stats
    }
