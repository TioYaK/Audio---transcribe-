from app.database import SessionLocal
from app.models import TranscriptionTask

db = SessionLocal()
task = db.query(TranscriptionTask).filter(
    TranscriptionTask.filename.like('%GEILDO%')
).first()

if task:
    print(f"✅ ENCONTRADO!")
    print(f"Filename: {task.filename}")
    print(f"Status: {task.status}")
    print(f"Task ID: {task.task_id}")
    print(f"Created: {task.created_at}")
    if task.error_message:
        print(f"Error: {task.error_message}")
else:
    print("❌ NÃO ENCONTRADO no banco de dados")

db.close()
