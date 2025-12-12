from pydantic import BaseModel, validator, Field
from typing import Optional
import re

class RenameTaskRequest(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=255)
    
    @validator('new_name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Nome não pode ser vazio')
        
        # Sanitizar caracteres perigosos
        forbidden = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(c in v for c in forbidden):
            raise ValueError(f'Nome contém caracteres inválidos: {", ".join(forbidden)}')
        
        return v.strip()

class UpdateAnalysisStatusRequest(BaseModel):
    status: str = Field(..., min_length=1, max_length=100)
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = [
            'Procedente',
            'Improcedente', 
            'Pendente de análise',
            'Indefinido',
            'Sem conclusão'
        ]
        if v not in allowed_statuses:
            raise ValueError(f'Status inválido. Permitidos: {", ".join(allowed_statuses)}')
        return v

class UpdateNotesRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=10000)

class UpdateUserLimitRequest(BaseModel):
    limit: int = Field(..., ge=0, le=10000)

class ChangePasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=100)

class KeywordsUpdateRequest(BaseModel):
    keywords: Optional[str] = Field(None, max_length=5000)
    keywords_red: Optional[str] = Field(None, max_length=5000)
    keywords_green: Optional[str] = Field(None, max_length=5000)

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=200)
    
    @property
    def offset(self):
        return (self.page - 1) * self.page_size

class UploadOptions(BaseModel):
    timestamp: bool = True
    diarization: bool = True
