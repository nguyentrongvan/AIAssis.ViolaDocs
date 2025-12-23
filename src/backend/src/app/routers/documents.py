import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from ..db import get_session
from ..dependencies import get_current_user, get_current_admin_user, security
from ..models.users import User
from ..models.documents import Document, DocumentVersion, Tag, DocumentTag, Share, Comment
from ..services.storage import generate_presigned_download_url, get_file_bytes_from_minio, get_proxy_download_url, get_proxy_download_url_for_doc, get_proxy_preview_url_for_doc
from ..services.permission_service import get_user_accessible_documents_query, check_document_access
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
    user_emails: Optional[list[str]] = None  # List of user emails to share with
    role_ids: Optional[list[int]] = None  # List of role IDs to share with
    expires_at: Optional[str] = None
    permissions: Optional[list[str]] = None


class TTSGenerateRequest(BaseModel):
    voice_id: Optional[int] = None  # If None, auto-select based on document language
    speed: float = 1.0  # Speed range: 0.5-2.0
    provider: Optional[str] = "gtts"  # TTS provider name


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
    folder_id: Optional[int] = Query(None),
    http_request: Request = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # Use permission service to get accessible documents query (includes shared documents)
    base_query = select(Document)
    accessible_query = await get_user_accessible_documents_query(session, current_user, base_query)
    
    if search:
        accessible_query = accessible_query.where(Document.title.ilike(f"%{search}%"))
    
    # Filter by folder_id if provided
    if folder_id is not None:
        accessible_query = accessible_query.where(Document.folder_id == folder_id)
    
    # Get total count
    count_query = select(func.count(Document.id))
    count_query = await get_user_accessible_documents_query(session, current_user, count_query)
    if search:
        count_query = count_query.where(Document.title.ilike(f"%{search}%"))
    if folder_id is not None:
        count_query = count_query.where(Document.folder_id == folder_id)
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated results with versions and tags for thumbnails
    # Note: Document.tags relationship needs to be defined in the model
    query = accessible_query.options(selectinload(Document.versions)).offset(skip).limit(limit)
    result = await session.execute(query)
    documents = result.scalars().all()
    
    from ..services.storage import generate_presigned_download_url, get_proxy_download_url
    
    items = []
    for doc in documents:
        item = {
            "id": doc.id,
            "title": doc.title,
            "mime": doc.mime,
            "size": doc.size,
            "status": doc.status,
            "folder_id": doc.folder_id,  # Include folder_id in response
            "created_at": doc.created_at.isoformat(),
            "deleted_at": doc.deleted_at.isoformat() if doc.deleted_at else None,
            "purge_at": doc.purge_at.isoformat() if doc.purge_at else None,
            "document_type": doc.mime.split('/')[0] if '/' in doc.mime else doc.mime,  # e.g., "application" -> "PDF", "image" -> "Image"
            "file_extension": _get_file_extension_from_mime(doc.mime),  # Extract short extension from MIME type
            "summary": doc.summary  # Include document summary
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
                    # In dev mode, use proxy endpoint
                    if settings.debug and http_request:
                        # Extract token from Authorization header
                        token = None
                        auth_header = http_request.headers.get("Authorization", "")
                        if auth_header.startswith("Bearer "):
                            token = auth_header.replace("Bearer ", "")
                        item["thumbnail_url"] = get_proxy_download_url(thumb_uri, doc.id, http_request.base_url, token)
                    else:
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
    http_request: Request,
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
    
    # Check access using permission service
    has_access, _, reason = await check_document_access(session, current_user, doc, "read")
    if not has_access:
        return error_response(reason or "Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    from ..services.storage import generate_presigned_download_url, get_proxy_download_url, get_proxy_preview_url_for_doc
    
    # Extract token from Authorization header for proxy URLs
    token = None
    auth_header = http_request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
    
    # Get latest version for preview URL
    latest_version = max(doc.versions, key=lambda v: v.version_no) if doc.versions else None
    preview_url = None
    if latest_version and latest_version.blob_uri:
        blob_uri = latest_version.blob_uri
        if blob_uri.startswith(f"minio://{settings.minio_bucket}/"):
            blob_uri = blob_uri.replace(f"minio://{settings.minio_bucket}/", "")
        # In dev mode, use proxy preview endpoint (inline) for browser preview
        if settings.debug:
            preview_url = get_proxy_preview_url_for_doc(doc_id, http_request.base_url, token)
        else:
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
            "thumbnail_uri": v.thumbnail_uri,
            "metadata_snapshot": v.metadata_snapshot  # Include metadata snapshot
        }
        # Add rendition URLs if available
        renditions = {}
        if v.thumbnail_uri:
            thumb_uri = v.thumbnail_uri
            if thumb_uri.startswith(f"minio://{settings.minio_bucket}/"):
                thumb_uri = thumb_uri.replace(f"minio://{settings.minio_bucket}/", "")
            # In dev mode, use proxy endpoint
            if settings.debug:
                renditions["thumbnail"] = get_proxy_download_url(thumb_uri, doc_id, http_request.base_url, token)
            else:
                renditions["thumbnail"] = generate_presigned_download_url(thumb_uri, expires=timedelta(hours=1))
        if v.blob_uri:
            blob_uri = v.blob_uri
            if blob_uri.startswith(f"minio://{settings.minio_bucket}/"):
                blob_uri = blob_uri.replace(f"minio://{settings.minio_bucket}/", "")
            # In dev mode, use proxy preview endpoint (inline) for browser preview
            if settings.debug:
                renditions["preview"] = get_proxy_preview_url_for_doc(doc_id, http_request.base_url, token, v.id)
            else:
                renditions["preview"] = generate_presigned_download_url(blob_uri, expires=timedelta(hours=1))
        if renditions:
            version_data["renditions"] = renditions
        versions.append(version_data)
    
    # Get tags for this document
    tags_result = await session.execute(
        select(Tag.name)
        .join(DocumentTag, Tag.id == DocumentTag.tag_id)
        .where(DocumentTag.document_id == doc.id)
    )
    tags = tags_result.scalars().all()
    
    return success_response({
        "id": doc.id,
        "title": doc.title,
        "mime": doc.mime,
        "size": doc.size,
        "status": doc.status,
        "owner_id": doc.owner_id,
        "folder_id": doc.folder_id,
        "retention_policy_id": doc.retention_policy_id,
        "sensitivity": doc.sensitivity,
        "created_at": doc.created_at.isoformat(),
        "preview_url": preview_url,
        "tags": list(tags) if tags else [],
        "versions": versions,
        "metadata": doc.file_metadata,  # Include comprehensive metadata
        "summary": doc.summary  # Include document summary
    })


@router.post("/{doc_id}/regenerate-summary")
async def regenerate_document_summary(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Regenerate document summary from latest version text content"""
    # Get document
    result = await session.execute(
        select(Document)
        .options(selectinload(Document.versions))
        .where(
            and_(
                Document.id == doc_id,
                Document.deleted_at.is_(None)
            )
        )
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Check access
    has_access, _, reason = await check_document_access(session, current_user, doc, "read")
    if not has_access:
        return error_response(reason or "Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    # Get latest version
    if not doc.versions:
        return error_response("No versions found for this document", status_code=status.HTTP_404_NOT_FOUND)
    
    latest_version = max(doc.versions, key=lambda v: v.version_no)
    
    # Get text content from version
    text_uri = latest_version.text_uri or latest_version.ocr_uri
    if not text_uri:
        return error_response("No text content available for this document", status_code=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Download text from MinIO
        from ..services.storage import get_minio_client
        from ..config import settings
        
        minio_client = get_minio_client()
        object_name = text_uri
        if object_name.startswith(f"minio://{settings.minio_bucket}/"):
            object_name = object_name.replace(f"minio://{settings.minio_bucket}/", "")
        
        file_data = minio_client.get_object(settings.minio_bucket, object_name)
        text_content = file_data.read().decode('utf-8')
        file_data.close()
        file_data.release_conn()
        
        # Get summary max_length setting
        from ..services.settings_service import SettingsService
        max_length = await SettingsService.get_setting(
            "document_summary.max_length",
            default=300,
            session=session
        )
        
        # Generate summary using LLM service
        from ..services.ai import get_llm_service
        llm_service = get_llm_service()
        
        if not llm_service:
            return error_response("LLM service not available", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        summary = await llm_service.generate_summary_async(
            content=text_content,
            max_length=max_length,
            session=session
        )
        
        # Check if summary generation failed
        if summary is None:
            # LLM not available or error occurred
            return error_response(
                "Failed to generate summary: LLM service is not available or returned an error. Please check LLM settings and try again.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        # Update document summary
        doc.summary = summary
        await session.commit()
        
        return success_response({
            "summary": summary,
            "message": "Summary regenerated successfully"
        })
        
    except Exception as e:
        logger.error(f"Error regenerating summary for document {doc_id}: {e}", exc_info=True)
        return error_response(f"Failed to regenerate summary: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
    
    # Only owner or admin/staff can update documents
    # (No separate "write" permission - update is owner/admin/staff only)
    if doc.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied: only owner or admin/staff can update", status_code=status.HTTP_403_FORBIDDEN)
    
    if request.title:
        doc.title = request.title
    if request.folder_id is not None:
        # Validate folder access if moving to a different folder
        if request.folder_id != doc.folder_id:
            from ..services.permission_service import check_folder_access
            has_folder_access, reason = await check_folder_access(session, current_user, request.folder_id)
            if not has_folder_access:
                return error_response(
                    reason or "Access denied: you don't have access to the target folder",
                    status_code=status.HTTP_403_FORBIDDEN
                )
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
        
        # Only owner or admin/staff can delete documents
        # (No separate "delete" permission - delete is owner/admin/staff only)
        if doc.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
            return error_response("Access denied: only owner or admin/staff can delete", status_code=status.HTTP_403_FORBIDDEN)
        
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
    
    # Check view access using permission service
    has_access, _, reason = await check_document_access(session, current_user, doc, "view")
    if not has_access:
        return error_response(reason or "Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
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
    
    # Check view access using permission service
    has_access, _, reason = await check_document_access(session, current_user, doc, "view")
    if not has_access:
        return error_response(reason or "Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
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
    
    # Only owner or admin/staff can upload new versions
    # (No separate "write" permission - upload new version is owner/admin/staff only)
    if doc.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied: only owner or admin/staff can upload new versions", status_code=status.HTTP_403_FORBIDDEN)
    
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
    
    if request.expires_at:
        expires_at = datetime.fromisoformat(request.expires_at)
    
    # Handle legacy fields
    # Default permissions: view (backward compatible with old "read")
    default_perms = request.permissions or ["view"]
    # Map old permissions to new ones for backward compatibility
    normalized_perms = []
    for perm in default_perms:
        if perm == "read":
            normalized_perms.append("view")
        elif perm == "write":
            normalized_perms.extend(["view", "search"])
        elif perm == "delete":
            normalized_perms.extend(["view", "search", "chat"])
        else:
            normalized_perms.append(perm)
    # Remove duplicates while preserving order
    normalized_perms = list(dict.fromkeys(normalized_perms))
    
    # Handle user_emails (frontend sends list of emails)
    if request.user_emails:
        from ..models.users import User
        for email in request.user_emails:
            user_result = await session.execute(select(User).where(User.email == email.strip()))
            user = user_result.scalar_one_or_none()
            if user:
                share = Share(
                    document_id=doc_id,
                    target_type="user",
                    target_id=user.id,
                    permissions=normalized_perms,
                    expires_at=expires_at
                )
                session.add(share)
    
    # Handle role_ids (frontend sends list of role IDs)
    if request.role_ids:
        for role_id in request.role_ids:
            role_result = await session.execute(select(Role).where(Role.id == role_id))
            role = role_result.scalar_one_or_none()
            if role:
                permissions_data = {
                    "role_name": role.name,
                    "permissions": normalized_perms
                }
                share = Share(
                    document_id=doc_id,
                    target_type="role",
                    target_id=0,
                    permissions=permissions_data,
                    expires_at=expires_at
                )
                session.add(share)
    
    # Handle legacy single user/role sharing (only if no user_emails or role_ids)
    if not request.user_emails and not request.role_ids:
        permissions_data = normalized_perms
        share_token = None
        
        if request.target_user_id:
            target_type = "user"
            target_id = request.target_user_id
        elif request.target_role:
            target_type = "role"
            # For role, store in target_id as 0 and use permissions JSON to store role name and permissions
            target_id = 0
            # Store role_name and permissions in a dict structure
            permissions_data = {
                "role_name": request.target_role,
                "permissions": normalized_perms
            }
        elif not target_type:
            # Create share link
            share_token = str(uuid.uuid4())
            target_type = "link"
            target_id = None
        
        # Create share
        share = Share(
            document_id=doc_id,
            target_type=target_type,
            target_id=target_id,
            share_token=share_token,
            expires_at=expires_at,
            permissions=permissions_data
        )
        session.add(share)
    
    await session.commit()
    
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
    
    # Check view access using permission service
    has_access, _, reason = await check_document_access(session, current_user, doc, "view")
    if not has_access:
        return error_response(reason or "Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
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
    
    # Check view access using permission service (comments require view access)
    has_access, _, reason = await check_document_access(session, current_user, doc, "view")
    if not has_access:
        return error_response(reason or "Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
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
    
    # Check view access using permission service
    has_access, _, reason = await check_document_access(session, current_user, doc, "view")
    if not has_access:
        return error_response(reason or "Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
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


@router.get("/{doc_id}/preview")
async def preview_document(
    doc_id: int,
    version_id: Optional[int] = Query(None, description="Specific version ID (defaults to latest)"),
    token: Optional[str] = Query(None, description="Authentication token (for browser direct access)"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session)
):
    """Preview document file in browser (proxy endpoint for dev mode). Uses inline Content-Disposition."""
    # Authenticate user - support both Authorization header and token query parameter
    current_user = None
    if credentials:
        try:
            current_user = await get_current_user(credentials=credentials, session=session)
        except HTTPException:
            pass
    elif token:
        # Try to authenticate with token from query parameter
        from ..services.auth import decode_token, get_user_by_id
        payload = decode_token(token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                current_user = await get_user_by_id(session, int(user_id))
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Get document
    result = await session.execute(
        select(Document)
        .options(selectinload(Document.versions))
        .where(
            and_(
                Document.id == doc_id,
                Document.deleted_at.is_(None)
            )
        )
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Check access
    has_access, _, reason = await check_document_access(session, current_user, doc, "view")
    if not has_access:
        return error_response(reason or "Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    # Get version
    if version_id:
        version_result = await session.execute(
            select(DocumentVersion).where(
                and_(
                    DocumentVersion.document_id == doc_id,
                    DocumentVersion.id == version_id
                )
            )
        )
        version = version_result.scalar_one_or_none()
    else:
        # Get latest version
        version = max(doc.versions, key=lambda v: v.version_no) if doc.versions else None
    
    if not version or not version.blob_uri:
        return error_response("File not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Extract object name from blob_uri
    blob_uri = version.blob_uri
    if blob_uri.startswith(f"minio://{settings.minio_bucket}/"):
        blob_uri = blob_uri.replace(f"minio://{settings.minio_bucket}/", "")
    
    # Get file from MinIO
    file_bytes = await get_file_bytes_from_minio(blob_uri)
    if not file_bytes:
        return error_response("Failed to retrieve file", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Return file with inline Content-Disposition for browser preview
    # Headers must be latin-1 compatible, so we need to sanitize Unicode filenames
    import re
    # Remove or replace non-ASCII characters
    filename_safe = re.sub(r'[^\x00-\x7F]+', '_', doc.title)
    # Remove any remaining problematic characters
    filename_safe = re.sub(r'[<>:"/\\|?*]', '_', filename_safe)
    # Limit length
    if len(filename_safe) > 200:
        filename_safe = filename_safe[:200]
    
    # Get file extension from mime type or filename
    file_ext = ""
    if doc.mime:
        mime_to_ext = {
            "application/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/tiff": ".tiff",
            "text/plain": ".txt",
            "text/csv": ".csv"
        }
        file_ext = mime_to_ext.get(doc.mime, "")
    
    if not file_ext and filename_safe:
        # Try to extract extension from original filename (sanitize extension too)
        if '.' in doc.title:
            ext_part = doc.title.rsplit('.', 1)[-1]
            # Sanitize extension to ASCII only
            ext_safe = ext_part.encode('ascii', 'ignore').decode('ascii')
            if ext_safe:
                file_ext = '.' + ext_safe
    
    filename_with_ext = filename_safe + file_ext if file_ext else filename_safe
    
    # Ensure filename is pure ASCII (double-check) - test latin-1 encoding
    # Headers must be latin-1 compatible
    try:
        # Test if it can be encoded to latin-1
        filename_final_bytes = filename_with_ext.encode('latin-1')
        filename_final = filename_final_bytes.decode('latin-1')
    except (UnicodeEncodeError, UnicodeDecodeError):
        # If encoding fails, force ASCII only
        filename_final = filename_with_ext.encode('ascii', 'ignore').decode('ascii')
        if not filename_final:
            filename_final = "document" + (file_ext if file_ext else ".pdf")
    
    # Build headers dict with inline Content-Disposition for browser preview
    headers_dict = {
        "Content-Disposition": f'inline; filename="{filename_final}"',  # inline instead of attachment
        "Content-Length": str(len(file_bytes))
    }
    
    return Response(
        content=file_bytes,
        media_type=doc.mime or "application/octet-stream",
        headers=headers_dict
    )


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: int,
    version_id: Optional[int] = Query(None, description="Specific version ID (defaults to latest)"),
    token: Optional[str] = Query(None, description="Authentication token (for browser direct access)"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session)
):
    """Download document file (proxy endpoint for dev mode). Uses attachment Content-Disposition."""
    # Authenticate user - support both Authorization header and token query parameter
    current_user = None
    if credentials:
        try:
            current_user = await get_current_user(credentials=credentials, session=session)
        except HTTPException:
            pass
    elif token:
        # Try to authenticate with token from query parameter
        from ..services.auth import decode_token, get_user_by_id
        payload = decode_token(token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                current_user = await get_user_by_id(session, int(user_id))
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Get document
    result = await session.execute(
        select(Document)
        .options(selectinload(Document.versions))
        .where(
            and_(
                Document.id == doc_id,
                Document.deleted_at.is_(None)
            )
        )
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Check access
    has_access, _, reason = await check_document_access(session, current_user, doc, "view")
    if not has_access:
        return error_response(reason or "Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    # Get version
    if version_id:
        version_result = await session.execute(
            select(DocumentVersion).where(
                and_(
                    DocumentVersion.document_id == doc_id,
                    DocumentVersion.id == version_id
                )
            )
        )
        version = version_result.scalar_one_or_none()
    else:
        # Get latest version
        version = max(doc.versions, key=lambda v: v.version_no) if doc.versions else None
    
    if not version or not version.blob_uri:
        return error_response("File not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Extract object name from blob_uri
    blob_uri = version.blob_uri
    if blob_uri.startswith(f"minio://{settings.minio_bucket}/"):
        blob_uri = blob_uri.replace(f"minio://{settings.minio_bucket}/", "")
    
    # Get file from MinIO
    file_bytes = await get_file_bytes_from_minio(blob_uri)
    if not file_bytes:
        return error_response("Failed to retrieve file", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Return file with appropriate headers
    # Headers must be latin-1 compatible, so we need to sanitize Unicode filenames
    # Use only ASCII characters in filename to avoid encoding issues
    import re
    # Remove or replace non-ASCII characters
    filename_safe = re.sub(r'[^\x00-\x7F]+', '_', doc.title)
    # Remove any remaining problematic characters
    filename_safe = re.sub(r'[<>:"/\\|?*]', '_', filename_safe)
    # Limit length
    if len(filename_safe) > 200:
        filename_safe = filename_safe[:200]
    
    # Get file extension from mime type or filename
    file_ext = ""
    if doc.mime:
        mime_to_ext = {
            "application/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/tiff": ".tiff",
            "text/plain": ".txt",
            "text/csv": ".csv"
        }
        file_ext = mime_to_ext.get(doc.mime, "")
    
    if not file_ext and filename_safe:
        # Try to extract extension from original filename (sanitize extension too)
        if '.' in doc.title:
            ext_part = doc.title.rsplit('.', 1)[-1]
            # Sanitize extension to ASCII only
            ext_safe = ext_part.encode('ascii', 'ignore').decode('ascii')
            if ext_safe:
                file_ext = '.' + ext_safe
    
    filename_with_ext = filename_safe + file_ext if file_ext else filename_safe
    
    # Ensure filename is pure ASCII (double-check) - test latin-1 encoding
    # Headers must be latin-1 compatible
    try:
        # Test if it can be encoded to latin-1
        filename_final_bytes = filename_with_ext.encode('latin-1')
        filename_final = filename_final_bytes.decode('latin-1')
    except (UnicodeEncodeError, UnicodeDecodeError):
        # If encoding fails, force ASCII only
        filename_final = filename_with_ext.encode('ascii', 'ignore').decode('ascii')
        if not filename_final:
            filename_final = "document" + (file_ext if file_ext else ".pdf")
    
    # Build headers dict with only ASCII-safe values
    headers_dict = {
        "Content-Disposition": f'attachment; filename="{filename_final}"',
        "Content-Length": str(len(file_bytes))
    }
    
    return Response(
        content=file_bytes,
        media_type=doc.mime or "application/octet-stream",
        headers=headers_dict
    )


@router.get("/{doc_id}/preview/{object_name:path}")
async def preview_object(
    doc_id: int,
    object_name: str,
    token: Optional[str] = Query(None, description="Authentication token (for browser direct access)"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session)
):
    """Proxy endpoint for previewing objects (thumbnails, etc.) in dev mode."""
    # Authenticate user - support both Authorization header and token query parameter
    current_user = None
    if credentials:
        try:
            current_user = await get_current_user(credentials=credentials, session=session)
        except HTTPException:
            pass
    elif token:
        # Try to authenticate with token from query parameter
        from ..services.auth import decode_token, get_user_by_id
        payload = decode_token(token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                current_user = await get_user_by_id(session, int(user_id))
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Get document
    result = await session.execute(
        select(Document).where(
            and_(
                Document.id == doc_id,
                Document.deleted_at.is_(None)
            )
        )
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Check access
    has_access, _, reason = await check_document_access(session, current_user, doc, "view")
    if not has_access:
        return error_response(reason or "Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    # Get file from MinIO
    file_bytes = await get_file_bytes_from_minio(object_name)
    if not file_bytes:
        return error_response("File not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Determine content type
    content_type = "image/png"  # Default for thumbnails
    if object_name.endswith('.jpg') or object_name.endswith('.jpeg'):
        content_type = "image/jpeg"
    elif object_name.endswith('.pdf'):
        content_type = "application/pdf"
    
    # Use inline Content-Disposition for browser preview
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": "inline",  # inline for browser preview
            "Content-Length": str(len(file_bytes))
        }
    )


@router.post("/{doc_id}/detect-language")
async def detect_document_language(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Detect language for a document"""
    # Check document access
    result = await session.execute(
        select(Document).where(
            and_(
                Document.id == doc_id,
                Document.deleted_at.is_(None)
            )
        )
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Check access
    has_access, _, reason = await check_document_access(session, current_user, doc, "view")
    if not has_access:
        return error_response(reason or "Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    # Get latest version with text
    version_result = await session.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.version_no.desc())
        .limit(1)
    )
    version = version_result.scalar_one_or_none()
    
    if not version or not version.text_uri:
        return error_response("Document must be processed (OCR/text extraction) before detecting language", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Read text from MinIO
    from ..services.storage import get_file_bytes_from_minio
    try:
        text_bytes = await get_file_bytes_from_minio(version.text_uri)
        if not text_bytes:
            return error_response("Failed to read document text", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        text_content = text_bytes.decode('utf-8')
    except Exception as e:
        return error_response(f"Failed to read document text: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Detect language
    from ..services.language_detection_service import LanguageDetectionService
    language_info = LanguageDetectionService.detect_language(text_content)
    
    # Save to document metadata
    # IMPORTANT: SQLAlchemy doesn't detect changes inside JSON dict
    # Must create a new dict to trigger update
    current_metadata = dict(doc.file_metadata) if doc.file_metadata else {}
    current_metadata["language"] = language_info
    doc.file_metadata = current_metadata  # Reassign to trigger SQLAlchemy change detection
    
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(doc, "file_metadata")
    
    await session.commit()
    
    return success_response({
        "language": language_info,
        "message": "Language detected successfully"
    })


@router.post("/{doc_id}/tts/generate")
async def generate_document_tts(
    doc_id: int,
    request: TTSGenerateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Generate TTS audio for a document.
    
    NOTE: TTS is only generated when explicitly requested by the user.
    It is NOT automatically created during document upload or processing.
    """
    # Check document access
    result = await session.execute(
        select(Document).where(
            and_(
                Document.id == doc_id,
                Document.deleted_at.is_(None)
            )
        )
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Check access
    has_access, _, reason = await check_document_access(session, current_user, doc, "view")
    if not has_access:
        return error_response(reason or "Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    # Validate speed
    if request.speed < 0.5 or request.speed > 2.0:
        return error_response("Speed must be between 0.5 and 2.0", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Check if document has text (must be processed first)
    version_result = await session.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.version_no.desc())
        .limit(1)
    )
    version = version_result.scalar_one_or_none()
    
    if not version or not version.text_uri:
        return error_response("Document must be processed (OCR/text extraction) before generating TTS", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Check if language is detected, if not, detect it first
    detected_language = None
    if not doc.file_metadata or not doc.file_metadata.get("language"):
        # Language not detected yet, detect it now
        from ..services.storage import get_file_bytes_from_minio
        from ..services.language_detection_service import LanguageDetectionService
        from sqlalchemy.orm.attributes import flag_modified
        
        try:
            text_bytes = await get_file_bytes_from_minio(version.text_uri)
            if text_bytes:
                text_content = text_bytes.decode('utf-8')
                language_info = LanguageDetectionService.detect_language(text_content)
                
                # Save to document metadata
                # IMPORTANT: SQLAlchemy doesn't detect changes inside JSON dict
                current_metadata = dict(doc.file_metadata) if doc.file_metadata else {}
                current_metadata["language"] = language_info
                doc.file_metadata = current_metadata
                flag_modified(doc, "file_metadata")
                
                await session.commit()
                
                detected_language = language_info.get("primary", "en")
        except Exception as e:
            logger.warning(f"Failed to detect language before TTS generation: {e}")
            # Continue with default language
            detected_language = "en"
    else:
        detected_language = doc.file_metadata.get("language", {}).get("primary", "en")
    
    # Create TTS job
    from ..models.ai import AIJob
    
    job = AIJob(
        job_type="tts",
        target={"document_id": doc_id},
        provider=request.provider or "gtts",
        status="queued",
        input_ref={
            "voice_id": request.voice_id,
            "speed": request.speed,
            "provider": request.provider or "gtts",
            "language": detected_language
        }
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    
    return success_response({
        "job_id": job.id,
        "status": job.status,
        "message": "TTS generation job created",
        "language": detected_language
    })


@router.get("/{doc_id}/tts")
async def get_document_tts(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get TTS audio for a document (returns latest TTS job result)"""
    # Check document access
    result = await session.execute(
        select(Document).where(
            and_(
                Document.id == doc_id,
                Document.deleted_at.is_(None)
            )
        )
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Check access
    has_access, _, reason = await check_document_access(session, current_user, doc, "view")
    if not has_access:
        return error_response(reason or "Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    # Find latest completed TTS job
    from ..models.ai import AIJob
    
    # Query all TTS jobs and filter in Python (more reliable for JSON fields)
    job_result = await session.execute(
        select(AIJob)
        .where(
            and_(
                AIJob.job_type == "tts",
                AIJob.status == "completed"
            )
        )
        .order_by(AIJob.created_at.desc())
    )
    all_jobs = job_result.scalars().all()
    
    # Filter jobs that match this document
    job = None
    for j in all_jobs:
        if j.target and isinstance(j.target, dict):
            target_doc_id = j.target.get("document_id")
            if target_doc_id == doc_id:
                job = j
                break
    
    if not job or not job.output_ref:
        return error_response("No TTS audio available. Please generate TTS first.", status_code=status.HTTP_404_NOT_FOUND)
    
    audio_uri = job.output_ref.get("audio_uri")
    if not audio_uri:
        return error_response("TTS job completed but audio URI not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Get audio from MinIO
    file_bytes = await get_file_bytes_from_minio(audio_uri)
    if not file_bytes:
        return error_response("TTS audio file not found", status_code=status.HTTP_404_NOT_FOUND)
    
    return Response(
        content=file_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f'inline; filename="tts_{doc_id}.mp3"',
            "Content-Length": str(len(file_bytes))
        }
    )


@router.get("/shared/{share_token}")
async def get_shared_document(
    share_token: str,
    http_request: Request,
    session: AsyncSession = Depends(get_session)
):
    """Access document via share link (no authentication required)."""
    from datetime import datetime
    
    # Find share by token
    share_result = await session.execute(
        select(Share).where(Share.share_token == share_token)
    )
    share = share_result.scalar_one_or_none()
    
    if not share:
        return error_response("Share link not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Check if share has expired
    if share.expires_at and share.expires_at < datetime.utcnow():
        return error_response("Share link has expired", status_code=status.HTTP_410_GONE)
    
    # Get document
    doc_result = await session.execute(
        select(Document)
        .options(selectinload(Document.versions))
        .where(
            and_(
                Document.id == share.document_id,
                Document.deleted_at.is_(None)
            )
        )
    )
    doc = doc_result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Get latest version for preview URL
    from ..services.storage import generate_presigned_download_url, get_proxy_download_url_for_doc
    from fastapi import Request as FastAPIRequest
    
    # Get request from context (for share links, we don't have http_request parameter)
    # In dev mode, we'll use a fallback URL
    latest_version = max(doc.versions, key=lambda v: v.version_no) if doc.versions else None
    preview_url = None
    if latest_version and latest_version.blob_uri:
        blob_uri = latest_version.blob_uri
        if blob_uri.startswith(f"minio://{settings.minio_bucket}/"):
            blob_uri = blob_uri.replace(f"minio://{settings.minio_bucket}/", "")
        # In dev mode, use proxy endpoint (fallback to localhost:8000 if no request)
        if settings.debug:
            base_url = str(http_request.base_url).rstrip('/') if http_request else "http://localhost:8000"
            preview_url = get_proxy_download_url_for_doc(blob_uri, doc.id, base_url)
        else:
            preview_url = generate_presigned_download_url(blob_uri, expires=timedelta(hours=1))
    
    # Return document info (read-only access via share link)
    share_permissions = share.permissions
    if isinstance(share_permissions, dict):
        permissions_list = share_permissions.get("permissions", [])
    elif isinstance(share_permissions, list):
        permissions_list = share_permissions
    else:
        permissions_list = []
    
    return success_response({
        "id": doc.id,
        "title": doc.title,
        "mime": doc.mime,
        "size": doc.size,
        "status": doc.status,
        "created_at": doc.created_at.isoformat(),
        "preview_url": preview_url,
        "share_token": share_token,
        "access_type": "shared_link",
        "permissions": permissions_list
    })

