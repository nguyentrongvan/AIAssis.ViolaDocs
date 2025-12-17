from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio
import os

from .config import settings
from .db import AsyncSessionLocal
from .models.users import User
from .models.roles import Role
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
    recycle_bin,
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
            logger.info(f"Root user created: {settings.root_user_email}")
            logger.warning(f"Default password: {settings.root_user_password} - Please change after first login!")
    except Exception as e:
        # Check if error is due to missing tables (database not migrated yet)
        error_str = str(e).lower()
        if "does not exist" in error_str or "undefinedtable" in error_str or "relation" in error_str:
            logger.warning("Database tables not found. Please run migrations first:")
            logger.warning("   cd src/backend && alembic upgrade head")
            logger.warning("   Root user will be created automatically after migrations.")
        else:
            logger.error(f"Failed to create root user: {e}", exc_info=True)


async def ensure_default_roles():
    """Ensure default roles exist, create if not"""
    # User-level permissions: upload, search, scan, chat, folder, settings, reports, user
    # Document-level permissions (view/search/chat) are set when sharing documents, not in roles
    DEFAULT_ROLES = [
        {"name": "viewer", "permissions": []},  # No user-level permissions, only document-level view permission when shared
        {"name": "searcher", "permissions": ["search"]},  # User-level: can access search menu
        {"name": "chatter", "permissions": ["chat"]},  # User-level: can access chat menu
        {"name": "uploader", "permissions": ["upload"]},  # User-level: can access upload menu
        {"name": "scanner", "permissions": ["scan"]},  # User-level: can access scan menu
        {"name": "deleter", "permissions": ["delete"]},  # User-level: can access recycle bin menu
        {"name": "editor", "permissions": ["upload", "search", "scan", "chat", "folder"]},  # User-level: can access multiple menus
        {"name": "manager", "permissions": ["upload", "search", "scan", "chat", "folder", "settings", "reports", "user"]}  # All user-level permissions
    ]
    
    try:
        async with AsyncSessionLocal() as session:
            created_count = 0
            for role_data in DEFAULT_ROLES:
                # Check if role exists
                result = await session.execute(
                    select(Role).where(Role.name == role_data["name"])
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    continue
                
                # Create role
                role = Role(
                    name=role_data["name"],
                    permissions=role_data["permissions"]
                )
                session.add(role)
                created_count += 1
            
            if created_count > 0:
                await session.commit()
                logger.info(f"Created {created_count} default roles")
    except Exception as e:
        # Check if error is due to missing tables (database not migrated yet)
        error_str = str(e).lower()
        if "does not exist" in error_str or "undefinedtable" in error_str or "relation" in error_str:
            logger.warning("Database tables not found. Please run migrations first.")
        else:
            logger.error(f"Failed to create default roles: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create root user if not exists
    await ensure_root_user()
    # Startup: Create default roles if not exist
    await ensure_default_roles()
    
    # Start background worker only if enabled (for backward compatibility)
    # By default, workers run as separate services (Docker)
    enable_in_process_worker = os.getenv("ENABLE_IN_PROCESS_WORKER", "false").lower() == "true"
    worker_task = None
    
    if enable_in_process_worker:
        from .workers.ocr_worker import worker_loop
        worker_task = asyncio.create_task(worker_loop())
        logger.info("Background worker started for processing OCR and embedding jobs (in-process mode)")
    else:
        logger.info("In-process worker disabled. Use separate OCR worker service for job processing.")
    
    yield
    
    # Shutdown: Cancel worker task if running
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            logger.info("Background worker stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan
    )
    
    # Configure CORS
    # Allow common development origins
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:5173",  # Vite default port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
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
    app.include_router(recycle_bin.router, prefix=api_prefix)
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

