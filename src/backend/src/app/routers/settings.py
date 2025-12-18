from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import time
import json
import os
from pathlib import Path

from ..db import get_session
from ..dependencies import get_current_admin_user, get_current_user, require_permission_or_staff
from ..models.users import User
from ..models.retention import RetentionPolicy
from ..services.settings_service import SettingsService
from ..utils.response import success_response, error_response
from ..utils.ocr_helpers import get_tesseract_install_guide, get_easyocr_fix_guide, detect_tesseract_path
import subprocess
import sys

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


# OCR Settings Models
class OCRSettingsUpdate(BaseModel):
    provider: Optional[str] = None  # paddle, tesseract, easyocr, auto
    languages: Optional[List[str]] = None  # List of language codes
    enabled_providers: Optional[Dict[str, bool]] = None  # Provider enable/disable


@router.get("/ocr")
async def get_ocr_settings(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Get OCR settings (provider, languages)"""
    from ..config import settings as config_settings
    
    # Get from DB, fallback to config
    ocr_provider = await SettingsService.get_setting("ocr.provider", config_settings.ocr_provider, session)
    ocr_languages = await SettingsService.get_setting("ocr.languages", config_settings.ocr_lang_list, session)
    
    # Get enabled providers from DB
    enabled_providers = {
        "paddle": await SettingsService.get_setting("ocr.paddle.enabled", True, session),
        "tesseract": await SettingsService.get_setting("ocr.tesseract.enabled", False, session),
        "easyocr": await SettingsService.get_setting("ocr.easyocr.enabled", False, session),
    }
    
    return success_response({
        "provider": ocr_provider,
        "languages": ocr_languages if isinstance(ocr_languages, list) else config_settings.ocr_lang_list,
        "enabled_providers": enabled_providers
    })


@router.post("/ocr")
async def update_ocr_settings(
    payload: OCRSettingsUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Update OCR settings"""
    updated_keys = []
    
    if payload.provider is not None:
        await SettingsService.set_setting(
            "ocr.provider",
            payload.provider,
            "ocr",
            "Selected OCR provider",
            False,
            current_user.id,
            session
        )
        updated_keys.append("provider")
    
    if payload.languages is not None:
        await SettingsService.set_setting(
            "ocr.languages",
            payload.languages,
            "ocr",
            "Selected OCR languages",
            False,
            current_user.id,
            session
        )
        updated_keys.append("languages")
    
    if payload.enabled_providers is not None:
        for provider_name, enabled in payload.enabled_providers.items():
            await SettingsService.set_setting(
                f"ocr.{provider_name}.enabled",
                enabled,
                "ocr",
                f"{provider_name} OCR provider enabled",
                False,
                current_user.id,
                session
            )
        updated_keys.append("enabled_providers")
    
    return success_response({
        "message": "OCR settings updated",
        "updated_keys": updated_keys
    })


@router.get("/providers")
async def get_provider_settings(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Get OCR/AI/search provider settings."""
    from ..config import settings
    
    # Get enabled providers from DB
    paddle_enabled = await SettingsService.get_setting("ocr.paddle.enabled", True, session)
    tesseract_enabled = await SettingsService.get_setting("ocr.tesseract.enabled", False, session)
    easyocr_enabled = await SettingsService.get_setting("ocr.easyocr.enabled", False, session)
    
    # Check OCR provider availability
    ocr_providers = []
    
    # PaddleOCR
    try:
        from paddleocr import PaddleOCR
        ocr_providers.append({
            "name": "paddle",
            "enabled": paddle_enabled,
            "health": "available",
            "languages": ["en", "vi", "ch", "japan", "korean"],
            "description": "Best for Vietnamese, supports English, Vietnamese, Chinese, Japanese, and Korean"
        })
    except ImportError:
        ocr_providers.append({
            "name": "paddle",
            "enabled": paddle_enabled,
            "health": "not_installed",
            "languages": ["en", "vi", "ch", "japan", "korean"],
            "description": "Best for Vietnamese, supports English, Vietnamese, Chinese, Japanese, and Korean"
        })
    
    # Tesseract
    try:
        import pytesseract
        try:
            pytesseract.get_tesseract_version()
            ocr_providers.append({
                "name": "tesseract",
                "enabled": tesseract_enabled,
                "health": "available",
                "languages": ["en", "vi", "zh", "ja", "ko", "fr", "de", "es"],
                "description": "Mature, stable, multi-language support. Requires system installation."
            })
        except Exception as e:
            # Tesseract Python package is installed but Tesseract binary not found
            tesseract_path = detect_tesseract_path()
            install_guide = get_tesseract_install_guide()
            ocr_providers.append({
                "name": "tesseract",
                "enabled": tesseract_enabled,
                "health": "system_not_found",
                "languages": ["en", "vi", "zh", "ja", "ko", "fr", "de", "es"],
                "description": "Tesseract OCR binary not found in system. Please install Tesseract OCR engine.",
                "fix_guide": install_guide,
                "can_auto_fix": False,
                "detected_path": tesseract_path
            })
    except ImportError:
        ocr_providers.append({
            "name": "tesseract",
            "enabled": tesseract_enabled,
            "health": "not_installed",
            "languages": ["en", "vi", "zh", "ja", "ko", "fr", "de", "es"],
            "description": "Mature, stable, multi-language support. Requires system installation."
        })
    
    # EasyOCR
    try:
        # Try to import easyocr - this may fail due to torch DLL issues on Windows
        import easyocr
        # If import succeeds, mark as available
        ocr_providers.append({
            "name": "easyocr",
            "enabled": easyocr_enabled,
            "health": "available",
            "languages": ["en", "vi", "ch_sim", "ja", "ko", "fr", "de", "es"],
            "description": "Easy to use, good accuracy, 80+ languages. Multi-language support. Downloads models automatically."
        })
    except (ImportError, ModuleNotFoundError):
        # EasyOCR not installed
        ocr_providers.append({
            "name": "easyocr",
            "enabled": easyocr_enabled,
            "health": "not_installed",
            "languages": ["en", "vi", "ch_sim", "ja", "ko", "fr", "de", "es"],
            "description": "Easy to use, good accuracy, 80+ languages. Multi-language support. Downloads models automatically."
        })
    except (OSError, RuntimeError, Exception) as e:
        # Catch torch DLL errors and other runtime errors (e.g., Windows DLL issues)
        error_msg = str(e)
        is_torch_error = "WinError" in error_msg or "dll" in error_msg.lower() or "torch" in error_msg.lower()
        
        if is_torch_error:
            error_msg = "Torch/PyTorch DLL error (common on Windows). Try reinstalling torch or use another OCR provider."
            fix_guide = get_easyocr_fix_guide()
            ocr_providers.append({
                "name": "easyocr",
                "enabled": easyocr_enabled,
                "health": "error",
                "languages": ["en", "vi", "ch_sim", "ja", "ko", "fr", "de", "es"],
                "description": error_msg,
                "fix_guide": fix_guide,
                "can_auto_fix": True,
                "error_details": str(e)[:200]
            })
        else:
            # Other errors
            ocr_providers.append({
                "name": "easyocr",
                "enabled": easyocr_enabled,
                "health": "error",
                "languages": ["en", "vi", "ch_sim", "ja", "ko", "fr", "de", "es"],
                "description": f"EasyOCR error: {error_msg[:150]}",
                "fix_guide": None,
                "can_auto_fix": False,
                "error_details": str(e)[:200]
            })
    
    return success_response({
        "ocr": ocr_providers,
        "embedding": [
            {
                "name": "ollama",
                "enabled": bool(settings.ollama_base_url),
                "health": "unknown",
                "model": settings.ollama_embedding_model,
                "description": "Local embedding via Ollama OpenAI-compatible API"
            }
        ],
        "llm": [
            {
                "name": "ollama",
                "enabled": bool(settings.ollama_base_url),
                "health": "unknown",
                "models": [settings.ollama_llm_model],
                "description": "Local LLM via Ollama OpenAI-compatible API"
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
    updated_keys = []
    
    # Update OCR provider enabled states
    if "ocr" in payload and isinstance(payload["ocr"], list):
        for provider in payload["ocr"]:
            if "name" in provider and "enabled" in provider:
                provider_name = provider["name"]
                enabled = provider.get("enabled", False)
                await SettingsService.set_setting(
                    f"ocr.{provider_name}.enabled",
                    enabled,
                    "ocr",
                    f"{provider_name} OCR provider enabled",
                    False,
                    current_user.id,
                    session
                )
                updated_keys.append(f"ocr.{provider_name}.enabled")
    
    return success_response({
        "message": "Provider settings updated",
        "updated_keys": updated_keys
    })


@router.post("/providers/{provider_name}/fix")
async def fix_provider(
    provider_name: str,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Auto-fix provider installation issues"""
    
    if provider_name == "easyocr":
        # Auto-fix EasyOCR by reinstalling torch and easyocr
        try:
            # Get the fix guide to get the command
            fix_guide = get_easyocr_fix_guide()
            command = fix_guide.get("auto_fix_command", "pip uninstall torch easyocr -y && pip install torch easyocr")
            
            # Split command into uninstall and install
            uninstall_cmd = [sys.executable, "-m", "pip", "uninstall", "torch", "easyocr", "-y"]
            install_cmd = [sys.executable, "-m", "pip", "install", "torch", "easyocr"]
            
            # Run uninstall
            uninstall_result = subprocess.run(
                uninstall_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if uninstall_result.returncode != 0:
                return error_response(
                    message="Failed to uninstall torch/easyocr",
                    details=uninstall_result.stderr,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Run install
            install_result = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout for installation
            )
            
            if install_result.returncode != 0:
                return error_response(
                    message="Failed to install torch/easyocr",
                    details=install_result.stderr,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Verify installation by trying to import
            try:
                import easyocr
                verification_status = "success"
                verification_message = "EasyOCR installed and importable"
            except Exception as e:
                verification_status = "warning"
                verification_message = f"EasyOCR installed but import failed: {str(e)[:200]}"
            
            return success_response({
                "message": "EasyOCR fix completed",
                "provider": provider_name,
                "verification": {
                    "status": verification_status,
                    "message": verification_message
                },
                "output": {
                    "uninstall": uninstall_result.stdout,
                    "install": install_result.stdout
                }
            })
            
        except subprocess.TimeoutExpired:
            return error_response(
                message="Fix operation timed out",
                details="The installation process took too long. Please try again or fix manually.",
                status_code=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except Exception as e:
            return error_response(
                message="Failed to fix EasyOCR",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif provider_name == "tesseract":
        # Tesseract cannot be auto-fixed, return guide
        install_guide = get_tesseract_install_guide()
        return error_response(
            message="Tesseract cannot be auto-fixed",
            details={"message": "Tesseract requires manual system installation. Please follow the installation guide.", "fix_guide": install_guide},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    else:
        return error_response(
            message=f"Provider '{provider_name}' does not support auto-fix",
            status_code=status.HTTP_400_BAD_REQUEST
        )


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


@router.get("/chatbot/prompts")
async def get_chatbot_prompts(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Get chatbot prompt templates."""
    from ..services.settings_service import SettingsService
    from ..prompts import (
        CHATBOT_SYSTEM_PROMPT,
        CHATBOT_CONTEXT_PROMPT,
        CHATBOT_NO_CONTEXT_PROMPT
    )
    
    # Get prompts from settings, fallback to defaults
    system_prompt = await SettingsService.get_setting(
        "chatbot_system_prompt",
        default=CHATBOT_SYSTEM_PROMPT,
        session=session
    )
    context_prompt = await SettingsService.get_setting(
        "chatbot_context_prompt",
        default=CHATBOT_CONTEXT_PROMPT,
        session=session
    )
    no_context_prompt = await SettingsService.get_setting(
        "chatbot_no_context_prompt",
        default=CHATBOT_NO_CONTEXT_PROMPT,
        session=session
    )
    
    return success_response({
        "system_prompt": system_prompt,
        "context_prompt": context_prompt,
        "no_context_prompt": no_context_prompt
    })


class ChatbotPromptsUpdate(BaseModel):
    system_prompt: Optional[str] = None
    context_prompt: Optional[str] = None
    no_context_prompt: Optional[str] = None


@router.post("/chatbot/prompts")
async def update_chatbot_prompts(
    payload: ChatbotPromptsUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Update chatbot prompt templates."""
    from ..services.settings_service import SettingsService
    from ..models.settings import SystemSettings
    
    updated = []
    deleted = []
    
    # Handle system_prompt
    if payload.system_prompt is not None:
        if payload.system_prompt == "":
            # Delete setting to use default
            result = await session.execute(
                select(SystemSettings).where(SystemSettings.key == "chatbot_system_prompt")
            )
            setting = result.scalar_one_or_none()
            if setting:
                await session.delete(setting)
                deleted.append("system_prompt")
        else:
            await SettingsService.set_setting(
                key="chatbot_system_prompt",
                value=payload.system_prompt,
                category="chatbot",
                description="System prompt for chatbot assistant",
                sensitive=False,
                user_id=current_user.id,
                session=session
            )
            updated.append("system_prompt")
    
    # Handle context_prompt
    if payload.context_prompt is not None:
        if payload.context_prompt == "":
            # Delete setting to use default
            result = await session.execute(
                select(SystemSettings).where(SystemSettings.key == "chatbot_context_prompt")
            )
            setting = result.scalar_one_or_none()
            if setting:
                await session.delete(setting)
                deleted.append("context_prompt")
        else:
            await SettingsService.set_setting(
                key="chatbot_context_prompt",
                value=payload.context_prompt,
                category="chatbot",
                description="Prompt template for chatbot with document context",
                sensitive=False,
                user_id=current_user.id,
                session=session
            )
            updated.append("context_prompt")
    
    # Handle no_context_prompt
    if payload.no_context_prompt is not None:
        if payload.no_context_prompt == "":
            # Delete setting to use default
            result = await session.execute(
                select(SystemSettings).where(SystemSettings.key == "chatbot_no_context_prompt")
            )
            setting = result.scalar_one_or_none()
            if setting:
                await session.delete(setting)
                deleted.append("no_context_prompt")
        else:
            await SettingsService.set_setting(
                key="chatbot_no_context_prompt",
                value=payload.no_context_prompt,
                category="chatbot",
                description="Prompt template for chatbot without document context",
                sensitive=False,
                user_id=current_user.id,
                session=session
            )
            updated.append("no_context_prompt")
    
    await session.commit()
    
    message_parts = []
    if updated:
        message_parts.append(f"Updated: {', '.join(updated)}")
    if deleted:
        message_parts.append(f"Reset to defaults: {', '.join(deleted)}")
    
    return success_response({
        "message": "; ".join(message_parts) if message_parts else "No changes",
        "updated": updated,
        "deleted": deleted
    })


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
    from ..config import settings as config_settings
    
    # Get from DB, fallback to config
    ollama_base_url = await SettingsService.get_setting("llm.ollama.base_url", config_settings.ollama_base_url, session)
    ollama_api_key_db = await SettingsService.get_setting("llm.ollama.api_key", None, session)
    ollama_llm_model = await SettingsService.get_setting("llm.ollama.llm_model", config_settings.ollama_llm_model, session)
    ollama_embedding_model = await SettingsService.get_setting("llm.ollama.embedding_model", config_settings.ollama_embedding_model, session)
    
    # Use config API key if DB doesn't have it
    api_key_display = "***" if (ollama_api_key_db or config_settings.ollama_api_key) else ""
    
    return success_response({
        "ollama_base_url": ollama_base_url,
        "ollama_api_key": api_key_display,
        "ollama_llm_model": ollama_llm_model,
        "ollama_embedding_model": ollama_embedding_model,
        "note": "API key is masked. Changes require server restart to take effect."
    })


@router.post("/llm")
async def update_llm_settings(
    payload: LLMSettingsUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Update LLM settings (Ollama configuration)."""
    from ..config import settings as config_settings
    updated_keys = []
    
    if payload.ollama_base_url is not None:
        await SettingsService.set_setting(
            "llm.ollama.base_url",
            payload.ollama_base_url,
            "llm",
            "Ollama base URL",
            False,
            current_user.id,
            session
        )
        updated_keys.append("ollama_base_url")
    
    if payload.ollama_api_key is not None:
        await SettingsService.set_setting(
            "llm.ollama.api_key",
            payload.ollama_api_key,
            "llm",
            "Ollama API key",
            True,  # Sensitive
            current_user.id,
            session
        )
        updated_keys.append("ollama_api_key")
    
    if payload.ollama_llm_model is not None:
        await SettingsService.set_setting(
            "llm.ollama.llm_model",
            payload.ollama_llm_model,
            "llm",
            "Ollama LLM model",
            False,
            current_user.id,
            session
        )
        updated_keys.append("ollama_llm_model")
    
    if payload.ollama_embedding_model is not None:
        await SettingsService.set_setting(
            "llm.ollama.embedding_model",
            payload.ollama_embedding_model,
            "llm",
            "Ollama embedding model",
            False,
            current_user.id,
            session
        )
        updated_keys.append("ollama_embedding_model")
    
    # Get updated values
    ollama_base_url = await SettingsService.get_setting("llm.ollama.base_url", config_settings.ollama_base_url, session)
    ollama_llm_model = await SettingsService.get_setting("llm.ollama.llm_model", config_settings.ollama_llm_model, session)
    ollama_embedding_model = await SettingsService.get_setting("llm.ollama.embedding_model", config_settings.ollama_embedding_model, session)
    ollama_api_key_db = await SettingsService.get_setting("llm.ollama.api_key", None, session)
    
    return success_response({
        "ollama_base_url": ollama_base_url,
        "ollama_api_key": "***" if ollama_api_key_db else "",
        "ollama_llm_model": ollama_llm_model,
        "ollama_embedding_model": ollama_embedding_model,
        "updated_keys": updated_keys,
        "message": "LLM settings updated. Server restart required to take effect."
    })


# Purge Grace Period Settings Models
class PurgeGracePeriodUpdate(BaseModel):
    days: int


@router.get("/purge_grace_period")
async def get_purge_grace_period(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get purge grace period setting (admin/staff only)."""
    # Only admin/staff can view this setting
    if current_user.role not in ["admin", "staff"]:
        return error_response("Access denied. Admin/staff only.", status_code=status.HTTP_403_FORBIDDEN)
    
    from ..services.deletion_service import DocumentDeletionService
    days = await DocumentDeletionService.get_purge_grace_period_days(session)
    
    return success_response({
        "days": days,
        "default": 1,
        "min": 0,
        "max": 365
    })


@router.put("/purge_grace_period")
async def update_purge_grace_period(
    payload: PurgeGracePeriodUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update purge grace period setting (admin/staff only)."""
    # Only admin/staff can update this setting
    if current_user.role not in ["admin", "staff"]:
        return error_response("Access denied. Admin/staff only.", status_code=status.HTTP_403_FORBIDDEN)
    
    # Validate days (min: 0, max: 365)
    if payload.days < 0 or payload.days > 365:
        return error_response(
            "Purge grace period must be between 0 and 365 days",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Update setting
    await SettingsService.set_setting(
        "purge_grace_period_days",
        payload.days,
        "deletion",
        "Number of days before soft-deleted documents are permanently purged",
        False,
        current_user.id,
        session
    )
    
    return success_response({
        "days": payload.days,
        "message": "Purge grace period updated successfully"
    })


# Ollama Models Management
class OllamaModelPullRequest(BaseModel):
    model_name: str


class OllamaModelTestRequest(BaseModel):
    model_name: str
    model_type: str  # "llm" or "embedding"
    test_input: Optional[str] = None


def _load_library_models() -> Dict:
    """Load curated library models from JSON file"""
    try:
        # Get the path to the data directory
        # settings.py is in routers/, so we need to go up one level to app/ then into data/
        current_dir = Path(__file__).parent.parent
        json_path = current_dir / "data" / "ollama_library_models.json"
        
        if not json_path.exists():
            print(f"Warning: Library models file not found at {json_path}")
            return {"models": []}
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Debug: Print loaded models count
            models_count = len(data.get("models", []))
            print(f"Loaded {models_count} library models from {json_path}")
            return data
    except Exception as e:
        print(f"Error loading library models: {e}")
        return {"models": []}


def _find_model_in_library(model_name: str, library_models: List[Dict]) -> Optional[Dict]:
    """Find model info in library by name"""
    for lib_model in library_models:
        # Check base name
        if lib_model.get("name") == model_name:
            return lib_model
        # Check variants
        variants = lib_model.get("variants", [])
        for variant in variants:
            if variant == model_name:
                return lib_model
        # Check if model_name starts with base name (e.g., "llama3.2:1b" starts with "llama3.2")
        base_name = lib_model.get("name", "")
        if model_name.startswith(base_name + ":") or model_name == base_name:
            return lib_model
    return None


@router.get("/ollama/models")
async def get_ollama_models(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Get list of Ollama models from Ollama API and library."""
    from ..config import settings as config_settings, get_ollama_base_url_from_db
    
    try:
        # Get Ollama base URL from DB or config
        ollama_base_url = await get_ollama_base_url_from_db()
        
        if not ollama_base_url:
            return error_response(
                "Ollama base URL not configured",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Get currently configured models
        ollama_llm_model = await SettingsService.get_setting(
            "llm.ollama.llm_model", 
            config_settings.ollama_llm_model, 
            session
        )
        ollama_embedding_model = await SettingsService.get_setting(
            "llm.ollama.embedding_model", 
            config_settings.ollama_embedding_model, 
            session
        )
        
        # Load library models
        library_data = _load_library_models()
        library_models = library_data.get("models", [])
        
        # Debug: Check for specific models in library
        target_models = ["qwen2.5:0.5b", "qwen2.5:1.5b", "mistral:latest", "phi3:latest"]
        print(f"Checking library for target models:")
        for lib_model in library_models:
            variants = lib_model.get("variants", [])
            for target in target_models:
                if target in variants:
                    print(f"  Found {target} in {lib_model.get('name')} variants")
        
        # Call Ollama API to get downloaded models
        downloaded_models = []
        ollama_connected = False
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{ollama_base_url}/api/tags")
                
                if response.status_code == 200:
                    ollama_connected = True
                    data = response.json()
                    downloaded_models = data.get("models", [])
        except (httpx.ConnectError, httpx.TimeoutException):
            ollama_connected = False
        except Exception as e:
            print(f"Error fetching downloaded models: {e}")
            ollama_connected = False
        
        # Create a set of downloaded model names for quick lookup
        downloaded_names = set()
        downloaded_models_dict = {}
        for model_data in downloaded_models:
            model_name = model_data.get("name") or model_data.get("model", "")
            downloaded_names.add(model_name)
            downloaded_models_dict[model_name] = model_data
        
        # Merge models: start with downloaded models
        merged_models = []
        
        # Add downloaded models with library info
        for model_name in downloaded_names:
            model_data = downloaded_models_dict[model_name]
            library_info = _find_model_in_library(model_name, library_models)
            
            merged_models.append({
                "name": model_name,
                "size": model_data.get("size", 0),
                "modified_at": model_data.get("modified_at", ""),
                "downloaded": True,
                "available": True if library_info else False,
                "type": library_info.get("type", "llm") if library_info else "llm",
                "description": library_info.get("description", "") if library_info else "",
                "tags": library_info.get("tags", []) if library_info else [],
                "is_current_llm": model_name == ollama_llm_model,
                "is_current_embedding": model_name == ollama_embedding_model
            })
        
        # Add library models that are not downloaded
        added_variants_count = 0
        for lib_model in library_models:
            variants = lib_model.get("variants", [lib_model.get("name")])
            for variant in variants:
                if variant not in downloaded_names:
                    merged_models.append({
                        "name": variant,
                        "size": 0,
                        "modified_at": None,
                        "downloaded": False,
                        "available": True,
                        "type": lib_model.get("type", "llm"),
                        "description": lib_model.get("description", ""),
                        "tags": lib_model.get("tags", []),
                        "is_current_llm": variant == ollama_llm_model,
                        "is_current_embedding": variant == ollama_embedding_model
                    })
                    added_variants_count += 1
                    # Debug: Log specific models being added
                    if variant in ["qwen2.5:0.5b", "qwen2.5:1.5b", "mistral:latest", "phi3:latest"]:
                        print(f"  Added library model: {variant} (type: {lib_model.get('type', 'llm')})")
        
        print(f"Added {added_variants_count} library models (not downloaded) to merged list")
        
        # Debug: Print some info about merged models
        print(f"Total merged models: {len(merged_models)}")
        print(f"Downloaded models: {len([m for m in merged_models if m['downloaded']])}")
        print(f"Library models (not downloaded): {len([m for m in merged_models if not m['downloaded']])}")
        # Check for specific models
        target_models = ["qwen2.5:0.5b", "qwen2.5:1.5b", "mistral:latest", "phi3:latest"]
        for target in target_models:
            found = any(m["name"] == target for m in merged_models)
            print(f"Model {target} in merged list: {found}")
        
        # Sort models: downloaded first, then by name
        merged_models.sort(key=lambda x: (not x["downloaded"], x["name"]))
        
        return success_response({
            "models": merged_models,
            "ollama_connected": ollama_connected,
            "ollama_base_url": ollama_base_url,
            "current_llm_model": ollama_llm_model,
            "current_embedding_model": ollama_embedding_model
        })
            
    except Exception as e:
        return error_response(
            f"Error: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/ollama/models/pull")
async def pull_ollama_model(
    payload: OllamaModelPullRequest,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Pull an Ollama model."""
    from ..config import get_ollama_base_url_from_db
    
    try:
        ollama_base_url = await get_ollama_base_url_from_db()
        
        if not ollama_base_url:
            return error_response(
                "Ollama base URL not configured",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Call Ollama API to pull model
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutes timeout for pulling
                response = await client.post(
                    f"{ollama_base_url}/api/pull",
                    json={"name": payload.model_name},
                    timeout=300.0
                )
                
                if response.status_code == 200:
                    # Ollama returns streaming JSON, but we'll just check if it started
                    return success_response({
                        "model_name": payload.model_name,
                        "status": "pulling",
                        "message": f"Started pulling model {payload.model_name}. This may take several minutes."
                    })
                else:
                    return error_response(
                        f"Failed to pull model: HTTP {response.status_code}",
                        status_code=status.HTTP_502_BAD_GATEWAY
                    )
                    
        except httpx.ConnectError:
            return error_response(
                f"Cannot connect to Ollama at {ollama_base_url}",
                status_code=status.HTTP_502_BAD_GATEWAY
            )
        except httpx.TimeoutException:
            return error_response(
                "Pull operation timed out. The model may still be downloading in the background.",
                status_code=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except Exception as e:
            return error_response(
                f"Error pulling model: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        return error_response(
            f"Error: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/ollama/models/test")
async def test_ollama_model(
    payload: OllamaModelTestRequest,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Test an Ollama model (LLM or Embedding) using native API."""
    from ..config import get_ollama_base_url_from_db
    import httpx
    
    try:
        ollama_base_url = await get_ollama_base_url_from_db()
        
        if not ollama_base_url:
            return error_response(
                "Ollama base URL not configured",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        if payload.model_type not in ["llm", "embedding"]:
            return error_response(
                "model_type must be 'llm' or 'embedding'",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Set default test input if not provided
        test_input = payload.test_input
        if not test_input:
            test_input = "Hello" if payload.model_type == "llm" else "test"
        
        start_time = time.time()
        base_url_clean = ollama_base_url.rstrip('/')
        model_name = payload.model_name
        
        try:
            # Use httpx.AsyncClient for async endpoint
            async with httpx.AsyncClient(timeout=60.0, base_url=base_url_clean) as client:
                if payload.model_type == "llm":
                    # Test LLM model using Ollama native API
                    response = await client.post(
                        "/api/generate",
                        json={
                            "model": model_name,
                            "prompt": test_input,
                            "stream": False
                        }
                    )
                    
                    if response.status_code != 200:
                        if response.status_code == 404:
                            return error_response(
                                f"Model '{model_name}' not found. Please ensure the model is pulled: ollama pull {model_name}",
                                status_code=status.HTTP_404_NOT_FOUND
                            )
                        return error_response(
                            f"Ollama API error: HTTP {response.status_code} - {response.text}",
                            status_code=status.HTTP_502_BAD_GATEWAY
                        )
                    
                    data = response.json()
                    result_text = data.get("response", "")
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    return success_response({
                        "model_name": model_name,
                        "model_type": "llm",
                        "test_input": test_input,
                        "result": {
                            "response": result_text,
                            "token_usage": {
                                "prompt_tokens": data.get("prompt_eval_count", 0),
                                "completion_tokens": data.get("eval_count", 0),
                                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                            }
                        },
                        "success": True,
                        "duration_ms": duration_ms
                    })
                    
                else:  # embedding
                    # Test Embedding model using Ollama native API
                    response = await client.post(
                        "/api/embeddings",
                        json={
                            "model": model_name,
                            "prompt": test_input
                        }
                    )
                    
                    if response.status_code != 200:
                        if response.status_code == 404:
                            return error_response(
                                f"Model '{model_name}' not found. Please ensure the model is pulled: ollama pull {model_name}",
                                status_code=status.HTTP_404_NOT_FOUND
                            )
                        return error_response(
                            f"Ollama API error: HTTP {response.status_code} - {response.text}",
                            status_code=status.HTTP_502_BAD_GATEWAY
                        )
                    
                    data = response.json()
                    embedding = data.get("embedding", [])
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    return success_response({
                        "model_name": model_name,
                        "model_type": "embedding",
                        "test_input": test_input,
                        "result": {
                            "embedding_dimension": len(embedding),
                            "embedding_sample": embedding[:10] if len(embedding) > 10 else embedding
                        },
                        "success": True,
                        "duration_ms": duration_ms
                    })
                    
        except httpx.RequestError as e:
            return error_response(
                f"Error connecting to Ollama: {str(e)}",
                status_code=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return error_response(
                f"Error testing model '{model_name}': {str(e)}\nDetails: {error_details}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        return error_response(
            f"Error: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
