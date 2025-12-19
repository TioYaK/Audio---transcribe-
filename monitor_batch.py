#!/usr/bin/env python3
"""
Monitor de Processamento em Lote
Acompanha o progresso de múltiplos áudios sendo processados
"""
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from collections import defaultdict

# Configuração do banco
db_user = os.getenv("DB_USER", "careca")
db_name = os.getenv("DB_NAME", "carecadb")
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")
db_password = os.getenv("DB_PASSWORD", "careca123")

# Tentar ler senha do secret (se estiver em Docker)
secret_path = Path("/run/secrets/db_password")
if secret_path.exists():
    with open(secret_path, "r") as f:
        db_password = f.read().strip()

# Conectar ao banco
try:
    engine = create_engine(
        f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )
except Exception as e:
    print(f"❌ Erro ao conectar ao banco: {e}")
    sys.exit(1)

def clear_screen():
    """Limpa a tela do terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')

def format_duration(seconds):
    """Formata duração em segundos para formato legível"""
    if seconds is None:
        return "N/A"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def get_stats():
    """Obtém estatísticas do banco de dados"""
    with engine.connect() as conn:
        # Status geral
        result = conn.execute(text("""
            SELECT 
                status,
                COUNT(*) as count,
                AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) as avg_duration
            FROM transcription_tasks
            WHERE created_at > NOW() - INTERVAL '24 hours'
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
        
        stats = {}
        for row in result:
            stats[row.status] = {
                'count': row.count,
                'avg_duration': row.avg_duration
            }
        
        # Jobs em processamento (detalhes)
        result = conn.execute(text("""
            SELECT 
                task_id,
                filename,
                created_at,
                processing_step,
                EXTRACT(EPOCH FROM (NOW() - created_at)) as elapsed
            FROM transcription_tasks
            WHERE status = 'processing'
            ORDER BY created_at ASC
            LIMIT 10
        """))
        
        processing_jobs = []
        for row in result:
            processing_jobs.append({
                'task_id': row.task_id,
                'filename': row.filename,
                'created_at': row.created_at,
                'step': row.processing_step or 'iniciando',
                'elapsed': row.elapsed
            })
        
        # Jobs recentemente completados
        result = conn.execute(text("""
            SELECT 
                task_id,
                filename,
                created_at,
                completed_at,
                EXTRACT(EPOCH FROM (completed_at - created_at)) as duration
            FROM transcription_tasks
            WHERE status = 'completed'
            ORDER BY completed_at DESC
            LIMIT 5
        """))
        
        recent_completed = []
        for row in result:
            recent_completed.append({
                'filename': row.filename,
                'duration': row.duration
            })
        
        # Estimativa de tempo restante
        queued_count = stats.get('queued', {}).get('count', 0)
        processing_count = stats.get('processing', {}).get('count', 0)
        completed_count = stats.get('completed', {}).get('count', 0)
        
        avg_duration = None
        if completed_count > 0:
            result = conn.execute(text("""
                SELECT AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) as avg_duration
                FROM transcription_tasks
                WHERE status = 'completed'
                AND created_at > NOW() - INTERVAL '1 hour'
            """))
            row = result.fetchone()
            if row and row.avg_duration:
                avg_duration = row.avg_duration
        
        return {
            'stats': stats,
            'processing_jobs': processing_jobs,
            'recent_completed': recent_completed,
            'avg_duration': avg_duration,
            'queued': queued_count,
            'processing': processing_count,
            'completed': completed_count
        }

def display_dashboard(data):
    """Exibe o dashboard de monitoramento"""
    clear_screen()
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("=" * 80)
    print(f"{'🎵 MONITOR DE PROCESSAMENTO EM LOTE':^80}")
    print("=" * 80)
    print(f"Atualizado em: {now}")
    print("=" * 80)
    
    # Estatísticas gerais
    stats = data['stats']
    queued = data['queued']
    processing = data['processing']
    completed = data['completed']
    failed = stats.get('failed', {}).get('count', 0)
    total = queued + processing + completed + failed
    
    print(f"\n📊 ESTATÍSTICAS GERAIS:")
    print(f"   Total de áudios: {total}")
    print(f"   ⏳ Em fila: {queued}")
    print(f"   🔄 Processando: {processing}")
    print(f"   ✅ Concluídos: {completed}")
    if failed > 0:
        print(f"   ❌ Falhas: {failed}")
    
    # Progresso
    if total > 0:
        progress = (completed / total) * 100
        bar_length = 50
        filled = int(bar_length * completed / total)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"\n📈 PROGRESSO:")
        print(f"   [{bar}] {progress:.1f}%")
        print(f"   {completed}/{total} áudios processados")
    
    # Estimativa de tempo
    if data['avg_duration'] and queued > 0:
        remaining_time = float(data['avg_duration']) * (queued + processing)
        eta = datetime.now() + timedelta(seconds=remaining_time)
        print(f"\n⏱️  ESTIMATIVA:")
        print(f"   Tempo médio por áudio: {format_duration(data['avg_duration'])}")
        print(f"   Tempo restante estimado: {format_duration(remaining_time)}")
        print(f"   Previsão de conclusão: {eta.strftime('%H:%M:%S')}")
    
    # Jobs em processamento
    if data['processing_jobs']:
        print(f"\n🔄 PROCESSANDO AGORA ({len(data['processing_jobs'])} jobs):")
        for job in data['processing_jobs'][:5]:
            filename = job['filename'][:40] + '...' if len(job['filename']) > 40 else job['filename']
            elapsed = format_duration(job['elapsed'])
            step = job['step']
            print(f"   • {filename}")
            print(f"     └─ Etapa: {step} | Tempo: {elapsed}")
    
    # Últimos completados
    if data['recent_completed']:
        print(f"\n✅ ÚLTIMOS CONCLUÍDOS:")
        for job in data['recent_completed'][:3]:
            filename = job['filename'][:50] + '...' if len(job['filename']) > 50 else job['filename']
            duration = format_duration(job['duration'])
            print(f"   • {filename} ({duration})")
    
    print("\n" + "=" * 80)
    print("Pressione Ctrl+C para sair")
    print("=" * 80)

def main():
    """Loop principal de monitoramento"""
    print("Iniciando monitoramento...")
    print("Aguarde enquanto coletamos os dados iniciais...\n")
    
    try:
        while True:
            try:
                data = get_stats()
                display_dashboard(data)
                
                # Verificar se terminou
                if data['queued'] == 0 and data['processing'] == 0 and data['completed'] > 0:
                    print("\n🎉 TODOS OS ÁUDIOS FORAM PROCESSADOS!")
                    print("\nPressione Ctrl+C para sair ou aguarde para continuar monitorando...")
                
                time.sleep(5)  # Atualiza a cada 5 segundos
                
            except KeyboardInterrupt:
                print("\n\n👋 Monitoramento encerrado pelo usuário.")
                sys.exit(0)
            except Exception as e:
                print(f"\n❌ Erro ao coletar dados: {e}")
                time.sleep(5)
                
    except KeyboardInterrupt:
        print("\n\n👋 Monitoramento encerrado pelo usuário.")
        sys.exit(0)

if __name__ == "__main__":
    main()
