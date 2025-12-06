import os
import logging
from typing import List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Settings:
    def __init__(self):
        self.WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
        self.DEVICE = os.getenv("DEVICE", "cpu")
        self.COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "int8")
        
        self.MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 100))
        self.ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS", "mp3,wav,m4a,ogg,webm,flac").split(",")
        
        self.DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/transcriptions.db")
        self.UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
        self.CLEANUP_AFTER_HOURS = int(os.getenv("CLEANUP_AFTER_HOURS", 24))

    def validate(self):
        if self.MAX_FILE_SIZE_MB <= 0:
            raise ValueError("MAX_FILE_SIZE_MB must be positive")
        
        if not self.ALLOWED_EXTENSIONS:
            raise ValueError("ALLOWED_EXTENSIONS cannot be empty")
            
        logger.info("Configuration validated successfully")

settings = Settings()
try:
    settings.validate()
except Exception as e:
    logger.critical(f"Configuration invalid: {e}")
    raise e
