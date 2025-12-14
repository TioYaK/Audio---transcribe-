"""
Audio noise reduction service using noisereduce library.
Applies spectral gating to remove background noise before transcription.
"""

import logging
import os
import numpy as np

logger = logging.getLogger(__name__)

def reduce_noise(audio_path: str, output_path: str = None) -> str:
    """
    Apply noise reduction to audio file.
    
    Args:
        audio_path: Path to input audio file
        output_path: Path to save cleaned audio (optional, defaults to temp file)
    
    Returns:
        Path to cleaned audio file
    """
    try:
        import noisereduce as nr
        import soundfile as sf
        
        logger.info(f"Applying noise reduction to {audio_path}")
        
        # Load audio
        data, rate = sf.read(audio_path)
        
        # Convert stereo to mono if needed
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
        
        # Apply noise reduction
        # stationary=True for consistent background noise (AC, fan, etc.)
        # prop_decrease=0.8 means reduce noise by 80% (aggressive but preserves speech)
        reduced_noise = nr.reduce_noise(
            y=data,
            sr=rate,
            stationary=True,
            prop_decrease=0.8,
            freq_mask_smooth_hz=500,  # Smooth frequency masking
            time_mask_smooth_ms=50    # Smooth time masking
        )
        
        # Generate output path if not provided
        if output_path is None:
            base, ext = os.path.splitext(audio_path)
            output_path = f"{base}_cleaned{ext}"
        
        # Save cleaned audio
        sf.write(output_path, reduced_noise, rate)
        
        logger.info(f"Noise reduction complete. Saved to {output_path}")
        return output_path
        
    except ImportError:
        logger.warning("noisereduce or soundfile not installed. Skipping noise reduction.")
        return audio_path
    except Exception as e:
        logger.error(f"Noise reduction failed: {e}. Using original audio.")
        return audio_path
