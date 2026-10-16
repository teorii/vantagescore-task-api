"""Task storage: the repository interface, an in-memory implementation, and the dependency."""

from typing import Any, Protocol
from uuid import UUID

from app.models import Task


class TaskNotFoundError(LookupError):
    """Raised by a repository when a task id is unknown."""

    def __init__(self, task_id: UUID) -> None:
        super().__init__(f"Task {task_id} not found")
        self.task_id = task_id


class TaskRepository(Protocol):
    """What the routes need from storage. A database-backed class implements the same methods."""

    def list_tasks(
        self, *, completed: bool | None = None, limit: int | None = None, offset: int = 0
    ) -> list[Task]: ...

    def count(self, *, completed: bool | None = None) -> int: ...

    def get(self, task_id: UUID) -> Task: ...

    def add(self, task: Task) -> Task: ...

    def update(self, task_id: UUID, changes: dict[str, Any]) -> Task: ...

    def delete(self, task_id: UUID) -> None: ...


class InMemoryTaskRepository:
    """Dict-backed storage. Insertion order doubles as creation order."""

    def __init__(self) -> None:
        self._tasks: dict[UUID, Task] = {}

    def list_tasks(
        self, *, completed: bool | None = None, limit: int | None = None, offset: int = 0
    ) -> list[Task]:
        end = None if limit is None else offset + limit
        return self._matching(completed)[offset:end]

    def count(self, *, completed: bool | None = None) -> int:
        return len(self._matching(completed))

    def get(self, task_id: UUID) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError:
            raise TaskNotFoundError(task_id) from None

    def add(self, task: Task) -> Task:
        self._tasks[task.id] = task
        return task

    def update(self, task_id: UUID, changes: dict[str, Any]) -> Task:
        current = self.get(task_id)
        updated = Task.model_validate({**current.model_dump(), **changes})
        self._tasks[task_id] = updated
        return updated

    def delete(self, task_id: UUID) -> None:
        try:
            del self._tasks[task_id]
        except KeyError:
            raise TaskNotFoundError(task_id) from None

    def _matching(self, completed: bool | None) -> list[Task]:
        tasks = list(self._tasks.values())
        if completed is None:
            return tasks
        return [task for task in tasks if task.completed == completed]


_repository = InMemoryTaskRepository()


def get_repository() -> TaskRepository:
    """FastAPI dependency: override it in tests, or return a database-backed repository here."""
    return _repository
