"""CRUD endpoints for tasks."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response, status

from app.events import log_event
from app.models import ErrorResponse, Task, TaskCreate, TaskPage, TaskUpdate
from app.storage import TaskRepository, get_repository

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Invalid input",
        },
    },
)

Repository = Annotated[TaskRepository, Depends(get_repository)]
NOT_FOUND = {status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Task not found"}}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    repo: Repository,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
) -> Task:
    task = repo.add(Task(**payload.model_dump()))
    response.headers["Location"] = str(request.url_for("get_task", task_id=task.id))
    background_tasks.add_task(log_event, "created", task.id)
    return task


@router.get("")
async def list_tasks(
    repo: Repository,
    completed: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TaskPage:
    return TaskPage(
        items=repo.list_tasks(completed=completed, limit=limit, offset=offset),
        total=repo.count(completed=completed),
        limit=limit,
        offset=offset,
    )


@router.get("/{task_id}", responses=NOT_FOUND)
async def get_task(task_id: UUID, repo: Repository) -> Task:
    return repo.get(task_id)


@router.patch("/{task_id}", responses=NOT_FOUND)
async def update_task(task_id: UUID, payload: TaskUpdate, repo: Repository) -> Task:
    return repo.update(task_id, payload.model_dump(exclude_unset=True))


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=NOT_FOUND,
)
async def delete_task(
    task_id: UUID,
    repo: Repository,
    background_tasks: BackgroundTasks,
) -> None:
    repo.delete(task_id)
    background_tasks.add_task(log_event, "deleted", task_id)
