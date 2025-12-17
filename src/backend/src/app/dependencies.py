from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .db import get_session
from .services.auth import decode_token, get_user_by_id
from .models.users import User
from .models.roles import Role, user_role

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    user = await get_user_by_id(session, int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != "admin" and current_user.role != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or staff access required"
        )
    return current_user


async def get_current_maintainer(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require maintainer/root admin access.
    Maintainer is a user with is_maintainer=True flag.
    This is the highest privilege level for system configuration management.
    """
    if not hasattr(current_user, 'is_maintainer') or not getattr(current_user, 'is_maintainer', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Maintainer access required. This endpoint is restricted to root administrators."
        )
    return current_user


def check_user_permission(user: User, user_permissions: List[str], permission: str) -> bool:
    """
    Check if user has a specific user-level permission.
    
    User-level permissions: upload, search, scan, chat, folder, settings, reports, user
    
    Staff automatically has all permissions.
    
    Args:
        user: User object
        user_permissions: List of permissions from user's roles
        permission: Permission to check
    
    Returns:
        True if user has the permission, False otherwise
    """
    # Staff automatically has all permissions
    if user.role in ["admin", "staff"]:
        return True
    
    # Check if permission is in user's role permissions
    return permission in user_permissions


async def get_user_permissions(session: AsyncSession, user: User) -> List[str]:
    """
    Get all user-level permissions for a user from their roles.
    
    Args:
        session: Database session
        user: User object
    
    Returns:
        List of permission strings
    """
    # Admin automatically has all permissions
    if user.role == "admin":
        return ["upload", "search", "scan", "chat", "folder", "delete", "settings", "reports", "user"]
    
    # Staff and regular users: get permissions from menu roles
    # Get roles from database
    result = await session.execute(
        select(Role)
        .join(user_role)
        .where(user_role.c.user_id == user.id)
    )
    roles = result.scalars().all()
    
    # Collect all permissions from roles
    all_permissions = set()
    for role in roles:
        if role.permissions:
            if isinstance(role.permissions, list):
                all_permissions.update(role.permissions)
            elif isinstance(role.permissions, str):
                all_permissions.add(role.permissions)
    
    return list(all_permissions)


def require_permission(permission: str):
    """
    Dependency factory to require a specific user-level permission.
    
    Usage:
        @router.get("/endpoint")
        async def my_endpoint(
            current_user: User = Depends(require_permission("upload")),
            session: AsyncSession = Depends(get_session)
        ):
            ...
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session)
    ) -> User:
        user_permissions = await get_user_permissions(session, current_user)
        if not check_user_permission(current_user, user_permissions, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    
    return permission_checker


def require_permission_or_staff(permission: str):
    """
    Dependency factory to require a specific user-level permission OR staff/admin role.
    
    Usage:
        @router.get("/endpoint")
        async def my_endpoint(
            current_user: User = Depends(require_permission_or_staff("settings")),
            session: AsyncSession = Depends(get_session)
        ):
            ...
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session)
    ) -> User:
        # Staff/admin always allowed
        if current_user.role in ["admin", "staff"]:
            return current_user
        
        user_permissions = await get_user_permissions(session, current_user)
        if not check_user_permission(current_user, user_permissions, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required or staff/admin access"
            )
        return current_user
    
    return permission_checker






