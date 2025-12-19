
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Import settings to get DATABASE_URL from Docker secrets
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL

connect_args = {}
pool_kwargs = {}

if "sqlite" in DATABASE_URL:
    # SQLite doesn't support connection pooling
    connect_args = {"check_same_thread": False}
else:
    # PostgreSQL - use connection pooling
    pool_kwargs = {
        "pool_size": 30,           # Aumentado de 20 para 30
        "max_overflow": 70,        # Aumentado de 40 para 70 (total=100)
        "pool_timeout": 60,
        "pool_pre_ping": True,     # Verify connections before use
        "pool_recycle": 3600,      # Recicla conexões a cada 1h
        "echo_pool": False         # Desabilita logging do pool
    }

engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args,
    **pool_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Dependency para obter sessão do banco.
    Usa try/except robusto para evitar erros em uploads simultâneos.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # Em caso de erro, faz rollback antes de fechar
        db.rollback()
        raise
    finally:
        try:
            db.close()
        except Exception:
            # Ignora erros ao fechar (conexão já pode estar fechada)
            pass
