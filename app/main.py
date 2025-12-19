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
            
        # 3. RECUPERAÇÃO DE TAREFAS - DESABILITADO
        # NOTA: Recuperação automática desabilitada para evitar duplicação de jobs
        # Quando o app reinicia, ele não deve reenfileirar tarefas que já estão no Redis
        # Se necessário, use o endpoint /api/admin/retry-failed para reprocessar tarefas específicas
        
        logger.info("Recuperação automática de tarefas desabilitada (evita duplicação)")


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

