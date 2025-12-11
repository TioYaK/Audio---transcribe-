# sitecustomize.py - Executed automatically by Python on startup
# This patches torchaudio BEFORE any module imports

try:
    import torchaudio
    if not hasattr(torchaudio, 'list_audio_backends'):
        torchaudio.list_audio_backends = lambda: []
except ImportError:
    pass
