
from sqlalchemy import Column, String, DateTime, Float, Text, Integer, Boolean, Index
from datetime import datetime
from .database import Base
import uuid

class TranscriptionTask(Base):
    __tablename__ = "transcription_tasks"

    task_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String, nullable=False, default="pending", index=True)  # pending, processing, completed, failed
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    result_text = Column(Text, nullable=True)
    language = Column(String, nullable=True)
    duration = Column(Float, nullable=True)
    progress = Column(Integer, default=0, nullable=False)
    processing_time = Column(Float, nullable=True)
    analysis_status = Column(String, default="Pendente de análise", nullable=True)
    summary = Column(Text, nullable=True)
    topics = Column(Text, nullable=True)
    options = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    owner_id = Column(String, nullable=True, index=True) # ForeignKey to User.id
    is_archived = Column(Boolean, default=False, nullable=False, index=True)  # For auto-cleanup
    
    # Composite indexes
    __table_args__ = (
        Index('idx_owner_status_completed', 'owner_id', 'status', 'completed_at'),
        Index('idx_status_created', 'status', 'created_at'),
        Index('idx_owner_created', 'owner_id', 'created_at'),
        Index('idx_completed_archived', 'completed_at', 'is_archived'),
    )

    def to_dict(self, include_text=False):
        data = {
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
            "analysis_status": self.analysis_status or "Pendente de análise",
            "summary": self.summary,
            "topics": self.topics,
            "options": self.options,
            "notes": self.notes,
            "is_archived": self.is_archived if hasattr(self, 'is_archived') else False
        }
        if include_text:
            data['result_text'] = self.result_text or ""
        return data

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    is_active = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    transcription_limit = Column(Integer, default=30)

class GlobalConfig(Base):
    __tablename__ = "global_config"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)

class AnalysisRule(Base):
    """
    Dynamic Rules for Business Analysis (Tier 3)
    """
    __tablename__ = "analysis_rules"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False) # e.g., "Termos Proibidos"
    category = Column(String, nullable=False) # 'positive', 'negative', 'critical'
    keywords = Column(Text, nullable=False) # Comma separated: "cancelar, não quero"
    is_active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
