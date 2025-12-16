import hashlib
import uuid
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..dependencies import get_current_user
from ..models.users import User
from ..models.documents import Document, DocumentVersion, Tag, DocumentTag
from ..models.workflows import Workflow
from ..services.storage import generate_presigned_upload_url
from ..utils.response import success_response, error_response
from ..config import settings
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])

# Temporary storage for upload metadata (in production, use Redis)
_upload_metadata: Dict[str, dict] = {}


class UploadInitRequest(BaseModel):
    filename: str
    size: int
    mime: str
    checksum: Optional[str] = None


class UploadFinalizeRequest(BaseModel):
    title: Optional[str] = None
    tags: list[str] = []
    folder_id: Optional[int] = None
    retention_policy_id: Optional[int] = None
    sensitivity: Optional[str] = None
    workflow_template: Optional[str] = None
    workflow_assignees: Optional[list[int]] = None


@router.post("/init")
async def init_upload(
    request: UploadInitRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if request.size > settings.max_upload_size_bytes:
        return error_response(
            f"File size exceeds maximum {settings.max_upload_size_mb}MB",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    if request.mime not in settings.allowed_mime_list:
        return error_response(
            "File type not allowed",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    upload_id = str(uuid.uuid4())
    object_name = f"uploads/{current_user.id}/{upload_id}/{request.filename}"
    
    # Store upload metadata for finalize step
    _upload_metadata[upload_id] = {
        "filename": request.filename,
        "size": request.size,
        "mime": request.mime,
        "checksum": request.checksum,
        "user_id": current_user.id,
        "object_name": object_name
    }
    
    upload_url = generate_presigned_upload_url(object_name, expires=timedelta(hours=1))
    
    return success_response({
        "upload_id": upload_id,
        "upload_url": upload_url,
        "object_name": object_name
    })


@router.post("/{upload_id}/finalize")
async def finalize_upload(
    upload_id: str,
    request: UploadFinalizeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # Retrieve upload metadata
    metadata = _upload_metadata.get(upload_id)
    if not metadata:
        return error_response(
            "Upload not found or expired",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # Verify user owns this upload
    if metadata["user_id"] != current_user.id:
        return error_response(
            "Unauthorized",
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    # Validate folder_id if provided (basic validation - ensure it's positive)
    if request.folder_id is not None and request.folder_id <= 0:
        return error_response(
            "Invalid folder_id",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate retention_policy_id if provided (basic validation - ensure it's positive)
    if request.retention_policy_id is not None and request.retention_policy_id <= 0:
        return error_response(
            "Invalid retention_policy_id",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Prepare metadata snapshot
    metadata_snapshot = {
        "title": request.title or metadata["filename"],
        "tags": request.tags,
        "folder_id": request.folder_id,
        "retention_policy_id": request.retention_policy_id,
        "sensitivity": request.sensitivity
    }
    
    # Create document
    doc = Document(
        title=request.title or metadata["filename"],
        source="web",
        owner_id=current_user.id,
        mime=metadata["mime"],
        size=metadata["size"],
        checksum=metadata.get("checksum"),
        status="processing",
        folder_id=request.folder_id,
        retention_policy_id=request.retention_policy_id,
        sensitivity=request.sensitivity
    )
    session.add(doc)
    await session.flush()
    
    # Create version with metadata snapshot
    version = DocumentVersion(
        document_id=doc.id,
        version_no=1,
        blob_uri=metadata["object_name"],
        created_by=current_user.id,
        checksum=metadata.get("checksum"),
        size=metadata["size"],
        status="processing",
        metadata_snapshot=metadata_snapshot
    )
    session.add(version)
    await session.flush()
    
    # Handle tags: create if not exists and associate with document
    if request.tags:
        for tag_name in request.tags:
            if not tag_name.strip():
                continue
            # Check if tag exists
            result = await session.execute(
                select(Tag).where(Tag.name == tag_name.strip())
            )
            tag = result.scalar_one_or_none()
            
            if not tag:
                # Create new tag
                tag = Tag(name=tag_name.strip())
                session.add(tag)
                await session.flush()
            
            # Check if document_tag association already exists
            result = await session.execute(
                select(DocumentTag).where(
                    DocumentTag.document_id == doc.id,
                    DocumentTag.tag_id == tag.id
                )
            )
            doc_tag = result.scalar_one_or_none()
            
            if not doc_tag:
                # Create association
                doc_tag = DocumentTag(document_id=doc.id, tag_id=tag.id)
                session.add(doc_tag)
    
    # Create workflow if template is provided
    if request.workflow_template:
        workflow = Workflow(
            document_id=doc.id,
            template=request.workflow_template,
            state="pending",
            assignees=request.workflow_assignees or []
        )
        session.add(workflow)
        await session.flush()
    
    # Create OCR job if file type supports OCR
    from ..models.ai import AIJob
    if metadata["mime"].startswith("image/") or metadata["mime"] == "application/pdf":
        ocr_job = AIJob(
            job_type="ocr",
            target={"document_id": doc.id, "version_id": version.id},
            provider="paddle",
            status="queued"
        )
        session.add(ocr_job)
        await session.flush()
        
        # Trigger OCR processing immediately (worker will also pick it up if this fails)
        try:
            from ..workers.ocr_worker import process_ocr_job
            import asyncio
            # Run OCR immediately in background - don't wait for worker loop
            asyncio.create_task(process_ocr_job(ocr_job.id))
        except Exception as e:
            logger.error(f"Failed to trigger OCR job immediately: {e}")
            # Job will be processed by worker loop
    
    await session.commit()
    
    # Clean up metadata
    _upload_metadata.pop(upload_id, None)
    
    return success_response({
        "document_id": doc.id,
        "version_id": version.id
    })


@router.put("/{upload_id}/chunk")
async def upload_chunk(
    upload_id: str,
    chunk_number: int = Query(..., description="Chunk number"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Optional chunked upload endpoint."""
    # Check if upload exists
    metadata = _upload_metadata.get(upload_id)
    if not metadata:
        return error_response(
            "Upload not found or expired",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # Verify user owns this upload
    if metadata["user_id"] != current_user.id:
        return error_response(
            "Unauthorized",
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    # For now, just return success (chunked upload can be implemented later)
    # In production, this would handle chunk assembly
    return success_response({
        "upload_id": upload_id,
        "chunk_number": chunk_number,
        "status": "received"
    })



