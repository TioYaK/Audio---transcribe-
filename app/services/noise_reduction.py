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
    logger.info(f"[NOISE_REDUCE] Input path: {audio_path}")
    logger.info(f"[NOISE_REDUCE] File exists: {os.path.exists(audio_path)}")
    
    # If file doesn't exist, return original path (will fail later with better error)
    if not os.path.exists(audio_path):
        logger.error(f"[NOISE_REDUCE] Input file does not exist: {audio_path}")
        return audio_path
    
    try:
        import noisereduce as nr
        import soundfile as sf
        
        logger.info(f"[NOISE_REDUCE] Starting noise reduction...")
        
        # Load audio
        data, rate = sf.read(audio_path)
        logger.info(f"[NOISE_REDUCE] Loaded audio: {len(data)} samples at {rate}Hz")
        
        # Convert stereo to mono if needed
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
            logger.info(f"[NOISE_REDUCE] Converted stereo to mono")
        
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
        
        logger.info(f"[NOISE_REDUCE] ✓ Complete. Saved to: {output_path}")
        logger.info(f"[NOISE_REDUCE] Output file exists: {os.path.exists(output_path)}")
        return output_path
        
    except ImportError as e:
        logger.warning(f"[NOISE_REDUCE] noisereduce or soundfile not installed: {e}. Skipping.")
        return audio_path
    except Exception as e:
        logger.error(f"[NOISE_REDUCE] Failed: {e}. Using original audio.")
        return audio_path
