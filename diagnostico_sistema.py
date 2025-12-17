#!/usr/bin/env python3
"""
Script de Diagnóstico do Sistema Mirror.ia
Verifica fila, arquivos, e status geral
"""

import os
import sys
import asyncio
from pathlib import Path

# Add app to path
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import TranscriptionTask
from app.core.queue import task_queue
from app.core.config import settings

async def diagnostico():
    print("=" * 60)
    print("🔍 DIAGNÓSTICO DO SISTEMA MIRROR.IA")
    print("=" * 60)
    
    # 1. Verificar Fila
    print("\n📋 FILA DE PROCESSAMENTO:")
    try:
        from rq import Queue
        from redis import Redis
        redis_conn = Redis.from_url(settings.REDIS_URL)
        queue = Queue('transcription', connection=redis_conn)
        queue_size = len(queue)
        print(f"   Tamanho da fila: {queue_size} tarefas")
    except Exception as e:
        print(f"   ⚠️  Erro ao verificar fila: {e}")
    
    # 2. Verificar Database
    db = SessionLocal()
    try:
        # Tarefas por status
        queued = db.query(TranscriptionTask).filter(TranscriptionTask.status == 'queued').count()
        processing = db.query(TranscriptionTask).filter(TranscriptionTask.status == 'processing').count()
        completed = db.query(TranscriptionTask).filter(TranscriptionTask.status == 'completed').count()
        failed = db.query(TranscriptionTask).filter(TranscriptionTask.status == 'failed').count()
        
        print(f"\n📊 STATUS DAS TAREFAS NO BANCO:")
        print(f"   ⏳ Na fila (queued): {queued}")
        print(f"   ⚙️  Processando: {processing}")
        print(f"   ✅ Concluídas: {completed}")
        print(f"   ❌ Falhas: {failed}")
        print(f"   📈 Total: {queued + processing + completed + failed}")
        
        # 3. Verificar arquivos de áudio
        print(f"\n🎵 VERIFICAÇÃO DE ARQUIVOS DE ÁUDIO:")
        print(f"   Diretório de uploads: {settings.UPLOAD_DIR}")
        
        if os.path.exists(settings.UPLOAD_DIR):
            files = list(Path(settings.UPLOAD_DIR).glob('*'))
            print(f"   Arquivos no diretório: {len(files)}")
            
            # Verificar tarefas concluídas sem arquivo
            completed_tasks = db.query(TranscriptionTask).filter(
                TranscriptionTask.status == 'completed'
            ).all()
            
            missing_files = []
            for task in completed_tasks:
                if not os.path.exists(task.file_path):
                    missing_files.append({
                        'task_id': task.task_id,
                        'filename': task.filename,
                        'path': task.file_path
                    })
            
            if missing_files:
                print(f"\n   ⚠️  ARQUIVOS FALTANDO ({len(missing_files)}):")
                for mf in missing_files[:5]:  # Mostrar apenas os primeiros 5
                    print(f"      - {mf['filename']}")
                    print(f"        Esperado em: {mf['path']}")
                if len(missing_files) > 5:
                    print(f"      ... e mais {len(missing_files) - 5} arquivos")
            else:
                print(f"   ✅ Todos os arquivos de tarefas concluídas existem!")
        else:
            print(f"   ❌ Diretório de uploads não existe!")
        
        # 4. Tarefas em processamento (detalhes)
        if processing > 0:
            print(f"\n⚙️  TAREFAS EM PROCESSAMENTO:")
            processing_tasks = db.query(TranscriptionTask).filter(
                TranscriptionTask.status == 'processing'
            ).all()
            for task in processing_tasks:
                print(f"   - {task.filename}")
                print(f"     ID: {task.task_id}")
                print(f"     Progresso: {task.progress}%")
                print(f"     Arquivo existe: {'✅' if os.path.exists(task.file_path) else '❌'}")
        
        # 5. Últimas tarefas na fila
        if queued > 0:
            print(f"\n⏳ TAREFAS NA FILA:")
            queued_tasks = db.query(TranscriptionTask).filter(
                TranscriptionTask.status == 'queued'
            ).order_by(TranscriptionTask.created_at).limit(5).all()
            for task in queued_tasks:
                print(f"   - {task.filename}")
                print(f"     ID: {task.task_id}")
                print(f"     Criado em: {task.created_at}")
        
        # 6. Últimas falhas
        if failed > 0:
            print(f"\n❌ ÚLTIMAS FALHAS:")
            failed_tasks = db.query(TranscriptionTask).filter(
                TranscriptionTask.status == 'failed'
            ).order_by(TranscriptionTask.created_at.desc()).limit(3).all()
            for task in failed_tasks:
                print(f"   - {task.filename}")
                print(f"     Erro: {task.error_message or 'Sem mensagem'}")
        
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("✅ Diagnóstico concluído!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(diagnostico())
