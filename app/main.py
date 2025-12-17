"""
Mirror.ia - Serviço de Transcrição de Áudio
Ponto de entrada principal da aplicação FastAPI
"""
from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import asyncio
import os
import secrets
import uuid

# Importações Core
from app.core.config import settings, logger
from app.core.limiter import limiter
from app.core.queue import task_queue


# Importações Banco de Dados
from app.database import engine, get_db
from app import models, auth, crud
from sqlalchemy.orm import Session
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

# Importar Routers
from app.api.v1.api import router as api_router

# Criar Tabelas do BD (Pendente Alembic)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mirror.ia - Sua voz, refletida em inteligência")

# Configuração do Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# Arquivos Estáticos e Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
CACHE_BUST = str(int(time.time()))

# Incluir API Router
app.include_router(api_router)

# Prometheus Instrumentator (Deve ser antes do startup)
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)
    logger.info("Métricas Prometheus inicializadas")
except ImportError:
    logger.warning("Prometheus instrumentator não instalado.")


@app.on_event("startup")
async def startup_event():
    """Evento de inicialização da aplicação."""
    logger.info("Serviço iniciando [Melhorias Aplicadas]...")
    

    # 2. Configuração de Infraestrutura (Admin e Migrações)
    db = next(get_db())
    try:
        # Criar Admin
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin:
            pwd = settings.ADMIN_PASSWORD
            if not pwd:
                pwd = secrets.token_urlsafe(16)
                # Segurança: NÃO logar a senha gerada
                logger.warning("ADMIN_PASSWORD não definida. Senha temporária gerada - defina ADMIN_PASSWORD no .env")
            
            try:
                db.add(models.User(
                    username="admin", 
                    hashed_password=auth.get_password_hash(pwd),
                    is_active=True, 
                    is_admin=True
                ))
                db.commit()
                logger.info("Usuário admin criado com sucesso.")
            except Exception as e:
                db.rollback()
                logger.warning(f"Criação do admin ignorada (pode já existir): {e}")
        else:
            logger.info("Usuário admin já existe.")
            
        # 3. RECUPERAÇÃO DE TAREFAS (Correção de Confiabilidade)
        # Reenficar tarefas pendentes se arquivo existe, senão marcar como falha
        pending_tasks = db.query(models.TranscriptionTask).filter(
            models.TranscriptionTask.status.in_(["queued", "processing"])
        ).all()
        
        recovered_count = 0
        failed_count = 0
        
        for task in pending_tasks:
            # Verificar se arquivo ainda existe
            if os.path.exists(task.file_path):
                # Resetar status para queued
                task.status = "queued"
                task.progress = 0
                task.started_at = None
                
                # Parsear opções do JSON armazenado no banco
                import json
                ops = {}
                if task.options:
                    try:
                        ops = json.loads(task.options)
                    except json.JSONDecodeError:
                        logger.warning(f"JSON de opções inválido para tarefa {task.task_id}, usando padrões")
                        ops = {}
                
                # Reenficar
                logger.info(f"✓ Recuperando tarefa {task.task_id} ({task.filename})")
                await task_queue.put((task.task_id, task.file_path, ops))
                recovered_count += 1
            else:
                # Arquivo ausente, marcar como falha ao invés de deletar
                logger.warning(f"✗ Arquivo da tarefa {task.task_id} ausente: {task.file_path}")
                task.status = "failed"
                task.error_message = f"Arquivo não encontrado: {os.path.basename(task.file_path)} (excluído ou movido)"
                task.completed_at = None
                failed_count += 1
                
        db.commit()
        logger.info(f"Inicialização: {recovered_count} tarefas recuperadas, {failed_count} marcadas como falha (arquivos ausentes)")


    finally:
        db.close()


# Páginas HTML (Interface Web)
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Página principal."""
    return templates.TemplateResponse("index.html", {"request": request, "cache_bust": CACHE_BUST})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Página de login."""
    return templates.TemplateResponse("login.html", {"request": request, "cache_bust": CACHE_BUST})


@app.get("/health")
async def health_check():
    """Endpoint de health check legado."""
    return {"status": "healthy", "gpu": settings.DEVICE == "cuda"}


@app.get("/health/live")
async def liveness_check():
    """
    Probe de liveness - verifica se a aplicação está executando.
    Retorna 200 se o processo está vivo.
    """
    return {"status": "alive", "timestamp": time.time()}


@app.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Probe de readiness - verifica se a aplicação está pronta para servir tráfego.
    Verifica conexões com banco de dados e Redis.
    """
    try:
        # Verificar conexão com banco de dados
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        
        # Verificar conexão com Redis
        from app.services.cache_service import cache_service
        if not cache_service.redis or not cache_service.redis.ping():
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "Falha na conexão com Redis"}
            )
        
        return {
            "status": "ready",
            "database": "connected",
            "redis": "connected",
            "gpu": settings.DEVICE == "cuda",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Verificação de readiness falhou: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": str(e)}
        )

