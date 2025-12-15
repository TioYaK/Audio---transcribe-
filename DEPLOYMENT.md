# 🚀 GUIA DE DEPLOYMENT - PRODUÇÃO

## 📋 Pré-requisitos

- Docker 24.0+
- Docker Compose 2.20+
- NVIDIA GPU com drivers instalados (para transcrição)
- 8GB RAM mínimo (16GB recomendado)
- 50GB espaço em disco

---

## 🔐 PASSO 1: Configurar Secrets

### Windows (PowerShell)

```powershell
# Executar script de inicialização de secrets
.\scripts\init-secrets.ps1

# Gerar certificados SSL self-signed
.\scripts\generate-ssl.ps1
```

### Linux/Mac

```bash
# Dar permissão de execução
chmod +x scripts/*.sh

# Gerar secrets manualmente
mkdir -p secrets
python -c "import secrets; print(secrets.token_hex(32))" > secrets/db_password.txt
python -c "import secrets; print(secrets.token_hex(32))" > secrets/admin_password.txt
python -c "import secrets; print(secrets.token_hex(64))" > secrets/secret_key.txt
python -c "import secrets; print(secrets.token_hex(32))" > secrets/redis_password.txt
python -c "import secrets; print(secrets.token_hex(32))" > secrets/backup_passphrase.txt

# Gerar certificados SSL
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout ssl/private/key.pem \
  -out ssl/certs/cert.pem \
  -subj "/C=BR/ST=SP/L=Sao Paulo/O=Careca.ai/CN=localhost"
```

---

## ⚙️ PASSO 2: Configurar Variáveis de Ambiente

```bash
# Copiar exemplo
cp .env.example .env

# Editar .env (as senhas já foram geradas pelo script)
nano .env
```

**Variáveis importantes:**

```env
# Modelo Whisper (tiny, base, small, medium, large-v2, large-v3)
WHISPER_MODEL=medium

# Device (cuda para GPU, cpu para CPU)
DEVICE=cuda

# Compute type (float16 para GPU, int8 para CPU)
COMPUTE_TYPE=float16

# Origens permitidas (CORS)
ALLOWED_ORIGINS=https://seu-dominio.com,https://192.168.15.3

# Senhas (geradas automaticamente)
DB_PASSWORD=<gerado>
ADMIN_PASSWORD=<gerado>
SECRET_KEY=<gerado>
REDIS_PASSWORD=<gerado>
```

---

## 🏗️ PASSO 3: Build e Deploy

### Primeira Instalação

```bash
# Build das imagens
docker compose build --no-cache

# Iniciar serviços
docker compose up -d

# Verificar logs
docker compose logs -f app worker

# Verificar saúde dos containers
docker compose ps
```

### Com Monitoramento (Prometheus + Grafana)

```bash
# Iniciar com profile de monitoring
docker compose --profile monitoring up -d

# Acessar:
# - Grafana: https://localhost:3000 (admin/admin)
# - Prometheus: http://localhost:9090
```

---

## 🔍 PASSO 4: Validação

### Verificar Health Checks

```bash
# Todos os serviços devem estar "healthy"
docker compose ps

# Testar endpoint de saúde
curl -k https://localhost/health
```

### Verificar Logs

```bash
# App
docker compose logs -f app

# Worker
docker compose logs -f worker

# Nginx
docker compose logs -f web

# Database
docker compose logs -f db
```

### Testar Funcionalidades

1. **Acesse:** `https://localhost` ou `https://192.168.15.3`
2. **Login:** Use a senha de admin gerada (veja output do script)
3. **Upload:** Teste upload de áudio
4. **Transcrição:** Verifique se worker processa
5. **Admin:** Acesse painel administrativo

---

## 🔄 PASSO 5: Backup e Manutenção

### Backup Automático

O backup do PostgreSQL roda diariamente às 00:00. Arquivos em `./backups/`

### Backup Manual

```bash
# Backup do banco de dados
docker compose exec db pg_dump -U careca carecadb | gzip > backups/manual-$(date +%Y%m%d).sql.gz

# Backup de volumes
docker compose --profile backup run volume-backup

# Criptografar backups (Linux/Mac)
./scripts/encrypt-backups.sh
```

### Validar Backup

```bash
# Testar restauração
docker compose --profile validation run backup-validator
```

### Limpeza de Cache

