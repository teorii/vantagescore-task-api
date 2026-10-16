"""Exception handlers that give every failure the same {"detail": "..."} body."""

from collections.abc import Mapping

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.storage import TaskNotFoundError

_LOCATION_PREFIXES = {"body", "query", "path"}


def _error(status_code: int, detail: str, headers: Mapping[str, str] | None = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)


def _describe(exc: RequestValidationError) -> str:
    """Flatten Pydantic's error list into 'field: message' pairs."""
    parts: list[str] = []
    for error in exc.errors():
        location = [str(item) for item in error["loc"]]
        if error["type"] == "json_invalid":
            location = ["body"]  # the offset of the syntax error means nothing to a client
        elif len(location) > 1 and location[0] in _LOCATION_PREFIXES:
            location = location[1:]
        parts.append(f"{'.'.join(location)}: {error['msg']}")
    return "; ".join(parts)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(TaskNotFoundError)
    async def task_not_found(request: Request, exc: TaskNotFoundError) -> JSONResponse:
        return _error(status.HTTP_404_NOT_FOUND, str(exc))

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, _describe(exc))

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Routes raise domain errors, never HTTPException, so a 404 here is an unmatched route.
        detail = exc.detail
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            detail = f"No route matches {request.method} {request.url.path}"
        return _error(exc.status_code, detail, headers=exc.headers)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        return _error(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error")
