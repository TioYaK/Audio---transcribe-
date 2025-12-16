# 🚀 Guia Rápido de Publicação

Este guia fornece os comandos necessários para publicar o projeto após a limpeza.

## 📋 Pré-requisitos

- Git configurado
- Conta no GitHub/GitLab
- Docker e Docker Compose instalados (para testes)

---

## 🧪 1. Testar Build Limpo

Antes de publicar, teste se tudo está funcionando:

```bash
# Parar containers existentes
docker-compose down

# Limpar cache do Docker (opcional, mas recomendado)
docker system prune -f

# Build limpo sem cache
docker-compose build --no-cache

# Iniciar serviços
docker-compose up -d

# Verificar logs
docker-compose logs -f

# Verificar saúde dos containers
docker-compose ps
```

---

## 📦 2. Preparar Commit

```bash
# Ver status das mudanças
git status

# Adicionar todos os arquivos
git add .

# Criar commit de limpeza
git commit -m "chore: clean project for publication

- Remove temporary documentation files (21 .txt files)
- Remove backup files (.env.backup, .yml.backup, etc.)
- Remove migration scripts (migrate_diarization.py)
- Add LICENSE (MIT)
- Add CHANGELOG.md
- Add CONTRIBUTING.md
- Update .gitignore and .dockerignore
- Organize project structure for publication"

# Verificar commit
git log -1 --stat
```

---

## 🏷️ 3. Criar Tag de Versão

```bash
# Criar tag anotada para v1.0.0
git tag -a v1.0.0 -m "Release version 1.0.0

Features:
- Audio transcription with Whisper
- Speaker diarization
- Web interface and REST API
- Background processing with Celery
- Redis caching
- PostgreSQL database
- User authentication
- Admin panel
- Grafana + Prometheus monitoring
- Docker containerization
- GPU acceleration support"

# Verificar tag
git tag -l -n9 v1.0.0
```

---

## 🌐 4. Criar Repositório Remoto

### GitHub

```bash
# Via GitHub CLI (gh)
gh repo create audio-transcription-service --public --description "Offline audio transcription service with speaker diarization using Whisper"

# Ou criar manualmente em: https://github.com/new
```

### GitLab

```bash
# Via GitLab CLI (glab)
glab repo create audio-transcription-service --public --description "Offline audio transcription service with speaker diarization using Whisper"

# Ou criar manualmente em: https://gitlab.com/projects/new
```

---

## 📤 5. Push para Repositório

```bash
# Adicionar remote (substitua com sua URL)
git remote add origin https://github.com/SEU_USUARIO/audio-transcription-service.git

# Verificar remote
git remote -v

# Push do código
git push -u origin main

# Push das tags
git push origin --tags
```

---

## 📝 6. Criar Release no GitHub

### Via Interface Web
1. Acesse: `https://github.com/SEU_USUARIO/audio-transcription-service/releases/new`
2. Selecione a tag: `v1.0.0`
3. Título: `v1.0.0 - Initial Release`
4. Descrição: Copie do CHANGELOG.md
5. Clique em "Publish release"

### Via GitHub CLI

```bash
gh release create v1.0.0 \
  --title "v1.0.0 - Initial Release" \
  --notes-file CHANGELOG.md
```

---

## 🎨 7. Adicionar Badges ao README

Adicione ao topo do `README.md`:

```markdown
# Audio Transcription Service

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
```

Commit e push:

```bash
git add README.md
git commit -m "docs: add badges to README"
git push
```

---

## 🔧 8. Configurar GitHub/GitLab

### Configurações Recomendadas

1. **Descrição do Repositório:**
   ```
   Offline audio transcription service with speaker diarization using Whisper
   ```

2. **Topics/Tags:**
   - `whisper`
   - `transcription`
   - `audio-processing`
   - `speaker-diarization`
   - `docker`
   - `fastapi`
   - `python`
   - `machine-learning`

3. **Website:**
   - Link para documentação ou demo (se houver)

4. **Proteção de Branch:**
   - Proteger branch `main`
   - Requer pull request reviews
   - Requer status checks

---

## 📊 9. Configurar GitHub Actions (Opcional)

Criar `.github/workflows/docker-build.yml`:

```yaml
name: Docker Build

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker-compose build
      - name: Run tests
        run: docker-compose run --rm transcription-service pytest tests/
```

---

## ✅ Checklist Final

- [ ] Build limpo testado localmente
- [ ] Commit criado com mensagem descritiva
- [ ] Tag v1.0.0 criada
- [ ] Repositório remoto criado
- [ ] Código pushed para remote
- [ ] Tags pushed para remote
- [ ] Release criada no GitHub/GitLab
- [ ] Badges adicionados ao README
- [ ] Descrição e topics configurados
- [ ] Proteção de branch configurada (opcional)
- [ ] GitHub Actions configurado (opcional)

---

## 🎉 Projeto Publicado!

Seu projeto está agora publicado e pronto para uso. Compartilhe o link:

```
https://github.com/SEU_USUARIO/audio-transcription-service
```

### Próximos Passos

1. **Compartilhar:**
   - Redes sociais
   - Reddit (r/Python, r/MachineLearning)
   - Hacker News
   - Dev.to

2. **Monitorar:**
   - Issues
   - Pull requests
   - Stars e forks

3. **Manter:**
   - Atualizar dependências
   - Responder issues
   - Revisar PRs
   - Atualizar CHANGELOG.md

---

## 📞 Suporte

Se encontrar problemas durante a publicação, consulte:

- [GitHub Docs](https://docs.github.com/)
- [GitLab Docs](https://docs.gitlab.com/)
- [Docker Docs](https://docs.docker.com/)

---

*Boa sorte com seu projeto! 🚀*
