
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app import models, auth, crud
from app.database import get_db
from app.core.config import settings, logger
from app.core.services import whisper_service
from app.schemas import RuleCreate, UpdateUserLimitRequest
import os
import uuid

router = APIRouter()

@router.get("/logs")
async def get_logs(limit: int = 100, current_user: models.User = Depends(auth.require_admin)):
    log_file = "/app/data/app.log"
    if not os.path.exists(log_file): return {"logs": ["Log file not found."]}
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            return {"logs": lines[-limit:]}
    except Exception as e: return {"logs": [f"Error: {e}"]}

@router.get("/admin/users")
async def get_all_users(db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_admin)):
    task_store = crud.TaskStore(db)
    users_data = []
    for u in task_store.get_users():
        usage = task_store.count_user_tasks(u.id)
        users_data.append({
            "id": u.id, "username": u.username, "full_name": u.full_name, "email": u.email,
            "is_active": u.is_active, "is_admin": u.is_admin, "transcription_limit": u.transcription_limit,
            "usage": usage
        })
    return users_data

from pydantic import BaseModel, Field

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    limit: int = 30

@router.post("/admin/users/create")
async def create_user_admin(
    payload: CreateUserRequest, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.require_admin)
):
    existing = db.query(models.User).filter(models.User.username == payload.username).first()
    if existing: raise HTTPException(400, "Username taken")
    
    new_user = models.User(
        username=payload.username,
        hashed_password=auth.get_password_hash(payload.password),
        is_active=True, 
        is_admin=False,
        transcription_limit=payload.limit
    )
    db.add(new_user)
    db.commit()
    return {"message": "User created", "id": new_user.id}

@router.post("/admin/approve/{user_id}")
async def approve_user(user_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_admin)):
    crud.TaskStore(db).approve_user(user_id)
    return {"message": "Aprovado"}

@router.post("/admin/user/{user_id}/limit")
async def update_limit(user_id: str, payload: UpdateUserLimitRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_admin)):
    crud.TaskStore(db).update_user_limit(user_id, payload.limit)
    return {"message": "Limite atualizado"}

@router.post("/admin/user/{user_id}/update")
async def update_user_credentials(
    user_id: str, 
    payload: dict = Body(...), 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.require_admin)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(404, "User not found")
    
    if "username" in payload and payload["username"]:
        if db.query(models.User).filter(models.User.username == payload["username"], models.User.id != user_id).first():
            raise HTTPException(400, "Username taken")
        user.username = payload["username"]
        
    if "password" in payload and payload["password"]:
        user.hashed_password = auth.get_password_hash(payload["password"])

    if "is_admin" in payload:
        user.is_admin = bool(payload["is_admin"])
        
    db.commit()
    return {"message": "Updated"}

@router.delete("/admin/user/{user_id}")
async def delete_user(user_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_admin)):
    # Proteção: Não permitir deletar o admin
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user and user.username.lower() == "admin":
        raise HTTPException(status_code=403, detail="O usuário 'admin' não pode ser excluído")
    
    crud.TaskStore(db).delete_user(user_id)
    return {"message": "User deleted"}

@router.post("/history/clear")
async def clear_history(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    if current_user.is_admin: 
        deleted = task_store.clear_all_history()
    else: 
        deleted = task_store.clear_history(current_user.id)
    
    # CLEANUP: Free RAM and GPU memory after clearing history
    try:
        from app.utils.memory_cleanup import cleanup_on_cache_clear
        cleanup_stats = cleanup_on_cache_clear("history")
        logger.info(f"Memory cleanup after history clear: {cleanup_stats['stats']}")
    except Exception as e:
        logger.warning(f"Post-clear cleanup failed: {e}")
    
    return {"deleted": deleted}

@router.post("/admin/regenerate-all")
async def regenerate_all(db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_admin)):
    tasks = db.query(models.TranscriptionTask).filter(models.TranscriptionTask.status == "completed").all()
    
    # Fetch active rules for regeneration context
    active_rules = db.query(models.AnalysisRule).filter(models.AnalysisRule.is_active == True).all()
    rules = [{'category': r.category, 'keywords': r.keywords} for r in active_rules]
    
    count = 0
    for t in tasks:
        if t.result_text:
            try:
                # Use new analyzer path
                anal = whisper_service.analyzer.analyze(t.result_text, rules=rules)
                t.summary = anal.get("summary")
                t.topics = anal.get("topics")
                t.analysis_status = "completed"
                count += 1
            except Exception as e:
                logger.error(f"Failed to regen task {t.task_id}: {e}")
    db.commit()
    return {"count": count}

