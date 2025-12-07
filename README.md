# Audio Transcription Service

An offline, containerized web service for transcribing audio files using OpenAI's Whisper model (via `faster-whisper`).

## Features

- **Local Processing**: Runs entirely on your machine, ensuring privacy.
- **Support for Multiple Formats**: Accepts MP3, WAV, M4A, OGG, WEBM, FLAC.
- **Optimized Performance**: Uses `faster-whisper` (CTranslate2) for up to 4x faster transcription than the original Whisper implementation.
- **Simple Interface**: Drag-and-drop web interface for easy uploads.
- **REST API**: Fully featured API for automation.
- **Background Processing**: Handles large files asynchronously..
- **Dockerized**: Easy setup and deployment with Docker Compose.

## Prerequisites

- Docker and Docker Compose installed.
- (Optional) NVIDIA GPU with Container Toolkit for faster processing (defaults to CPU).

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone <repository_url>
   cd audio-transcription-service
   ```

2. **Configure Environment (Optional)**:
   Copy `.env.example` to `.env` and adjust settings if needed.
   ```bash
   cp .env.example .env
   ```

3. **Run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```

4. **Access the Application**:
   Open `http://localhost:8000` in your browser.

## Configuration (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL` | `base` | Model size: `tiny`, `base`, `small`, `medium`, `large`. Larger = better accuracy but slower. |
| `DEVICE` | `cpu` | Processing device: `cpu` or `cuda`. |
| `COMPUTE_TYPE` | `int8` | Quantization: `int8` (CPU default), `float16` (GPU recommended). |
| `MAX_FILE_SIZE_MB` | `100` | Maximum upload size in MB. |
| `ALLOWED_EXTENSIONS` | `mp3,wav...` | Comma-separated list of allowed extensions. |
| `CLEANUP_AFTER_HOURS`| `24` | Hours to keep files after processing. |

### Model Selection Trade-offs

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| tiny  | 39M  | ~32x  | Basic   | Testing, demos |
| base  | 74M  | ~16x  | Good    | **Recommended for generic use** |
| small | 244M | ~6x   | Better  | Higher quality needed |
| medium| 769M | ~2x   | Great   | Professional use |
| large | 1550M| 1x    | Best    | Maximum quality |

## Usage

### Web Interface
Simply drag and drop your audio file onto the upload area. The status will update automatically, and you can download the transcription when finished.

### API Examples

**Upload Audio**:
```bash
curl -X POST -F "file=@/path/to/audio.mp3" http://localhost:8000/api/upload
```
Returns: `{"task_id": "uuid...", "status_url": "..."}`

**Check Status**:
```bash
curl http://localhost:8000/api/status/{task_id}
```

**Get Result**:
```bash
curl http://localhost:8000/api/result/{task_id}
```

**Download Text**:
```bash
curl -O -J http://localhost:8000/api/download/{task_id}
```

## Troubleshooting

- **Upload Failed**: Check file size limit (`MAX_FILE_SIZE_MB`) and format.
- **Slow Transcription**: Try a smaller model (`tiny` or `base`) or enable GPU support.
- **Docker Volume Errors**: Ensure permissions are correct for `uploads/` and `data/` directories.
- **Model Download Failures**: The initial run downloads the model from Hugging Face. Ensure internet connection is available.

## Development

**Running Tests**:
```bash
docker-compose run --rm transcription-service pytest tests/
```

**Local Setup (No Docker)**:
1. Install ffmpeg.
2. Install Python requirements: `pip install -r requirements.txt`.
3. Run server: `uvicorn app.main:app --reload`.

## License

MIT
