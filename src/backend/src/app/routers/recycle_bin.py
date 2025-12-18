"""
Recycle Bin Router
Manages deleted documents (soft-deleted documents before permanent purge)
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from sqlalchemy.orm import selectinload

from ..db import get_session
from ..dependencies import get_current_user, get_current_admin_user, require_permission
from ..models.users import User
from ..models.documents import Document, DocumentVersion, Tag, DocumentTag
from ..services.storage import generate_presigned_download_url
from ..utils.response import success_response, error_response
from ..config import settings


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


router = APIRouter(prefix="/recycle-bin", tags=["recycle-bin"])


@router.get("")
async def list_deleted_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(require_permission("delete")),
    session: AsyncSession = Depends(get_session)
):
    """Get list of deleted documents for current user"""
    # Base query - only deleted documents
    conditions = [
        Document.owner_id == current_user.id,
        Document.deleted_at.isnot(None)
    ]
    
    # Admin can see all deleted documents
    if current_user.role == "admin":
        conditions = [Document.deleted_at.isnot(None)]
    
    base_query = select(Document).where(and_(*conditions))
    
    if search:
        base_query = base_query.where(Document.title.ilike(f"%{search}%"))
    
    # Sort by deleted_at DESC (newest deleted first)
    base_query = base_query.order_by(Document.deleted_at.desc())
    
    # Get total count
    count_query = select(func.count(Document.id)).where(and_(*conditions))
    if search:
        count_query = count_query.where(Document.title.ilike(f"%{search}%"))
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated results
    query = base_query.options(selectinload(Document.versions)).offset(skip).limit(limit)
    result = await session.execute(query)
    documents = result.scalars().all()
    
    # Load deleted_by user info
    deleted_by_user_ids = {doc.deleted_by for doc in documents if doc.deleted_by}
    deleted_by_users = {}
    if deleted_by_user_ids:
        users_result = await session.execute(
            select(User).where(User.id.in_(deleted_by_user_ids))
        )
        users = users_result.scalars().all()
        deleted_by_users = {user.id: user for user in users}
    
    items = []
    now = datetime.utcnow()
    
    for doc in documents:
        # Calculate days until purge
        # Use ceil to round up partial days (e.g., 1.5 days = 2 days)
        days_until_purge = None
        if doc.purge_at:
            delta = doc.purge_at - now
            if delta.total_seconds() > 0:
                # Calculate days with decimal precision, then round up
                # This ensures that even if there's 1 hour left, it shows as 1 day
                days_until_purge = max(0, int(delta.total_seconds() / 86400) + (1 if delta.total_seconds() % 86400 > 0 else 0))
            else:
                days_until_purge = 0
        
        # Get deleted_by user info
        deleted_by_info = None
        if doc.deleted_by and doc.deleted_by in deleted_by_users:
            user = deleted_by_users[doc.deleted_by]
            deleted_by_info = {
                "id": user.id,
                "name": user.name or user.email
            }
        
        item = {
            "id": doc.id,
            "title": doc.title,
            "mime": doc.mime,
            "size": doc.size,
            "status": doc.status,
            "created_at": doc.created_at.isoformat(),
            "deleted_at": doc.deleted_at.isoformat() if doc.deleted_at else None,
            "deleted_by": deleted_by_info,
            "purge_at": doc.purge_at.isoformat() if doc.purge_at else None,
            "days_until_purge": days_until_purge,
            "document_type": doc.mime.split('/')[0] if '/' in doc.mime else doc.mime,
            "file_extension": _get_file_extension_from_mime(doc.mime)  # Extract short extension from MIME type
        }
        
        # Get folder info
        if doc.folder_id:
            from ..models.documents import Folder
            folder_result = await session.execute(
                select(Folder).where(Folder.id == doc.folder_id)
            )
            folder = folder_result.scalar_one_or_none()
            item["folder"] = {"id": folder.id, "name": folder.name} if folder else None
        else:
            item["folder"] = None
        
        # Get tags
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
                    pass
        
        items.append(item)
    
    return success_response({
        "items": items,
        "total": total
    })


@router.post("/{doc_id}/restore")
async def restore_from_recycle_bin(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Restore a document from recycle bin"""
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
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error restoring document {doc_id}: {e}", exc_info=True)
        return error_response("Failed to restore document", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.delete("/{doc_id}/permanent")
async def delete_permanently(
    doc_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Permanently delete a document from recycle bin (admin only)"""
    from ..services.deletion_service import DocumentDeletionService
    
    try:
        # Admin only
        if current_user.role != "admin":
            return error_response("Access denied. Admin only.", status_code=status.HTTP_403_FORBIDDEN)
        
        # Hard delete using service (force=True bypasses purge_at check)
        await DocumentDeletionService.hard_delete_document(doc_id, current_user.id, session, force=True)
        
        return success_response({"id": doc_id, "permanently_deleted": True})
    except ValueError as e:
        return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error permanently deleting document {doc_id}: {e}", exc_info=True)
        return error_response("Failed to permanently delete document", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

