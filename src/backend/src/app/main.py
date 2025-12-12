from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import (
    ai,
    audit,
    auth,
    chat,
    devices,
    documents,
    folders,
    groups,
    health,
    reports,
    roles,
    scan_jobs,
    search,
    settings as settings_router,
    tasks,
    uploads,
    users,
    workflows,
)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",  # Vite default port
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    api_prefix = settings.api_prefix

    app.include_router(health.router, prefix=api_prefix)
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(uploads.router, prefix=api_prefix)
    app.include_router(scan_jobs.router, prefix=api_prefix)
    app.include_router(search.router, prefix=api_prefix)
    app.include_router(chat.router, prefix=api_prefix)
    app.include_router(reports.router, prefix=api_prefix)
    app.include_router(audit.router, prefix=api_prefix)
    app.include_router(documents.router, prefix=api_prefix)
    app.include_router(folders.router, prefix=api_prefix)
    app.include_router(groups.router, prefix=api_prefix)
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(roles.router, prefix=api_prefix)
    app.include_router(devices.router, prefix=api_prefix)
    app.include_router(workflows.router, prefix=api_prefix)
    app.include_router(tasks.router, prefix=api_prefix)
    app.include_router(ai.router, prefix=api_prefix)
    app.include_router(settings_router.router, prefix=api_prefix)
    return app


app = create_app()

