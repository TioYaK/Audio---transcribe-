from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
import shutil
import os
import uuid
from typing import List
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from pydantic import BaseModel
import magic
from typing import Optional

class KeywordsUpdate(BaseModel):
    keywords: Optional[str] = None
    keywords_red: Optional[str] = None
    keywords_green: Optional[str] = None

from .database import engine, get_db, Base
from . import models, crud, auth
from .validation import FileValidator
from .whisper_service import WhisperService

from .config import settings, logger
from time import perf_counter

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Careca.ai")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

task_queue: asyncio.Queue = asyncio.Queue()
# Consumer that processes tasks sequentially
async def task_consumer():
    from .database import SessionLocal
    while True:
        item = await task_queue.get()
        if len(item) == 3:
            task_id, file_path, options = item
        else:
             # Backward compatibility or simple tuple
             task_id, file_path = item
             options = {}
             
        db = SessionLocal()
        task_store = crud.TaskStore(db)
        
        # Check if task still exists before processing
        task = task_store.get_task(task_id)
        if not task:
            logger.info(f"Task {task_id} not found (deleted?), skipping.")
            db.close()
            task_queue.task_done()
            continue
            
        # Mark as processing and reset progress
        task_store.update_status(task_id, "processing")
        task_store.update_progress(task_id, 0)
        try:
            # Run blocking transcription in a separate thread
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, process_transcription, task_id, file_path, options)
            
            task_store.update_progress(task_id, 100)
        except Exception:
            task_store.update_progress(task_id, 0)
        finally:
            db.close()
        task_queue.task_done()

@app.on_event("startup")
async def startup_event():
    logger.info("Service starting up...")
    
    # DB Migration Check for new Analysis columns
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # Add summary column if not exists
            try:
                conn.execute(text("ALTER TABLE transcription_tasks ADD COLUMN summary TEXT"))
                logger.info("Migrated DB: Added summary column")
            except Exception:
                pass # Column likely exists
            
            # Add topics column if not exists
            try:
                conn.execute(text("ALTER TABLE transcription_tasks ADD COLUMN topics TEXT"))
                logger.info("Migrated DB: Added topics column")
            except Exception:
                pass # Column likely exists
    except Exception as e:
        logger.warning(f"DB Migration check skipped: {e}")

    logger.info(f"Model: {settings.WHISPER_MODEL}, Device: {settings.DEVICE}")
    asyncio.create_task(cleanup_old_files())
    # Start the queue consumer (Parallelism: 2 - Concurrent Processing)
    for i in range(2):
        asyncio.create_task(task_consumer())
        logger.info(f"Started task_consumer worker {i+1}")
    
    # Create Admin User with empty password
    db = next(get_db())
    admin_user = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin_user:
        # Hash empty password for admin
        hashed_pwd = auth.get_password_hash("")
        new_user = models.User(
            username="admin",
            hashed_password=hashed_pwd,
            is_active="True",
            is_admin="True"
        )
        db.add(new_user)
        db.commit()
        db.commit()
        logger.info("Created Admin user with empty password")
    
    # Auto-migration: Add 'options' column if not exists
    try:
        from sqlalchemy import text
        db.execute(text("ALTER TABLE transcription_tasks ADD COLUMN options TEXT"))
        db.commit()
        logger.info("Migration: Added 'options' column.")
    except Exception as e:
        # Column likely exists
        # logger.info(f"Migration skip: {e}")
        db.rollback()
    
    # Cleanup: Cancel and delete all pending/processing tasks on startup
    # This ensures a clean slate as requested
    pending_tasks = db.query(models.TranscriptionTask).filter(
        models.TranscriptionTask.status.in_(["queued", "processing"])
    ).all()
    
    for task in pending_tasks:
        logger.info(f"Cleanup: Removing unfinished task {task.task_id} from previous session.")
        # Attempt to delete file
        try:
            if os.path.exists(task.file_path):
                os.remove(task.file_path)
        except Exception as e:
            logger.error(f"Error deleting file for task {task.task_id}: {e}")
            
        db.delete(task)
    
    db.commit()


