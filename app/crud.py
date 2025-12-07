from sqlalchemy.orm import Session
from .models import TranscriptionTask
from datetime import datetime
from typing import Optional

class TaskStore:
    def __init__(self, db: Session):
        self.db = db

    def create_task(self, filename: str, file_path: str) -> TranscriptionTask:
        db_task = TranscriptionTask(
            filename=filename,
            file_path=file_path,
            status="pending"
        )
        self.db.add(db_task)
        self.db.commit()
        self.db.refresh(db_task)
        return db_task

    def get_task(self, task_id: str) -> Optional[TranscriptionTask]:
        return self.db.query(TranscriptionTask).filter(TranscriptionTask.task_id == task_id).first()

    def update_status(self, task_id: str, status: str, error_message: str = None) -> Optional[TranscriptionTask]:
        task = self.get_task(task_id)
        if task:
            task.status = status
            if status == "processing":
                task.started_at = datetime.utcnow()
            elif status == "failed":
                task.completed_at = datetime.utcnow()
                task.error_message = error_message
            self.db.commit()
            self.db.refresh(task)
        return task

    def save_result(self, task_id: str, text: str, language: str, duration: float, processing_time: float = None) -> Optional[TranscriptionTask]:
        task = self.get_task(task_id)
        if task:
            task.result_text = text
            task.language = language
            task.duration = duration
            task.processing_time = processing_time
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(task)
        return task

    def rename_task(self, task_id: str, new_filename: str) -> Optional[TranscriptionTask]:
        task = self.get_task(task_id)
        if task:
            task.filename = new_filename
            self.db.commit()
            self.db.refresh(task)
        return task

    def clear_history(self) -> int:
        """Delete all completed tasks from the database and return count deleted."""
        q = self.db.query(TranscriptionTask).filter(TranscriptionTask.status == "completed")
        count = q.count()
        if count > 0:
            q.delete(synchronize_session=False)
            self.db.commit()
        return count

    def delete_task(self, task_id: str) -> bool:
        """Delete a single task by ID."""
        task = self.get_task(task_id)
        if task:
            self.db.delete(task)
            self.db.commit()
            return True
        return False

    def delete_old_tasks(self, hours: int):
        # Implementation for cleanup (to be used later)
        # We can implement this when we do the cleanup task
        pass