# --- Dynamic Analysis Rules (Tier 3) ---

@router.get("/admin/rules")
async def get_rules(db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_admin)):
    return db.query(models.AnalysisRule).all()

@router.post("/admin/rules")
async def create_rule(
    payload: RuleCreate,  # Now using Pydantic schema for validation
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.require_admin)
):
    rule = models.AnalysisRule(
        name=payload.name,
        category=payload.category,
        keywords=payload.keywords,
        description=payload.description,
        is_active=payload.is_active
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

@router.delete("/admin/rules/{rule_id}")
async def delete_rule(rule_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_admin)):
    rule = db.query(models.AnalysisRule).filter(models.AnalysisRule.id == rule_id).first()
    if rule:
        db.delete(rule)
        db.commit()
    return {"status": "deleted"}

# Legacy Config (Deprecated but kept for now)
@router.post("/admin/config/keywords")
async def update_keywords(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_admin)):
    # Redirect legacy config to create default rules if needed?
    # For now just ignore or keep simple
    return {"status": "legacy_update_ignored"}

@router.get("/config/keywords")
async def get_keywords(db: Session = Depends(get_db)):
    return {"keywords": "", "keywords_red": "", "keywords_green": ""}

# --- Diarization Cache Management (Performance Optimization) ---

@router.get("/admin/diarization/stats")
async def get_diarization_stats(current_user: models.User = Depends(auth.require_admin)):
    """
    Get diarization cache statistics.
    
    Returns:
        - cache_size: Current number of cached entries
        - max_size: Maximum cache capacity
        - hits: Number of cache hits
        - misses: Number of cache misses
        - hit_rate: Cache hit rate percentage
        - ttl_seconds: Time-to-live for cache entries
        - total_diarizations: Total diarization requests
        - overall_hit_rate: Overall hit rate across all requests
    """
    try:
        diarizer = whisper_service.diarizer
        stats = diarizer.get_cache_stats()
        
        return {
            "status": "success",
            "stats": stats,
            "message": f"Cache is {'efficient' if float(stats.get('hit_rate', '0').rstrip('%')) > 50 else 'warming up'}"
        }
    except Exception as e:
        logger.error(f"Failed to get diarization stats: {e}")
        return {
            "status": "error",
            "message": str(e),
            "stats": {}
        }

