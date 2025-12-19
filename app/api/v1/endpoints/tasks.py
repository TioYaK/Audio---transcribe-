
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
import os
import shutil
import uuid
import magic
import asyncio
from datetime import datetime
import io
import csv

from app import models, auth, crud
# from app.main import whisper_service # Circular import issue. We need a service instance.
# Solution: Instantiate service in dependency or singleton. 
# For now, we will import the CLASS and create a global instance in api/deps.py or similar, 
# BUT main.py already creates it.
# Let's import the instance from a new file `app.core.services` to avoid main.py circular.

from app.core.config import settings, logger
from app.database import get_db
from app.validation import FileValidator
from app.core.queue import task_queue

# Note: We need the whisper_service instance. 
# I will initialize it in `app.core.services` in the next step.
from app.core.services import whisper_service

router = APIRouter()

@router.post("/upload")
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
    if not current_user.is_admin:
        usage = task_store.count_user_tasks(current_user.id)
        limit = current_user.transcription_limit if current_user.transcription_limit is not None else 100
        if limit > 0 and usage >= limit:
             raise HTTPException(status_code=403, detail=f"Limite de transcrições atingido ({usage}/{limit}). Contate o admin.")

    # Validate file (validates extension, MIME type, and file size)
    try:
        safe_filename, file_size = await FileValidator.validate_file(file)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"File validation error: {e}")
        raise HTTPException(400, f"Erro na validação do arquivo: {str(e)}")

    # --- Filename Sanitization & Collision Handling ---
    import re
    
    # 1. Cleaning: Remove digits and underscores that look like clutter
    # Strategy: Replace underscores with space, remove digits, strip.
    raw_name = file.filename
    # Remove extension for processing
    base, ext = os.path.splitext(raw_name)
    
    # Replace _ with space
    clean_base = base.replace("_", " ")
    
    # Remove digits (often random IDs like 12345_Name)
    # Be careful not to kill "Number 5", but user asked for "random numbers".
    # Regex: Remove isolated number blocks or numbers at start/end
    clean_base = re.sub(r'\b\d+\b', '', clean_base) # Remove standalone numbers
    clean_base = re.sub(r'^\d+|\d+$', '', clean_base) # Remove start/end numbers
    
    # Remove 'Resgate' (case insensitive)
    clean_base = re.sub(r'(?i)resgate', '', clean_base)
    
    # Clean standardizing spaces
    clean_base = " ".join(clean_base.split())
    if not clean_base: clean_base = "Audio" # Fallback if empty
    
    final_display_name = clean_base + ext
    
    # 2. Collision Detection (Append _2, _3...)
    # Check if user already has a task with this EXACT display name
    # We query the DB for existing names for this user
    existing_count = db.query(models.TranscriptionTask).filter(
        models.TranscriptionTask.owner_id == current_user.id,
        models.TranscriptionTask.filename == final_display_name
    ).count()
    
    if existing_count > 0:
        # Check iteratively for availability
        counter = 2
        while True:
            candidate = f"{clean_base} ({counter}){ext}"
            exists = db.query(models.TranscriptionTask).filter(
                models.TranscriptionTask.owner_id == current_user.id,
                models.TranscriptionTask.filename == candidate
            ).count()
            if exists == 0:
                final_display_name = candidate
                break
            counter += 1

    # Generate unique task ID and filepath
    task_id = str(uuid.uuid4())
    unique_filename = f"{task_id}_{safe_filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    # Create task FIRST (DB record)
    options = {"timestamp": timestamp, "diarization": diarization}
    task = task_store.create_task(
        filename=final_display_name,
        file_path=file_path,
        owner_id=current_user.id,
        options=options
    )
    
    # Read content properly before response (fixes closed file error in background task)
    file_content = await file.read()

    # Save file AND enqueue AFTER successful save (fixes race condition)
    async def save_and_enqueue(content):
        """Save uploaded file and enqueue ONLY after successful save"""
        try:
            # 2. Write to disk (runs in thread pool to not block event loop)
            import aiofiles
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            logger.info(f"✅ File saved: {unique_filename}")
            
            # 3. ONLY NOW enqueue for processing (guarantees file exists)
            await task_queue.put((task.task_id, file_path, options))
            logger.info(f"✅ Task enqueued: {task.task_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save/enqueue {unique_filename}: {e}")
            # Mark task as failed if file save fails
            task.status = "failed"
            task.error_message = f"Falha ao salvar arquivo: {str(e)}"
            # Precisamos de nova sessão pois 'db' pode estar fechada/inválida no bg task? 
            # SQLAlchemy session from Depends usually scoped to request. 
            # Safe to use if not async strict? Actually safe in fastapi usually.
            # But let's verify commit.
            try:
                db.add(task)
                db.commit()
            except:
                pass # Best effort
    
    # Schedule background save + enqueue (non-blocking)
    background_tasks.add_task(save_and_enqueue, file_content)
    
    return {
        "task_id": task.task_id,
        "message": "Envio realizado com sucesso",
        "status_url": f"/api/status/{task.task_id}"
    }

