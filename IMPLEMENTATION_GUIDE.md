# 🚀 IMPLEMENTATION GUIDE - Quick Wins

**Correções Críticas de Segurança e Performance**  
**Tempo Total:** ~1h 40min  
**Impacto:** Security Score 7.0/10 → 8.5/10

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

### 🔴 #1: Corrigir Alembic Database URL (15 min)
**Arquivo:** `alembic/env.py`

```python
# alembic/env.py - Localizar run_migrations_online() e ADICIONAR:

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    
    # ✅ ADICIONAR NO INÍCIO
    from app.core.config import settings
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = settings.DATABASE_URL
    
    # Resto permanece igual...
```

**Teste:** `docker-compose run --rm migration`

---

### 🔴 #2: Migration com Docker Secrets (15 min)
**Arquivo:** `docker-compose.yml` (linha ~300)

```yaml
migration:
  secrets:
    - db_password
  command: >
    sh -c "
      export DB_PASSWORD=$(cat /run/secrets/db_password);
      export DATABASE_URL=postgresql://${DB_USER}:$DB_PASSWORD@${DB_HOST}:${DB_PORT}/${DB_NAME};
      alembic upgrade head
    "
  environment:
    - DB_USER=${DB_USER:-careca}
    - DB_NAME=${DB_NAME:-carecadb}
    - DB_HOST=db
    - DB_PORT=5432
```

**Teste:** `docker-compose build migration && docker-compose run --rm migration`

---

### 🔴 #3: Fixar Versões (20 min)
**Arquivo:** `requirements.txt` - SUBSTITUIR TUDO

```txt
# Core
fastapi==0.109.0
uvicorn[standard]==0.27.0
gunicorn==21.2.0
python-multipart==0.0.6

# AI/ML
faster-whisper==0.10.0
torch==2.1.2
torchaudio==2.1.2
speechbrain==0.5.16
huggingface-hub==0.20.3
scikit-learn==1.4.0
numpy==1.26.3

# Database
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
alembic==1.13.1

# Cache
redis==5.0.1
rq==1.15.1

# Security
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
bcrypt==4.0.1

# Monitoring
prometheus-fastapi-instrumentator==6.1.0
psutil==5.9.8

# Utils
requests==2.31.0
httpx==0.26.0
python-magic==0.4.27

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
hypothesis==6.92.2

# Audio
soundfile==0.12.1
noisereduce==3.0.0

# NLP
sumy==0.11.0
language-tool-python==2.7.1
nltk==3.8.1

# Rate Limiting
slowapi==0.1.9
```

**Teste:** `docker-compose build app worker`

---

### 🔴 #4: Rate Limiting Backend (45 min)

#### **app/core/limiter.py** - REFATORAR COMPLETO:

```python
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
import logging

logger = logging.getLogger(__name__)

def get_rate_limit_key(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    
    user = getattr(request.state, "user", None)
    if user:
        return f"{ip}:{user.id}"
    return ip

limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri="redis://redis:6379/2",
    strategy="fixed-window",
    default_limits=["1000/hour", "100/minute"],
    headers_enabled=True
)

async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit: {get_rate_limit_key(request)} | {request.url.path}")
    return Response(
        content='{"detail":"Rate limit exceeded"}',
        status_code=429,
        media_type="application/json",
        headers={"Retry-After": "60"}
    )
```

#### **app/main.py** - ADICIONAR após linha 33:

```python
from app.core.limiter import limiter, rate_limit_handler

app = FastAPI(title="Mirror.ia")

# ✅ ADICIONAR:
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
```

---

### 🔴 #5: Nginx Health Check (5 min)
**Arquivo:** `docker-compose.yml` (linha ~38)

```yaml
web:
  healthcheck:
    test: [ "CMD-SHELL", "wget --no-verbose --tries=1 --spider http://127.0.0.1:80/health || exit 1" ]
    interval: 15s
    timeout: 5s
    retries: 3
    start_period: 20s
```

**Teste:** `docker-compose restart web && docker inspect careca-nginx --format='{{.State.Health.Status}}'`

---

## 🧪 VALIDAÇÃO COMPLETA

```bash
# 1. Rebuild
docker-compose down
docker-compose build

# 2. Start
docker-compose up -d db redis
docker-compose run --rm migration
docker-compose up -d

# 3. Verificar
docker-compose ps
curl http://localhost:8000/health
```

---

## 📊 RESULTADOS ESPERADOS

| Métrica | Antes | Depois |
|---------|-------|--------|
| Security | 7.0 | 8.5 |
| Reliability | 7.5 | 8.5 |
| Manutenibilidade | 6.5 | 7.5 |

**Próximo:** Consulte `CODE_AUDIT_REPORT.md` para correções adicionais.
