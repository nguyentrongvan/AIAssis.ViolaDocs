from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .config import settings
from .db import AsyncSessionLocal
from .models.users import User
from .services.auth import get_password_hash
from sqlalchemy import select

logger = logging.getLogger(__name__)
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
    system_config,
    tasks,
    uploads,
    users,
    workflows,
)


async def ensure_root_user():
    """Ensure root user exists, create if not"""
    try:
        async with AsyncSessionLocal() as session:
            # Check if root user exists
            result = await session.execute(
                select(User).where(User.email == settings.root_user_email)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.info(f"Root user already exists: {settings.root_user_email}")
                return
            
            # Check if any maintainer exists
            result = await session.execute(
                select(User).where(User.is_maintainer == True)
            )
            maintainer_exists = result.scalar_one_or_none()
            
            if maintainer_exists:
                logger.info("Maintainer user already exists, skipping root user creation")
                return
            
            # Create root user
            root_user = User(
                name=settings.root_user_name,
                email=settings.root_user_email,
                password_hash=get_password_hash(settings.root_user_password),
                role="admin",
                status="active",
                is_maintainer=True,  # Root user is maintainer
                created_by=None
            )
            session.add(root_user)
            await session.commit()
            logger.info(f"✅ Root user created: {settings.root_user_email}")
            logger.warning(f"⚠️  Default password: {settings.root_user_password} - Please change after first login!")
    except Exception as e:
        # Check if error is due to missing tables (database not migrated yet)
        error_str = str(e).lower()
        if "does not exist" in error_str or "undefinedtable" in error_str or "relation" in error_str:
            logger.warning("⚠️  Database tables not found. Please run migrations first:")
            logger.warning("   cd src/backend && alembic upgrade head")
            logger.warning("   Root user will be created automatically after migrations.")
        else:
            logger.error(f"Failed to create root user: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create root user if not exists
    await ensure_root_user()
    yield
    # Shutdown: cleanup if needed
    pass


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan
    )
    
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
    app.include_router(system_config.router, prefix=api_prefix)
    return app


app = create_app()

