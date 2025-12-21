from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, status, UploadFile, File, Response, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..db import get_session
from ..dependencies import get_current_user, get_current_admin_user, require_permission_or_staff
from ..models.users import User
from ..models.roles import Role
from ..models.user_preferences import UserPreferences
from ..services.auth import get_password_hash, verify_password
from ..services.user_preferences_service import UserPreferencesService
from ..services.avatar_service import upload_avatar, delete_avatar
from ..services.storage import get_file_bytes_from_minio
from ..utils.password_validator import PasswordValidator
from ..utils.response import success_response, error_response

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "user"
    expires_at: Optional[str] = None
    role_ids: Optional[list[int]] = None  # Menu roles IDs


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    status: Optional[str] = None
    expires_at: Optional[str] = None
    role_ids: Optional[list[int]] = None  # Menu roles IDs


@router.post("")
async def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_permission_or_staff("user")),
    session: AsyncSession = Depends(get_session)
):
    # Check if email exists
    result = await session.execute(select(User).where(User.email == payload.email))
    existing = result.scalar_one_or_none()
    if existing:
        return error_response("Email already exists", status_code=status.HTTP_400_BAD_REQUEST)
    
    expires_at = None
    if payload.expires_at:
        expires_at = datetime.fromisoformat(payload.expires_at)
    
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        status="active",
        expires_at=expires_at,
        created_by=current_user.id
    )
    session.add(user)
    await session.flush()  # Flush to get user.id
    
    # Assign menu roles if provided
    if payload.role_ids:
        role_result = await session.execute(
            select(Role).where(Role.id.in_(payload.role_ids))
        )
        roles = role_result.scalars().all()
        
        # Validate: editor và manager chỉ dành cho staff/admin
        restricted_role_names = ["editor", "manager"]
        if payload.role not in ["staff", "admin"]:
            restricted_roles = [r for r in roles if r.name in restricted_role_names]
            if restricted_roles:
                await session.rollback()
                return error_response(
                    f"Cannot assign roles {[r.name for r in restricted_roles]} to user with role '{payload.role}'. Only staff/admin can have these roles.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        user.roles.extend(roles)
    
    await session.commit()
    await session.refresh(user)
    
    # Load roles for response
    await session.refresh(user, ["roles"])
    
    return success_response({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "roles": [{"id": r.id, "name": r.name, "permissions": r.permissions} for r in user.roles]
    })


@router.get("")
async def list_users(
    current_user: User = Depends(require_permission_or_staff("user")),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(User).options(selectinload(User.roles))
    )
    users = result.scalars().all()
    
    return success_response([{
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "status": u.status,
        "expires_at": u.expires_at.isoformat() if u.expires_at else None,
        "roles": [{"id": r.id, "name": r.name, "permissions": r.permissions} for r in u.roles]
    } for u in users])


@router.patch("/{user_id}")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(require_permission_or_staff("user")),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return error_response("User not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Determine the final role (use payload.role if provided, otherwise keep existing)
    final_role = payload.role if payload.role is not None else user.role
    
    # Update basic fields
    if payload.name:
        user.name = payload.name
    if payload.email:
        user.email = payload.email
    if payload.role:
        user.role = payload.role
    if payload.status:
        user.status = payload.status
    if payload.expires_at is not None:
        user.expires_at = datetime.fromisoformat(payload.expires_at) if payload.expires_at else None
    
    # Update menu roles if provided
    restricted_role_names = ["editor", "manager"]
    
    if payload.role_ids is not None:
        role_result = await session.execute(
            select(Role).where(Role.id.in_(payload.role_ids))
        )
        roles = role_result.scalars().all()
        
        # Validate: editor và manager chỉ dành cho staff/admin
        if final_role not in ["staff", "admin"]:
            restricted_roles = [r for r in roles if r.name in restricted_role_names]
            if restricted_roles:
                return error_response(
                    f"Cannot assign roles {[r.name for r in restricted_roles]} to user with role '{final_role}'. Only staff/admin can have these roles.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        user.roles = roles
    elif payload.role is not None and final_role == "user":
        # If updating role to "user" but role_ids not provided, remove restricted roles
        # Keep non-restricted roles
        # Need to refresh user.roles first
        await session.refresh(user, ["roles"])
        current_roles = user.roles or []
        allowed_roles = [r for r in current_roles if r.name not in restricted_role_names]
        user.roles = allowed_roles
    
    await session.commit()
    await session.refresh(user, ["roles"])
    
    return success_response({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "roles": [{"id": r.id, "name": r.name, "permissions": r.permissions} for r in user.roles]
    })


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_permission_or_staff("user")),
    session: AsyncSession = Depends(get_session)
):
    if user_id == current_user.id:
        return error_response("Cannot delete yourself", status_code=status.HTTP_400_BAD_REQUEST)
    
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        return error_response("User not found", status_code=status.HTTP_404_NOT_FOUND)
    
    await session.delete(user)
    await session.commit()
    
    return success_response({"id": user_id, "deleted": True})


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_user: User = Depends(require_permission_or_staff("user")),
    session: AsyncSession = Depends(get_session)
):
    """Activate user account."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        return error_response("User not found", status_code=status.HTTP_404_NOT_FOUND)
    
    user.status = "active"
    await session.commit()
    
    return success_response({
        "id": user.id,
        "status": user.status
    })


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_permission_or_staff("user")),
    session: AsyncSession = Depends(get_session)
):
    """Deactivate user account."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        return error_response("User not found", status_code=status.HTTP_404_NOT_FOUND)
    
    user.status = "inactive"
    await session.commit()
    
    return success_response({
        "id": user.id,
        "status": user.status
    })


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    current_user: User = Depends(require_permission_or_staff("user")),
    session: AsyncSession = Depends(get_session)
):
    """Get user details."""
    result = await session.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return error_response("User not found", status_code=status.HTTP_404_NOT_FOUND)
    
    return success_response({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "expires_at": user.expires_at.isoformat() if user.expires_at else None,
        "locale": user.locale,
        "time_zone": user.time_zone,
        "created_at": user.created_at.isoformat(),
        "roles": [{"id": r.id, "name": r.name, "permissions": r.permissions} for r in user.roles]
    })


