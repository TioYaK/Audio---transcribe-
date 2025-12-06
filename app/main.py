from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import uuid
from typing import List
from sqlalchemy.orm import Session

from .database import engine, get_db, Base
from . import models, crud
from .validation import FileValidator
from .whisper_service import WhisperService

from .config import settings, logger

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Audio Transcription Service")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize services
whisper_service = WhisperService(
    model_size=settings.WHISPER_MODEL,
    device=settings.DEVICE,
    compute_type=settings.COMPUTE_TYPE
)

validator = FileValidator(
    allowed_extensions=settings.ALLOWED_EXTENSIONS,
    max_size_mb=settings.MAX_FILE_SIZE_MB
)

UPLOAD_DIR = settings.UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)

from .cleanup import cleanup_old_files
import asyncio

@app.on_event("startup")
async def startup_event():
    logger.info("Service starting up...")
    logger.info(f"Model: {settings.WHISPER_MODEL}, Device: {settings.DEVICE}")
    # Start cleanup task in background
    asyncio.create_task(cleanup_old_files())


@app.get("/", response_class=HTMLResponse)
async def read_root():
    # We will serve the index.html from templates or just static
    # For simplicity as per design, let's assume it's in templates/index.html
    # But since we haven't implemented templates yet, we'll just check if file exists
    # or return a simple message if not ready.
    # The task says "Serve index.html", usually via templates or static.
    # Let's try to read from templates/index.html
    index_path = os.path.join("templates", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Audio Transcription Service</h1><p>Frontend not ready yet.</p>"

def process_transcription(task_id: str, file_path: str):
    # This function runs in the background
    # We need a new db session here
    from .database import SessionLocal
    background_db = SessionLocal()
    task_store = crud.TaskStore(background_db)
    
    try:
        logger.info(f"Starting processing for task {task_id}")
        # Update status to processing
        task_store.update_status(task_id, "processing")
        
        # Transcribe
        result = whisper_service.transcribe(file_path)
        
        # Save result
        task_store.save_result(
            task_id, 
            text=result["text"], 
            language=result["language"], 
            duration=result["duration"]
        )
        logger.info(f"Task {task_id} completed successfully. Language: {result['language']}, Duration: {result['duration']}s")
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        task_store.update_status(task_id, "failed", error_message=str(e))
    finally:
        background_db.close()
        # Cleanup file if it exists
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Error removing file {file_path}: {e}") 

@app.post("/api/upload")
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Validate file
    # We need to read a bit to validate content, but UploadFile is a SpooledTemporaryFile
    # content_type is available in headers, but we want to verify magic bytes if possible.
    # Reading header
    head = await file.read(2048)
    await file.seek(0)
    
    is_valid, error_msg = validator.validate(
        filename=file.filename,
        file_size=file.size if file.size else 0, # file.size might not be available depending on client
        file_content_head=head
    )
    
    if not is_valid:
        logger.warning(f"Upload validation failed for file {file.filename}: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)

    # 2. Save file
    task_id = str(uuid.uuid4())
    ext = file.filename.split(".")[-1]
    safe_filename = f"{task_id}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
         logger.error(f"Failed to save file for task {task_id}: {e}")
         raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # 3. Create task in DB
    task_store = crud.TaskStore(db)
    task = task_store.create_task(
        filename=file.filename,
        file_path=file_path
    )
    
    # 4. Start background processing
    logger.info(f"Task created: {task.task_id} for file {file.filename}")
    background_tasks.add_task(process_transcription, task.task_id, file_path)
    
    return {
        "task_id": task.task_id,
        "message": "Upload successful, processing started",
        "status_url": f"/api/status/{task.task_id}"
    }

@app.get("/api/status/{task_id}")
async def get_status(task_id: str, db: Session = Depends(get_db)):
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    response = {
        "task_id": task.task_id,
        "status": task.status,
        "created_at": task.created_at,
    }
    
    if task.status == "failed":
        response["error"] = task.error_message
        
    return response

@app.get("/api/result/{task_id}")
async def get_result(task_id: str, db: Session = Depends(get_db)):
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="Transcription not yet completed")
        
    return {
        "task_id": task.task_id,
        "text": task.result_text,
        "language": task.language,
        "duration": task.duration,
        "filename": task.filename,
        "completed_at": task.completed_at
    }

@app.get("/api/download/{task_id}")
async def download_result(task_id: str, db: Session = Depends(get_db)):
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="Transcription not yet completed")
    
    # Generate a temporary file or return StreamingResponse
    # For now, let's just write to a temp file and serve it
    
    # Check if we already stored it? No, we store in DB.
    # Create a temp file path
    filename = f"{os.path.splitext(task.filename)[0]}_{int(task.completed_at.timestamp())}.txt"
    # sanitize
    filename = validator.sanitize_filename(filename)
    
    # We can use a temp directory
    temp_path = os.path.join(UPLOAD_DIR, filename) # reusing upload dir for output? or temp
    
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(task.result_text)
        
    return FileResponse(
        path=temp_path, 
        filename=filename, 
        media_type="text/plain"
    )

# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )
