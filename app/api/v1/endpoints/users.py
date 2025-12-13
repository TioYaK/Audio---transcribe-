
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import models, auth, crud
from app.database import get_db

router = APIRouter()

@router.get("/user/info")
async def get_user_info(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    usage = task_store.count_user_tasks(current_user.id)
    
    return {
        "username": current_user.username,
        "is_admin": str(current_user.is_admin), # String to match JS expectation
        "limit": current_user.transcription_limit,
        "usage": usage
    }
