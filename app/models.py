from sqlalchemy import Column, String, DateTime, Float, Text
from datetime import datetime
from .database import Base
import uuid

class TranscriptionTask(Base):
    __tablename__ = "transcription_tasks"

    task_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String, nullable=False, default="pending")  # pending, processing, completed, failed
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    result_text = Column(Text, nullable=True)
    language = Column(String, nullable=True)
    duration = Column(Float, nullable=True)
    duration = Column(Float, nullable=True)
    processing_time = Column(Float, nullable=True)
    analysis_status = Column(String, default="Pendente de análise", nullable=True)

    def to_dict(self):
        """Helper method to convert model to dictionary for API responses"""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "filename": self.filename,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "language": self.language,
            "duration": self.duration,
            "processing_time": self.processing_time,
            "analysis_status": self.analysis_status or "Pendente de análise"
            # omitting result_text for list views usually, but can be added if needed
        }
