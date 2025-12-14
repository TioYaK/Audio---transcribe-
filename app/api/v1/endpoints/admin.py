
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

@router.post("/admin/approve/{user_id}")
async def approve_user(user_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_admin)):
    crud.TaskStore(db).approve_user(user_id)
    return {"message": "Aprovado"}

@router.post("/admin/user/{user_id}/limit")
async def update_limit(user_id: str, payload: UpdateUserLimitRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_admin)):
    crud.TaskStore(db).update_user_limit(user_id, payload.limit)
    return {"message": "Limite atualizado"}

@router.delete("/admin/user/{user_id}")
async def delete_user(user_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_admin)):
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

