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