@app.get("/", response_class=HTMLResponse)
async def read_root():
    index_path = os.path.join("templates", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Audio Transcription Service</h1><p>Frontend not ready yet.</p>"

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    login_path = os.path.join("templates", "login.html")
    if os.path.exists(login_path):
        with open(login_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Login page not found."

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    # Special case: admin can login with any password (no password check)
    if user and user.username == "admin":
        password_valid = True
    elif user:
        password_valid = auth.verify_password(form_data.password, user.hashed_password)
    else:
        password_valid = False
    
    if not user or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.is_active != "True":
        raise HTTPException(status_code=400, detail="Conta aguardando aprovação")
        
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "is_admin": user.is_admin == "True",
        "username": user.username
    }

class RegisterModel(BaseModel):
    username: str
    password: str
    full_name: str
    email: str

@app.post("/register")
async def register(user: RegisterModel, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Nome de usuário já existe")
    
    hashed = auth.get_password_hash(user.password)
    task_store = crud.TaskStore(db)
    new_user = task_store.create_user(
        username=user.username, 
        hashed_password=hashed,
        full_name=user.full_name,
        email=user.email
    )
    return {"message": "Usuário criado. Aguarde aprovação do administrador."}


# Admin Endpoints
@app.get("/api/logs")
async def get_logs(limit: int = 100, current_user: models.User = Depends(auth.get_current_user)):
    """Get application logs from file"""
    if current_user.is_admin != "True":
        raise HTTPException(status_code=403, detail="Acesso restrito ao Administrador")
    
    log_file = "/app/data/app.log"
    if not os.path.exists(log_file):
        return {"logs": ["Log file not found."]}
        
    try:
        # Efficiently read last N lines (simple consistency)
        with open(log_file, "r", encoding="utf-8", errors='ignore') as f:
            # Read all is okay for small logs, but for large...
            # A simple approach for < 10MB logs
            lines = f.readlines()
            return {"logs": lines[-limit:]}
    except Exception as e:
        return {"logs": [f"Error reading logs: {str(e)}"]}

@app.get("/api/admin/users")
async def get_all_users(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.is_admin != "True":
        raise HTTPException(status_code=403, detail="Acesso exclusivo para administradores")
    task_store = crud.TaskStore(db)
    users = task_store.get_users()
    
    # Calculate usage for each user
    users_data = []
    for u in users:
        usage = task_store.count_user_tasks(u.id)
        users_data.append({
            "id": u.id, 
            "username": u.username, 
            "full_name": u.full_name, 
            "email": u.email, 
            "is_active": u.is_active, 
            "is_admin": u.is_admin,
            "transcription_limit": u.transcription_limit,
            "usage": usage
        })
    return users_data

@app.post("/api/admin/approve/{user_id}")
async def approve_user(user_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.is_admin != "True":
        raise HTTPException(status_code=403, detail="Acesso exclusivo para administradores")
    task_store = crud.TaskStore(db)
    task_store.approve_user(user_id)
    return {"message": "Usuário aprovado"}

@app.post("/api/admin/user/{user_id}/password")
async def admin_change_password(user_id: str, payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.is_admin != "True":
        raise HTTPException(status_code=403, detail="Acesso exclusivo para administradores")
        
    new_password = payload.get("password")
    if not new_password or len(new_password) < 4:
         raise HTTPException(status_code=400, detail="Senha muito curta")
         
    task_store = crud.TaskStore(db)
    if task_store.update_user_password(user_id, hashed):
        return {"message": "Senha atualizada"}
    raise HTTPException(status_code=404, detail="Usuário não encontrado")

@app.delete("/api/admin/user/{user_id}")
async def delete_user(user_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.is_admin != "True":
        raise HTTPException(status_code=403, detail="Acesso exclusivo para administradores")
    if user_id == current_user.id:
         raise HTTPException(status_code=400, detail="Não é possível excluir sua própria conta de admin")
         
    task_store = crud.TaskStore(db)
    if task_store.delete_user(user_id):
        return {"message": "Usuário excluído"}
    raise HTTPException(status_code=404, detail="Usuário não encontrado")


@app.get("/api/user/info")
async def get_user_info(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Get current user's transcription usage and limit"""
    task_store = crud.TaskStore(db)
    usage = task_store.count_user_tasks(current_user.id)
    limit = current_user.transcription_limit if current_user.transcription_limit is not None else 100
    
    return {
        "username": current_user.username,
        "is_admin": current_user.is_admin,
        "usage": usage,
        "limit": limit
    }


@app.post("/api/admin/user/{user_id}/toggle-admin")
async def toggle_admin_status(user_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.is_admin != "True":
        raise HTTPException(status_code=403, detail="Acesso exclusivo para administradores")
    if user_id == current_user.id:
         raise HTTPException(status_code=400, detail="Não é possível alterar seu próprio status de admin")
         
    task_store = crud.TaskStore(db)
    if task_store.toggle_admin_status(user_id):
        return {"message": "Status de admin alterado"}
    raise HTTPException(status_code=404, detail="Usuário não encontrado")



def process_transcription(task_id: str, file_path: str, options: dict = {}):
    from .database import SessionLocal
    background_db = SessionLocal()
    task_store = crud.TaskStore(background_db)
    
    try:
        logger.info(f"Starting processing for task {task_id}")
        task_store.update_status(task_id, "processing")
        
        start_ts = perf_counter()
        
        def update_prog(pct):
            task_store.update_progress(task_id, pct)
            
        result = whisper_service.transcribe(file_path, options=options, progress_callback=update_prog)
        processing_time = perf_counter() - start_ts
        
        # Save Result
        task_store.save_result(
            task_id=task_id,
            text=result.get("text", ""),
            language=result.get("language", "unknown"),
            duration=result.get("duration", 0.0),
            processing_time=processing_time,
            summary=result.get("summary"),
            topics=result.get("topics")
        )
        logger.info(f"Task {task_id} completed successfully.")

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        task_store.update_status(task_id, "failed", error_message=str(e))
    finally:
        background_db.close()
        # Do not delete file so it can be played/downloaded later 

@app.post("/api/upload")
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
    timestamp: bool = Form(True),
    diarization: bool = Form(True)
):
    task_store = crud.TaskStore(db)
    
    # Check limits if not admin
    if current_user.is_admin != "True":
        usage = task_store.count_user_tasks(current_user.id)
        limit = current_user.transcription_limit if current_user.transcription_limit is not None else 100
        # If limit is 0, it means unlimited
        if limit > 0 and usage >= limit:
             raise HTTPException(status_code=403, detail=f"Limite de transcrições atingido ({usage}/{limit}). Contate o admin.")

    # 1. Validate file
    head = await file.read(2048)
    await file.seek(0)
    
    is_valid, error_msg = validator.validate(
        filename=file.filename,
        file_size=file.size if file.size else 0,
        file_content_head=head
    )
    
    if not is_valid:
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
         raise HTTPException(status_code=500, detail=f"Falha ao salvar arquivo: {str(e)}")

    # 3. Create task in DB
    options = {"timestamp": timestamp, "diarization": diarization}
    task = task_store.create_task(
        filename=file.filename,
        file_path=file_path,
        owner_id=current_user.id,
        options=options
    )
    
    # 4. Enqueue task for sequential processing with options
    await task_queue.put((task.task_id, file_path, options))
    
    return {
        "task_id": task.task_id,
        "message": "Envio realizado com sucesso",
        "status_url": f"/api/status/{task.task_id}"
    }

@app.get("/api/status/{task_id}")
async def get_status(task_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    # Owner check
    if task.owner_id != current_user.id and current_user.is_admin != "True":
         raise HTTPException(status_code=403, detail="Não autorizado")

    # Determine a user‑friendly phase based on the internal status
    phase_map = {
        "queued": "queued",
        "processing": "processing",
        "completed": "completed",
        "failed": "failed",
    }
    response = {
        "task_id": task.task_id,
        "status": task.status,
        "phase": phase_map.get(task.status, "unknown"),
        "created_at": task.created_at,
    }
    
    progress = 0
    if task.status == "processing" and task.started_at:
        from datetime import datetime
        elapsed = (datetime.utcnow() - task.started_at).total_seconds()
        progress = min(90, int((elapsed / 30) * 100))
    elif task.status == "completed":
        progress = 100
    
    response["progress"] = progress
    
    if task.status == "failed":
        response["error"] = task.error_message
        
    return response

@app.get("/api/result/{task_id}")
async def get_result(task_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
        
    if task.owner_id != current_user.id and current_user.is_admin != "True":
         raise HTTPException(status_code=403, detail="Não autorizado")

    return {
        "task_id": task.task_id,
        "text": task.result_text,
        "language": task.language,
        "duration": task.duration,
        "processing_time": task.processing_time,
        "filename": task.filename,
        "completed_at": task.completed_at,
        "summary": task.summary,
        "topics": task.topics
    }

@app.get("/api/download/{task_id}")
async def download_result(task_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
        
    if task.owner_id != current_user.id and current_user.is_admin != "True":
         raise HTTPException(status_code=403, detail="Não autorizado")
        
    filename = f"{os.path.splitext(task.filename)[0]}.txt"
    temp_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(task.result_text or "")
        
    return FileResponse(
        path=temp_path, 
        filename=filename, 
        media_type="text/plain"
    )

@app.get("/api/audio/{task_id}")
async def get_audio_file(task_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Stream/Download the original audio file"""
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
        
    if task.owner_id != current_user.id and current_user.is_admin != "True":
         raise HTTPException(status_code=403, detail="Não autorizado")
    
    if not os.path.exists(task.file_path):
        raise HTTPException(status_code=404, detail="Arquivo de áudio não encontrado no servidor")

    # Determine media type based on extension with Fallback
    media_type = "application/octet-stream"
    try:
        mime = magic.Magic(mime=True)
        media_type = mime.from_file(task.file_path)
    except Exception as e:
        logger.warning(f"Magic lib failed ({e}), falling back to mimetypes")
        import mimetypes
        mt, _ = mimetypes.guess_type(task.file_path)
        if mt:
            media_type = mt
    
    return FileResponse(
        path=task.file_path, 
        filename=task.filename,
        media_type=media_type
    )

@app.get("/api/history")
async def get_history(all: bool = False, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Get all completed transcriptions. Admins can request all=True."""
    task_store = crud.TaskStore(db)
    
    if all and current_user.is_admin == "True":
        return task_store.get_all_tasks_admin()
    
    # Filter by user (Default) - Show ALL tasks (including queued/processing) for transparency
    tasks = db.query(models.TranscriptionTask).filter(
        models.TranscriptionTask.owner_id == current_user.id
    ).order_by(models.TranscriptionTask.created_at.desc()).all()
    
    return [task.to_dict() for task in tasks]


@app.post("/api/rename/{task_id}")
async def rename_task(task_id: str, payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    new_name = payload.get("new_name")
    if not new_name:
        raise HTTPException(status_code=400, detail="Novo nome é obrigatório")
    
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    if task.owner_id != current_user.id and current_user.is_admin != "True":
         raise HTTPException(status_code=403, detail="Não autorizado")

    task = task_store.rename_task(task_id, new_name)
    return {"task_id": task.task_id, "filename": task.filename}


@app.post("/api/task/{task_id}/analysis")
async def update_task_analysis(task_id: str, payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    status = payload.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="Status é obrigatório")
    
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    if task.owner_id != current_user.id and current_user.is_admin != "True":
         raise HTTPException(status_code=403, detail="Não autorizado")

    task = task_store.update_analysis_status(task_id, status)
    return {"task_id": task.task_id, "analysis_status": task.analysis_status}


@app.get("/api/reports")
async def get_reports(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    
    # If admin, fetch global stats (owner_id=None)
    # If user, fetch own stats
    target_id = None if current_user.is_admin == "True" else current_user.id
    
    stats = task_store.get_stats(target_id)
    return stats


@app.post("/api/history/clear")
async def clear_history(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    
    if current_user.is_admin == "True":
        deleted = task_store.clear_all_history()
    else:
        deleted = task_store.clear_history(current_user.id)
        
    return {"deleted": deleted}


@app.get("/api/export")
async def export_csv(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    from fastapi.responses import StreamingResponse
    import csv
    import io
    
    task_store = crud.TaskStore(db)
    
    # Fetch Data
    if current_user.is_admin == "True":
        data = task_store.get_all_tasks_admin(include_text=True) # Returns list of dicts with owner_name
    else:
        # Re-use manual fetch logic for clean dicts
        tasks = db.query(models.TranscriptionTask).filter(
            models.TranscriptionTask.owner_id == current_user.id
        ).order_by(models.TranscriptionTask.created_at.desc()).all()
        data = [task.to_dict(include_text=True) for task in tasks]
        # Add basic own name
        for d in data: d['owner_name'] = current_user.full_name or current_user.username

    # CSV Generation
    output = io.StringIO()
    # Write BOM for Excel UTF-8 compatibility
    output.write('\ufeff')
    
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    
    # Headers in Portuguese
    headers = [
        "ID da Tarefa", 
        "Nome do Arquivo", 
        "Status", 
        "Data de Envio", 
        "Data de Conclusão", 
        "Duração (s)", 
        "Tempo de Processamento (s)", 
        "Proprietário", 
        "Status da Análise", 
        "Resumo IA", 
        "Tópicos", 
        "Transcrição Completa"
    ]
    
    # Switch to TAB separation - much safer for copy-pasting into Excel
    # We use .txt extension so Excel triggers the wizard automatically or handles paste better
    writer = csv.writer(output, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    
    for row in data:
        def clean(val, limit=32000):
            if val is None: return ""
            s = str(val)
            # Remove all whitespace chars (tabs, newlines) and replace with space
            s = " ".join(s.split())
            # Truncate to Excel Safe Limit (32767 is max, 32000 is safe)
            if len(s) > limit:
                return s[:limit] + " [TRUNCADO PELO EXCEL]"
            return s
            
        def fmt_float(val):
            if val is None: return ""
            return str(val).replace('.', ',')

        writer.writerow([
            row.get('task_id', ''),
            row.get('filename', ''),
            row.get('status', ''),
            row.get('created_at', ''),
            row.get('completed_at', ''),
            fmt_float(row.get('duration')),
            fmt_float(row.get('processing_time')),
            clean(row.get('owner_name', '')),
            clean(row.get('analysis_status', '')),
            clean(row.get('summary', '')),
            clean(row.get('topics', '')),
            clean(row.get('result_text', ''))
        ])
        
    output.seek(0)
    
    # Changed filename to .txt which is standard for Tab delimited
    filename = f"relatorio_transcricoes_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
    
    response = StreamingResponse(iter([output.getvalue()]), media_type="text/plain; charset=utf-8")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response
        
    output.seek(0)
    
    filename = f"transcricoes_relatorio_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

@app.delete("/api/task/{task_id}")
async def delete_task(task_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    if task.owner_id != current_user.id and current_user.is_admin != "True":
         raise HTTPException(status_code=403, detail="Não autorizado")

    if task_store.delete_task(task_id):
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="Task not found")
# Global Config Endpoints
@app.get("/api/config/keywords")
async def get_keywords(db: Session = Depends(get_db)):
    task_store = crud.TaskStore(db)
    kw_yellow = task_store.get_global_config("keywords")
    kw_red = task_store.get_global_config("keywords_red")
    kw_green = task_store.get_global_config("keywords_green")
    
    return {
        "keywords": kw_yellow or "", 
        "keywords_red": kw_red or "", 
        "keywords_green": kw_green or ""
    }

@app.post("/api/admin/config/keywords")
async def update_keywords(config: KeywordsUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.is_admin != "True":
        raise HTTPException(status_code=403, detail="Acesso exclusivo para administradores")
        
    task_store = crud.TaskStore(db)
    
    # Save each key if present
    if config.keywords is not None:
        task_store.update_global_config("keywords", config.keywords)
    if config.keywords_red is not None:
        task_store.update_global_config("keywords_red", config.keywords_red)
    if config.keywords_green is not None:
        task_store.update_global_config("keywords_green", config.keywords_green)
        
    return {"status": "updated"}

# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "Erro Interno do Servidor", "detail": str(exc)},
    )
