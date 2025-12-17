from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..db import get_session
from ..dependencies import get_current_user, get_current_admin_user, require_permission
from ..models.users import User
from ..models.documents import Folder
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
    
    # Filter by owner or admin/staff
    if current_user.role not in ["admin", "staff"]:
        query = query.where(Folder.owner_id == current_user.id)
    
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
    
    # Check access
    if folder.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
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

