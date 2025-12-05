import hashlib
import uuid
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..dependencies import get_current_user
from ..models.users import User
from ..models.documents import Document, DocumentVersion
from ..services.storage import generate_presigned_upload_url
from ..utils.response import success_response, error_response
from ..config import settings

router = APIRouter(prefix="/uploads", tags=["uploads"])


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
    workflow_template: Optional[str] = None


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
    # Create document
    doc = Document(
        title=request.title or "Untitled",
        source="web",
        owner_id=current_user.id,
        mime=request.mime,
        status="processing",
        created_at=datetime.utcnow()
    )
    session.add(doc)
    await session.flush()
    
    # Create version
    version = DocumentVersion(
        document_id=doc.id,
        version_no=1,
        blob_uri=f"minio://{settings.minio_bucket}/uploads/{current_user.id}/{upload_id}",
        created_by=current_user.id,
        created_at=datetime.utcnow(),
        status="processing"
    )
    session.add(version)
    await session.commit()
    
    # TODO: Enqueue OCR/AI processing job
    
    return success_response({
        "document_id": doc.id,
        "version_id": version.id
    })

