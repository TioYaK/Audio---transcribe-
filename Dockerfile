# ============================================
# STAGE 1: Build Stage
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Download NLTK data
RUN python -m nltk.downloader -d /build/nltk_data punkt punkt_tab stopwords

# ============================================
# STAGE 2: Production Stage
# ============================================
FROM python:3.11-slim AS production

# Labels for image metadata
LABEL maintainer="Careca.ai"
LABEL description="Audio Transcription Service with Whisper AI"
LABEL version="3.0"

# Build arguments for dynamic user/group IDs
ARG USER_ID=1000
ARG GROUP_ID=1000

# Security: Create non-root user with dynamic IDs
RUN groupadd --gid ${GROUP_ID} appgroup \
    && useradd --uid ${USER_ID} --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Install runtime dependencies (including Java for LanguageTool)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libmagic1 \
    curl \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/*

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy NLTK data from builder stage
COPY --from=builder /build/nltk_data /home/appuser/nltk_data

# Set environment variables
ENV PATH="/home/appuser/.local/bin:$PATH"
ENV NLTK_DATA="/home/appuser/nltk_data"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# NVIDIA library paths for GPU acceleration (faster-whisper/ctranslate2)
ENV LD_LIBRARY_PATH="/home/appuser/.local/lib/python3.11/site-packages/nvidia/cublas/lib:/home/appuser/.local/lib/python3.11/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH"

# Copy sitecustomize.py to patch torchaudio globally
COPY --chown=appuser:appgroup sitecustomize.py /home/appuser/.local/lib/python3.11/site-packages/

# Copy application code
COPY --chown=appuser:appgroup . .

# Create necessary directories with correct permissions
RUN mkdir -p /app/uploads /app/data \
    && chown -R appuser:appgroup /app/uploads /app/data

# Create cache directory for Whisper models
RUN mkdir -p /home/appuser/.cache/huggingface \
    && chown -R appuser:appgroup /home/appuser/.cache

# Remove unnecessary files from image
RUN rm -rf \
    /app/.git \
    /app/__pycache__ \
    /app/**/__pycache__ \
    /app/*.md \
    /app/tests \
    /app/.pytest_cache \
    /app/.mypy_cache \
    /app/*.backup \
    /app/*.fixed \
    2>/dev/null || true

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Healthcheck - verifies the app is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
