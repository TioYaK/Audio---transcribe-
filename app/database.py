from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/transcriptions.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# specific configuration for sqlite to work well with persistent files and threads
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
