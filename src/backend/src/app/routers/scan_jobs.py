import uuid
from typing import Optional, Dict
from datetime import timedelta
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_session
from ..dependencies import get_current_user, get_current_admin_user
from ..models.users import User
from ..models.devices import Device
from ..models.documents import Document, DocumentVersion
from ..models.ai import AIJob
from ..services.storage import generate_presigned_upload_url
from ..services.auth import decode_token
from ..utils.response import success_response, error_response

router = APIRouter(prefix="/scan-jobs", tags=["scan-jobs"])

# Temporary storage for scan jobs (in production, use Redis or DB)
_scan_jobs: Dict[str, dict] = {}


class ScanJobRequest(BaseModel):
    device_id: int
    device_token: str
    user_id: int
    mailbox: Optional[str] = None
    filename: str
    metadata: Optional[dict] = None


class ScanJobFinalizeRequest(BaseModel):
    metadata: Optional[dict] = None


@router.post("")
async def create_scan_job(
    request: ScanJobRequest,
    session: AsyncSession = Depends(get_session)
):
    """Create scan job from device."""
    # Verify device token
    payload = decode_token(request.device_token)
    if not payload or payload.get("type") != "device" or payload.get("device_id") != request.device_id:
        return error_response(
            "Invalid device token",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Verify device exists
    result = await session.execute(select(Device).where(Device.id == request.device_id))
    device = result.scalar_one_or_none()
    if not device:
        return error_response(
            "Device not found",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # Create scan job
    job_id = str(uuid.uuid4())
    object_name = f"scans/{request.device_id}/{job_id}/{request.filename}"
    
    _scan_jobs[job_id] = {
        "device_id": request.device_id,
        "user_id": request.user_id,
        "mailbox": request.mailbox,
        "filename": request.filename,
        "metadata": request.metadata or {},
        "object_name": object_name,
        "status": "pending"
    }
    
    upload_url = generate_presigned_upload_url(object_name, expires=timedelta(hours=1))
    
    return success_response({
        "job_id": job_id,
        "upload_url": upload_url,
        "object_name": object_name
    })


@router.post("/{job_id}/finalize")
async def finalize_scan_job(
    job_id: str,
    request: ScanJobFinalizeRequest,
    session: AsyncSession = Depends(get_session)
):
    """Finalize scan job."""
    job = _scan_jobs.get(job_id)
    if not job:
        return error_response(
            "Scan job not found",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # Update metadata if provided
    if request.metadata:
        job["metadata"].update(request.metadata)
    
    # Get user
    result = await session.execute(select(User).where(User.id == job["user_id"]))
    user = result.scalar_one_or_none()
    if not user:
        return error_response(
            "User not found",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # Create document from scan
    doc = Document(
        title=job["metadata"].get("title", job["filename"]),
        source="scan",
        device_id=job["device_id"],
        owner_id=job["user_id"],
        mime=job["metadata"].get("mime", "application/pdf"),
        size=job["metadata"].get("size", 0),
        checksum=job["metadata"].get("checksum"),
        status="processing"
    )
    session.add(doc)
    await session.flush()
    
    # Create version
    version = DocumentVersion(
        document_id=doc.id,
        version_no=1,
        blob_uri=job["object_name"],
        created_by=job["user_id"],
        device_id=job["device_id"],
        job_id=job_id,
        checksum=job["metadata"].get("checksum"),
        size=job["metadata"].get("size", 0),
        status="processing",
        metadata_snapshot=job["metadata"]
    )
    session.add(version)
    await session.flush()
    
    # Create OCR job
    if doc.mime.startswith("image/") or doc.mime == "application/pdf":
        ocr_job = AIJob(
            job_type="ocr",
            target={"document_id": doc.id, "version_id": version.id},
            provider="paddle",
            status="queued"
        )
        session.add(ocr_job)
        await session.flush()
    
    await session.commit()
    
    # Update job status
    job["status"] = "completed"
    
    return success_response({
        "document_id": doc.id,
        "version_id": version.id
    })


@router.get("/pending")
async def get_pending_scan_jobs(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Get pending scan jobs (for devices)."""
    pending_jobs = [
        {
            "job_id": job_id,
            "device_id": job["device_id"],
            "user_id": job["user_id"],
            "filename": job["filename"],
            "status": job["status"]
        }
        for job_id, job in _scan_jobs.items()
        if job["status"] == "pending"
    ]
    
    return success_response({
        "pending_jobs": pending_jobs
    })

