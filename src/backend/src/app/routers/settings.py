from typing import Optional, List
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_session
from ..dependencies import get_current_admin_user
from ..models.users import User
from ..models.retention import RetentionPolicy
from ..utils.response import success_response, error_response

router = APIRouter(prefix="/settings", tags=["settings"])


# Retention Policy Models
class RetentionPolicyCreate(BaseModel):
    name: str
    duration_days: int
    disposition: str  # delete, archive
    legal_hold: bool = False


class RetentionPolicyUpdate(BaseModel):
    name: Optional[str] = None
    duration_days: Optional[int] = None
    disposition: Optional[str] = None
    legal_hold: Optional[bool] = None


# Provider Settings Models
class ProviderConfig(BaseModel):
    provider: str
    enabled: bool
    config: dict


# Chatbot Policy Models
class ChatbotPolicyUpdate(BaseModel):
    group_id: int
    policy: Optional[dict] = None  # Allow flexible policy dict
    # Also support flat structure for backward compatibility
    allowed_sources: Optional[List[str]] = None  # docs, reports, metrics
    allow_previews: Optional[bool] = None
    redaction_patterns: Optional[List[str]] = None
    max_context_tokens: Optional[int] = None
    allowed_llm_providers: Optional[List[str]] = None
    rate_limits: Optional[dict] = None


