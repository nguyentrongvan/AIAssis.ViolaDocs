from typing import Optional, List
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_session
from ..dependencies import get_current_admin_user, get_current_user
from ..models.users import User
from ..models.roles import Role
from ..utils.response import success_response, error_response

router = APIRouter(prefix="/roles", tags=["roles"])


class RoleCreate(BaseModel):
    name: str
    permissions: List[str] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    permissions: Optional[List[str]] = None


class PermissionsUpdate(BaseModel):
    permissions: List[str]


@router.get("")
async def list_roles(
    current_user: User = Depends(get_current_user),  # Allow all authenticated users to list roles (for sharing)
    session: AsyncSession = Depends(get_session)
):
    """List all roles. Available to all authenticated users (for document sharing)."""
    result = await session.execute(select(Role))
    roles = result.scalars().all()
    
    return success_response([{
        "id": r.id,
        "name": r.name,
        "permissions": r.permissions,
        "created_at": r.created_at.isoformat()
    } for r in roles])


@router.post("")
async def create_role(
    payload: RoleCreate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Create a new role."""
    # Check if role name already exists
    result = await session.execute(select(Role).where(Role.name == payload.name))
    existing = result.scalar_one_or_none()
    if existing:
        return error_response("Role name already exists", status_code=status.HTTP_400_BAD_REQUEST)
    
    role = Role(
        name=payload.name,
        permissions=payload.permissions
    )
    session.add(role)
    await session.commit()
    await session.refresh(role)
    
    return success_response({
        "id": role.id,
        "name": role.name,
        "permissions": role.permissions
    })


@router.get("/{role_id}")
async def get_role(
    role_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Get role details."""
    result = await session.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        return error_response("Role not found", status_code=status.HTTP_404_NOT_FOUND)
    
    return success_response({
        "id": role.id,
        "name": role.name,
        "permissions": role.permissions,
        "created_at": role.created_at.isoformat()
    })


@router.patch("/{role_id}")
async def update_role(
    role_id: int,
    payload: RoleUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Update a role."""
    result = await session.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        return error_response("Role not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if payload.name is not None:
        # Check if new name already exists
        if payload.name != role.name:
            existing_result = await session.execute(
                select(Role).where(Role.name == payload.name)
            )
            existing = existing_result.scalar_one_or_none()
            if existing:
                return error_response("Role name already exists", status_code=status.HTTP_400_BAD_REQUEST)
        role.name = payload.name
    
    if payload.permissions is not None:
        role.permissions = payload.permissions
    
    await session.commit()
    await session.refresh(role)
    
    return success_response({
        "id": role.id,
        "name": role.name,
        "permissions": role.permissions
    })


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete a role."""
    result = await session.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        return error_response("Role not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Check if role is assigned to any users
    if role.users:
        return error_response(
            "Cannot delete role that is assigned to users",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    await session.delete(role)
    await session.commit()
    
    return success_response({"id": role_id, "deleted": True})


@router.post("/{role_id}/permissions")
async def set_role_permissions(
    role_id: int,
    payload: PermissionsUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Set permissions for a role."""
    result = await session.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        return error_response("Role not found", status_code=status.HTTP_404_NOT_FOUND)
    
    role.permissions = payload.permissions
    await session.commit()
    await session.refresh(role)
    
    return success_response({
        "id": role.id,
        "name": role.name,
        "permissions": role.permissions
    })

