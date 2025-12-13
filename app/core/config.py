
import os
import logging
from typing import List
from datetime import datetime, timedelta

# Custom formatter to convert UTC to BRT (UTC-3)
class BRTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        # Get UTC time and subtract 3 hours for BRT
        dt = datetime.fromtimestamp(record.created) - timedelta(hours=3)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime('%Y-%m-%d %H:%M:%S')

# Ensure log directory exists (Absolute path)
LOG_DIR = "/app/data"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

if not os.path.exists(LOG_DIR):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except Exception:
        pass # Might be permissions issue, but we try

# Setup logging with BRT timezone
formatter = BRTFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

handlers = [stream_handler]

# Only add file handler if directory is writable/exists
if os.path.exists(LOG_DIR):
    try:
        file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    except Exception as e:
        print(f"WARNING: Could not set up file logging: {e}")

logging.basicConfig(
    level=logging.INFO,
    handlers=handlers
)
logger = logging.getLogger("careca_ai")

class Settings:
    def __init__(self):
        self.WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")
        self.DEVICE = os.getenv("DEVICE", "cpu")
        self.COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "int8")
        
        self.MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 100))
        self.ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS", "mp3,wav,m4a,ogg,webm,flac,opus,ptt").split(",")
        
        self.DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/transcriptions.db")
        self.UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
        self.CLEANUP_AFTER_HOURS = int(os.getenv("CLEANUP_AFTER_HOURS", 24))
        
        # Security
        self.SECRET_KEY = os.getenv("SECRET_KEY")
        self.ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")
        
        # Admin
        self.ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    def validate(self):
        if self.MAX_FILE_SIZE_MB <= 0:
            raise ValueError("MAX_FILE_SIZE_MB must be positive")
        
        if not self.ALLOWED_EXTENSIONS:
            raise ValueError("ALLOWED_EXTENSIONS cannot be empty")
        
        # WEAK CHECK for now to allow dev without strict env, but warn
        if not self.SECRET_KEY:
            logger.warning("SECRET_KEY not set! Session security is compromised.")
        
        logger.info("Configuration loaded.")

settings = Settings()
try:
    settings.validate()
except Exception as e:
    logger.critical(f"Configuration invalid: {e}")
    raise e
