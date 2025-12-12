"""
System Configuration Management Router
Only accessible by root admin/maintainer users
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..dependencies import get_current_user, get_current_maintainer
from ..models.users import User
from ..config import settings
from ..utils.response import success_response, error_response

# Get .env file path (in backend directory)
BACKEND_DIR = Path(__file__).parent.parent.parent.parent
ENV_FILE_PATH = BACKEND_DIR / ".env"

router = APIRouter(prefix="/system/config", tags=["System Config"])


class ConfigUpdate(BaseModel):
    """Update configuration value"""
    key: str
    value: Any
    description: Optional[str] = None


class ConfigBulkUpdate(BaseModel):
    """Bulk update configuration"""
    configs: Dict[str, Any]


@router.get("")
async def get_system_config(
    current_user: User = Depends(get_current_maintainer),
    session: AsyncSession = Depends(get_session)
):
    """
    Get all system configuration values.
    Sensitive values (passwords, keys) are masked.
    """
    # Get all config values from settings
    config_dict = {}
    
    # Database settings
    config_dict["postgres_host"] = {
        "value": settings.postgres_host,
        "type": "string",
        "category": "database",
        "sensitive": False
    }
    config_dict["postgres_port"] = {
        "value": settings.postgres_port,
        "type": "integer",
        "category": "database",
        "sensitive": False
    }
    config_dict["postgres_user"] = {
        "value": settings.postgres_user,
        "type": "string",
        "category": "database",
        "sensitive": False
    }
    config_dict["postgres_password"] = {
        "value": "***" if settings.postgres_password else "",
        "type": "string",
        "category": "database",
        "sensitive": True
    }
    config_dict["postgres_db"] = {
        "value": settings.postgres_db,
        "type": "string",
        "category": "database",
        "sensitive": False
    }
    
    # Redis settings
    config_dict["redis_host"] = {
        "value": settings.redis_host,
        "type": "string",
        "category": "redis",
        "sensitive": False
    }
    config_dict["redis_port"] = {
        "value": settings.redis_port,
        "type": "integer",
        "category": "redis",
        "sensitive": False
    }
    config_dict["redis_db"] = {
        "value": settings.redis_db,
        "type": "integer",
        "category": "redis",
        "sensitive": False
    }
    
    # MinIO settings
    config_dict["minio_endpoint"] = {
        "value": settings.minio_endpoint,
        "type": "string",
        "category": "storage",
        "sensitive": False
    }
    config_dict["minio_access_key"] = {
        "value": settings.minio_access_key,
        "type": "string",
        "category": "storage",
        "sensitive": False
    }
    config_dict["minio_secret_key"] = {
        "value": "***" if settings.minio_secret_key else "",
        "type": "string",
        "category": "storage",
        "sensitive": True
    }
    config_dict["minio_secure"] = {
        "value": settings.minio_secure,
        "type": "boolean",
        "category": "storage",
        "sensitive": False
    }
    config_dict["minio_bucket"] = {
        "value": settings.minio_bucket,
        "type": "string",
        "category": "storage",
        "sensitive": False
    }
    
    # JWT settings
    config_dict["jwt_secret_key"] = {
        "value": "***" if settings.jwt_secret_key else "",
        "type": "string",
        "category": "security",
        "sensitive": True
    }
    config_dict["jwt_algorithm"] = {
        "value": settings.jwt_algorithm,
        "type": "string",
        "category": "security",
        "sensitive": False
    }
    config_dict["jwt_access_token_expire_minutes"] = {
        "value": settings.jwt_access_token_expire_minutes,
        "type": "integer",
        "category": "security",
        "sensitive": False
    }
    config_dict["jwt_refresh_token_expire_days"] = {
        "value": settings.jwt_refresh_token_expire_days,
        "type": "integer",
        "category": "security",
        "sensitive": False
    }
    
    # LLM settings
    config_dict["gemini_api_key"] = {
        "value": "***" if settings.gemini_api_key else "",
        "type": "string",
        "category": "ai",
        "sensitive": True
    }
    config_dict["openai_api_key"] = {
        "value": "***" if settings.openai_api_key else "",
        "type": "string",
        "category": "ai",
        "sensitive": True
    }
    
    # OCR settings
    config_dict["ocr_provider"] = {
        "value": settings.ocr_provider,
        "type": "string",
        "category": "ai",
        "sensitive": False
    }
    config_dict["ocr_languages"] = {
        "value": settings.ocr_languages,
        "type": "string",
        "category": "ai",
        "sensitive": False
    }
    
    # Embedding settings
    config_dict["embedding_model_name"] = {
        "value": settings.embedding_model_name,
        "type": "string",
        "category": "ai",
        "sensitive": False
    }
    config_dict["chroma_persist_dir"] = {
        "value": settings.chroma_persist_dir,
        "type": "string",
        "category": "ai",
        "sensitive": False
    }
    config_dict["chroma_collection"] = {
        "value": settings.chroma_collection,
        "type": "string",
        "category": "ai",
        "sensitive": False
    }
    config_dict["chroma_server_host"] = {
        "value": settings.chroma_server_host,
        "type": "string",
        "category": "ai",
        "sensitive": False
    }
    config_dict["chroma_server_port"] = {
        "value": settings.chroma_server_port,
        "type": "integer",
        "category": "ai",
        "sensitive": False
    }
    config_dict["chroma_server_ssl"] = {
        "value": settings.chroma_server_ssl,
        "type": "boolean",
        "category": "ai",
        "sensitive": False
    }
    
    # App settings
    config_dict["app_name"] = {
        "value": settings.app_name,
        "type": "string",
        "category": "app",
        "sensitive": False
    }
    config_dict["env"] = {
        "value": settings.env,
        "type": "string",
        "category": "app",
        "sensitive": False
    }
    config_dict["debug"] = {
        "value": settings.debug,
        "type": "boolean",
        "category": "app",
        "sensitive": False
    }
    config_dict["log_level"] = {
        "value": settings.log_level,
        "type": "string",
        "category": "app",
        "sensitive": False
    }
    
    # Retention settings
    config_dict["default_retention_days"] = {
        "value": settings.default_retention_days,
        "type": "integer",
        "category": "retention",
        "sensitive": False
    }
    config_dict["purge_grace_period_days"] = {
        "value": settings.purge_grace_period_days,
        "type": "integer",
        "category": "retention",
        "sensitive": False
    }
    
    # Upload settings
    config_dict["max_upload_size_mb"] = {
        "value": settings.max_upload_size_mb,
        "type": "integer",
        "category": "upload",
        "sensitive": False
    }
    config_dict["allowed_mime_types"] = {
        "value": settings.allowed_mime_types,
        "type": "string",
        "category": "upload",
        "sensitive": False
    }
    
    return success_response({
        "config": config_dict,
        "note": "Sensitive values are masked. Changes require server restart to take effect."
    })


@router.post("/update")
async def update_system_config(
    payload: ConfigUpdate,
    current_user: User = Depends(get_current_maintainer),
    session: AsyncSession = Depends(get_session)
):
    """
    Update a single configuration value.
    Note: This updates the .env file. Server restart may be required.
    """
    # Validate key exists
    if not hasattr(settings, payload.key):
        return error_response(
            f"Configuration key '{payload.key}' not found",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # Read current .env file
    try:
        with open(ENV_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return error_response(
            ".env file not found",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Update or add the key
    env_key = payload.key.upper()
    updated = False
    new_lines = []
    
    for line in lines:
        if line.strip().startswith(f"{env_key}="):
            # Update existing line
            if payload.value is None:
                continue  # Skip if value is None (delete)
            new_lines.append(f"{env_key}={payload.value}\n")
            updated = True
        else:
            new_lines.append(line)
    
    if not updated:
        # Add new line
        if payload.value is not None:
            new_lines.append(f"{env_key}={payload.value}\n")
    
    # Write back to .env file
    try:
        with open(ENV_FILE_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        return error_response(
            f"Failed to write .env file: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return success_response({
        "key": payload.key,
        "value": "***" if payload.key in ["postgres_password", "minio_secret_key", "jwt_secret_key", "gemini_api_key", "openai_api_key"] else payload.value,
        "message": "Configuration updated. Server restart may be required."
    })


@router.post("/update-bulk")
async def update_system_config_bulk(
    payload: ConfigBulkUpdate,
    current_user: User = Depends(get_current_maintainer),
    session: AsyncSession = Depends(get_session)
):
    """
    Bulk update multiple configuration values.
    Note: This updates the .env file. Server restart may be required.
    """
    # Read current .env file
    try:
        with open(ENV_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return error_response(
            ".env file not found",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Track which keys were updated
    updated_keys = set()
    new_lines = []
    existing_keys = set()
    
    # First pass: update existing keys
    for line in lines:
        line_stripped = line.strip()
        if "=" in line_stripped and not line_stripped.startswith("#"):
            key = line_stripped.split("=")[0].strip()
            existing_keys.add(key)
            
            if key in payload.configs:
                value = payload.configs[key]
                if value is not None:
                    new_lines.append(f"{key}={value}\n")
                    updated_keys.add(key)
                # If value is None, skip (delete)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Second pass: add new keys
    for key, value in payload.configs.items():
        if key not in updated_keys and value is not None:
            new_lines.append(f"{key}={value}\n")
            updated_keys.add(key)
    
    # Write back to .env file
    try:
        with open(ENV_FILE_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        return error_response(
            f"Failed to write .env file: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return success_response({
        "updated_keys": list(updated_keys),
        "message": "Configuration updated. Server restart may be required."
    })


@router.get("/categories")
async def get_config_categories(
    current_user: User = Depends(get_current_maintainer),
    session: AsyncSession = Depends(get_session)
):
    """Get list of configuration categories"""
    categories = [
        {"id": "database", "name": "Database", "description": "PostgreSQL connection settings"},
        {"id": "redis", "name": "Redis", "description": "Redis cache settings"},
        {"id": "storage", "name": "Storage", "description": "MinIO/S3 object storage settings"},
        {"id": "security", "name": "Security", "description": "JWT and authentication settings"},
        {"id": "ai", "name": "AI Services", "description": "LLM, OCR, and embedding settings"},
        {"id": "app", "name": "Application", "description": "General application settings"},
        {"id": "retention", "name": "Retention", "description": "Document retention policies"},
        {"id": "upload", "name": "Upload", "description": "File upload settings"},
    ]
    return success_response({"categories": categories})

