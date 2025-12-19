@echo off
chcp 65001 > nul
title 🚀 Upload de Áudios - Mirror.ia

echo.
echo ========================================================
echo      🚀 INICIANDO SISTEMA DE UPLOAD DE ÁUDIOS
echo ========================================================
echo.

REM Verifica se Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python não encontrado! Por favor instale o Python.
    echo Baixe em: https://www.python.org/downloads/
    pause
    exit
)

REM Instala dependências (requests) se necessário
echo 📦 Verificando dependências...
pip install requests >nul 2>&1

REM Executa o script
echo ▶️ Executando script de upload...
python "%~dp0upload_batch.py"

echo.
pause
