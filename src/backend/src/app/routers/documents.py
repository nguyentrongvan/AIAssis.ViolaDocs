import uuid
import logging
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
from ..models.documents import Document, DocumentVersion, Tag, DocumentTag, Share, Comment
from ..services.storage import generate_presigned_download_url
from ..utils.response import success_response, error_response
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_file_extension_from_mime(mime: str) -> str:
    """Extract short file extension from MIME type"""
    if not mime:
        return ""
    
    mime_lower = mime.lower()
    
    # Map common MIME types to extensions
    mime_to_ext = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
        "text/csv": "csv",
        "application/csv": "csv",
        "text/plain": "txt",
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
        "image/tiff": "tiff"
    }
    
    if mime_lower in mime_to_ext:
        return mime_to_ext[mime_lower]
    
    # Fallback: try to extract from MIME type
    if '/' in mime:
        subtype = mime.split('/')[-1].split('+')[0]
        # Handle vnd.openxmlformats... cases
        if 'wordprocessingml' in subtype:
            return "docx"
        elif 'spreadsheetml' in subtype:
            return "xlsx"
        elif 'presentationml' in subtype:
            return "pptx"
        # For simple cases like "pdf", "png", etc.
        if len(subtype) <= 5 and '.' not in subtype:
            return subtype
    
    return ""


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
    # Base query conditions - only show active (non-deleted) documents
    conditions = [
        Document.owner_id == current_user.id,
        Document.deleted_at.is_(None)  # Always filter out deleted documents
    ]
    
    base_query = select(Document).where(and_(*conditions))
    
    if search:
        base_query = base_query.where(Document.title.ilike(f"%{search}%"))
    
    # Get total count
    count_query = select(func.count(Document.id)).where(and_(*conditions))
    if search:
        count_query = count_query.where(Document.title.ilike(f"%{search}%"))
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated results with versions and tags for thumbnails
    # Note: Document.tags relationship needs to be defined in the model
    query = base_query.options(selectinload(Document.versions)).offset(skip).limit(limit)
    result = await session.execute(query)
    documents = result.scalars().all()
    
    from ..services.storage import generate_presigned_download_url
    
    items = []
    for doc in documents:
        item = {
            "id": doc.id,
            "title": doc.title,
            "mime": doc.mime,
            "size": doc.size,
            "status": doc.status,
            "created_at": doc.created_at.isoformat(),
            "deleted_at": doc.deleted_at.isoformat() if doc.deleted_at else None,
            "purge_at": doc.purge_at.isoformat() if doc.purge_at else None,
            "document_type": doc.mime.split('/')[0] if '/' in doc.mime else doc.mime,  # e.g., "application" -> "PDF", "image" -> "Image"
            "file_extension": _get_file_extension_from_mime(doc.mime)  # Extract short extension from MIME type
        }
        
        # Get tags from DocumentTag join
        tags_result = await session.execute(
            select(Tag.name)
            .join(DocumentTag, Tag.id == DocumentTag.tag_id)
            .where(DocumentTag.document_id == doc.id)
        )
        tags = tags_result.scalars().all()
        item["tags"] = list(tags) if tags else []
        
        # Get thumbnail from latest version
        if doc.versions:
            latest_version = max(doc.versions, key=lambda v: v.version_no)
            if latest_version.thumbnail_uri:
                thumb_uri = latest_version.thumbnail_uri
                if thumb_uri.startswith(f"minio://{settings.minio_bucket}/"):
                    thumb_uri = thumb_uri.replace(f"minio://{settings.minio_bucket}/", "")
                try:
                    item["thumbnail_url"] = generate_presigned_download_url(thumb_uri, expires=timedelta(hours=1))
                except Exception:
                    pass  # Skip if thumbnail generation fails
        
        items.append(item)
    
    return success_response({
        "items": items,
        "total": total
    })


