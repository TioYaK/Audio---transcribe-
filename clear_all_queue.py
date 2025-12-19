#!/usr/bin/env python3
"""
Script para LIMPAR COMPLETAMENTE a fila de transcrições
Remove TODOS os jobs pendentes e em processamento
Use com cuidado - esta ação é irreversível!
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text

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

print("=" * 70)
print("🧹 LIMPEZA COMPLETA DA FILA DE TRANSCRIÇÕES")
print("=" * 70)
print("\n⚠️  ATENÇÃO: Este script irá:")
print("   - Cancelar TODOS os jobs em fila (queued)")
print("   - Cancelar TODOS os jobs em processamento (processing)")
print("   - Limpar cache do Redis")
print("   - Remover arquivos de upload órfãos")
print("\n" + "=" * 70)

# Confirmação (pular se --force for passado)
if "--force" not in sys.argv:
    confirm = input("\n❓ Deseja continuar? (digite 'SIM' para confirmar): ")
    if confirm.upper() != "SIM":
        print("\n❌ Operação cancelada pelo usuário.")
        sys.exit(0)
else:
    print("\n⚡ Modo --force ativado, pulando confirmação...")

print("\n🚀 Iniciando limpeza completa...\n")

with engine.connect() as conn:
    # 1. Mostrar status atual
    print("📊 Status ANTES da limpeza:")
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
    
    status_before = {}
    for row in result:
        status_before[row.status] = row.total
        print(f"   {row.status}: {row.total}")
    
    # 2. Cancelar todos os jobs em fila
    print("\n🗑️  Cancelando jobs em fila (queued)...")
    result = conn.execute(text("""
        UPDATE transcription_tasks 
        SET status = 'failed', 
            error_message = 'Cancelado - limpeza manual da fila',
            completed_at = NOW()
        WHERE status = 'queued'
        RETURNING task_id, filename
    """))
    
    queued_cancelled = result.rowcount
    conn.commit()
    print(f"   ✅ {queued_cancelled} jobs em fila cancelados")
    
    # 3. Cancelar todos os jobs em processamento
    print("\n🗑️  Cancelando jobs em processamento (processing)...")
    result = conn.execute(text("""
        UPDATE transcription_tasks 
        SET status = 'failed', 
            error_message = 'Cancelado - limpeza manual da fila',
            completed_at = NOW()
        WHERE status = 'processing'
        RETURNING task_id, filename
    """))
    
    processing_cancelled = result.rowcount
    conn.commit()
    print(f"   ✅ {processing_cancelled} jobs em processamento cancelados")
    
    # 4. Limpar jobs com arquivos inexistentes
    print("\n🔍 Verificando arquivos inexistentes...")
    result = conn.execute(text("""
        SELECT task_id, filename, file_path
        FROM transcription_tasks
        WHERE status NOT IN ('completed', 'failed')
    """))
    
    uploads_dir = Path("/app/uploads") if Path("/app/uploads").exists() else Path("./uploads")
    missing_count = 0
    
    for row in result:
        file_path = Path(row.file_path)
        if not file_path.exists():
            conn.execute(text("""
                UPDATE transcription_tasks 
                SET status = 'failed', 
                    error_message = 'Arquivo não encontrado',
                    completed_at = NOW()
                WHERE task_id = :task_id
            """), {"task_id": row.task_id})
            missing_count += 1
    
    if missing_count > 0:
        conn.commit()
        print(f"   ✅ {missing_count} jobs com arquivos inexistentes marcados como falhados")
    else:
        print("   ✅ Nenhum arquivo inexistente encontrado")
    
    # 5. Status final
    print("\n📊 Status DEPOIS da limpeza:")
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
    
    for row in result:
        print(f"   {row.status}: {row.total}")

# 6. Limpar cache Redis (opcional)
print("\n🔄 Limpando cache Redis...")
try:
    import redis
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    
    # Tentar ler senha do secret (se estiver em Docker)
    redis_secret_path = Path("/run/secrets/redis_password")
    if redis_secret_path.exists():
        with open(redis_secret_path, "r") as f:
            redis_password = f.read().strip()
    else:
        redis_password = os.getenv("REDIS_PASSWORD", "")
    
    r = redis.Redis(
        host=redis_host,
        port=redis_port,
        password=redis_password if redis_password else None,
        decode_responses=True
    )
    
    # Limpar apenas chaves relacionadas a transcrições
    keys_to_delete = []
    for pattern in ["transcription:*", "task:*", "queue:*"]:
        keys = r.keys(pattern)
        keys_to_delete.extend(keys)
    
    if keys_to_delete:
        r.delete(*keys_to_delete)
        print(f"   ✅ {len(keys_to_delete)} chaves do Redis removidas")
    else:
        print("   ✅ Nenhuma chave para remover no Redis")
        
except ImportError:
    print("   ⚠️  Módulo redis não instalado - pulando limpeza do cache")
except Exception as e:
    print(f"   ⚠️  Erro ao limpar Redis: {e}")

print("\n" + "=" * 70)
print("✅ LIMPEZA COMPLETA CONCLUÍDA!")
print("=" * 70)
print(f"\n📈 Resumo:")
print(f"   - Jobs em fila cancelados: {queued_cancelled}")
print(f"   - Jobs em processamento cancelados: {processing_cancelled}")
print(f"   - Jobs com arquivos inexistentes: {missing_count}")
print(f"\n🎯 A fila está limpa e pronta para novos uploads!")
print("=" * 70 + "\n")
