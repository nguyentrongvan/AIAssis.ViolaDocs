from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_session
from ..dependencies import get_current_admin_user, get_current_user
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
