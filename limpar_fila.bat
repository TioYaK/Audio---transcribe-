@echo off
REM ============================================
REM Script para Limpar Fila de Upload e Processamento
REM ============================================

echo.
echo ======================================================================
echo   LIMPEZA COMPLETA DA FILA DE TRANSCRICOES
echo ======================================================================
echo.
echo Este script ira:
echo   - Cancelar TODOS os jobs em fila (queued)
echo   - Cancelar TODOS os jobs em processamento (processing)
echo   - Limpar cache do Redis
echo   - Remover TODOS os arquivos de upload
echo.
echo ======================================================================
echo.

set /p confirm="Deseja continuar? (S/N): "
if /i not "%confirm%"=="S" (
    echo.
    echo Operacao cancelada pelo usuario.
    pause
    exit /b 0
)

REM Define o diretorio do projeto
set PROJECT_DIR=d:\projeto mirror\Audio---transcribe-

echo.
echo [1/3] Copiando script de limpeza para o container...
docker cp "%PROJECT_DIR%\clear_all_queue.py" careca-worker:/app/clear_all_queue.py
if errorlevel 1 (
    echo ERRO: Falha ao copiar script para o container
    echo Verifique se o Docker esta rodando e o container careca-worker esta ativo
    pause
    exit /b 1
)
echo OK!

echo.
echo [2/3] Executando limpeza da fila no banco de dados e Redis...
docker exec careca-worker python /app/clear_all_queue.py --force
if errorlevel 1 (
    echo ERRO: Falha ao executar limpeza da fila
    pause
    exit /b 1
)

echo.
echo [3/3] Removendo arquivos de upload...
docker exec careca-worker sh -c "rm -rf /app/uploads/* ; echo 'Arquivos removidos!'"
if errorlevel 1 (
    echo ERRO: Falha ao remover arquivos de upload
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo   LIMPEZA COMPLETA CONCLUIDA!
echo ======================================================================
echo.
echo Voce pode agora enviar novos audios para processamento.
echo.
pause
