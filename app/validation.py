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
    
    @staticmethod
    async def validate_file(file: UploadFile) -> tuple[str, int]:
        """
        Validate uploaded file
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
        
        # 2. Read file content for validation
        file_content = await file.read(8192)  # Read first 8KB
        await file.seek(0)  # Reset file pointer
        
        # 3. Validate MIME type
        try:
            mime = magic.from_buffer(file_content, mime=True)
            logger.info(f"File MIME type detected: {mime}")
            
            # Some audio files might be detected as octet-stream
            # Allow them if extension is valid
            if mime not in FileValidator.ALLOWED_MIMES and mime != 'application/octet-stream':
                logger.warning(f"Suspicious MIME type: {mime} for extension: {ext}")
                # Still allow if extension matches
                if ext not in ['mp3', 'wav', 'm4a', 'ogg', 'webm', 'flac']:
                    raise HTTPException(
                        400, 
                        f"Tipo de arquivo inválido: {mime}. Esperado: arquivo de áudio"
                    )
        except Exception as e:
            logger.error(f"Error detecting MIME type: {e}")
            # Continue if MIME detection fails but extension is valid
        
        
        # 4. Validate file size
        # Read entire file to get size (UploadFile doesn't support tell/seek properly)
        await file.seek(0)  # Ensure we're at start
        content = await file.read()  # Read all content
        size = len(content)
        await file.seek(0)  # Reset to start for later use
        
        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if size > max_size:
            raise HTTPException(
                400, 
                f"Arquivo muito grande: {size/1024/1024:.1f}MB. Máximo: {settings.MAX_FILE_SIZE_MB}MB"
            )
        
        if size == 0:
            raise HTTPException(400, "Arquivo vazio")
        
        # 5. Sanitize filename
        safe_filename = FileValidator.sanitize_filename(file.filename)
        
        logger.info(f"File validated: {safe_filename}, size: {size/1024/1024:.2f}MB, mime: {mime if 'mime' in locals() else 'unknown'}")
        
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
