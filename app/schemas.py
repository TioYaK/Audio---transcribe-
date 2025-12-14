from pydantic import BaseModel, validator, Field
from typing import Optional, Literal
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

# Admin Schemas - Phase 1 Security
class RuleCreate(BaseModel):
    """Schema for creating analysis rules"""
    name: str = Field(..., min_length=1, max_length=100, description="Rule name")
    category: Literal['positive', 'negative', 'critical'] = Field(..., description="Rule category")
    keywords: str = Field(..., max_length=2000, description="Comma-separated keywords")
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(True)
    
    @validator('keywords')
    def validate_keywords(cls, v):
        if not v or not v.strip():
            raise ValueError('Keywords cannot be empty')
        # Ensure proper comma-separated format
        keywords = [k.strip() for k in v.split(',') if k.strip()]
        if not keywords:
            raise ValueError('At least one keyword is required')
        return ', '.join(keywords)

class RuleUpdate(BaseModel):
    """Schema for updating analysis rules"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[Literal['positive', 'negative', 'critical']] = None
    keywords: Optional[str] = Field(None, max_length=2000)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

class TokenRefreshRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str = Field(..., min_length=10)

class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_admin: bool
    username: str