@router.get("/{doc_id}")
async def get_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # Filter out deleted documents - they should only be accessible via Recycle Bin
    result = await session.execute(
        select(Document)
        .options(selectinload(Document.versions))
        .where(
            and_(
                Document.id == doc_id,
                Document.deleted_at.is_(None)  # Only show non-deleted documents
            )
        )
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if doc.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    from ..services.storage import generate_presigned_download_url
    
    # Get latest version for preview URL
    latest_version = max(doc.versions, key=lambda v: v.version_no) if doc.versions else None
    preview_url = None
    if latest_version and latest_version.blob_uri:
        blob_uri = latest_version.blob_uri
        if blob_uri.startswith(f"minio://{settings.minio_bucket}/"):
            blob_uri = blob_uri.replace(f"minio://{settings.minio_bucket}/", "")
        preview_url = generate_presigned_download_url(blob_uri, expires=timedelta(hours=1))
    
    versions = []
    for v in doc.versions:
        version_data = {
            "id": v.id,
            "version_no": v.version_no,
            "created_at": v.created_at.isoformat(),
            "created_by": v.created_by,
            "status": v.status,
            "text_uri": v.text_uri,
            "ocr_uri": v.ocr_uri,
            "thumbnail_uri": v.thumbnail_uri
        }
        # Add rendition URLs if available
        renditions = {}
        if v.thumbnail_uri:
            thumb_uri = v.thumbnail_uri
            if thumb_uri.startswith(f"minio://{settings.minio_bucket}/"):
                thumb_uri = thumb_uri.replace(f"minio://{settings.minio_bucket}/", "")
            renditions["thumbnail"] = generate_presigned_download_url(thumb_uri, expires=timedelta(hours=1))
        if v.blob_uri:
            blob_uri = v.blob_uri
            if blob_uri.startswith(f"minio://{settings.minio_bucket}/"):
                blob_uri = blob_uri.replace(f"minio://{settings.minio_bucket}/", "")
            renditions["preview"] = generate_presigned_download_url(blob_uri, expires=timedelta(hours=1))
        if renditions:
            version_data["renditions"] = renditions
        versions.append(version_data)
    
    return success_response({
        "id": doc.id,
        "title": doc.title,
        "mime": doc.mime,
        "size": doc.size,
        "status": doc.status,
        "owner_id": doc.owner_id,
        "created_at": doc.created_at.isoformat(),
        "preview_url": preview_url,
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
    """Soft delete a document"""
    from ..services.deletion_service import DocumentDeletionService
    
    try:
        # Check permission first
        result = await session.execute(
            select(Document).where(and_(Document.id == doc_id, Document.deleted_at.is_(None)))
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
        
        # Only owner or admin/staff can delete
        if doc.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
            return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
        
        # Soft delete using service
        doc = await DocumentDeletionService.soft_delete_document(doc_id, current_user.id, session)
        
        # Get purge grace period for response
        grace_period_days = await DocumentDeletionService.get_purge_grace_period_days(session)
        
        return success_response({
            "id": doc.id,
            "deleted": True,
            "deleted_at": doc.deleted_at.isoformat() if doc.deleted_at else None,
            "purge_at": doc.purge_at.isoformat() if doc.purge_at else None,
            "grace_period_days": grace_period_days
        })
    except ValueError as e:
        return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error deleting document {doc_id}: {e}", exc_info=True)
        return error_response("Failed to delete document", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.delete("/{doc_id}/purge")
async def purge_document(
    doc_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Force immediate hard delete of a document (admin only)"""
    from ..services.deletion_service import DocumentDeletionService
    
    try:
        # Admin only
        if current_user.role != "admin":
            return error_response("Access denied. Admin only.", status_code=status.HTTP_403_FORBIDDEN)
        
        # Hard delete using service (force=True bypasses purge_at check)
        await DocumentDeletionService.hard_delete_document(doc_id, current_user.id, session, force=True)
        
        return success_response({"id": doc_id, "purged": True})
    except ValueError as e:
        return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error purging document {doc_id}: {e}", exc_info=True)
        return error_response("Failed to purge document", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/{doc_id}/restore")
async def restore_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Restore a soft-deleted document"""
    from ..services.deletion_service import DocumentDeletionService
    
    try:
        # Check permission first
        result = await session.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
        
        if not doc.deleted_at:
            return error_response("Document is not deleted", status_code=status.HTTP_400_BAD_REQUEST)
        
        # Only owner or admin/staff can restore
        if doc.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
            return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
        
        # Restore using service
        doc = await DocumentDeletionService.restore_document(doc_id, current_user.id, session)
        
        return success_response({"id": doc.id, "restored": True})
    except ValueError as e:
        return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error restoring document {doc_id}: {e}", exc_info=True)
        return error_response("Failed to restore document", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
    
    from ..services.storage import generate_presigned_download_url
    
    version_list = []
    for v in versions:
        version_data = {
            "id": v.id,
            "version_no": v.version_no,
            "created_at": v.created_at.isoformat(),
            "created_by": v.created_by,
            "status": v.status,
            "text_uri": v.text_uri,
            "ocr_uri": v.ocr_uri,
            "thumbnail_uri": v.thumbnail_uri
        }
        # Add rendition URLs if available
        renditions = {}
        if v.thumbnail_uri:
            thumb_uri = v.thumbnail_uri
            if thumb_uri.startswith(f"minio://{settings.minio_bucket}/"):
                thumb_uri = thumb_uri.replace(f"minio://{settings.minio_bucket}/", "")
            renditions["thumbnail"] = generate_presigned_download_url(thumb_uri, expires=timedelta(hours=1))
        if v.blob_uri:
            blob_uri = v.blob_uri
            if blob_uri.startswith(f"minio://{settings.minio_bucket}/"):
                blob_uri = blob_uri.replace(f"minio://{settings.minio_bucket}/", "")
            renditions["preview"] = generate_presigned_download_url(blob_uri, expires=timedelta(hours=1))
        if renditions:
            version_data["renditions"] = renditions
        version_list.append(version_data)
    
    return success_response(version_list)


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
    
    # Use diff service to compare versions
    from ..services.diff import compare_versions as diff_compare
    
    diff_result = await diff_compare(
        v1.text_uri,
        v2.text_uri,
        v1.metadata_snapshot,
        v2.metadata_snapshot
    )
    
    # Get ACL changes from audit events (simplified - would need to query audit events)
    acl_diff = {}
    
    return success_response({
        "content_diff": diff_result["content_diff"],
        "metadata_diff": diff_result["metadata_diff"],
        "acl_diff": acl_diff,
        "has_content_diff": diff_result["has_content_diff"],
        "has_metadata_diff": diff_result["has_metadata_diff"]
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
        share_token = str(uuid.uuid4())
        target_type = "link"
        target_id = None
    else:
        share_token = None
    
    if request.expires_at:
        expires_at = datetime.fromisoformat(request.expires_at)
    
    # Create share
    share = Share(
        document_id=doc_id,
        target_type=target_type,
        target_id=target_id,
        share_token=share_token,
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
    
    response_data = {
        "share_id": share.id,
        "target": target_response,
        "expires_at": share.expires_at.isoformat() if share.expires_at else None
    }
    
    if share.share_token:
        response_data["share_token"] = share.share_token
        response_data["share_url"] = f"/api/v1/documents/shared/{share.share_token}"
    
    return success_response(response_data)


@router.get("/{doc_id}/renditions/{rendition_type}")
async def get_rendition(
    doc_id: int,
    rendition_type: str,
    version_id: Optional[int] = Query(None, description="Specific version ID (defaults to latest)"),
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
    
    # Get version (specific or latest)
    if version_id:
        version_result = await session.execute(
            select(DocumentVersion)
            .where(and_(DocumentVersion.document_id == doc_id, DocumentVersion.id == version_id))
        )
        version = version_result.scalar_one_or_none()
    else:
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
        if not uri:
            return error_response(f"{rendition_type} not available", status_code=status.HTTP_404_NOT_FOUND)
        # Generate presigned URL for thumbnail
        download_url = generate_presigned_download_url(uri, expires=timedelta(hours=1))
        return success_response({
            "rendition_type": rendition_type,
            "url": download_url,
            "expires_in": 3600
        })
    elif rendition_type == "text" or rendition_type == "ocr":
        uri = version.text_uri or version.ocr_uri
        if not uri:
            return error_response(f"{rendition_type} not available", status_code=status.HTTP_404_NOT_FOUND)
        
        # Return text content directly instead of presigned URL
        try:
            from ..services.storage import get_minio_client
            minio_client = get_minio_client()
            text_object_name = uri
            if text_object_name.startswith(f"minio://{settings.minio_bucket}/"):
                text_object_name = text_object_name.replace(f"minio://{settings.minio_bucket}/", "")
            
            file_data = minio_client.get_object(settings.minio_bucket, text_object_name)
            text_content = file_data.read().decode('utf-8')
            file_data.close()
            file_data.release_conn()
            
            return success_response({
                "rendition_type": rendition_type,
                "content": text_content
            })
        except Exception as e:
            return error_response(f"Failed to read text: {e}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return error_response("Invalid rendition type", status_code=status.HTTP_400_BAD_REQUEST)


class CommentCreate(BaseModel):
    content: str
    version_id: Optional[int] = None
    type: str = "comment"  # comment, annotation
    position: Optional[dict] = None  # For annotations: page, x, y, width, height, etc.


class CommentUpdate(BaseModel):
    content: Optional[str] = None
    position: Optional[dict] = None


@router.post("/{doc_id}/comments")
async def create_comment(
    doc_id: int,
    payload: CommentCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Create a comment or annotation on a document."""
    # Verify document access
    doc_result = await session.execute(
        select(Document).where(and_(Document.id == doc_id, Document.deleted_at.is_(None)))
    )
    doc = doc_result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Check access via share if not owner
    has_access = False
    if doc.owner_id == current_user.id or current_user.role in ["admin", "staff"]:
        has_access = True
    else:
        # Check shares
        shares_result = await session.execute(
            select(Share).where(
                and_(
                    Share.document_id == doc_id,
                    or_(
                        Share.expires_at.is_(None),
                        Share.expires_at > datetime.utcnow()
                    )
                )
            )
        )
        shares = shares_result.scalars().all()
        for share in shares:
            if share.target_type == "user" and share.target_id == current_user.id:
                has_access = True
                break
            elif share.target_type == "role" and current_user.role == share.permissions.get("role"):
                has_access = True
                break
    
    if not has_access:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    # Validate version_id if provided
    if payload.version_id:
        version_result = await session.execute(
            select(DocumentVersion).where(
                and_(
                    DocumentVersion.id == payload.version_id,
                    DocumentVersion.document_id == doc_id
                )
            )
        )
        version = version_result.scalar_one_or_none()
        if not version:
            return error_response("Version not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Validate type
    if payload.type not in ["comment", "annotation"]:
        return error_response("Type must be 'comment' or 'annotation'", status_code=status.HTTP_400_BAD_REQUEST)
    
    comment = Comment(
        document_id=doc_id,
        version_id=payload.version_id,
        user_id=current_user.id,
        content=payload.content,
        type=payload.type,
        position=payload.position
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    
    return success_response({
        "id": comment.id,
        "document_id": comment.document_id,
        "version_id": comment.version_id,
        "user_id": comment.user_id,
        "content": comment.content,
        "type": comment.type,
        "position": comment.position,
        "created_at": comment.created_at.isoformat()
    })


@router.get("/{doc_id}/comments")
async def list_comments(
    doc_id: int,
    version_id: Optional[int] = None,
    comment_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """List comments and annotations for a document."""
    # Verify document access
    doc_result = await session.execute(
        select(Document).where(and_(Document.id == doc_id, Document.deleted_at.is_(None)))
    )
    doc = doc_result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Check access (similar to create_comment)
    has_access = False
    if doc.owner_id == current_user.id or current_user.role in ["admin", "staff"]:
        has_access = True
    else:
        shares_result = await session.execute(
            select(Share).where(
                and_(
                    Share.document_id == doc_id,
                    or_(
                        Share.expires_at.is_(None),
                        Share.expires_at > datetime.utcnow()
                    )
                )
            )
        )
        shares = shares_result.scalars().all()
        for share in shares:
            if share.target_type == "user" and share.target_id == current_user.id:
                has_access = True
                break
    
    if not has_access:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    # Build query
    query = select(Comment).where(Comment.document_id == doc_id)
    
    if version_id:
        query = query.where(Comment.version_id == version_id)
    
    if comment_type:
        query = query.where(Comment.type == comment_type)
    
    query = query.order_by(Comment.created_at.desc())
    
    result = await session.execute(query)
    comments = result.scalars().all()
    
    return success_response([{
        "id": c.id,
        "document_id": c.document_id,
        "version_id": c.version_id,
        "user_id": c.user_id,
        "content": c.content,
        "type": c.type,
        "position": c.position,
        "created_at": c.created_at.isoformat()
    } for c in comments])


@router.patch("/{doc_id}/comments/{comment_id}")
async def update_comment(
    doc_id: int,
    comment_id: int,
    payload: CommentUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update a comment or annotation."""
    result = await session.execute(
        select(Comment).where(
            and_(
                Comment.id == comment_id,
                Comment.document_id == doc_id
            )
        )
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        return error_response("Comment not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Only owner or admin can update
    if comment.user_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    if payload.content is not None:
        comment.content = payload.content
    if payload.position is not None:
        comment.position = payload.position
    
    await session.commit()
    await session.refresh(comment)
    
    return success_response({
        "id": comment.id,
        "content": comment.content,
        "position": comment.position,
        "updated_at": comment.updated_at.isoformat()
    })


@router.delete("/{doc_id}/comments/{comment_id}")
async def delete_comment(
    doc_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete a comment or annotation."""
    result = await session.execute(
        select(Comment).where(
            and_(
                Comment.id == comment_id,
                Comment.document_id == doc_id
            )
        )
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        return error_response("Comment not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Only owner or admin can delete
    if comment.user_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    await session.delete(comment)
    await session.commit()
    
    return success_response({"id": comment_id, "deleted": True})

