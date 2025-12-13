from fastapi import UploadFile, HTTPException
import magic
from .config import settings, logger

class FileValidator:
    """Enhanced file validation with MIME type checking and size limits"""
    
    ALLOWED_MIMES = [
        'audio/mpeg',           # MP3
        'audio/wav',            # WAV
        'audio/x-wav',          # WAV alternative
        'audio/mp4',            # M4A
        'audio/x-m4a',          # M4A alternative
        'audio/ogg',            # OGG
        'audio/webm',           # WEBM
        'audio/flac',           # FLAC
        'audio/x-flac',         # FLAC alternative
        'video/mp4',            # MP4 (video with audio)
        'application/octet-stream'  # Fallback for some audio files
    ]
    
    # Magic bytes for audio file detection (first few bytes)
    MAGIC_HEADERS = {
        b'\xff\xfb': 'audio/mpeg',      # MP3
        b'\xff\xfa': 'audio/mpeg',      # MP3
        b'\xff\xf3': 'audio/mpeg',      # MP3
        b'\xff\xf2': 'audio/mpeg',      # MP3
        b'ID3': 'audio/mpeg',           # MP3 with ID3 tag
        b'RIFF': 'audio/wav',           # WAV
        b'fLaC': 'audio/flac',          # FLAC
        b'OggS': 'audio/ogg',           # OGG
    }
    
    @staticmethod
    async def validate_file(file: UploadFile) -> tuple[str, int]:
        """
        Validate uploaded file - OPTIMIZED VERSION
        - Only reads first 8KB for MIME detection
        - Uses seek/tell for file size (no full read required)
        Returns: (safe_filename, file_size)
        Raises: HTTPException if validation fails
        """
        
        # 1. Validate extension
        if not file.filename:
            raise HTTPException(400, "Nome de arquivo inválido")
        
        ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                400, 
                f"Extensão '{ext}' não permitida. Permitidas: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
        
        # 2. Read ONLY the header (first 8KB) for MIME detection
        # This is O(1) memory regardless of file size
        header = await file.read(8192)
        
        # 3. Get file size using seek/tell on underlying file object
        # UploadFile.seek() only accepts position, so we use file.file directly
        # SpooledTemporaryFile supports seek(pos, whence)
        file.file.seek(0, 2)  # SEEK_END on underlying file
        size = file.file.tell()
        
        # Reset to start for later use
        file.file.seek(0)
        await file.seek(0)  # Also reset UploadFile position
        
        # 4. Validate file size
        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if size > max_size:
            raise HTTPException(
                400, 
                f"Arquivo muito grande: {size/1024/1024:.1f}MB. Máximo: {settings.MAX_FILE_SIZE_MB}MB"
            )
        
        if size == 0:
            raise HTTPException(400, "Arquivo vazio")
        
        # 5. Validate MIME type (using header only)
        mime = 'unknown'
        try:
            mime = magic.from_buffer(header, mime=True)
            logger.debug(f"File MIME type detected: {mime}")
            
            # Some audio files might be detected as octet-stream
            # Allow them if extension is valid
            if mime not in FileValidator.ALLOWED_MIMES and mime != 'application/octet-stream':
                logger.warning(f"Suspicious MIME type: {mime} for extension: {ext}")
                # Still allow if extension matches known audio formats
                if ext not in ['mp3', 'wav', 'm4a', 'ogg', 'webm', 'flac']:
                    raise HTTPException(
                        400, 
                        f"Tipo de arquivo inválido: {mime}. Esperado: arquivo de áudio"
                    )
        except Exception as e:
            logger.debug(f"MIME detection fallback: {e}")
            # Continue if MIME detection fails but extension is valid
        
        # 6. Sanitize filename
        safe_filename = FileValidator.sanitize_filename(file.filename)
        
        logger.info(f"File validated: {safe_filename}, size: {size/1024/1024:.2f}MB, mime: {mime}")
        
        return safe_filename, size
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Remove dangerous characters from filename"""
        import re
        import uuid
        
        # Get extension
        parts = filename.rsplit('.', 1)
        name = parts[0] if len(parts) > 1 else filename
        ext = parts[1] if len(parts) > 1 else ''
        
        # Remove dangerous characters
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[-\s]+', '-', name)
        name = name.strip('-')
        
        # Limit length
        if len(name) > 200:
            name = name[:200]
        
        # If name is empty after sanitization, use UUID
        if not name:
            name = str(uuid.uuid4())[:8]
        
        return f"{name}.{ext}" if ext else name