@router.post("/admin/diarization/cache/clear")
async def clear_diarization_cache(
    expired_only: bool = False,
    current_user: models.User = Depends(auth.require_admin)
):
    """
    Clear diarization cache.
    
    Args:
        expired_only: If True, only clear expired entries. If False, clear all.
    
    Returns:
        Status message
    """
    try:
        diarizer = whisper_service.diarizer
        
        if expired_only:
            diarizer.clear_expired_cache()
            message = "Expired cache entries cleared"
        else:
            diarizer.clear_cache()
            message = "All cache entries cleared"
        
        logger.info(f"Admin {current_user.username} cleared diarization cache (expired_only={expired_only})")
        
        # CLEANUP: Free RAM and GPU memory after clearing cache
        try:
            from app.utils.memory_cleanup import cleanup_on_cache_clear
            cleanup_stats = cleanup_on_cache_clear("diarization")
            logger.info(f"Memory cleanup after cache clear: {cleanup_stats['stats']}")
        except Exception as e:
            logger.warning(f"Post-clear cleanup failed: {e}")
        
        return {
            "status": "success",
            "message": message
        }
    except Exception as e:
        logger.error(f"Failed to clear diarization cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Redis Distributed Cache Management (NEW) ---

@router.get("/admin/cache/stats")
async def get_cache_stats(current_user: models.User = Depends(auth.require_admin)):
    """
    Get Redis distributed cache statistics.
    
    Returns:
        - total_keys: Total cached items
        - transcription_keys: Cached transcriptions
        - analysis_keys: Cached analyses
        - used_memory_mb: Redis memory usage
        - connected: Redis connection status
    """
    try:
        from app.services.cache_service import cache_service
        stats = cache_service.get_stats()
        
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {
            "status": "error",
            "message": str(e),
            "stats": {}
        }

@router.post("/admin/cache/clear")
async def clear_cache(
    cache_type: str = "all",  # all, transcriptions, analysis
    current_user: models.User = Depends(auth.require_admin)
):
    """
    Clear Redis distributed cache.
    
    Args:
        cache_type: Type of cache to clear ('all', 'transcriptions', 'analysis')
    
    Returns:
        Status message
    """
    try:
        from app.services.cache_service import cache_service
        
        if cache_type == "transcriptions":
            cache_service.clear_transcriptions()
            message = "Transcription cache cleared"
        elif cache_type == "analysis":
            cache_service.clear_analysis()
            message = "Analysis cache cleared"
        elif cache_type == "all":
            cache_service.clear_all()
            message = "All cache cleared"
        else:
            raise HTTPException(status_code=400, detail=f"Invalid cache_type: {cache_type}")
        
        logger.info(f"Admin {current_user.username} cleared cache: {cache_type}")
        
        # CLEANUP: Free RAM and GPU memory after clearing cache
        try:
            from app.utils.memory_cleanup import cleanup_on_cache_clear
            cleanup_stats = cleanup_on_cache_clear(cache_type)
            logger.info(f"Memory cleanup after cache clear: {cleanup_stats['stats']}")
        except Exception as e:
            logger.warning(f"Post-clear cleanup failed: {e}")
        
        return {
            "status": "success",
            "message": message,
            "cache_type": cache_type
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

import psutil
import shutil
import subprocess

@router.get("/resources")
async def get_system_resources(current_user: models.User = Depends(auth.require_admin)):
    """
    Get server system resources (CPU, RAM, Disk, GPU).
    """
    
    # 1. CPU
    # Interval=0.1 avoids 0.0 return on first call (blocking for 100ms)
    cpu_usage = psutil.cpu_percent(interval=0.1)
    
    # 2. RAM
    mem = psutil.virtual_memory()
    ram_usage = mem.percent
    ram_total_gb = round(mem.total / (1024**3), 1)
    
    # 3. Disk (Root)
    disk = shutil.disk_usage("/")
    disk_usage = round((disk.used / disk.total) * 100, 1)
    
    # 4. GPU (Basic check via nvidia-smi if available)
    gpu_usage = "N/A"
    gpu_mem = "N/A"
    try:
        # Get GPU utilization
        result = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"], 
            encoding='utf-8'
        )
        util, mem_used, mem_total = result.strip().split(',')
        gpu_usage = f"{util.strip()}%"
        try:
            gpu_percent = (float(mem_used) / float(mem_total)) * 100
            gpu_mem = f"{gpu_percent:.1f}%"
        except:
            gpu_mem = "N/A"
    except Exception:
        pass # No GPU or nvidia-smi not found
        
    return {
        "cpu": cpu_usage,
        "ram": ram_usage,
        "ram_total": ram_total_gb,
        "disk": disk_usage,
        "gpu": gpu_usage,
        "gpu_mem": gpu_mem
    }
