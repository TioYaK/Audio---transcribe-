#!/usr/bin/env python3
"""
Análise de Tempo por Etapa do Processamento
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

# Configuração do banco
db_user = os.getenv("DB_USER", "careca")
db_name = os.getenv("DB_NAME", "carecadb")
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")
db_password = os.getenv("DB_PASSWORD", "careca123")

# Tentar ler senha do secret
secret_path = Path("/run/secrets/db_password")
if secret_path.exists():
    with open(secret_path, "r") as f:
        db_password = f.read().strip()

engine = create_engine(
    f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)

def format_duration(seconds):
    """Formata duração em segundos"""
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

print("=" * 80)
print("📊 ANÁLISE DE TEMPO POR ETAPA")
print("=" * 80)

with engine.connect() as conn:
    # Análise de jobs completados
    print("\n✅ JOBS COMPLETADOS - Tempo total:")
    result = conn.execute(text("""
        SELECT 
            filename,
            EXTRACT(EPOCH FROM (completed_at - created_at)) as total_duration
        FROM transcription_tasks
        WHERE status = 'completed'
        AND created_at > NOW() - INTERVAL '24 hours'
        ORDER BY completed_at DESC
        LIMIT 10
    """))
    
    durations = []
    for row in result:
        duration = row.total_duration
        durations.append(duration)
        filename = row.filename[:50] + '...' if len(row.filename) > 50 else row.filename
        print(f"   • {filename}: {format_duration(duration)}")
    
    if durations:
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        
        print(f"\n📈 Estatísticas:")
        print(f"   Média: {format_duration(avg_duration)}")
        print(f"   Mínimo: {format_duration(min_duration)}")
        print(f"   Máximo: {format_duration(max_duration)}")
    
    # Jobs em processamento - tempo na etapa atual
    print("\n\n🔄 JOBS EM PROCESSAMENTO - Tempo na etapa atual:")
    result = conn.execute(text("""
        SELECT 
            filename,
            processing_step,
            EXTRACT(EPOCH FROM (NOW() - created_at)) as elapsed
        FROM transcription_tasks
        WHERE status = 'processing'
        ORDER BY created_at ASC
    """))
    
    processing_jobs = []
    for row in result:
        processing_jobs.append(row)
        filename = row.filename[:40] + '...' if len(row.filename) > 40 else row.filename
        step = row.processing_step or 'iniciando'
        elapsed = format_duration(row.elapsed)
        print(f"   • {filename}")
        print(f"     └─ Etapa: {step} | Tempo total: {elapsed}")
    
    if not processing_jobs:
        print("   Nenhum job em processamento no momento")
    
    # Análise de etapas (se houver logs)
    print("\n\n⚠️  OBSERVAÇÃO:")
    print("   A etapa de 'correção ortográfica' parece estar demorando muito.")
    print("   Isso pode indicar:")
    print("   1. Processamento muito pesado na correção ortográfica")
    print("   2. Possível gargalo de CPU/memória")
    print("   3. Necessidade de otimização ou desabilitação dessa etapa")

print("\n" + "=" * 80)
