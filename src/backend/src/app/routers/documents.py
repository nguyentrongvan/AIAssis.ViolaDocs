import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from ..db import get_session
from ..dependencies import get_current_user, get_current_admin_user
from ..models.users import User
from ..models.documents import Document, DocumentVersion, Tag, DocumentTag, Share
from ..services.storage import generate_presigned_download_url
from ..utils.response import success_response, error_response
from ..config import settings

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentCreate(BaseModel):
    title: str
    mime: str
    size: int
    source: str = "api"
    folder_id: Optional[int] = None
    tags: Optional[list[str]] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    tags: Optional[list[str]] = None
    folder_id: Optional[int] = None
    retention_policy_id: Optional[int] = None


class ShareRequest(BaseModel):
    target_type: Optional[str] = None  # user, role, link
    target_id: Optional[int] = None
    target_user_id: Optional[int] = None  # Alias for target_id when target_type=user
    target_role: Optional[str] = None  # For role sharing
    expires_at: Optional[str] = None
    permissions: Optional[list[str]] = None


@router.post("")
async def create_document(
    request: DocumentCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Create document (metadata-only)."""
    doc = Document(
        title=request.title,
        source=request.source,
        owner_id=current_user.id,
        mime=request.mime,
        size=request.size,
        folder_id=request.folder_id,
        status="ready"
    )
    session.add(doc)
    await session.flush()
    
    # Handle tags
    if request.tags:
        for tag_name in request.tags:
            if not tag_name.strip():
                continue
            tag_result = await session.execute(
                select(Tag).where(Tag.name == tag_name.strip())
            )
            tag = tag_result.scalar_one_or_none()
            
            if not tag:
                tag = Tag(name=tag_name.strip())
                session.add(tag)
                await session.flush()
            
            doc_tag = DocumentTag(document_id=doc.id, tag_id=tag.id)
            session.add(doc_tag)
    
    await session.commit()
    await session.refresh(doc)
    
    return success_response({
        "id": doc.id,
        "title": doc.title,
        "mime": doc.mime,
        "status": doc.status
    })


@router.get("")
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # Base query
    base_query = select(Document).where(
        and_(
            Document.owner_id == current_user.id,
            Document.deleted_at.is_(None)
        )
    )
    
    if search:
        base_query = base_query.where(Document.title.ilike(f"%{search}%"))
    
    # Get total count
    count_query = select(func.count(Document.id)).where(
        and_(
            Document.owner_id == current_user.id,
            Document.deleted_at.is_(None)
        )
    )
    if search:
        count_query = count_query.where(Document.title.ilike(f"%{search}%"))
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated results
    query = base_query.offset(skip).limit(limit)
    result = await session.execute(query)
    documents = result.scalars().all()
    
    return success_response({
        "items": [{
            "id": doc.id,
            "title": doc.title,
            "mime": doc.mime,
            "size": doc.size,
            "status": doc.status,
            "created_at": doc.created_at.isoformat()
        } for doc in documents],
        "total": total
    })


@router.get("/{doc_id}")
async def get_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Document)
        .options(selectinload(Document.versions))
        .where(and_(Document.id == doc_id, Document.deleted_at.is_(None)))
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if doc.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    versions = [{
        "id": v.id,
        "version_no": v.version_no,
        "created_at": v.created_at.isoformat(),
        "created_by": v.created_by,
        "status": v.status
    } for v in doc.versions]
    
    return success_response({
        "id": doc.id,
        "title": doc.title,
        "mime": doc.mime,
        "size": doc.size,
        "status": doc.status,
        "owner_id": doc.owner_id,
        "created_at": doc.created_at.isoformat(),
        "versions": versions
    })


@router.patch("/{doc_id}")
async def update_document(
    doc_id: int,
    request: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Document).where(and_(Document.id == doc_id, Document.deleted_at.is_(None)))
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if doc.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    if request.title:
        doc.title = request.title
    if request.folder_id is not None:
        doc.folder_id = request.folder_id
    if request.retention_policy_id is not None:
        doc.retention_policy_id = request.retention_policy_id
    
    # Handle tags update
    if request.tags is not None:
        # Remove existing tags
        existing_tags_result = await session.execute(
            select(DocumentTag).where(DocumentTag.document_id == doc.id)
        )
        existing_tags = existing_tags_result.scalars().all()
        for doc_tag in existing_tags:
            await session.delete(doc_tag)
        
        # Add new tags
        for tag_name in request.tags:
            if not tag_name.strip():
                continue
            # Check if tag exists
            tag_result = await session.execute(
                select(Tag).where(Tag.name == tag_name.strip())
            )
            tag = tag_result.scalar_one_or_none()
            
            if not tag:
                tag = Tag(name=tag_name.strip())
                session.add(tag)
                await session.flush()
            
            doc_tag = DocumentTag(document_id=doc.id, tag_id=tag.id)
            session.add(doc_tag)
    
    await session.commit()
    
    return success_response({"id": doc.id, "title": doc.title})


@router.delete("/{doc_id}")
async def soft_delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Document).where(and_(Document.id == doc_id, Document.deleted_at.is_(None)))
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Only owner or admin/staff can delete
    if doc.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    doc.deleted_at = datetime.utcnow()
    doc.deleted_by = current_user.id
    doc.purge_at = datetime.utcnow() + timedelta(days=settings.purge_grace_period_days)
    
    await session.commit()
    
    return success_response({"id": doc.id, "deleted": True})


@router.post("/{doc_id}/restore")
async def restore_document(
    doc_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Document).where(Document.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if not doc.deleted_at:
        return error_response("Document is not deleted", status_code=status.HTTP_400_BAD_REQUEST)
    
    doc.deleted_at = None
    doc.deleted_by = None
    doc.purge_at = None
    
    await session.commit()
    
    return success_response({"id": doc.id, "restored": True})


@router.get("/{doc_id}/versions")
async def list_versions(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Document).where(and_(Document.id == doc_id, Document.deleted_at.is_(None)))
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if doc.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    versions_result = await session.execute(
        select(DocumentVersion).where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.version_no.desc())
    )
    versions = versions_result.scalars().all()
    
    return success_response([{
        "id": v.id,
        "version_no": v.version_no,
        "created_at": v.created_at.isoformat(),
        "created_by": v.created_by,
        "status": v.status
    } for v in versions])


@router.get("/{doc_id}/versions/{v1_id}/diff/{v2_id}")
async def compare_versions(
    doc_id: int,
    v1_id: int,
    v2_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Compare two document versions."""
    # Verify document access
    doc_result = await session.execute(
        select(Document).where(and_(Document.id == doc_id, Document.deleted_at.is_(None)))
    )
    doc = doc_result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if doc.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    # Get versions
    v1_result = await session.execute(
        select(DocumentVersion).where(DocumentVersion.id == v1_id)
    )
    v1 = v1_result.scalar_one_or_none()
    
    v2_result = await session.execute(
        select(DocumentVersion).where(DocumentVersion.id == v2_id)
    )
    v2 = v2_result.scalar_one_or_none()
    
    if not v1 or not v2:
        return error_response("Version not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Simple diff (can be enhanced later)
    return success_response({
        "content_diff": {},
        "metadata_diff": {
            "v1": v1.metadata_snapshot or {},
            "v2": v2.metadata_snapshot or {}
        },
        "acl_diff": {}
    })


class VersionUploadRequest(BaseModel):
    version_metadata: Optional[dict] = None


@router.post("/{doc_id}/versions")
async def upload_new_version(
    doc_id: int,
    request: VersionUploadRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Upload new version (similar to upload flow)."""
    # Verify document access
    doc_result = await session.execute(
        select(Document).where(and_(Document.id == doc_id, Document.deleted_at.is_(None)))
    )
    doc = doc_result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if doc.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    # Get latest version number
    latest_version_result = await session.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.version_no.desc())
        .limit(1)
    )
    latest_version = latest_version_result.scalar_one_or_none()
    next_version_no = (latest_version.version_no + 1) if latest_version else 1
    
    # For now, return placeholder (actual upload would use upload flow)
    return success_response({
        "document_id": doc_id,
        "next_version_no": next_version_no,
        "message": "Use /uploads/init and /uploads/{id}/finalize to upload new version"
    })


@router.post("/{doc_id}/share")
async def share_document(
    doc_id: int,
    request: ShareRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Share document with user, role, or create share link."""
    # Verify document access
    doc_result = await session.execute(
        select(Document).where(and_(Document.id == doc_id, Document.deleted_at.is_(None)))
    )
    doc = doc_result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if doc.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    # Determine target
    target_type = request.target_type
    target_id = request.target_id
    expires_at = None
    
    # Handle legacy fields
    if request.target_user_id:
        target_type = "user"
        target_id = request.target_user_id
    elif request.target_role:
        target_type = "role"
        # For role, store in target_id as 0 and use permissions JSON to store role name
        target_id = 0
    elif not target_type:
        # Create share link
        import uuid
        share_token = str(uuid.uuid4())
        target_type = "link"
        target_id = None
    
    if request.expires_at:
        expires_at = datetime.fromisoformat(request.expires_at)
    
    # Create share
    share = Share(
        document_id=doc_id,
        target_type=target_type,
        target_id=target_id,
        expires_at=expires_at,
        permissions=request.permissions or ["read"]
    )
    session.add(share)
    await session.commit()
    await session.refresh(share)
    
    # Build target response
    target_response = {"type": share.target_type}
    if share.target_id:
        target_response["id"] = share.target_id
    if request.target_role:
        target_response["role"] = request.target_role
    
    return success_response({
        "share_id": share.id,
        "target": target_response,
        "expires_at": share.expires_at.isoformat() if share.expires_at else None
    })


@router.get("/{doc_id}/renditions/{rendition_type}")
async def get_rendition(
    doc_id: int,
    rendition_type: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get document rendition (thumbnail, OCR text, etc.)."""
    # Verify document access
    doc_result = await session.execute(
        select(Document).where(and_(Document.id == doc_id, Document.deleted_at.is_(None)))
    )
    doc = doc_result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if doc.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    # Get latest version
    version_result = await session.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.version_no.desc())
        .limit(1)
    )
    version = version_result.scalar_one_or_none()
    
    if not version:
        return error_response("No version found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Get rendition URI based on type
    if rendition_type == "thumbnail":
        uri = version.thumbnail_uri
    elif rendition_type == "text" or rendition_type == "ocr":
        uri = version.text_uri or version.ocr_uri
    else:
        return error_response("Invalid rendition type", status_code=status.HTTP_400_BAD_REQUEST)
    
    if not uri:
        return error_response(f"{rendition_type} not available", status_code=status.HTTP_404_NOT_FOUND)
    
    # Generate presigned URL
    download_url = generate_presigned_download_url(uri, expires=timedelta(hours=1))
    
    return success_response({
        "rendition_type": rendition_type,
        "url": download_url,
        "expires_in": 3600
    })

