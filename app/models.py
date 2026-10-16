"""Pydantic models for the task API."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
    field_validator,
)

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def utc_now() -> datetime:
    return datetime.now(UTC)


class TaskCreate(BaseModel):
    """Body of POST /tasks."""

    model_config = ConfigDict(extra="forbid")

    title: Title
    description: str | None = None


class TaskUpdate(BaseModel):
    """Body of PATCH /tasks/{id}. Only fields present in the request are applied.

    title and completed may be omitted but not set to null; description may be null to clear it.
    """

    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    description: str | None = None
    completed: bool | None = None

    @field_validator("title", "completed")
    @classmethod
    def reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("cannot be null")
        return value


class Task(BaseModel):
    """A stored task. The server generates id and created_at."""

    id: UUID = Field(default_factory=uuid4)
    title: Title
    description: str | None = None
    completed: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class TaskPage(BaseModel):
    """One page of tasks plus the metadata needed to reach the neighbouring pages."""

    items: list[Task]
    total: int
    limit: int
    offset: int

    @computed_field
    @property
    def next_offset(self) -> int | None:
        following = self.offset + self.limit
        return following if following < self.total else None

    @computed_field
    @property
    def previous_offset(self) -> int | None:
        return max(self.offset - self.limit, 0) if self.offset > 0 else None


class ErrorResponse(BaseModel):
    """Body of every error response."""

    detail: str
