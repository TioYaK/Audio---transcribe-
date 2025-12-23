#!/usr/bin/env python3
"""
Script para recriar o usuário admin
"""
import os
import sys

# Adiciona o diretório root ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models, auth

def recreate_admin():
    db = SessionLocal()
    try:
        # Verifica se admin já existe
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        
        if admin:
            print("[INFO] Usuário admin já existe. Atualizando senha...")
            # Atualiza senha do admin existente
            admin.password = auth.get_password_hash("7OIeiHAcrPlXOQpssBWuSlm0")
            admin.is_admin = True
            admin.is_active = True
            db.commit()
            print("[OK] Senha do admin atualizada!")
        else:
            print("[INFO] Criando usuário admin...")
            # Cria novo admin
            admin = models.User(
                username="admin",
                email="admin@mirror.ia",
                full_name="Administrador",
                password=auth.get_password_hash("7OIeiHAcrPlXOQpssBWuSlm0"),
                is_admin=True,
                is_active=True,
                transcription_limit=999999  # Sem limite
            )
            db.add(admin)
            db.commit()
            print("[OK] Usuário admin criado com sucesso!")
        
        print("\n" + "="*50)
        print("  ADMIN RECRIADO COM SUCESSO!")
        print("="*50)
        print(f"  Usuário: admin")
        print(f"  Senha: 7OIeiHAcrPlXOQpssBWuSlm0")
        print(f"  Email: admin@mirror.ia")
        print("="*50)
        
    except Exception as e:
        print(f"[ERRO] Falha ao recriar admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    recreate_admin()