@router.get("/retention")
async def get_retention_policies(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Get all retention policies."""
    result = await session.execute(select(RetentionPolicy))
    policies = result.scalars().all()
    
    return success_response([{
        "id": p.id,
        "name": p.name,
        "duration_days": p.duration_days,
        "disposition": p.disposition,
        "legal_hold": p.legal_hold,
        "created_at": p.created_at.isoformat()
    } for p in policies])


@router.post("/retention")
async def create_retention_policy(
    payload: RetentionPolicyCreate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Create a new retention policy."""
    if payload.disposition not in ["delete", "archive"]:
        return error_response(
            "Disposition must be 'delete' or 'archive'",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    policy = RetentionPolicy(
        name=payload.name,
        duration_days=payload.duration_days,
        disposition=payload.disposition,
        legal_hold=payload.legal_hold
    )
    session.add(policy)
    await session.commit()
    await session.refresh(policy)
    
    return success_response({
        "id": policy.id,
        "name": policy.name,
        "duration_days": policy.duration_days,
        "disposition": policy.disposition,
        "legal_hold": policy.legal_hold
    })


@router.patch("/retention/{policy_id}")
async def update_retention_policy(
    policy_id: int,
    payload: RetentionPolicyUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Update a retention policy."""
    result = await session.execute(
        select(RetentionPolicy).where(RetentionPolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    
    if not policy:
        return error_response("Retention policy not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if payload.name is not None:
        policy.name = payload.name
    if payload.duration_days is not None:
        policy.duration_days = payload.duration_days
    if payload.disposition is not None:
        if payload.disposition not in ["delete", "archive"]:
            return error_response(
                "Disposition must be 'delete' or 'archive'",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        policy.disposition = payload.disposition
    if payload.legal_hold is not None:
        policy.legal_hold = payload.legal_hold
    
    await session.commit()
    await session.refresh(policy)
    
    return success_response({
        "id": policy.id,
        "name": policy.name,
        "duration_days": policy.duration_days,
        "disposition": policy.disposition,
        "legal_hold": policy.legal_hold
    })


@router.get("/providers")
async def get_provider_settings(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Get OCR/AI/search provider settings."""
    # TODO: Store provider settings in database or config
    # For now, return default settings
    from ..config import settings
    
    return success_response({
        "ocr": [
            {
                "name": "paddle",
                "enabled": True,
                "health": "unknown",
                "languages": ["en", "vi"]
            }
        ],
        "embedding": [
            {
                "name": "ollama",
                "enabled": bool(settings.ollama_base_url),
                "health": "unknown",
                "model": settings.ollama_embedding_model
            },
            {
                "name": "local",
                "enabled": True,
                "health": "unknown",
                "model": settings.embedding_model_name
            }
        ],
        "llm": [
            {
                "name": "ollama",
                "enabled": bool(settings.ollama_base_url),
                "health": "unknown",
                "models": [settings.ollama_llm_model]
            }
        ],
        "search": [
            {
                "name": "postgres",
                "enabled": True,
                "health": "unknown"
            }
        ]
    })


@router.post("/providers")
async def update_provider_settings(
    payload: dict,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Update OCR/AI/search provider settings."""
    # TODO: Store provider settings in database
    return success_response({
        "message": "Provider settings updated",
        "settings": payload
    })


@router.get("/chatbot")
async def get_chatbot_settings(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Get chatbot policies per group."""
    from ..models.groups import DocumentGroup
    
    result = await session.execute(select(DocumentGroup))
    groups = result.scalars().all()
    
    return success_response([{
        "group_id": g.id,
        "group_name": g.name,
        "chatbot_policy": g.chatbot_policy or {}
    } for g in groups])


@router.post("/chatbot")
async def update_chatbot_policy(
    payload: ChatbotPolicyUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Update chatbot policy for a document group."""
    from ..models.groups import DocumentGroup
    
    result = await session.execute(
        select(DocumentGroup).where(DocumentGroup.id == payload.group_id)
    )
    group = result.scalar_one_or_none()
    
    if not group:
        return error_response("Document group not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Update chatbot policy
    if payload.policy:
        # Use policy dict directly if provided
        group.chatbot_policy = payload.policy
    else:
        # Build policy from individual fields
        policy = group.chatbot_policy or {}
        if payload.allowed_sources is not None:
            policy["allowed_sources"] = payload.allowed_sources
        if payload.allow_previews is not None:
            policy["allow_previews"] = payload.allow_previews
        if payload.redaction_patterns is not None:
            policy["redaction_patterns"] = payload.redaction_patterns
        if payload.max_context_tokens is not None:
            policy["max_context_tokens"] = payload.max_context_tokens
        if payload.allowed_llm_providers is not None:
            policy["allowed_llm_providers"] = payload.allowed_llm_providers
        if payload.rate_limits is not None:
            policy["rate_limits"] = payload.rate_limits
        group.chatbot_policy = policy
    
    await session.commit()
    await session.refresh(group)
    
    return success_response({
        "group_id": group.id,
        "chatbot_policy": group.chatbot_policy
    })


# LLM Settings Models
class LLMSettingsUpdate(BaseModel):
    ollama_base_url: Optional[str] = None
    ollama_api_key: Optional[str] = None
    ollama_llm_model: Optional[str] = None
    ollama_embedding_model: Optional[str] = None


@router.get("/llm")
async def get_llm_settings(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Get LLM settings (Ollama configuration)."""
    from ..config import settings
    from pathlib import Path
    
    # Get .env file path
    BACKEND_DIR = Path(__file__).parent.parent.parent.parent
    ENV_FILE_PATH = BACKEND_DIR / ".env"
    
    # Read current values from settings
    return success_response({
        "ollama_base_url": settings.ollama_base_url,
        "ollama_api_key": "***" if settings.ollama_api_key else "",
        "ollama_llm_model": settings.ollama_llm_model,
        "ollama_embedding_model": settings.ollama_embedding_model,
        "note": "API key is masked. Changes require server restart to take effect."
    })


@router.post("/llm")
async def update_llm_settings(
    payload: LLMSettingsUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Update LLM settings (Ollama configuration)."""
    from pathlib import Path
    
    # Get .env file path
    BACKEND_DIR = Path(__file__).parent.parent.parent.parent
    ENV_FILE_PATH = BACKEND_DIR / ".env"
    
    # Read current .env file
    try:
        with open(ENV_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return error_response(
            ".env file not found",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Update or add the keys
    updated_keys = []
    new_lines = []
    existing_keys = set()
    
    # Map of setting names to env variable names
    setting_map = {
        "ollama_base_url": "OLLAMA_BASE_URL",
        "ollama_api_key": "OLLAMA_API_KEY",
        "ollama_llm_model": "OLLAMA_LLM_MODEL",
        "ollama_embedding_model": "OLLAMA_EMBEDDING_MODEL"
    }
    
    # First pass: update existing keys
    for line in lines:
        line_stripped = line.strip()
        if "=" in line_stripped and not line_stripped.startswith("#"):
            key = line_stripped.split("=")[0].strip()
            existing_keys.add(key)
            
            # Check if this key should be updated
            updated = False
            for setting_name, env_key in setting_map.items():
                if key == env_key:
                    value = getattr(payload, setting_name, None)
                    if value is not None:
                        new_lines.append(f"{env_key}={value}\n")
                        updated_keys.append(setting_name)
                        updated = True
                        break
            
            if not updated:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Second pass: add new keys
    for setting_name, env_key in setting_map.items():
        if setting_name not in updated_keys:
            value = getattr(payload, setting_name, None)
            if value is not None and env_key not in existing_keys:
                new_lines.append(f"{env_key}={value}\n")
                updated_keys.append(setting_name)
    
    # Write back to .env file
    try:
        with open(ENV_FILE_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        return error_response(
            f"Failed to write .env file: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Return updated settings (mask API key)
    from ..config import settings
    return success_response({
        "ollama_base_url": payload.ollama_base_url or settings.ollama_base_url,
        "ollama_api_key": "***" if (payload.ollama_api_key or settings.ollama_api_key) else "",
        "ollama_llm_model": payload.ollama_llm_model or settings.ollama_llm_model,
        "ollama_embedding_model": payload.ollama_embedding_model or settings.ollama_embedding_model,
        "updated_keys": updated_keys,
        "message": "LLM settings updated. Server restart required to take effect."
    })
