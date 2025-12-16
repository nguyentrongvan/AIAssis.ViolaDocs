from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime

from ..db import get_session
from ..dependencies import get_current_user, get_current_admin_user
from ..models.users import User
from ..models.ai import AIJob
from ..models.documents import Document, DocumentVersion
from ..services.ai import get_llm_service, get_embedding_service
from ..services.storage import get_minio_client
from ..config import settings
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


class ClassifyRequest(BaseModel):
    document_id: int
    provider: Optional[str] = None


class QARequest(BaseModel):
    document_id: int
    question: str
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
    current_user: User = Depends(get_current_user),
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


@router.post("/classify")
async def classify_document(
    request: ClassifyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Classify document using LLM."""
    # Get document
    result = await session.execute(select(Document).where(Document.id == request.document_id))
    document = result.scalar_one_or_none()
    
    if not document:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Get latest version
    version_result = await session.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_no.desc())
        .limit(1)
    )
    version = version_result.scalar_one_or_none()
    
    if not version or not version.text_uri:
        return error_response("Document text not available. Run OCR first.", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Get text content
    try:
        minio_client = get_minio_client()
        text_object_name = version.text_uri
        if text_object_name.startswith(f"minio://{settings.minio_bucket}/"):
            text_object_name = text_object_name.replace(f"minio://{settings.minio_bucket}/", "")
        
        file_data = minio_client.get_object(settings.minio_bucket, text_object_name)
        text_content = file_data.read().decode('utf-8')
        file_data.close()
        file_data.release_conn()
    except Exception as e:
        return error_response(f"Failed to read document text: {e}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Classify using LLM
    llm_service = get_llm_service()
    if not llm_service:
        return error_response("LLM provider not configured", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    classification = llm_service.classify_document(text_content)
    
    return success_response({
        "document_id": document.id,
        "classification": classification
    })


@router.post("/qa")
async def rag_qa(
    request: QARequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """RAG Q&A over document."""
    # Get document
    result = await session.execute(select(Document).where(Document.id == request.document_id))
    document = result.scalar_one_or_none()
    
    if not document:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Get latest version
    version_result = await session.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_no.desc())
        .limit(1)
    )
    version = version_result.scalar_one_or_none()
    
    if not version or not version.text_uri:
        return error_response("Document text not available. Run OCR first.", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Get text content
    try:
        minio_client = get_minio_client()
        text_object_name = version.text_uri
        if text_object_name.startswith(f"minio://{settings.minio_bucket}/"):
            text_object_name = text_object_name.replace(f"minio://{settings.minio_bucket}/", "")
        
        file_data = minio_client.get_object(settings.minio_bucket, text_object_name)
        text_content = file_data.read().decode('utf-8')
        file_data.close()
        file_data.release_conn()
    except Exception as e:
        return error_response(f"Failed to read document text: {e}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Use RAG Q&A
    llm_service = get_llm_service()
    if not llm_service:
        return error_response("LLM provider not configured", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    # Simple RAG: use document text as context
    answer = llm_service.rag_qa(request.question, [text_content])
    
    return success_response({
        "document_id": document.id,
        "question": request.question,
        "answer": answer
    })


@router.get("/jobs")
async def list_jobs(
    job_type: Optional[str] = Query(None, description="Filter by job type (ocr, embed, classify, qa)"),
    status_filter: Optional[str] = Query(None, description="Filter by status (queued, processing, completed, failed)"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """List AI jobs with filters (admin only)."""
    query = select(AIJob)
    
    if job_type:
        query = query.where(AIJob.job_type == job_type)
    if status_filter:
        query = query.where(AIJob.status == status_filter)
    if provider:
        query = query.where(AIJob.provider == provider)
    
    query = query.order_by(desc(AIJob.created_at)).limit(limit).offset(offset)
    
    result = await session.execute(query)
    jobs = result.scalars().all()
    
    # Get total count
    count_query = select(func.count(AIJob.id))
    if job_type:
        count_query = count_query.where(AIJob.job_type == job_type)
    if status_filter:
        count_query = count_query.where(AIJob.status == status_filter)
    if provider:
        count_query = count_query.where(AIJob.provider == provider)
    
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0
    
    return success_response({
        "jobs": [{
            "id": job.id,
            "job_type": job.job_type,
            "target": job.target,
            "provider": job.provider,
            "status": job.status,
            "input_ref": job.input_ref,
            "output_ref": job.output_ref,
            "error": job.error,
            "worker_id": job.worker_id,
            "claimed_at": job.claimed_at.isoformat() if job.claimed_at else None,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None
        } for job in jobs],
        "total": total,
        "limit": limit,
        "offset": offset
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
        "worker_id": job.worker_id,
        "claimed_at": job.claimed_at.isoformat() if job.claimed_at else None,
        "retry_count": job.retry_count,
        "max_retries": job.max_retries,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat() if job.updated_at else None
    })


class ReprocessRequest(BaseModel):
    provider: Optional[str] = None  # Optional: change provider for reprocessing


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Cancel a job (admin only)"""
    result = await session.execute(select(AIJob).where(AIJob.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        return error_response("Job not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if job.status not in ["queued", "processing"]:
        return error_response(
            f"Cannot cancel job with status '{job.status}'. Only queued or processing jobs can be cancelled.",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Release worker lock if processing
    if job.status == "processing":
        job.release()
    
    job.status = "cancelled"
    await session.commit()
    
    return success_response({
        "id": job.id,
        "status": job.status,
        "message": "Job cancelled successfully"
    })


@router.post("/jobs/{job_id}/reprocess")
async def reprocess_job(
    job_id: int,
    request: Optional[ReprocessRequest] = None,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Reprocess a failed or completed job (admin only)"""
    result = await session.execute(select(AIJob).where(AIJob.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        return error_response("Job not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if job.status not in ["failed", "completed", "cancelled"]:
        return error_response(
            f"Cannot reprocess job with status '{job.status}'. Only failed, completed, or cancelled jobs can be reprocessed.",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Reset job
    job.status = "queued"
    job.error = None
    job.retry_count = 0
    job.release()  # Clear worker tracking
    
    # Update provider if specified
    if request and request.provider:
        job.provider = request.provider
    
    await session.commit()
    
    return success_response({
        "id": job.id,
        "status": job.status,
        "provider": job.provider,
        "message": "Job queued for reprocessing"
    })


class BatchCancelRequest(BaseModel):
    job_ids: list[int]
    status_filter: Optional[str] = None
    job_type: Optional[str] = None


class BatchReprocessRequest(BaseModel):
    job_ids: list[int]
    provider: Optional[str] = None


@router.post("/jobs/batch-cancel")
async def batch_cancel_jobs(
    request: BatchCancelRequest,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Cancel multiple jobs (admin only)"""
    query = select(AIJob).where(AIJob.id.in_(request.job_ids))
    
    if request.status_filter:
        query = query.where(AIJob.status == request.status_filter)
    if request.job_type:
        query = query.where(AIJob.job_type == request.job_type)
    
    result = await session.execute(query)
    jobs = result.scalars().all()
    
    cancelled_count = 0
    for job in jobs:
        if job.status in ["queued", "processing"]:
            if job.status == "processing":
                job.release()
            job.status = "cancelled"
            cancelled_count += 1
    
    await session.commit()
    
    return success_response({
        "cancelled_count": cancelled_count,
        "total_requested": len(request.job_ids),
        "message": f"Cancelled {cancelled_count} job(s)"
    })


@router.post("/jobs/batch-reprocess")
async def batch_reprocess_jobs(
    request: BatchReprocessRequest,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Reprocess multiple jobs (admin only)"""
    result = await session.execute(
        select(AIJob).where(AIJob.id.in_(request.job_ids))
    )
    jobs = result.scalars().all()
    
    reprocessed_count = 0
    for job in jobs:
        if job.status in ["failed", "completed", "cancelled"]:
            job.status = "queued"
            job.error = None
            job.retry_count = 0
            job.release()
            
            if request.provider:
                job.provider = request.provider
            
            reprocessed_count += 1
    
    await session.commit()
    
    return success_response({
        "reprocessed_count": reprocessed_count,
        "total_requested": len(request.job_ids),
        "message": f"Queued {reprocessed_count} job(s) for reprocessing"
    })


