from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..db import get_session
from ..dependencies import get_current_admin_user, require_permission_or_staff
from ..models.users import User
from ..models.roles import Role
from ..services.auth import get_password_hash
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


