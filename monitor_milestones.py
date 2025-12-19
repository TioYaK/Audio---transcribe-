#!/usr/bin/env python3
"""
Monitor de Marcos - Notifica em 25%, 50%, 75% e 100%
"""
import os
import sys
import time
from pathlib import Path
from datetime import datetime
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

# Marcos já notificados
notified_milestones = set()

def get_progress():
    """Obtém o progresso atual"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'queued') as queued,
                COUNT(*) FILTER (WHERE status = 'processing') as processing,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COUNT(*) as total
            FROM transcription_tasks
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """))
        
        row = result.fetchone()
        return {
            'completed': row.completed,
            'queued': row.queued,
            'processing': row.processing,
            'failed': row.failed,
            'total': row.total
        }

def check_milestone(progress):
    """Verifica se atingiu algum marco"""
    if progress['total'] == 0:
        return None
    
    percentage = (progress['completed'] / progress['total']) * 100
    
    milestones = [25, 50, 75, 100]
    for milestone in milestones:
        if percentage >= milestone and milestone not in notified_milestones:
            notified_milestones.add(milestone)
            return milestone
    
    return None

def print_milestone_alert(milestone, progress):
    """Imprime alerta de marco atingido"""
    print("\n" + "=" * 80)
    print(f"🎉 MARCO ATINGIDO: {milestone}% CONCLUÍDO!")
    print("=" * 80)
    print(f"✅ Concluídos: {progress['completed']}/{progress['total']}")
    print(f"⏳ Em fila: {progress['queued']}")
    print(f"🔄 Processando: {progress['processing']}")
    if progress['failed'] > 0:
        print(f"❌ Falhas: {progress['failed']}")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")

def main():
    """Loop principal"""
    print("🔔 Monitor de Marcos Iniciado")
    print("Aguardando marcos: 25%, 50%, 75%, 100%\n")
    
    try:
        while True:
            progress = get_progress()
            milestone = check_milestone(progress)
            
            if milestone:
                print_milestone_alert(milestone, progress)
                
                if milestone == 100:
                    print("🎊 TODOS OS ÁUDIOS FORAM PROCESSADOS!")
                    print("Monitor encerrando...\n")
                    break
            
            time.sleep(10)  # Verifica a cada 10 segundos
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitor encerrado pelo usuário.")
        sys.exit(0)

if __name__ == "__main__":
    main()
