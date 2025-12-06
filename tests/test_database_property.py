from hypothesis import given, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, TranscriptionTask
from app.crud import TaskStore

# In-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

def test_create_task(db_session):
    store = TaskStore(db_session)
    task = store.create_task("test.mp3", "/tmp/test.mp3")
    assert task.task_id is not None
    assert task.status == "pending"
    assert task.filename == "test.mp3"

def test_update_status(db_session):
    store = TaskStore(db_session)
    task = store.create_task("test.mp3", "/tmp/test.mp3")
    
    updated = store.update_status(task.task_id, "processing")
    assert updated.status == "processing"
    assert updated.started_at is not None

def test_save_result(db_session):
    store = TaskStore(db_session)
    task = store.create_task("test.mp3", "/tmp/test.mp3")
    
    result = store.save_result(task.task_id, "Hello world", "en", 1.5)
    assert result.status == "completed"
    assert result.result_text == "Hello world"
    assert result.language == "en"
    assert result.completed_at is not None

# Property-based test
# Property 5: Status polling reflects processing state
# This validates that for any sequence of valid state transitions, the status is correctly updated
class TaskStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.engine = create_engine(TEST_DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.store = TaskStore(self.session)
        self.task_id = None

    @initialize()
    def init_task(self):
        task = self.store.create_task("prop_test.mp3", "/path/to/prop_test.mp3")
        self.task_id = task.task_id

    @rule(status=st.sampled_from(["processing", "failed", "completed"]))
    def transition_status(self, status):
        # We model the transitions.
        # Note: In the real app, transitions are "pending" -> "processing" -> "completed" or "failed".
        # This test checks if update_status persists the new status correctly.
        
        if self.task_id:
            if status == "failed":
                self.store.update_status(self.task_id, status, error_message="Something went wrong")
            elif status == "completed":
                # save_result sets status to completed
                self.store.save_result(self.task_id, "Transcribed text", "en", 10.0)
            else:
                 self.store.update_status(self.task_id, status)
            
            # Verify
            task = self.store.get_task(self.task_id)
            assert task.status == status

    def teardown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)


TestTaskMachine = TaskStateMachine.TestCase
