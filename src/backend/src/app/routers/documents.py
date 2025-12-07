from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from ..db import get_session
from ..dependencies import get_current_user, get_current_admin_user
from ..models.users import User
from ..models.documents import Document, DocumentVersion, Tag, DocumentTag
from ..services.storage import generate_presigned_download_url
from ..utils.response import success_response, error_response
from ..config import settings

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    tags: Optional[list[str]] = None
    folder_id: Optional[int] = None
    retention_policy_id: Optional[int] = None


@router.get("")
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    query = select(Document).where(
        and_(
            Document.owner_id == current_user.id,
            Document.deleted_at.is_(None)
        )
    )
    
    if search:
        query = query.where(Document.title.ilike(f"%{search}%"))
    
    query = query.offset(skip).limit(limit)
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
        "total": len(documents)
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
    
    await session.commit()
    
    return success_response({"id": doc.id, "title": doc.title})


@router.delete("/{doc_id}")
async def soft_delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Document).where(and_(Document.id == doc_id, Document.deleted_at.is_(None)))
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
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
    # TODO: Implement version diff
    return success_response({
        "content_diff": {},
        "metadata_diff": {},
        "acl_diff": {}
    })