@router.get("/status/{task_id}")
async def get_status(task_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    if task.owner_id != current_user.id and not current_user.is_admin:
         raise HTTPException(status_code=403, detail="Não autorizado")

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
    
    # Use actual progress from database instead of fake time-based estimation
    progress = task.progress if task.progress else 0
    if task.status == "completed":
        progress = 100
    elif task.status == "queued":
        progress = 0
    
    response["progress"] = progress
    
    if task.status == "failed":
        response["error"] = task.error_message
        
    return response

@router.get("/result/{task_id}")
async def get_result(task_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
        
    if task.owner_id != current_user.id and not current_user.is_admin:
         raise HTTPException(status_code=403, detail="Não autorizado")

    return {
        "task_id": task.task_id,
        "text": task.result_text,
        "text_corrected": task.result_text_corrected,  # Spell-corrected version
        "language": task.language,
        "duration": task.duration,
        "processing_time": task.processing_time,
        "filename": task.filename,
        "completed_at": task.completed_at,
        "summary": task.summary,
        "topics": task.topics,
        "analysis_status": task.analysis_status # Added field
    }

@router.get("/download/{task_id}")
async def download_result(task_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
        
    if task.owner_id != current_user.id and not current_user.is_admin:
         raise HTTPException(status_code=403, detail="Não autorizado")
        
    filename = f"{os.path.splitext(task.filename)[0]}.txt"
    content = task.result_text or ""
    
    # Use StreamingResponse to avoid creating temp files that never get deleted
    return StreamingResponse(
        iter([content]),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/audio/{task_id}")
async def get_audio_file(task_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
        
    if task.owner_id != current_user.id and not current_user.is_admin:
         raise HTTPException(status_code=403, detail="Não autorizado")
    
    if not os.path.exists(task.file_path):
        raise HTTPException(status_code=404, detail="Arquivo de áudio não encontrado no servidor")

    media_type = "application/octet-stream"
    try:
        mime = magic.Magic(mime=True)
        media_type = mime.from_file(task.file_path)
    except Exception as e:
        import mimetypes
        mt, _ = mimetypes.guess_type(task.file_path)
        if mt: media_type = mt
    
    return FileResponse(
        path=task.file_path, 
        filename=task.filename, 
        media_type=media_type
    )

@router.get("/history")
async def get_history(
    all: bool = False, 
    limit: int = 50,  # Paginação: itens por página
    offset: int = 0,  # Paginação: deslocamento
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    task_store = crud.TaskStore(db)
    
    if all and current_user.is_admin:
        tasks = task_store.get_all_tasks_admin_paginated(offset=offset, limit=limit)
        total = task_store.count_all_tasks()
    else:
        tasks = task_store.get_user_tasks_paginated(
            owner_id=current_user.id,
            offset=offset,
            limit=limit
        )
        total = task_store.count_user_completed_tasks(current_user.id)
    
    return {
        "tasks": tasks,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total
    }

@router.post("/rename/{task_id}")
async def rename_task(task_id: str, payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    new_name = payload.get("new_name")
    if not new_name:
        raise HTTPException(status_code=400, detail="Novo nome é obrigatório")
    
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    if task.owner_id != current_user.id and not current_user.is_admin:
         raise HTTPException(status_code=403, detail="Não autorizado")

    task = task_store.rename_task(task_id, new_name)
    return {"task_id": task.task_id, "filename": task.filename}

@router.post("/task/{task_id}/regenerate")
async def regenerate_analysis(task_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    if task.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Não autorizado")
    
    if not task.result_text:
        raise HTTPException(status_code=400, detail="Tarefa não possui transcrição para analisar")
    
    try:
        logger.info(f"Regenerating analysis for task {task_id}")
        analysis = whisper_service.generate_analysis(task.result_text)
        
        task.summary = analysis.get("summary")
        task.topics = analysis.get("topics")
        db.commit()
        
        return {
            "task_id": task_id,
            "summary": task.summary,
            "topics": task.topics,
            "message": "Análise regenerada com sucesso"
        }
    except Exception as e:
        logger.error(f"Failed to regenerate analysis for {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao regenerar análise: {str(e)}")



# Missing endpoint for status update
@router.post("/task/{task_id}/analysis")
async def update_analysis_status(
    task_id: str, 
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    status = payload.get("status")
    if not status:
         raise HTTPException(status_code=400, detail="Status é obrigatório")

    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    if task.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Não autorizado")
    
    updated_task = task_store.update_analysis_status(task_id, status)
    return {"task_id": updated_task.task_id, "analysis_status": updated_task.analysis_status}

# Use raw dict for update to avoid import complexity
@router.put("/task/{task_id}/notes")
async def update_notes(
    task_id: str, 
    update: dict,
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if not current_user.is_admin and task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    task.notes = update.get("notes", "")
    db.commit()
    return {"status": "ok", "notes": task.notes}

@router.delete("/task/{task_id}")
async def delete_task(task_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    if task.owner_id != current_user.id and not current_user.is_admin:
         raise HTTPException(status_code=403, detail="Não autorizado")

    if task_store.delete_task(task_id):
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="Task not found")

@router.get("/export")
async def export_csv_route(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    
    if current_user.is_admin:
        data = task_store.get_all_tasks_admin(include_text=True)
    else:
        tasks = db.query(models.TranscriptionTask).filter(
            models.TranscriptionTask.owner_id == current_user.id
        ).order_by(models.TranscriptionTask.created_at.desc()).all()
        data = [task.to_dict(include_text=True) for task in tasks]
        for d in data: d['owner_name'] = current_user.full_name or current_user.username

    output = io.StringIO()
    # BOM for Excel UTF-8 compatibility
    output.write('\ufeff')
    # Use semicolon for Excel compatibility in regions that use comma for decimals (like Brazil)
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)
    
    headers = ["Arquivo", "ID", "Resumo", "Proprietário", "Transcrição Completa"]
    writer.writerow(headers)
    
    for row in data:
        writer.writerow([
            row.get('filename'),
            row.get('task_id'),
            str(row.get('summary', ''))[:5000], # Keep summary reasonable length if huge
            row.get('owner_name', 'Eu'),
            str(row.get('result_text', '')) # Full text, no truncation
        ])
        
    output.seek(0)
    filename = f"relatorio_transcricoes_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]), 
        media_type="text/csv", 
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/reports")
async def get_reports(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task_store = crud.TaskStore(db)
    target_id = None if current_user.is_admin else current_user.id
    return task_store.get_stats(target_id)
