FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# ffmpeg is needed for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data (punkt, punkt_tab, stopwords)
RUN python -m nltk.downloader punkt punkt_tab stopwords

# Copy sitecustomize.py to patch torchaudio globally
COPY sitecustomize.py /usr/local/lib/python3.11/site-packages/

# Copy the rest of the application
COPY . .

# Create necessary directories for volumes
RUN mkdir -p /app/uploads /app/data /root/.cache/whisper
# Add local python package bin to PATH
ENV PATH="$PATH:/root/.local/bin"

# IMPORTANT: Add NVIDIA library paths to LD_LIBRARY_PATH for faster-whisper/ctranslate2
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib/python3.11/site-packages/nvidia/cublas/lib:/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
