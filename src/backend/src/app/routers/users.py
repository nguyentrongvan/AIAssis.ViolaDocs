from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_session
from ..dependencies import get_current_admin_user
from ..models.users import User
from ..services.auth import get_password_hash
from ..utils.response import success_response, error_response

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "user"
    expires_at: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    status: Optional[str] = None
    expires_at: Optional[str] = None


@router.post("")
async def create_user(
    payload: UserCreate,
    current_user: User = Depends(get_current_admin_user),
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
    await session.commit()
    await session.refresh(user)
    
    return success_response({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status
    })


@router.get("")
async def list_users(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(User))
    users = result.scalars().all()
    
    return success_response([{
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "status": u.status,
        "expires_at": u.expires_at.isoformat() if u.expires_at else None
    } for u in users])


@router.patch("/{user_id}")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        return error_response("User not found", status_code=status.HTTP_404_NOT_FOUND)
    
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
    
    await session.commit()
    
    return success_response({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status
    })


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
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
    current_user: User = Depends(get_current_admin_user),
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
    current_user: User = Depends(get_current_admin_user),
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