```bash
# Limpar cache Redis
docker compose exec redis redis-cli -a $REDIS_PASSWORD FLUSHALL

# Limpar uploads antigos (>24h)
docker compose exec app python -c "from app.utils import cleanup_old_files; cleanup_old_files()"
```

---

## 📊 PASSO 6: Monitoramento

### Métricas Prometheus

```bash
# Habilitar Prometheus
docker compose --profile monitoring up -d prometheus grafana

# Acessar Prometheus
open http://localhost:9090

# Queries úteis:
# - Transcrições por hora: rate(transcriptions_total[1h])
# - Uso de memória: process_resident_memory_bytes
# - Latência p95: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Dashboards Grafana

1. Acesse: `https://localhost:3000`
2. Login: `admin` / `admin` (ou senha configurada)
3. Dashboards pré-configurados em `grafana/dashboards/`

---

## 🔒 PASSO 7: Hardening de Segurança

### Certificados Let's Encrypt (Produção)

```bash
# Instalar certbot
apt-get install certbot

# Gerar certificado
certbot certonly --standalone -d seu-dominio.com

# Copiar certificados
cp /etc/letsencrypt/live/seu-dominio.com/fullchain.pem ssl/certs/cert.pem
cp /etc/letsencrypt/live/seu-dominio.com/privkey.pem ssl/private/key.pem

# Reiniciar nginx
docker compose restart web
```

### Firewall

```bash
# UFW (Ubuntu)
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# Bloquear portas internas
ufw deny 5432  # PostgreSQL
ufw deny 6379  # Redis
ufw deny 9090  # Prometheus
```

### Atualizar Secrets Regularmente

```bash
# Rodar script novamente
.\scripts\init-secrets.ps1

# Recriar containers
docker compose up -d --force-recreate
```

---

## 🐛 TROUBLESHOOTING

### Container não inicia

```bash
# Ver logs detalhados
docker compose logs --tail=100 <service_name>

# Verificar recursos
docker stats

# Verificar networks
docker network ls
docker network inspect careca-frontend
```

### Erro de GPU

```bash
# Verificar NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Se falhar, instalar nvidia-container-toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Erro de Memória

```bash
# Aumentar limite do worker
# Editar docker-compose.yml:
# worker.deploy.resources.limits.memory: '6G'

# Reduzir workers do app
# app.command: ... --workers 2
```

### Erro de Conexão ao Banco

```bash
# Verificar health do DB
docker compose exec db pg_isready -U careca

# Verificar senha
docker compose exec db psql -U careca -d carecadb

# Recriar banco (CUIDADO: apaga dados!)
docker compose down -v
docker compose up -d
```

---

## 📈 PERFORMANCE TUNING

### Para Alta Carga

```yaml
# docker-compose.yml
app:
  command: gunicorn ... --workers 8  # Aumentar workers
  deploy:
    resources:
      limits:
        cpus: '4.0'
        memory: 4G

worker:
  deploy:
    replicas: 2  # Múltiplos workers
```

### Para Baixo Uso de Recursos

```yaml
app:
  command: uvicorn ... --workers 1
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 1G

# Desabilitar monitoring
# docker compose up -d (sem --profile monitoring)
```

---

## 🔄 UPDATES

### Atualizar Aplicação

```bash
# Pull novo código
git pull

# Rebuild
docker compose build --no-cache app worker

# Deploy com zero downtime
docker compose up -d --no-deps --build app worker

# Verificar
docker compose ps
docker compose logs -f app worker
```

### Atualizar Dependências

```bash
# Editar requirements.txt

# Rebuild
docker compose build --no-cache

# Deploy
docker compose up -d
```

---

## 📞 SUPORTE

- **Logs:** `./logs/` e `docker compose logs`
- **Backups:** `./backups/`
- **Métricas:** Prometheus (porta 9090)
- **Dashboards:** Grafana (porta 3000)

---

## ✅ CHECKLIST DE PRODUÇÃO

- [ ] Secrets gerados e seguros
- [ ] Certificados SSL válidos
- [ ] Firewall configurado
- [ ] Backups automáticos funcionando
- [ ] Monitoramento ativo
- [ ] Health checks passando
- [ ] Logs rotacionando
- [ ] Rate limiting testado
- [ ] HTTPS funcionando
- [ ] GPU detectada (se aplicável)
- [ ] Testes de carga realizados
- [ ] Documentação atualizada

---

**Versão:** 3.0  
**Última Atualização:** 2025-12-14  
**Autor:** Careca.ai Team
