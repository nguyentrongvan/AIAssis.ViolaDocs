from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from ..db import get_session
from ..dependencies import get_current_user, get_current_admin_user
from ..models.users import User
from ..models.ai import AIJob
from ..utils.response import success_response, error_response

router = APIRouter(prefix="/ai", tags=["ai"])


class OCRRequest(BaseModel):
    document_id: Optional[int] = None
    version_id: Optional[int] = None
    provider: Optional[str] = None


class EmbedRequest(BaseModel):
    document_id: Optional[int] = None
    version_id: Optional[int] = None
    provider: Optional[str] = None


@router.post("/ocr")
async def enqueue_ocr(
    request: OCRRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if not request.version_id and not request.document_id:
        return error_response("Either version_id or document_id required", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Create OCR job
    target = {}
    if request.version_id:
        target["version_id"] = request.version_id
    if request.document_id:
        target["document_id"] = request.document_id
    
    job = AIJob(
        job_type="ocr",
        target=target,
        provider=request.provider or "paddle",
        status="queued"
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    
    return success_response({
        "job_id": job.id,
        "status": job.status,
        "job_type": job.job_type
    })


@router.post("/embed")
async def enqueue_embedding(
    request: EmbedRequest,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    if not request.version_id and not request.document_id:
        return error_response("Either version_id or document_id required", status_code=status.HTTP_400_BAD_REQUEST)
    
    target = {}
    if request.version_id:
        target["version_id"] = request.version_id
    if request.document_id:
        target["document_id"] = request.document_id
    
    job = AIJob(
        job_type="embed",
        target=target,
        provider=request.provider or "openai",
        status="queued"
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    
    return success_response({
        "job_id": job.id,
        "status": job.status,
        "job_type": job.job_type
    })


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(AIJob).where(AIJob.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        return error_response("Job not found", status_code=status.HTTP_404_NOT_FOUND)
    
    return success_response({
        "id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "provider": job.provider,
        "error": job.error,
        "output_ref": job.output_ref,
        "created_at": job.created_at.isoformat()
    })


