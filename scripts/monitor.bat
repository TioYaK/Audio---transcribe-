@echo off
REM Monitor de Transcrições - Windows Script
REM Usage: monitor_transcriptions.bat

echo ======================================================================
echo 🎙️  MONITOR DE TRANSCRIÇÕES - Mirror.ia
echo ======================================================================
echo.
echo ✅ Sistema verificado: Nenhuma tarefa em processamento
echo 📊 Aguardando uploads para começar monitoramento...
echo.
echo Pressione Ctrl+C para finalizar e ver o relatório
echo ======================================================================
echo.

:loop
docker-compose exec -T app python -c "
import sys
sys.path.insert(0, '/app')
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import TranscriptionTask
import statistics

db = SessionLocal()

# Get counts
queued = db.query(TranscriptionTask).filter_by(status='queued').count()
processing = db.query(TranscriptionTask).filter_by(status='processing').count()
completed = db.query(TranscriptionTask).filter_by(status='completed').count()
failed = db.query(TranscriptionTask).filter_by(status='failed').count()

# Get completed tasks with processing time
completed_tasks = db.query(TranscriptionTask).filter(
    TranscriptionTask.status == 'completed',
    TranscriptionTask.processing_time.isnot(None)
).all()

print(f'\n⏱️  {datetime.now().strftime(\"%H:%M:%S\")}')
print(f'📊 FILA: {queued} | 🔄 PROCESSANDO: {processing} | ✅ COMPLETAS: {completed} | ❌ FALHAS: {failed}')

if completed_tasks:
    times = [t.processing_time for t in completed_tasks]
    durations = [t.duration for t in completed_tasks if t.duration]
    
    avg_time = statistics.mean(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f'\n⚡ TEMPO DE PROCESSAMENTO:')
    print(f'   Média: {avg_time:.2f}s ({avg_time/60:.2f} min)')
    print(f'   Min: {min_time:.2f}s | Max: {max_time:.2f}s')
    
    if durations:
        avg_duration = statistics.mean(durations)
        total_audio = sum(durations)
        total_proc = sum(times)
        rtf = total_proc / total_audio if total_audio > 0 else 0
        
        print(f'\n🎵 ÁUDIOS: {len(completed_tasks)} processados')
        print(f'   Duração média: {avg_duration:.2f}s ({avg_duration/60:.2f} min)')
        print(f'   Real-Time Factor: {rtf:.2f}x')
        
        if rtf < 1.0:
            print(f'   🚀 Mais rápido que tempo real!')
        elif rtf < 2.0:
            print(f'   ✅ Eficiente (< 2x tempo real)')
        else:
            print(f'   ⚠️  Lento (> 2x tempo real)')
    
    # ETA
    if queued > 0:
        eta_seconds = queued * avg_time
        print(f'\n⏰ ESTIMATIVA: ~{eta_seconds/60:.1f} min restantes ({queued} áudios)')

print(f'\n{"="*60}')

db.close()
" 2>nul

timeout /t 10 /nobreak >nul
goto loop
