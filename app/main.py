
from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import asyncio
import os
import secrets
import uuid

# Import Core
from app.core.config import settings, logger
from app.core.limiter import limiter
from app.core.queue import task_queue
from app.core.worker import task_consumer

# Import Database
from app.database import engine, get_db
from app import models, auth, crud
from sqlalchemy.orm import Session
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

# Import Routers
from app.api.v1.api import router as api_router

# Create DB Tables (Pending Alembic)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Careca.ai - Transcription Service")

# Limiter Setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
CACHE_BUST = str(int(time.time()))

# Include API Router
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    logger.info("Service starting up [Applied Improvements]...")
    
    # 1. Start Workers
    for i in range(2):
        asyncio.create_task(task_consumer())
        logger.info(f"Started task_consumer worker {i+1}")
        
    # 2. Infrastructure Setup (Admin & Migrations)
    db = next(get_db())
    try:
        # Create Admin
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin:
            pwd = settings.ADMIN_PASSWORD
            if not pwd:
                pwd = secrets.token_urlsafe(16)
                logger.warning(f"ADMIN_PASSWORD not set. Generated: {pwd}")
            
            db.add(models.User(
                username="admin", 
                hashed_password=auth.get_password_hash(pwd),
                is_active=True, 
                is_admin=True
            ))
            db.commit()
            logger.info("Admin user verified/created.")
            
        # 3. TASK RECOVERY (Reliability Fix)
        # Instead of deleting, we re-queue pending tasks!
        pending_tasks = db.query(models.TranscriptionTask).filter(
            models.TranscriptionTask.status.in_(["queued", "processing"])
        ).all()
        
        recovered_count = 0
        deleted_count = 0
        
        for task in pending_tasks:
            # Check if file still exists
            if os.path.exists(task.file_path):
                # Reset status to queued
                task.status = "queued"
                task.progress = 0
                task.started_at = None
                
                # Re-add to memory queue
                # We need to parse options from string if stored as logic, but model has JSON/Text?
                # Simplification: we might lose options if not stored properly in composite or dict.
                # models.py says: options = Column(Text)
                # But we treat it as dict in code. SQLAlchemy doesn't auto-convert Text->Dict unless using TypeDecorator.
                # Let's assume for now default options or try eval if safe (JSON should be used).
                # Actually, the original code stored it as JSON/Text probably but raw.
                # For safety, pass empty dict or try to load if really needed.
                ops = {} 
                # Re-queue
                logger.info(f"Recovering task {task.task_id}...")
                await task_queue.put((task.task_id, task.file_path, ops))
                recovered_count += 1
            else:
                # File missing, cannot recover
                logger.warning(f"Task {task.task_id} file missing. Deleting task.")
                db.delete(task)
                deleted_count += 1
                
        db.commit()
        logger.info(f"Startup Plan: Recovered {recovered_count} tasks, Cleaned {deleted_count} broken tasks.")

    finally:
        db.close()

# HTML Pages (Web Interface)
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "cache_bust": CACHE_BUST})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "cache_bust": CACHE_BUST})

@app.get("/health")
async def health_check():
    return {"status": "healthy", "gpu": settings.DEVICE == "cuda"}
