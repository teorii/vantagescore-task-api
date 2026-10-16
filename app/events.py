"""Append-only event log written from background tasks."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

LOG_PATH = Path(__file__).resolve().parent.parent / "task_events.log"


def log_event(action: str, task_id: UUID) -> None:
    """Append one line: ISO 8601 UTC timestamp, action, task id."""
    timestamp = datetime.now(UTC).isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as log:
        log.write(f"{timestamp} {action} {task_id}\n")
