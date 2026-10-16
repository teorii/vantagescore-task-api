"""Application factory."""

from fastapi import FastAPI

from app.errors import register_error_handlers
from app.routers import tasks


def create_app() -> FastAPI:
    app = FastAPI(title="Task API", version="1.0.0")
    register_error_handlers(app)
    app.include_router(tasks.router)
    return app


app = create_app()
