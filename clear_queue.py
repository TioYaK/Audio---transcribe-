#!/usr/bin/env python3
"""
Script para limpar fila de transcrições
Remove jobs antigos, falhados e com arquivos inexistentes
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
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

print("=" * 60)
print("🧹 LIMPEZA DE FILA DE TRANSCRIÇÕES")
print("=" * 60)

with engine.connect() as conn:
    # 1. Contar status atual
    result = conn.execute(text("""
        SELECT status, COUNT(*) as total 
        FROM transcription_tasks 
        GROUP BY status 
        ORDER BY total DESC
    """))
    
    print("\n📊 Status atual:")
    for row in result:
        print(f"  - {row.status}: {row.total}")
    
    # 2. Encontrar arquivos inexistentes
    result = conn.execute(text("""
        SELECT task_id, filename, file_path, status, created_at
        FROM transcription_tasks
        WHERE status IN ('queued', 'processing')
        ORDER BY created_at DESC
    """))
    
    uploads_dir = Path("/app/uploads")
    missing_files = []
    
    print("\n🔍 Verificando arquivos...")
    for row in result:
        file_path = Path(row.file_path)
        if not file_path.exists():
            missing_files.append(row.task_id)
            print(f"  ❌ Arquivo não encontrado: {row.filename}")
    
    # 3. Marcar arquivos inexistentes como falhados
    if missing_files:
        print(f"\n🗑️  Marcando {len(missing_files)} tarefas com arquivos inexistentes como falhadas...")
        for task_id in missing_files:
            conn.execute(text("""
                UPDATE transcription_tasks 
                SET status = 'failed', 
                    error_message = 'Arquivo não encontrado - limpeza automática',
                    completed_at = NOW()
                WHERE task_id = :task_id
            """), {"task_id": task_id})
        conn.commit()
        print("  ✅ Concluído!")
    else:
        print("\n  ✅ Todos os arquivos existem!")
    
    # 4. Limpar jobs muito antigos (mais de 24h em processing)
    print("\n⏰ Limpando jobs travados (>24h em processing)...")
    result = conn.execute(text("""
        UPDATE transcription_tasks 
        SET status = 'failed', 
            error_message = 'Timeout - processamento excedeu 24 horas',
            completed_at = NOW()
        WHERE status = 'processing' 
        AND created_at < NOW() - INTERVAL '24 hours'
        RETURNING task_id, filename
    """))
    
    cleaned = result.rowcount
    conn.commit()
    
    if cleaned > 0:
        print(f"  ✅ {cleaned} jobs travados marcados como falhados")
    else:
        print("  ✅ Nenhum job travado encontrado")
    
    # 5. Status final
    result = conn.execute(text("""
        SELECT status, COUNT(*) as total 
        FROM transcription_tasks 
        GROUP BY status 
        ORDER BY total DESC
    """))
    
    print("\n📊 Status após limpeza:")
    for row in result:
        print(f"  - {row.status}: {row.total}")

print("\n" + "=" * 60)
print("✅ Limpeza concluída!")
print("=" * 60)
