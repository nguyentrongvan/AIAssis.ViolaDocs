from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from ..db import get_session
from ..dependencies import get_current_user, get_current_admin_user, require_permission
from ..models.users import User
from ..models.documents import Folder, FolderShare
from ..models.roles import Role
from ..services.permission_service import check_folder_access, get_user_role_names
from ..utils.response import success_response, error_response

router = APIRouter(prefix="/folders", tags=["folders"])


class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None


@router.get("")
async def list_folders(
    parent_id: Optional[int] = None,
    current_user: User = Depends(require_permission("folder")),
    session: AsyncSession = Depends(get_session)
):
    """List folders. If parent_id is provided, list children of that folder."""
    query = select(Folder)
    
    if parent_id is not None:
        query = query.where(Folder.parent_id == parent_id)
    else:
        # List root folders (no parent)
        query = query.where(Folder.parent_id.is_(None))
    
    # Filter by owner, admin/staff, or folders shared with user
    if current_user.role not in ["admin", "staff"]:
        now = datetime.utcnow()
        
        # Get folder IDs from folder shares (user-specific)
        user_folder_share_condition = and_(
            FolderShare.target_type == "user",
            FolderShare.target_id == current_user.id,
            or_(
                FolderShare.expires_at.is_(None),
                FolderShare.expires_at > now
            )
        )
        user_shared_folder_ids_query = select(FolderShare.folder_id).where(user_folder_share_condition)
        
        # Get folder IDs from folder shares (role-based)
        user_role_names = await get_user_role_names(session, current_user)
        role_folder_shares_result = await session.execute(
            select(FolderShare).where(
                and_(
                    FolderShare.target_type == "role",
                    or_(
                        FolderShare.expires_at.is_(None),
                        FolderShare.expires_at > now
                    )
                )
            )
        )
        role_folder_shares = role_folder_shares_result.scalars().all()
        
        role_shared_folder_ids = []
        for folder_share in role_folder_shares:
            role_result = await session.execute(
                select(Role).where(Role.id == folder_share.target_id)
            )
            role = role_result.scalar_one_or_none()
            
            if role and role.name in user_role_names:
                role_shared_folder_ids.append(folder_share.folder_id)
        
        # Combine: owner OR shared folders
        folder_access_conditions = [Folder.owner_id == current_user.id]
        
        if user_shared_folder_ids_query is not None:
            folder_access_conditions.append(Folder.id.in_(user_shared_folder_ids_query))
        
        if role_shared_folder_ids:
            folder_access_conditions.append(Folder.id.in_(role_shared_folder_ids))
        
        folder_access_condition = or_(*folder_access_conditions) if len(folder_access_conditions) > 1 else folder_access_conditions[0]
        query = query.where(folder_access_condition)
    
    result = await session.execute(query)
    folders = result.scalars().all()
    
    return success_response([{
        "id": f.id,
        "name": f.name,
        "parent_id": f.parent_id,
        "owner_id": f.owner_id,
        "created_at": f.created_at.isoformat()
    } for f in folders])