class UserExpiryUpdate(BaseModel):
    expires_at: Optional[str] = None


class UserPreferencesUpdate(BaseModel):
    primary_color: Optional[str] = None
    font_size: Optional[str] = None
    border_radius: Optional[str] = None
    animation_speed: Optional[str] = None
    compact_mode: Optional[bool] = None


@router.get("/me/preferences")
async def get_my_preferences(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get current user's preferences"""
    preferences = await UserPreferencesService.get_or_create_preferences(
        current_user.id, session
    )
    
    return success_response({
        "primary_color": preferences.primary_color,
        "font_size": preferences.font_size,
        "border_radius": preferences.border_radius,
        "animation_speed": preferences.animation_speed,
        "compact_mode": preferences.compact_mode
    })


@router.put("/me/preferences")
async def update_my_preferences(
    payload: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update current user's preferences"""
    preferences = await UserPreferencesService.update_preferences(
        user_id=current_user.id,
        session=session,
        primary_color=payload.primary_color,
        font_size=payload.font_size,
        border_radius=payload.border_radius,
        animation_speed=payload.animation_speed,
        compact_mode=payload.compact_mode
    )
    
    return success_response({
        "primary_color": preferences.primary_color,
        "font_size": preferences.font_size,
        "border_radius": preferences.border_radius,
        "animation_speed": preferences.animation_speed,
        "compact_mode": preferences.compact_mode
    })


@router.get("/me/preferences/theme")
async def get_my_theme(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get theme CSS variables for current user"""
    preferences = await UserPreferencesService.get_or_create_preferences(
        current_user.id, session
    )
    
    theme_vars = {}
    
    # If user has custom primary color, calculate theme colors
    if preferences.primary_color:
        theme_vars = UserPreferencesService.calculate_theme_colors(
            preferences.primary_color
        )
    
    return success_response({
        "css_variables": theme_vars,
        "preferences": {
            "primary_color": preferences.primary_color,
            "font_size": preferences.font_size,
            "border_radius": preferences.border_radius,
            "animation_speed": preferences.animation_speed,
            "compact_mode": preferences.compact_mode
        }
    })


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[str] = None  # ISO format date string
    phone: Optional[str] = None
    address: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


@router.get("/me/profile")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get current user's full profile"""
    return success_response({
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "status": current_user.status,
        "date_of_birth": current_user.date_of_birth.isoformat() if current_user.date_of_birth else None,
        "phone": current_user.phone,
        "address": current_user.address,
        "avatar_url": current_user.avatar_url,
        "locale": current_user.locale,
        "time_zone": current_user.time_zone,
        "created_at": current_user.created_at.isoformat(),
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None
    })


@router.put("/me/profile")
async def update_my_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update current user's profile"""
    # Refresh user from database
    await session.refresh(current_user)
    
    if payload.name is not None:
        current_user.name = payload.name
    if payload.date_of_birth is not None:
        if payload.date_of_birth:
            current_user.date_of_birth = datetime.fromisoformat(payload.date_of_birth)
        else:
            current_user.date_of_birth = None
    if payload.phone is not None:
        current_user.phone = payload.phone
    if payload.address is not None:
        current_user.address = payload.address
    
    await session.commit()
    await session.refresh(current_user)
    
    return success_response({
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "date_of_birth": current_user.date_of_birth.isoformat() if current_user.date_of_birth else None,
        "phone": current_user.phone,
        "address": current_user.address,
        "avatar_url": current_user.avatar_url
    })


@router.post("/me/avatar")
async def upload_my_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Upload avatar for current user"""
    # Read file data
    file_data = await file.read()
    
    # Upload avatar
    try:
        old_avatar_url = current_user.avatar_url
        avatar_url = await upload_avatar(
            current_user.id,
            file_data,
            file.filename,
            file.content_type,
            old_avatar_url
        )
        
        # Update user's avatar_url
        current_user.avatar_url = avatar_url
        await session.commit()
        await session.refresh(current_user)
        
        return success_response({
            "avatar_url": avatar_url
        })
    except ValueError as e:
        return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return error_response(f"Failed to upload avatar: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.put("/me/password")
async def change_my_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Change current user's password"""
    # Verify current password
    if not verify_password(payload.current_password, current_user.password_hash):
        return error_response("Current password is incorrect", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Check if new password matches confirmation
    if payload.new_password != payload.confirm_password:
        return error_response("New password and confirmation do not match", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Validate new password strength
    is_valid, errors = PasswordValidator.validate(payload.new_password)
    if not is_valid:
        return error_response({
            "message": "Password does not meet requirements",
            "errors": errors
        }, status_code=status.HTTP_400_BAD_REQUEST)
    
    # Update password
    current_user.password_hash = get_password_hash(payload.new_password)
    await session.commit()
    
    return success_response({
        "message": "Password changed successfully"
    })


@router.get("/me/avatar")
async def get_my_avatar(
    object: Optional[str] = Query(None, description="Object name in MinIO (optional, will use from avatar_url if not provided)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get current user's avatar image"""
    from urllib.parse import urlparse, parse_qs
    from fastapi import Query
    
    # Refresh user to get latest avatar_url
    await session.refresh(current_user)
    
    object_name = None
    
    # First, try to get object_name from query parameter (if provided)
    if object:
        object_name = object
    elif current_user.avatar_url:
        # Extract object name from avatar URL stored in database
        # URL format: /api/v1/users/me/avatar?object=avatars/{user_id}/{avatar_id}.jpg (dev) or full MinIO URL (prod)
        if current_user.avatar_url.startswith('/api/v1/users/me/avatar'):
            # Dev mode: extract object from query parameter in stored URL
            parsed = urlparse(current_user.avatar_url)
            params = parse_qs(parsed.query)
            if 'object' in params:
                object_name = params['object'][0]
        elif '/avatars/' in current_user.avatar_url:
            # Production mode: extract from MinIO URL
            parts = current_user.avatar_url.split('/avatars/')
            if len(parts) > 1:
                object_name = f"avatars/{parts[-1]}"
        elif current_user.avatar_url.startswith('http'):
            # Full URL - extract object name
            if '/avatars/' in current_user.avatar_url:
                parts = current_user.avatar_url.split('/avatars/')
                if len(parts) > 1:
                    object_name = f"avatars/{parts[-1]}"
    
    if not object_name:
        return error_response("Avatar not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Get file from MinIO
    file_data = await get_file_bytes_from_minio(object_name)
    if file_data:
        return Response(
            content=file_data,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600"
            }
        )
    
    return error_response("Avatar not found", status_code=status.HTTP_404_NOT_FOUND)


@router.patch("/{user_id}/expiry")
async def set_user_expiry(
    user_id: int,
    payload: UserExpiryUpdate,
    current_user: User = Depends(require_permission_or_staff("user")),
    session: AsyncSession = Depends(get_session)
):
    """Set expires_at for short-term accounts."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        return error_response("User not found", status_code=status.HTTP_404_NOT_FOUND)
    
    user.expires_at = datetime.fromisoformat(payload.expires_at) if payload.expires_at else None
    await session.commit()
    await session.refresh(user)
    
    return success_response({
        "id": user.id,
        "expires_at": user.expires_at.isoformat() if user.expires_at else None
    })


