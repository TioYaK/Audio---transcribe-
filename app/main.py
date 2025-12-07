from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
import shutil
import os
import uuid
from typing import List
from sqlalchemy.orm import Session
from datetime import timedelta
from pydantic import BaseModel

from .database import engine, get_db, Base
from . import models, crud, auth
from .validation import FileValidator
from .whisper_service import WhisperService

from .config import settings, logger
from time import perf_counter

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Audio Transcription Service")

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

@app.on_event("startup")
async def startup_event():
    logger.info("Service starting up...")
    logger.info(f"Model: {settings.WHISPER_MODEL}, Device: {settings.DEVICE}")
    asyncio.create_task(cleanup_old_files())
    
    # Create Admin User
    db = next(get_db())
    admin_user = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin_user:
        hashed_pwd = auth.get_password_hash("Kx3nvqt1!")
        new_user = models.User(
            username="admin", 
            hashed_password=hashed_pwd,
            is_active="True",
            is_admin="True"
        )
        db.add(new_user)
        db.commit()
        logger.info("Created Admin user")


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
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
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
         
    hashed = auth.get_password_hash(new_password)
    task_store = crud.TaskStore(db)
    if task_store.update_user_password(user_id, hashed):
        return {"message": "Senha atualizada"}
    raise HTTPException(status_code=404, detail="Usuário não encontrado")

@app.post("/api/admin/user/{user_id}/limit")
async def admin_set_limit(user_id: str, payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.is_admin != "True":
        raise HTTPException(status_code=403, detail="Acesso exclusivo para administradores")
        
    limit = payload.get("limit")
    if limit is None or not isinstance(limit, int) or limit < 0:
         raise HTTPException(status_code=400, detail="Limite inválido")
         
    task_store = crud.TaskStore(db)
    if task_store.update_user_limit(user_id, limit):
        return {"message": "Limite atualizado"}
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


def process_transcription(task_id: str, file_path: str):
    from .database import SessionLocal
    background_db = SessionLocal()
    task_store = crud.TaskStore(background_db)
    
    try:
        logger.info(f"Starting processing for task {task_id}")
        task_store.update_status(task_id, "processing")
        
        start_ts = perf_counter()
        result = whisper_service.transcribe(file_path)
        processing_time = perf_counter() - start_ts

        task_store.save_result(
            task_id, 
            text=result["text"], 
            language=result["language"], 
            duration=result["duration"],
            processing_time=processing_time
        )
        logger.info(f"Task {task_id} completed successfully.")
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        task_store.update_status(task_id, "failed", error_message=str(e))
    finally:
        background_db.close()
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Error removing file {file_path}: {e}") 

@app.post("/api/upload")
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    task_store = crud.TaskStore(db)
    
    # Check limits if not admin
    if current_user.is_admin != "True":
        usage = task_store.count_user_tasks(current_user.id)
        limit = current_user.transcription_limit if current_user.transcription_limit is not None else 10
        if usage >= limit:
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
    task = task_store.create_task(
        filename=file.filename,
        file_path=file_path,
        owner_id=current_user.id
    )
    
    # 4. Start background processing
    background_tasks.add_task(process_transcription, task.task_id, file_path)
    
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

    response = {
        "task_id": task.task_id,
        "status": task.status,
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
        "completed_at": task.completed_at
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

@app.get("/api/history")
async def get_history(all: bool = False, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Get all completed transcriptions. Admins can request all=True."""
    task_store = crud.TaskStore(db)
    
    if all and current_user.is_admin == "True":
        return task_store.get_all_tasks_admin()
    
    # Filter by user (Default)
    tasks = db.query(models.TranscriptionTask).filter(
        models.TranscriptionTask.status == "completed",
        models.TranscriptionTask.owner_id == current_user.id
    ).order_by(models.TranscriptionTask.completed_at.desc()).all()
    
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
    deleted = task_store.clear_history(current_user.id)
    return {"deleted": deleted}


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

# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "Erro Interno do Servidor", "detail": str(exc)},
    )