@router.post("")
async def create_folder(
    payload: FolderCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Create a new folder."""
    # Validate parent_id if provided
    if payload.parent_id is not None:
        parent_result = await session.execute(
            select(Folder).where(Folder.id == payload.parent_id)
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            return error_response("Parent folder not found", status_code=status.HTTP_404_NOT_FOUND)
        
        # Check access to parent folder
        if parent.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
            return error_response("Access denied to parent folder", status_code=status.HTTP_403_FORBIDDEN)
    
    folder = Folder(
        name=payload.name,
        parent_id=payload.parent_id,
        owner_id=current_user.id,
        created_by=current_user.id
    )
    session.add(folder)
    await session.commit()
    await session.refresh(folder)
    
    return success_response({
        "id": folder.id,
        "name": folder.name,
        "parent_id": folder.parent_id,
        "owner_id": folder.owner_id
    })


@router.get("/{folder_id}")
async def get_folder(
    folder_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get folder details."""
    result = await session.execute(select(Folder).where(Folder.id == folder_id))
    folder = result.scalar_one_or_none()
    
    if not folder:
        return error_response("Folder not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Check access (owner, admin/staff, or via folder share)
    has_access, reason = await check_folder_access(session, current_user, folder_id)
    if not has_access:
        return error_response(reason or "Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    # Get child folders count
    children_result = await session.execute(
        select(Folder).where(Folder.parent_id == folder_id)
    )
    children_count = len(children_result.scalars().all())
    
    # Get documents count
    from ..models.documents import Document
    docs_result = await session.execute(
        select(Document).where(
            and_(
                Document.folder_id == folder_id,
                Document.deleted_at.is_(None)
            )
        )
    )
    docs_count = len(docs_result.scalars().all())
    
    return success_response({
        "id": folder.id,
        "name": folder.name,
        "parent_id": folder.parent_id,
        "owner_id": folder.owner_id,
        "created_by": folder.created_by,
        "children_count": children_count,
        "documents_count": docs_count,
        "created_at": folder.created_at.isoformat()
    })


@router.patch("/{folder_id}")
async def update_folder(
    folder_id: int,
    payload: FolderUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update a folder."""
    result = await session.execute(select(Folder).where(Folder.id == folder_id))
    folder = result.scalar_one_or_none()
    
    if not folder:
        return error_response("Folder not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Check access
    if folder.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    if payload.name is not None:
        folder.name = payload.name
    
    if payload.parent_id is not None:
        # Validate parent_id
        if payload.parent_id == folder_id:
            return error_response("Folder cannot be its own parent", status_code=status.HTTP_400_BAD_REQUEST)
        
        if payload.parent_id != folder.parent_id:
            parent_result = await session.execute(
                select(Folder).where(Folder.id == payload.parent_id)
            )
            parent = parent_result.scalar_one_or_none()
            if not parent:
                return error_response("Parent folder not found", status_code=status.HTTP_404_NOT_FOUND)
            
            # Check for circular reference
            current_parent_id = payload.parent_id
            depth = 0
            while current_parent_id and depth < 100:  # Prevent infinite loop
                if current_parent_id == folder_id:
                    return error_response("Cannot create circular reference", status_code=status.HTTP_400_BAD_REQUEST)
                parent_result = await session.execute(
                    select(Folder).where(Folder.id == current_parent_id)
                )
                parent = parent_result.scalar_one_or_none()
                if not parent:
                    break
                current_parent_id = parent.parent_id
                depth += 1
        
        folder.parent_id = payload.parent_id
    
    await session.commit()
    await session.refresh(folder)
    
    return success_response({
        "id": folder.id,
        "name": folder.name,
        "parent_id": folder.parent_id
    })


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete a folder (admin only)."""
    result = await session.execute(select(Folder).where(Folder.id == folder_id))
    folder = result.scalar_one_or_none()
    
    if not folder:
        return error_response("Folder not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Check if folder has children
    children_result = await session.execute(
        select(Folder).where(Folder.parent_id == folder_id)
    )
    children = children_result.scalars().all()
    if children:
        return error_response(
            "Cannot delete folder with subfolders. Delete or move subfolders first.",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if folder has documents
    from ..models.documents import Document
    docs_result = await session.execute(
        select(Document).where(
            and_(
                Document.folder_id == folder_id,
                Document.deleted_at.is_(None)
            )
        )
    )
    docs = docs_result.scalars().all()
    if docs:
        return error_response(
            "Cannot delete folder with documents. Move or delete documents first.",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    await session.delete(folder)
    await session.commit()
    
    return success_response({"id": folder_id, "deleted": True})


class FolderShareRequest(BaseModel):
    user_emails: Optional[List[str]] = None
    role_ids: Optional[List[int]] = None
    expires_at: Optional[str] = None


@router.post("/{folder_id}/share")
async def share_folder(
    folder_id: int,
    request: FolderShareRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Share a folder with users or roles."""
    # Get folder
    folder_result = await session.execute(select(Folder).where(Folder.id == folder_id))
    folder = folder_result.scalar_one_or_none()
    
    if not folder:
        return error_response("Folder not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Only folder owner or admin/staff can share
    if folder.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied: only folder owner or admin/staff can share", status_code=status.HTTP_403_FORBIDDEN)
    
    # Parse expiration date if provided
    expires_at = None
    if request.expires_at:
        try:
            expires_at = datetime.fromisoformat(request.expires_at.replace('Z', '+00:00'))
        except ValueError:
            return error_response("Invalid expires_at format. Use ISO 8601 format.", status_code=status.HTTP_400_BAD_REQUEST)
    
    created_shares = []
    
    # Handle user_emails
    if request.user_emails:
        from ..models.users import User
        for email in request.user_emails:
            user_result = await session.execute(select(User).where(User.email == email.strip()))
            user = user_result.scalar_one_or_none()
            if user:
                # Check if share already exists
                existing_result = await session.execute(
                    select(FolderShare).where(
                        and_(
                            FolderShare.folder_id == folder_id,
                            FolderShare.target_type == "user",
                            FolderShare.target_id == user.id
                        )
                    )
                )
                existing = existing_result.scalar_one_or_none()
                
                if existing:
                    # Update expiration if provided
                    if expires_at:
                        existing.expires_at = expires_at
                    created_shares.append({
                        "id": existing.id,
                        "target_type": "user",
                        "target_id": user.id,
                        "target_email": user.email,
                        "expires_at": existing.expires_at.isoformat() if existing.expires_at else None
                    })
                else:
                    folder_share = FolderShare(
                        folder_id=folder_id,
                        target_type="user",
                        target_id=user.id,
                        expires_at=expires_at
                    )
                    session.add(folder_share)
                    await session.flush()
                    created_shares.append({
                        "id": folder_share.id,
                        "target_type": "user",
                        "target_id": user.id,
                        "target_email": user.email,
                        "expires_at": folder_share.expires_at.isoformat() if folder_share.expires_at else None
                    })
    
    # Handle role_ids
    if request.role_ids:
        for role_id in request.role_ids:
            role_result = await session.execute(select(Role).where(Role.id == role_id))
            role = role_result.scalar_one_or_none()
            if role:
                # Check if share already exists
                existing_result = await session.execute(
                    select(FolderShare).where(
                        and_(
                            FolderShare.folder_id == folder_id,
                            FolderShare.target_type == "role",
                            FolderShare.target_id == role.id
                        )
                    )
                )
                existing = existing_result.scalar_one_or_none()
                
                if existing:
                    # Update expiration if provided
                    if expires_at:
                        existing.expires_at = expires_at
                    created_shares.append({
                        "id": existing.id,
                        "target_type": "role",
                        "target_id": role.id,
                        "target_role_name": role.name,
                        "expires_at": existing.expires_at.isoformat() if existing.expires_at else None
                    })
                else:
                    folder_share = FolderShare(
                        folder_id=folder_id,
                        target_type="role",
                        target_id=role.id,
                        expires_at=expires_at
                    )
                    session.add(folder_share)
                    await session.flush()
                    created_shares.append({
                        "id": folder_share.id,
                        "target_type": "role",
                        "target_id": role.id,
                        "target_role_name": role.name,
                        "expires_at": folder_share.expires_at.isoformat() if folder_share.expires_at else None
                    })
    
    await session.commit()
    
    return success_response({
        "folder_id": folder_id,
        "shares": created_shares
    })


@router.get("/{folder_id}/shares")
async def list_folder_shares(
    folder_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """List all shares for a folder."""
    # Get folder
    folder_result = await session.execute(select(Folder).where(Folder.id == folder_id))
    folder = folder_result.scalar_one_or_none()
    
    if not folder:
        return error_response("Folder not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Only folder owner or admin/staff can view shares
    if folder.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied: only folder owner or admin/staff can view shares", status_code=status.HTTP_403_FORBIDDEN)
    
    # Get all folder shares
    shares_result = await session.execute(
        select(FolderShare).where(FolderShare.folder_id == folder_id)
    )
    shares = shares_result.scalars().all()
    
    shares_list = []
    for share in shares:
        share_data = {
            "id": share.id,
            "target_type": share.target_type,
            "target_id": share.target_id,
            "expires_at": share.expires_at.isoformat() if share.expires_at else None,
            "created_at": share.created_at.isoformat()
        }
        
        # Add target details
        if share.target_type == "user":
            from ..models.users import User
            user_result = await session.execute(select(User).where(User.id == share.target_id))
            user = user_result.scalar_one_or_none()
            if user:
                share_data["target_email"] = user.email
                share_data["target_name"] = user.name
        elif share.target_type == "role":
            role_result = await session.execute(select(Role).where(Role.id == share.target_id))
            role = role_result.scalar_one_or_none()
            if role:
                share_data["target_role_name"] = role.name
        
        shares_list.append(share_data)
    
    return success_response(shares_list)


@router.delete("/{folder_id}/shares/{share_id}")
async def delete_folder_share(
    folder_id: int,
    share_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Remove a folder share."""
    # Get folder
    folder_result = await session.execute(select(Folder).where(Folder.id == folder_id))
    folder = folder_result.scalar_one_or_none()
    
    if not folder:
        return error_response("Folder not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Only folder owner or admin/staff can delete shares
    if folder.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied: only folder owner or admin/staff can delete shares", status_code=status.HTTP_403_FORBIDDEN)
    
    # Get folder share
    share_result = await session.execute(
        select(FolderShare).where(
            and_(
                FolderShare.id == share_id,
                FolderShare.folder_id == folder_id
            )
        )
    )
    share = share_result.scalar_one_or_none()
    
    if not share:
        return error_response("Folder share not found", status_code=status.HTTP_404_NOT_FOUND)
    
    await session.delete(share)
    await session.commit()
    
    return success_response({"id": share_id, "deleted": True})

