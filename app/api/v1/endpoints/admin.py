
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app import models, auth, crud
from app.database import get_db
from app.core.config import settings, logger
from app.core.services import whisper_service
import os
import uuid

router = APIRouter()

@router.get("/logs")
async def get_logs(limit: int = 100, current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso restrito")
    log_file = "/app/data/app.log"
    if not os.path.exists(log_file): return {"logs": ["Log file not found."]}
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            return {"logs": lines[-limit:]}
    except Exception as e: return {"logs": [f"Error: {e}"]}

@router.get("/admin/users")
async def get_all_users(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin: raise HTTPException(403)
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
async def approve_user(user_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin: raise HTTPException(403)
    crud.TaskStore(db).approve_user(user_id)
    return {"message": "Aprovado"}

@router.post("/admin/user/{user_id}/limit")
async def update_limit(user_id: str, payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin: raise HTTPException(403)
    crud.TaskStore(db).update_user_limit(user_id, int(payload.get("limit", 0)))
    return {"message": "Limite atualizado"}

@router.delete("/admin/user/{user_id}")
async def delete_user(user_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin: raise HTTPException(403)
    crud.TaskStore(db).delete_user(user_id)
    return {"message": "User deleted"}

@router.post("/history/clear")
async def clear_history(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    if current_user.is_admin: deleted = task_store.clear_all_history()
    else: deleted = task_store.clear_history(current_user.id)
    return {"deleted": deleted}

@router.post("/admin/regenerate-all")
async def regenerate_all(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin: raise HTTPException(403)
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
async def get_rules(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin: raise HTTPException(403)
    return db.query(models.AnalysisRule).all()

@router.post("/admin/rules")
async def create_rule(
    payload: dict = Body(...), 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    if not current_user.is_admin: raise HTTPException(403)
    
    # Simple validation
    if not payload.get('name') or not payload.get('category'):
        raise HTTPException(400, "Missing name or category")
        
    rule = models.AnalysisRule(
        name=payload['name'],
        category=payload['category'],
        keywords=payload.get('keywords', ''),
        description=payload.get('description', ''),
        is_active=payload.get('is_active', True)
    )
    db.add(rule)
    db.commit()
    return rule

@router.delete("/admin/rules/{rule_id}")
async def delete_rule(rule_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin: raise HTTPException(403)
    rule = db.query(models.AnalysisRule).filter(models.AnalysisRule.id == rule_id).first()
    if rule:
        db.delete(rule)
        db.commit()
    return {"status": "deleted"}

# Legacy Config (Deprecated but kept for now)
@router.post("/admin/config/keywords")
async def update_keywords(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin: raise HTTPException(403)
    # Redirect legacy config to create default rules if needed?
    # For now just ignore or keep simple
    return {"status": "legacy_update_ignored"}

@router.get("/config/keywords")
async def get_keywords(db: Session = Depends(get_db)):
    return {"keywords": "", "keywords_red": "", "keywords_green": ""}
