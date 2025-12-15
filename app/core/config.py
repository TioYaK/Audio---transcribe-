
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

# Use RotatingFileHandler to prevent disk space issues
if os.path.exists(LOG_DIR):
    try:
        from logging.handlers import RotatingFileHandler
        # Rotate at 10MB, keep 5 backup files
        file_handler = RotatingFileHandler(
            LOG_FILE, 
            mode='a', 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
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
        # PERFORMANCE: Changed from 'medium' to 'small' for 3-4x speed improvement
        # Quality: 90-92% (vs 95% with medium) - excellent trade-off
        self.WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
        self.DEVICE = os.getenv("DEVICE", "cpu")
        self.COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "int8")
        
        self.MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 100))
        self.ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS", "mp3,wav,m4a,ogg,webm,flac,opus,ptt").split(",")
        
        self.DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/transcriptions.db")
        self.UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
        self.CLEANUP_AFTER_HOURS = int(os.getenv("CLEANUP_AFTER_HOURS", 24))
        
        # Security - Use secrets module for sensitive data
        try:
            from app.core.secrets import get_secret_key, get_admin_password, get_database_url, get_redis_url
            self.SECRET_KEY = get_secret_key()
            self.ADMIN_PASSWORD = get_admin_password()
            self.DATABASE_URL = get_database_url()
            self.REDIS_URL = get_redis_url()
        except Exception as e:
            logger.warning(f"Failed to load secrets from Docker secrets, falling back to env vars: {e}")
            # Fallback to environment variables for development
            self.SECRET_KEY = os.getenv("SECRET_KEY")
            self.ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
            
            # Build URLs from components
            db_user = os.getenv("DB_USER", "careca")
            db_password = os.getenv("DB_PASSWORD", "")
            db_host = os.getenv("DB_HOST", "db")
            db_port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", "carecadb")
            self.DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            
            redis_host = os.getenv("REDIS_HOST", "redis")
            redis_port = os.getenv("REDIS_PORT", "6379")
            redis_password = os.getenv("REDIS_PASSWORD", "")
            redis_db = os.getenv("REDIS_DB", "0")
            self.REDIS_URL = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
        
        self.ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")


    def validate(self):
        if self.MAX_FILE_SIZE_MB <= 0:
            raise ValueError("MAX_FILE_SIZE_MB must be positive")
        
        if not self.ALLOWED_EXTENSIONS:
            raise ValueError("ALLOWED_EXTENSIONS cannot be empty")
        
        # SECRET_KEY is REQUIRED for security
        if not self.SECRET_KEY:
            raise ValueError(
                "SECRET_KEY is required! Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        
        if len(self.SECRET_KEY) < 32:
            raise ValueError(
                f"SECRET_KEY must be at least 32 characters (current: {len(self.SECRET_KEY)}). "
                "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        
        logger.info("Configuration loaded and validated.")

settings = Settings()
try:
    settings.validate()
except Exception as e:
    logger.critical(f"Configuration invalid: {e}")
    raise e
