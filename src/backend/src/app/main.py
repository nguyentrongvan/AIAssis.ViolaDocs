from fastapi import FastAPI

from .config import settings
from .routers import (
    ai,
    auth,
    chat,
    devices,
    documents,
    groups,
    health,
    reports,
    search,
    uploads,
    users,
    workflows,
)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")
    api_prefix = settings.api_prefix

    app.include_router(health.router, prefix=api_prefix)
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(uploads.router, prefix=api_prefix)
    app.include_router(search.router, prefix=api_prefix)
    app.include_router(chat.router, prefix=api_prefix)
    app.include_router(reports.router, prefix=api_prefix)
    app.include_router(documents.router, prefix=api_prefix)
    app.include_router(groups.router, prefix=api_prefix)
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(devices.router, prefix=api_prefix)
    app.include_router(workflows.router, prefix=api_prefix)
    app.include_router(ai.router, prefix=api_prefix)
    return app


app = create_app()

