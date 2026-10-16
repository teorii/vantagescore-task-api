from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import events
from app.main import create_app
from app.storage import InMemoryTaskRepository, get_repository


@pytest.fixture(autouse=True)
def event_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the background event log at a temp file so tests never write into the project."""
    log_path = tmp_path / "task_events.log"
    monkeypatch.setattr(events, "LOG_PATH", log_path)
    return log_path


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A client whose app uses a repository that lives only for this test."""
    app = create_app()
    repository = InMemoryTaskRepository()
    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app) as test_client:
        yield test_client
