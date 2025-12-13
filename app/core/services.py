
from app.services.transcription import TranscriptionService
from app.core.config import settings

# Singleton instance
# Named 'whisper_service' to maintain compatibility with existing worker imports
# but it is now the new refactored orchestrator.
whisper_service = TranscriptionService(settings)
