
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import logging

from app import models, auth
from app.api import schemas
from app.database import get_db
from app.core.limiter import limiter
from app.schemas import TokenRefreshRequest

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
    
    # Create both access and refresh tokens
    access_token = auth.create_access_token(data={"sub": user.username})
    refresh_token = auth.create_refresh_token(data={"sub": user.username})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "is_admin": user.is_admin,
        "username": user.username
    }

@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh_access_token(request: Request, payload: TokenRefreshRequest, db: Session = Depends(get_db)):
    """Exchange a refresh token for a new access token"""
    try:
        token_data = auth.verify_token(payload.refresh_token, token_type="refresh")
        username = token_data.get("sub")
        
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # Create new access token
        new_access_token = auth.create_access_token(data={"sub": username})
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.post("/register")
async def register(user: schemas.RegisterModel, db: Session = Depends(get_db)):
    from app import crud
    existing = db.query(models.User).filter(models.User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Nome de usuário já existe")
    crud.TaskStore(db).create_user(user.username, auth.get_password_hash(user.password), user.full_name, user.email)
    return {"message": "Usuário criado. Aguarde aprovação."}

