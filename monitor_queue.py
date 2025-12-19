#!/usr/bin/env python3
"""
Monitor de Fila de Transcrições em Tempo Real
Acompanha uploads, processamento e conclusões
"""
import os
import time
from datetime import datetime
from sqlalchemy import create_engine, text

# Configuração do banco
db_user = os.getenv("DB_USER", "careca")
db_name = os.getenv("DB_NAME", "carecadb")
db_host = os.getenv("DB_HOST", "db")
db_port = os.getenv("DB_PORT", "5432")

# Ler senha do secret
with open("/run/secrets/db_password", "r") as f:
    db_password = f.read().strip()

# Conectar ao banco
engine = create_engine(
    f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)

def clear_screen():
    """Limpa a tela"""
    os.system('clear' if os.name != 'nt' else 'cls')

def get_stats(conn):
    """Obtém estatísticas da fila"""
    # Status geral
    result = conn.execute(text("""
        SELECT status, COUNT(*) as total 
        FROM transcription_tasks 
        GROUP BY status 
        ORDER BY 
            CASE status 
                WHEN 'processing' THEN 1
                WHEN 'queued' THEN 2
                WHEN 'completed' THEN 3
                WHEN 'failed' THEN 4
                ELSE 5
            END
    """))
    
    stats = {row.status: row.total for row in result}
    
    # Últimas 5 tarefas em processamento
    result = conn.execute(text("""
        SELECT filename, started_at, progress
        FROM transcription_tasks
        WHERE status = 'processing'
        ORDER BY started_at DESC
        LIMIT 5
    """))
    
    processing = list(result)
    
    # Últimas 5 completadas
    result = conn.execute(text("""
        SELECT filename, completed_at, processing_time
        FROM transcription_tasks
        WHERE status = 'completed'
        ORDER BY completed_at DESC
        LIMIT 5
    """))
    
    completed = list(result)
    
    # Últimas 5 falhadas
    result = conn.execute(text("""
        SELECT filename, error_message
        FROM transcription_tasks
        WHERE status = 'failed'
        ORDER BY completed_at DESC
        LIMIT 5
    """))
    
    failed = list(result)
    
    return stats, processing, completed, failed

def format_time(seconds):
    """Formata segundos em formato legível"""
    if seconds is None:
        return "N/A"
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

def monitor():
    """Loop principal de monitoramento"""
    print("🚀 Iniciando monitoramento...")
    print("Pressione Ctrl+C para sair\n")
    time.sleep(2)
    
    with engine.connect() as conn:
        iteration = 0
        while True:
            try:
                iteration += 1
                stats, processing, completed, failed = get_stats(conn)
                
                # Limpar tela
                clear_screen()
                
                # Header
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print("=" * 80)
                print(f"📊 MONITOR DE TRANSCRIÇÕES - {now}")
                print(f"🔄 Atualização #{iteration} (a cada 3s)")
                print("=" * 80)
                
                # Estatísticas gerais
                total = sum(stats.values())
                queued = stats.get('queued', 0)
                processing_count = stats.get('processing', 0)
                completed_count = stats.get('completed', 0)
                failed_count = stats.get('failed', 0)
                
                print(f"\n📈 ESTATÍSTICAS GERAIS:")
                print(f"  📦 Total de tarefas: {total}")
                print(f"  ⏳ Na fila: {queued}")
                print(f"  🔄 Processando: {processing_count}")
                print(f"  ✅ Completadas: {completed_count}")
                print(f"  ❌ Falhadas: {failed_count}")
                
                if total > 0:
                    progress_pct = (completed_count / total) * 100
                    print(f"\n  📊 Progresso: {progress_pct:.1f}% ({completed_count}/{total})")
                    
                    # Barra de progresso
                    bar_length = 50
                    filled = int(bar_length * completed_count / total)
                    bar = "█" * filled + "░" * (bar_length - filled)
                    print(f"  [{bar}]")
                
                # Tarefas em processamento
                if processing:
                    print(f"\n🔄 EM PROCESSAMENTO ({len(processing)}):")
                    for task in processing:
                        elapsed = (datetime.now() - task.started_at).total_seconds() if task.started_at else 0
                        print(f"  • {task.filename[:50]:<50} | {task.progress}% | {format_time(elapsed)}")
                
                # Últimas completadas
                if completed:
                    print(f"\n✅ ÚLTIMAS COMPLETADAS ({len(completed)}):")
                    for task in completed[:3]:
                        print(f"  • {task.filename[:50]:<50} | {format_time(task.processing_time)}")
                
                # Últimas falhadas
                if failed:
                    print(f"\n❌ ÚLTIMAS FALHADAS ({len(failed)}):")
                    for task in failed[:3]:
                        error = task.error_message[:60] if task.error_message else "Erro desconhecido"
                        print(f"  • {task.filename[:40]:<40} | {error}")
                
                print("\n" + "=" * 80)
                print("💡 Aguardando próxima atualização em 3 segundos...")
                print("   Pressione Ctrl+C para sair")
                
                time.sleep(3)
                
            except KeyboardInterrupt:
                print("\n\n👋 Monitoramento encerrado!")
                break
            except Exception as e:
                print(f"\n❌ Erro: {e}")
                time.sleep(5)

if __name__ == '__main__':
    monitor()
