
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

app = FastAPI(title="Mirror.ia - Sua voz, refletida em inteligência")

# Limiter Setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# Static & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
CACHE_BUST = str(int(time.time()))

# Include API Router
app.include_router(api_router)

# Prometheus Instrumentator (Must be before startup)
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)
    logger.info("Prometheus metrics initialized")
except ImportError:
    logger.warning("Prometheus instrumentator not installed.")


@app.on_event("startup")
async def startup_event():
    logger.info("Service starting up [Applied Improvements]...")
    

    # 2. Infrastructure Setup (Admin & Migrations)
    db = next(get_db())
    try:
        # Create Admin
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin:
            pwd = settings.ADMIN_PASSWORD
            if not pwd:
                pwd = secrets.token_urlsafe(16)
                # Security: Do NOT log the generated password
                logger.warning("ADMIN_PASSWORD not set. A temporary password was generated - set ADMIN_PASSWORD in .env")
            
            try:
                db.add(models.User(
                    username="admin", 
                    hashed_password=auth.get_password_hash(pwd),
                    is_active=True, 
                    is_admin=True
                ))
                db.commit()
                logger.info("Admin user created successfully.")
            except Exception as e:
                db.rollback()
                logger.warning(f"Admin user creation skipped (may already exist): {e}")
        else:
            logger.info("Admin user already exists.")
            
        # 3. TASK RECOVERY (Reliability Fix with Better Error Handling)
        # Re-queue pending tasks if file exists, otherwise mark as failed
        pending_tasks = db.query(models.TranscriptionTask).filter(
            models.TranscriptionTask.status.in_(["queued", "processing"])
        ).all()
        
        recovered_count = 0
        failed_count = 0
        
        for task in pending_tasks:
            # Check if file still exists
            if os.path.exists(task.file_path):
                # Reset status to queued
                task.status = "queued"
                task.progress = 0
                task.started_at = None
                
                # Parse options from JSON stored in database
                import json
                ops = {}
                if task.options:
                    try:
                        ops = json.loads(task.options)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid options JSON for task {task.task_id}, using defaults")
                        ops = {}
                
                # Re-queue
                logger.info(f"✓ Recovering task {task.task_id} ({task.filename})")
                await task_queue.put((task.task_id, task.file_path, ops))
                recovered_count += 1
            else:
                # File missing, mark as failed instead of deleting
                logger.warning(f"✗ Task {task.task_id} file missing: {task.file_path}")
                task.status = "failed"
                task.error_message = f"File not found: {os.path.basename(task.file_path)} (deleted or moved)"
                task.completed_at = None
                failed_count += 1
                
        db.commit()
        logger.info(f"Startup: Recovered {recovered_count} tasks, Marked {failed_count} as failed (missing files)")


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
    """Legacy health check endpoint"""
    return {"status": "healthy", "gpu": settings.DEVICE == "cuda"}

@app.get("/health/live")
async def liveness_check():
    """
    Liveness probe - checks if the application is running.
    Returns 200 if the process is alive.
    """
    return {"status": "alive", "timestamp": time.time()}

@app.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness probe - checks if the application is ready to serve traffic.
    Verifies database and Redis connections.
    """
    try:
        # Check database connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        
        # Check Redis connection
        from app.services.cache_service import cache_service
        if not cache_service.redis or not cache_service.redis.ping():
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "Redis connection failed"}
            )
        
        return {
            "status": "ready",
            "database": "connected",
            "redis": "connected",
            "gpu": settings.DEVICE == "cuda",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": str(e)}
        )

