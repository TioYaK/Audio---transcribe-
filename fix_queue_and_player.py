#!/usr/bin/env python3
"""
Script para corrigir fila de processamento e reprocessar tarefas presas
"""

import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import TranscriptionTask
from app.core.queue import task_queue
from app.core.config import logger

def fix_queued_tasks():
    """Reprocessa tarefas que estão presas em 'queued'"""
    db = SessionLocal()
    try:
        # Buscar tarefas presas
        queued_tasks = db.query(TranscriptionTask).filter(
            TranscriptionTask.status == 'queued'
        ).all()
        
        print(f"\n🔧 Encontradas {len(queued_tasks)} tarefas presas em 'queued'")
        
        if len(queued_tasks) == 0:
            print("✅ Nenhuma tarefa presa!")
            return
        
        # Reenfileirar cada tarefa
        requeued = 0
        for task in queued_tasks:
            try:
                # Extrair opções do banco (se existirem)
                options = {
                    'timestamp': True,
                    'diarization': True
                }
                
                # Adicionar à fila RQ usando put() que é async
                import asyncio
                asyncio.run(task_queue.put((task.task_id, task.file_path, options)))
                
                print(f"   ✅ Reenfileirado: {task.filename} ({task.task_id})")
                requeued += 1
                
            except Exception as e:
                print(f"   ❌ Erro ao reenfileirar {task.filename}: {e}")
        
        print(f"\n✅ {requeued}/{len(queued_tasks)} tarefas reenfileiradas com sucesso!")
        
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 CORREÇÃO DE FILA DE PROCESSAMENTO")
    print("=" * 60)
    fix_queued_tasks()
    print("=" * 60)
