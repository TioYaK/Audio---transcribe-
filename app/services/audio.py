
import logging
import subprocess
import uuid
import os

logger = logging.getLogger(__name__)

class AudioProcessor:
    @staticmethod
    def enhance_audio(input_path: str) -> str:
        """
        Enhances audio quality (Optimized for Speed):
        1. Standardize (FFmpeg) -> 16kHz Mono
        2. Normalize (FFmpeg loudnorm) - Fast and effective
        """
        # Temp paths
        final_output = f"{input_path}_opt_{uuid.uuid4().hex[:6]}.wav"
        
        try:
            logger.info("Starting Optimized Audio Pipeline (FFmpeg only)...")
            
            # Single pass FFmpeg: Convert to WAV 16k Mono AND Normalize
            # -ar 16000: Resample to 16k (Whisper native)
            # -ac 1: Mono
            # -af loudnorm: EBU R128 Loudness Normalization (better than peak)
            command = [
                "ffmpeg", "-y", "-i", input_path,
                "-ar", "16000", 
                "-ac", "1",
                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", 
                final_output
            ]
            
            # Run fast C++ binary
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            logger.info(f"Audio optimization complete: {final_output}")
            return final_output

        except Exception as e:
            logger.error(f"Audio enhancement failed: {e}", exc_info=True)
            return input_path # Fallback to original
