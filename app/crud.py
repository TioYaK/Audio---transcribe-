from sqlalchemy.orm import Session
from . import models
from datetime import datetime
import uuid
from typing import Optional, List
import os

class TaskStore:
    def __init__(self, db: Session):
        self.db = db

    def create_task(self, filename: str, file_path: str, owner_id: str, options: dict = None) -> models.TranscriptionTask:
        import json
        options_str = json.dumps(options) if options else None
        
        task = models.TranscriptionTask(
            filename=filename,
            file_path=file_path,
            owner_id=owner_id,
            status="queued",
            progress=0,
            options=options_str
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_task(self, task_id: str) -> Optional[models.TranscriptionTask]:
        return self.db.query(models.TranscriptionTask).filter(
            models.TranscriptionTask.task_id == task_id
        ).first()

    def update_progress(self, task_id: str, progress: int):
        task = self.get_task(task_id)
        if task:
            task.progress = progress
            self.db.commit()
            self.db.refresh(task)
        return task
        return task

    def update_status(self, task_id: str, status: str, error_message: str = None):
        task = self.get_task(task_id)
        if task:
            task.status = status
            if status == "processing":
                task.started_at = datetime.utcnow()
            elif status in ["completed", "failed"]:
                task.completed_at = datetime.utcnow()
            
            if error_message:
                task.error_message = error_message
                
            self.db.commit()
            self.db.refresh(task)
        return task

    def save_result(self, task_id: str, text: str, language: str, duration: float, processing_time: float, summary: str = None, topics: str = None):
        task = self.get_task(task_id)
        if task:
            task.status = "completed"
            task.result_text = text
            task.language = language
            task.duration = duration
            task.processing_time = processing_time
            task.summary = summary
            task.topics = topics
            task.analysis_status = "Pendente de análise" if summary else "Não processado"
            task.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(task)
        return task
    
    def rename_task(self, task_id: str, new_name: str) -> Optional[models.TranscriptionTask]:
        task = self.get_task(task_id)
        if task:
            task.filename = new_name
            self.db.commit()
            self.db.refresh(task)
        return task

    def update_analysis_status(self, task_id: str, status: str) -> Optional[models.TranscriptionTask]:
        task = self.get_task(task_id)
        if task:
            task.analysis_status = status
            self.db.commit()
            self.db.refresh(task)
        return task

    def clear_history(self, owner_id: str):
        # Get tasks before deleting to clean up files
        tasks = self.db.query(models.TranscriptionTask).filter(
            models.TranscriptionTask.status.in_(["completed", "failed"]),
            models.TranscriptionTask.owner_id == owner_id
        ).all()
        
        count = len(tasks)
        
        # Delete files
        for task in tasks:
            if task.file_path and os.path.exists(task.file_path):
                try:
                    os.remove(task.file_path)
                except OSError:
                    pass
            # Delete processed .wav
            if task.file_path:
                wav_path = os.path.splitext(task.file_path)[0] + '.wav'
                if wav_path != task.file_path and os.path.exists(wav_path):
                    try:
                        os.remove(wav_path)
                    except OSError:
                        pass
        
        # Delete from DB
        self.db.query(models.TranscriptionTask).filter(
            models.TranscriptionTask.status.in_(["completed", "failed"]),
            models.TranscriptionTask.owner_id == owner_id
        ).delete(synchronize_session=False)
        self.db.commit()
        return count

    def clear_all_history(self):
        """Delete ALL tasks for ALL users (Admin only)"""
        # Get all tasks before deleting to clean up files
        tasks = self.db.query(models.TranscriptionTask).all()
        
        count = len(tasks)
        
        # Delete files
        for task in tasks:
            if task.file_path and os.path.exists(task.file_path):
                try:
                    os.remove(task.file_path)
                except OSError:
                    pass
            # Delete processed .wav
            if task.file_path:
                wav_path = os.path.splitext(task.file_path)[0] + '.wav'
                if wav_path != task.file_path and os.path.exists(wav_path):
                    try:
                        os.remove(wav_path)
                    except OSError:
                        pass
        
        # Delete from DB
        self.db.query(models.TranscriptionTask).delete(synchronize_session=False)
        self.db.commit()
        return count

    def delete_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if task:
            # Delete original file from disk
            if task.file_path and os.path.exists(task.file_path):
                try:
                    os.remove(task.file_path)
                    logger.info(f"Deleted file: {task.file_path}")
                except OSError as e:
                    logger.warning(f"Failed to delete file {task.file_path}: {e}")
            
            # Also delete processed .wav file if it exists
            if task.file_path:
                wav_path = os.path.splitext(task.file_path)[0] + '.wav'
                if wav_path != task.file_path and os.path.exists(wav_path):
                    try:
                        os.remove(wav_path)
                        logger.info(f"Deleted processed file: {wav_path}")
                    except OSError as e:
                        logger.warning(f"Failed to delete processed file {wav_path}: {e}")
            
            self.db.delete(task)
            self.db.commit()
            return True
        return False

    # User Management
    def create_user(self, username, hashed_password, full_name=None, email=None):
        user = models.User(
            username=username, 
            hashed_password=hashed_password, 
            full_name=full_name, 
            email=email,
            is_active="False"
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user_id: str):
        # Delete user's tasks first (manual cascade)
        self.db.query(models.TranscriptionTask).filter(models.TranscriptionTask.owner_id == user_id).delete()
        
        # Delete user
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False

    def get_users(self):
        return self.db.query(models.User).all()

    def approve_user(self, user_id):
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            user.is_active = True
            self.db.commit()
        return user

    def update_user_password(self, user_id, hashed_password):
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            user.hashed_password = hashed_password
            self.db.commit()
            return True
        return False

    def update_user_limit(self, user_id, limit: int):
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            user.transcription_limit = limit
            self.db.commit()
            return True
        return False
    
    def toggle_admin_status(self, user_id):
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            # Toggle between "True" and "False" strings
            user.is_admin = not user.is_admin
            self.db.commit()
            return True
        return False
    
    def count_user_tasks(self, user_id):
        # Count non-failed tasks for limit usage
        return self.db.query(models.TranscriptionTask).filter(
            models.TranscriptionTask.owner_id == user_id,
            models.TranscriptionTask.status != "failed"
        ).count()
        
    def get_all_tasks_admin(self, include_text: bool = False):
        # Join User to get owner name
        # We perform an outer join in case owner was deleted (though cascade should handle it)
        results = (
            self.db.query(models.TranscriptionTask, models.User.full_name, models.User.username)
            .outerjoin(models.User, models.TranscriptionTask.owner_id == models.User.id)
            .order_by(models.TranscriptionTask.completed_at.desc())
            .all()
        )
        
        tasks_data = []
        for task, full_name, username in results:
            t_dict = task.to_dict(include_text=include_text)
            t_dict["owner_name"] = full_name or username or "Desconhecido"
            tasks_data.append(t_dict)
        return tasks_data

    def get_stats(self, owner_id: str = None):
        """Aggregate stats for reports. If owner_id is None, aggregates all."""
        from sqlalchemy import func
        
        query = self.db.query(
            models.TranscriptionTask.analysis_status,
            func.count(models.TranscriptionTask.task_id)
        )
        
        # Filter if user
        if owner_id:
            query = query.filter(models.TranscriptionTask.owner_id == owner_id)
            
        # Group by status
        results = query.group_by(models.TranscriptionTask.analysis_status).all()
        
        # Get total count (completed)
        total_query = self.db.query(models.TranscriptionTask).filter(models.TranscriptionTask.status == "completed")
        if owner_id:
            total_query = total_query.filter(models.TranscriptionTask.owner_id == owner_id)
        total_count = total_query.count()
        
        # Process into clean dict
        stats = {
            "total_completed": total_count,
            "procedente": 0,
            "improcedente": 0,
            "pendente": 0,
            "sem_conclusao": 0
        }
        
        for status, count in results:
            s_lower = (status or "").lower()
            if "procedente" in s_lower and "improcedente" not in s_lower:
                stats["procedente"] += count
            elif "improcedente" in s_lower:
                stats["improcedente"] += count
            elif "pendente" in s_lower:
                stats["pendente"] += count
            elif "indefinido" in s_lower or "sem conclusão" in s_lower:
                stats["sem_conclusao"] += count
                
        return stats

    # Global Configuration
    def get_global_config(self, key: str) -> str:
        config = self.db.query(models.GlobalConfig).filter(models.GlobalConfig.key == key).first()
        return config.value if config else None

    def update_global_config(self, key: str, value: str):
        config = self.db.query(models.GlobalConfig).filter(models.GlobalConfig.key == key).first()
        if not config:
            config = models.GlobalConfig(key=key, value=value)
            self.db.add(config)
        else:
            config.value = value
        self.db.commit()
        return config.value
    
    # Pagination methods
    def get_user_tasks_paginated(self, owner_id: str, offset: int, limit: int, include_text: bool = False):
        """Get user's tasks with pagination"""
        tasks = self.db.query(models.TranscriptionTask).filter(
            models.TranscriptionTask.owner_id == owner_id,
            models.TranscriptionTask.status.in_(["completed", "failed"])
        ).order_by(
            models.TranscriptionTask.completed_at.desc()
        ).offset(offset).limit(limit).all()
        
        return [task.to_dict(include_text=include_text) for task in tasks]
    
    def get_all_tasks_admin_paginated(self, offset: int, limit: int, include_text: bool = False):
        """Get all tasks with pagination (admin only)"""
        results = (
            self.db.query(models.TranscriptionTask, models.User.full_name, models.User.username)
            .outerjoin(models.User, models.TranscriptionTask.owner_id == models.User.id)
            .order_by(models.TranscriptionTask.completed_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        tasks_data = []
        for task, full_name, username in results:
            t_dict = task.to_dict(include_text=include_text)
            t_dict["owner_name"] = full_name or username or "Desconhecido"
            tasks_data.append(t_dict)
        return tasks_data
    
    def count_all_tasks(self):
        """Count all tasks"""
        return self.db.query(models.TranscriptionTask).count()
    
    def count_user_completed_tasks(self, owner_id: str):
        """Count user's completed/failed tasks"""
        return self.db.query(models.TranscriptionTask).filter(
            models.TranscriptionTask.owner_id == owner_id,
            models.TranscriptionTask.status.in_(["completed", "failed"])
        ).count()
