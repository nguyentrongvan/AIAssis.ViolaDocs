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
                "name": "openai",
                "enabled": bool(settings.openai_api_key),
                "health": "unknown",
                "model": "text-embedding-3-small"
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
                "name": "openai",
                "enabled": bool(settings.openai_api_key),
                "health": "unknown",
                "models": ["gpt-4", "gpt-3.5-turbo"]
            },
            {
                "name": "gemini",
                "enabled": bool(settings.gemini_api_key),
                "health": "unknown",
                "models": ["gemini-pro"]
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

