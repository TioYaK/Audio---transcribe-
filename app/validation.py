import os
import re
from typing import List, Tuple
import magic  # python-magic for MIME type checking

class FileValidator:
    def __init__(
        self, 
        allowed_extensions: List[str] = None, 
        max_size_mb: int = 100,
        allowed_mime_types: List[str] = None
    ):
        self.allowed_extensions = set(ext.lower() for ext in (allowed_extensions or ["mp3", "wav", "m4a", "ogg", "webm", "flac", "opus", "ptt"]))
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.allowed_mime_types = set(allowed_mime_types or [
            "audio/mpeg", 
            "audio/wav", 
            "audio/x-wav",
            "audio/x-m4a",
            "audio/mp4",
            "audio/ogg", 
            "audio/webm", 
            "audio/flac", 
            "application/ogg",
            "audio/opus",
            "audio/x-opus"
        ])

    def validate_filename(self, filename: str) -> Tuple[bool, str]:
        if not filename:
            return False, "Filename cannot be empty"
        
        # Check extension
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext not in self.allowed_extensions:
            return False, f"Invalid file extension: .{ext}. Allowed: {', '.join(self.allowed_extensions)}"
        
        return True, "Valid filename"

    def validate_size(self, file_size: int) -> Tuple[bool, str]:
        if file_size > self.max_size_bytes:
            return False, f"File size {file_size / (1024*1024):.2f}MB exceeds limit of {self.max_size_bytes / (1024*1024):.0f}MB"
        return True, "Valid size"

    def validate_content(self, file_content: bytes) -> Tuple[bool, str]:
        # Use python-magic to detect mime type from content
        try:
            mime = magic.Magic(mime=True)
            detected_mime = mime.from_buffer(file_content[:2048])
            
            if detected_mime not in self.allowed_mime_types:
                # Some flexibility for application/octet-stream if needed, but strict for now
                return False, f"Invalid file content type: {detected_mime}"
            
            return True, "Valid content"
        except Exception as e:
            return False, f"Error validating file content: {str(e)}"

    def sanitize_filename(self, filename: str) -> str:
        # Keep only alphanumeric, dots, dashes, and underscores
        name = os.path.basename(filename)
        # remove strictly invalid characters for filenames
        clean_name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
        
        # Ensure it doesn't start with a dot/dash/underscore if that's an issue (usually fine)
        # But let's prevent empty names after sanitization
        if not clean_name:
            clean_name = "audio_file"
            
        return clean_name

    def validate(self, filename: str, file_size: int, file_content_head: bytes = None) -> Tuple[bool, str]:
        # Order matters: Size -> Extension -> Content (optimistic check)
        
        # 1. Size
        valid_size, msg_size = self.validate_size(file_size)
        if not valid_size:
            return False, msg_size
            
        # 2. Filename/Extension
        valid_name, msg_name = self.validate_filename(filename)
        if not valid_name:
            return False, msg_name
            
        # 3. Content (MIME) - optional if head provided
        if file_content_head:
            valid_content, msg_content = self.validate_content(file_content_head)
            if not valid_content:
                return False, msg_content
                
        return True, "File is valid"
