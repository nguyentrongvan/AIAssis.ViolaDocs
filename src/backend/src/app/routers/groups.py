from typing import Optional, List
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from ..db import get_session
from ..dependencies import get_current_user, get_current_admin_user
from ..models.users import User
from ..models.groups import DocumentGroup, document_group_documents, document_group_folders, document_group_tags
from ..models.documents import Document, Folder, Tag
from ..utils.response import success_response, error_response

router = APIRouter(prefix="/groups", tags=["groups"])


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    owners: Optional[List[int]] = None
    allowed_roles: Optional[List[str]] = None
    allowed_users: Optional[List[int]] = None
    chatbot_policy: Optional[dict] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    owners: Optional[List[int]] = None
    allowed_roles: Optional[List[str]] = None
    allowed_users: Optional[List[int]] = None
    chatbot_policy: Optional[dict] = None


class GroupMembersUpdate(BaseModel):
    user_ids: Optional[List[int]] = None
    role_names: Optional[List[str]] = None
    action: str = "add"  # add, remove


@router.post("")
async def create_group(
    payload: GroupCreate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    group = DocumentGroup(
        name=payload.name,
        description=payload.description,
        owners=payload.owners or [current_user.id],
        allowed_roles=payload.allowed_roles or [],
        allowed_users=payload.allowed_users or [],
        chatbot_policy=payload.chatbot_policy or {}
    )
    session.add(group)
    await session.commit()
    await session.refresh(group)
    
    return success_response({
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "owners": group.owners,
        "allowed_roles": group.allowed_roles,
        "allowed_users": group.allowed_users
    })


@router.get("")
async def list_groups(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(DocumentGroup))
    groups = result.scalars().all()
    
    response = []
    for g in groups:
        # Count documents
        doc_count = await session.execute(
            select(func.count()).select_from(document_group_documents).where(
                document_group_documents.c.group_id == g.id
            )
        )
        doc_count_val = doc_count.scalar() or 0
        
        # Count members (owners + allowed_users)
        member_count = len(g.owners or []) + len(g.allowed_users or [])
        
        response.append({
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "document_count": doc_count_val,
            "member_count": member_count
        })
    
    return success_response(response)


@router.get("/{group_id}")
async def get_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get group details."""
    result = await session.execute(select(DocumentGroup).where(DocumentGroup.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        return error_response("Group not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Count documents, folders, tags
    doc_count = await session.execute(
        select(func.count()).select_from(document_group_documents).where(
            document_group_documents.c.group_id == group_id
        )
    )
    folder_count = await session.execute(
        select(func.count()).select_from(document_group_folders).where(
            document_group_folders.c.group_id == group_id
        )
    )
    tag_count = await session.execute(
        select(func.count()).select_from(document_group_tags).where(
            document_group_tags.c.group_id == group_id
        )
    )
    
    return success_response({
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "owners": group.owners or [],
        "allowed_roles": group.allowed_roles or [],
        "allowed_users": group.allowed_users or [],
        "chatbot_policy": group.chatbot_policy or {},
        "document_count": doc_count.scalar() or 0,
        "folder_count": folder_count.scalar() or 0,
        "tag_count": tag_count.scalar() or 0,
        "created_at": group.created_at.isoformat()
    })


@router.patch("/{group_id}")
async def update_group(
    group_id: int,
    payload: GroupUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Update a document group."""
    result = await session.execute(select(DocumentGroup).where(DocumentGroup.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        return error_response("Group not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if payload.name is not None:
        group.name = payload.name
    if payload.description is not None:
        group.description = payload.description
    if payload.owners is not None:
        group.owners = payload.owners
    if payload.allowed_roles is not None:
        group.allowed_roles = payload.allowed_roles
    if payload.allowed_users is not None:
        group.allowed_users = payload.allowed_users
    if payload.chatbot_policy is not None:
        group.chatbot_policy = payload.chatbot_policy
    
    await session.commit()
    await session.refresh(group)
    
    return success_response({
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "owners": group.owners,
        "allowed_roles": group.allowed_roles,
        "allowed_users": group.allowed_users,
        "chatbot_policy": group.chatbot_policy
    })


@router.post("/{group_id}/members")
async def update_group_members(
    group_id: int,
    payload: GroupMembersUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Add or remove members (users/roles) from a group."""
    result = await session.execute(select(DocumentGroup).where(DocumentGroup.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        return error_response("Group not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if payload.action == "add":
        if payload.user_ids:
            current_users = set(group.allowed_users or [])
            current_users.update(payload.user_ids)
            group.allowed_users = list(current_users)
        if payload.role_names:
            current_roles = set(group.allowed_roles or [])
            current_roles.update(payload.role_names)
            group.allowed_roles = list(current_roles)
    elif payload.action == "remove":
        if payload.user_ids:
            current_users = set(group.allowed_users or [])
            current_users.difference_update(payload.user_ids)
            group.allowed_users = list(current_users)
        if payload.role_names:
            current_roles = set(group.allowed_roles or [])
            current_roles.difference_update(payload.role_names)
            group.allowed_roles = list(current_roles)
    else:
        return error_response("Action must be 'add' or 'remove'", status_code=status.HTTP_400_BAD_REQUEST)
    
    await session.commit()
    await session.refresh(group)
    
    return success_response({
        "id": group.id,
        "allowed_users": group.allowed_users,
        "allowed_roles": group.allowed_roles
    })


@router.post("/{group_id}/documents")
async def add_documents_to_group(
    group_id: int,
    document_ids: List[int],
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Add documents to a group."""
    result = await session.execute(select(DocumentGroup).where(DocumentGroup.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        return error_response("Group not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Verify documents exist
    docs_result = await session.execute(
        select(Document).where(
            and_(
                Document.id.in_(document_ids),
                Document.deleted_at.is_(None)
            )
        )
    )
    docs = docs_result.scalars().all()
    
    if len(docs) != len(document_ids):
        return error_response("Some documents not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Add documents to group
    for doc in docs:
        if doc not in group.documents:
            group.documents.append(doc)
    
    await session.commit()
    
    return success_response({
        "group_id": group_id,
        "added_documents": document_ids
    })


@router.post("/{group_id}/folders")
async def add_folders_to_group(
    group_id: int,
    folder_ids: List[int],
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Add folders to a group."""
    result = await session.execute(select(DocumentGroup).where(DocumentGroup.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        return error_response("Group not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Verify folders exist
    folders_result = await session.execute(
        select(Folder).where(Folder.id.in_(folder_ids))
    )
    folders = folders_result.scalars().all()
    
    if len(folders) != len(folder_ids):
        return error_response("Some folders not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Add folders to group
    for folder in folders:
        if folder not in group.folders:
            group.folders.append(folder)
    
    await session.commit()
    
    return success_response({
        "group_id": group_id,
        "added_folders": folder_ids
    })


@router.post("/{group_id}/tags")
async def add_tags_to_group(
    group_id: int,
    tag_ids: List[int],
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Add tags to a group."""
    result = await session.execute(select(DocumentGroup).where(DocumentGroup.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        return error_response("Group not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Verify tags exist
    tags_result = await session.execute(
        select(Tag).where(Tag.id.in_(tag_ids))
    )
    tags = tags_result.scalars().all()
    
    if len(tags) != len(tag_ids):
        return error_response("Some tags not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Add tags to group
    for tag in tags:
        if tag not in group.tags:
            group.tags.append(tag)
    
    await session.commit()
    
    return success_response({
        "group_id": group_id,
        "added_tags": tag_ids
    })


@router.post("/{group_id}/reindex")
async def reindex_group(
    group_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Reindex embeddings for documents in a group."""
    result = await session.execute(select(DocumentGroup).where(DocumentGroup.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        return error_response("Group not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Get all documents in the group (eager load to avoid lazy loading issues)
    from ..models.ai import AIJob
    from ..models.documents import DocumentVersion, Document
    from sqlalchemy.orm import selectinload
    
    # Eager load documents
    group_result = await session.execute(
        select(DocumentGroup)
        .where(DocumentGroup.id == group_id)
        .options(selectinload(DocumentGroup.documents))
    )
    group = group_result.scalar_one_or_none()
    
    if not group:
        return error_response("Group not found", status_code=status.HTTP_404_NOT_FOUND)
    
    job_count = 0
    for doc in group.documents:
        if doc.deleted_at is not None:
            continue
        
        # Get latest version
        version_result = await session.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == doc.id)
            .order_by(DocumentVersion.version_no.desc())
            .limit(1)
        )
        version = version_result.scalar_one_or_none()
        
        if version and version.text_uri:
            # Create embedding job
            embed_job = AIJob(
                job_type="embed",
                target={"document_id": doc.id, "version_id": version.id, "group_id": group_id},
                provider="openai",
                status="queued"
            )
            session.add(embed_job)
            job_count += 1
    
    await session.commit()
    
    return success_response({
        "group_id": group_id,
        "message": f"Reindexing initiated for {job_count} documents",
        "job_count": job_count
    })


@router.delete("/{group_id}")
async def delete_group(
    group_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(DocumentGroup).where(DocumentGroup.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        return error_response("Group not found", status_code=status.HTTP_404_NOT_FOUND)
    
    await session.delete(group)
    await session.commit()
    
    return success_response({"id": group_id, "deleted": True})

