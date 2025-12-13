
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import logging

from app import models, auth
from app.api import schemas
from app.database import get_db
from app.core.limiter import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/token")
@limiter.limit("5/minute")
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user:
        auth.get_password_hash(form_data.password)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Conta aguardando aprovação")
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": auth.create_access_token(data={"sub": user.username}, expires_delta=access_token_expires), 
        "token_type": "bearer",
        "is_admin": user.is_admin,
        "username": user.username
    }

@router.post("/register")
async def register(user: schemas.RegisterModel, db: Session = Depends(get_db)):
    from app import crud
    existing = db.query(models.User).filter(models.User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Nome de usuário já existe")
    crud.TaskStore(db).create_user(user.username, auth.get_password_hash(user.password), user.full_name, user.email)
    return {"message": "Usuário criado. Aguarde aprovação."}
