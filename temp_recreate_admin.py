from app.database import SessionLocal
from app import models, auth
from app.crud import TaskStore

db = SessionLocal()

try:
    # Verifica se admin existe
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    
    if admin:
        print("[INFO] Admin encontrado, atualizando...")
        admin.hashed_password = auth.get_password_hash("7OIeiHAcrPlXOQpssBWuSlm0")
        admin.is_admin = True
        admin.is_active = True
        db.commit()
        print("[OK] Admin atualizado!")
    else:
        print("[INFO] Admin não existe, criando...")
        store = TaskStore(db)
        user = store.create_user("admin", auth.get_password_hash("7OIeiHAcrPlXOQpssBWuSlm0"), "Administrador", "admin@mirror.ia")
        user.is_admin = True
        user.is_active = True
        user.transcription_limit = 999999
        db.commit()
        print("[OK] Admin criado!")
    
    print("\n==============================================")
    print("  ADMIN RECRIADO/ATUALIZADO COM SUCESSO!")
    print("==============================================")
    print("  Usuario: admin")
    print("  Senha: 7OIeiHAcrPlXOQpssBWuSlm0")
    print("==============================================")
    
except Exception as e:
    print(f"[ERRO] {e}")
    db.rollback()
finally:
    db.close()
