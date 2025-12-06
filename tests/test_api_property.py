from hypothesis import given, strategies as st, settings
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, ANY
import os
import shutil
import uuid

# We MUST mock the lazy load of WhisperService in main, otherwise importing main loads the model
# We can do this by patching app.main.WhisperService BEFORE importing app.main
# But app.main is imported at module level.
# Safer is to patch the INSTANCE in app.main if possible, or use dependency override if we had one.
# Since we instantiated it globally in main.py, we have to patch it there.

# However, hypothesis tests run multiple times.
# We will setup the client as a fixture.

from app.main import app, UPLOAD_DIR

client = TestClient(app)

# Helper to clear uploads
def setup_module(module):
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

def teardown_module(module):
    # Instead of rmtree on the dir itself which might be a volume mount point,
    # clean the contents
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")

# Mock whisper service methods globally for these tests
@pytest.fixture(autouse=True)
def mock_whisper():
    with patch("app.main.whisper_service") as mock:
        mock.transcribe.return_value = {
            "text": "Hypothesis generated text",
            "language": "en",
            "duration": 5.0
        }
        yield mock

# Strategies
audio_content = st.binary(min_size=100, max_size=1000) # Small dummy content
# Valid extensions from our env/default
valid_exts = st.sampled_from(["mp3", "wav"])
filenames = st.builds(lambda s, ext: f"test_{s}.{ext}", st.text(min_size=1, alphabet=st.characters(whitelist_categories=('L', 'N'))), valid_exts)

@settings(deadline=None)
@given(filenames, audio_content)
def test_upload_returns_task_id_immediately(filename, content):
    """Property 4: Upload returns task ID immediately"""
    # We need to mock FileValidator to accept our dummy content always, 
    # effectively isolating this test to API response structure
    with patch("app.main.validator.validate", return_value=(True, "OK")):
        files = {"file": (filename, content, "audio/mpeg")} 
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "status_url" in data
        assert data["status_url"].endswith(data["task_id"])

def test_download_generates_correct_file():
    """Property 7 & 8: Download generates correct file & filename format"""
    # 1. Create a dummy completed task in DB
    # We can inject into DB or just simulate the flow
    # Simulating flow is better but harder with background tasks in sync test.
    # Let's manually insert into DB using app dependency logic? 
    # Accessing DB directly is easier.
    
    from app.database import SessionLocal
    from app.crud import TaskStore
    from app.models import TranscriptionTask
    from datetime import datetime
    
    db = SessionLocal()
    task_id = str(uuid.uuid4())
    filename = "test_download.mp3"
    
    store = TaskStore(db)
    # Create manually to set completed state
    task = TranscriptionTask(
        task_id=task_id,
        filename=filename,
        file_path="/tmp/dummy",
        status="completed",
        result_text="Expected Content",
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    db.add(task)
    db.commit()
    db.close()
    
    # 2. Call download endpoint
    response = client.get(f"/api/download/{task_id}")
    assert response.status_code == 200
    assert response.text == "Expected Content"
    
    # Property 8: Filename format
    # Content-Disposition: attachment; filename="test_download_1712312312.txt"
    cd = response.headers["content-disposition"]
    assert "attachment" in cd
    assert "filename=" in cd
    # Check it ends with .txt and has original name part
    assert filename.split('.')[0] in cd
    assert ".txt" in cd

def test_status_polling():
    """Property 5: Status polling reflects processing state (API level)"""
    # Create a task
    from app.database import SessionLocal
    from app.crud import TaskStore
    from app.models import TranscriptionTask
    
    db = SessionLocal()
    task_id = str(uuid.uuid4())
    store = TaskStore(db)
    # Created/Pending
    task = TranscriptionTask(task_id=task_id, filename="poll.mp3", file_path="/tmp/p", status="pending")
    db.add(task)
    db.commit()
    db.close()
    
    resp = client.get(f"/api/status/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"

def test_error_handling_graceful():
    """Property 10: Errors are handled gracefully (API level for non-existent task)"""
    resp = client.get("/api/status/non-existent-uuid")
    assert resp.status_code == 404
    assert "detail" in resp.json()
