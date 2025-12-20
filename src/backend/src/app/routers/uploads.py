import hashlib
import uuid
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..dependencies import get_current_user, require_permission
from ..models.users import User
from ..models.documents import Document, DocumentVersion, Tag, DocumentTag, Share
from ..models.workflows import Workflow
from ..models.roles import Role
from ..services.storage import generate_presigned_upload_url, get_file_bytes_from_minio
from ..services.metadata_service import MetadataService
from ..utils.response import success_response, error_response
from ..config import settings, get_ocr_provider_from_db
from ..services.settings_service import SettingsService
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
    allowed_users: Optional[list[int]] = None  # User IDs to share with
    allowed_roles: Optional[list[int]] = None  # Role IDs to share with (changed from list[str] to list[int])
    share_permissions: Optional[list[str]] = None  # Permissions: view, search, chat
    auto_ai_tag: Optional[bool] = True  # Enable auto AI tag generation (default: True)


@router.post("/init")
async def init_upload(
    request: UploadInitRequest,
    http_request: Request,
    current_user: User = Depends(require_permission("upload")),
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
    
    # In dev mode, use proxy endpoint instead of presigned URL to avoid hostname/CORS issues
    if settings.debug:
        # Return full proxy endpoint URL using request base URL
        base_url = str(http_request.base_url).rstrip('/')
        upload_url = f"{base_url}/api/v1/uploads/{upload_id}/proxy"
    else:
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
    http_request: Request,
    current_user: User = Depends(require_permission("upload")),
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
    
    # Extract file metadata from uploaded file
    file_metadata = None
    try:
        # Download file from MinIO to extract metadata
        file_bytes = await get_file_bytes_from_minio(metadata["object_name"])
        if file_bytes:
            # Get upload IP and user agent
            upload_ip = http_request.client.host if http_request.client else None
            upload_user_agent = http_request.headers.get("user-agent")
            
            # Extract comprehensive metadata
            file_metadata = await MetadataService.extract_file_metadata(
                mime=metadata["mime"],
                file_bytes=file_bytes,
                filename=metadata["filename"],
                checksum=metadata.get("checksum"),
                upload_method="web",
                upload_ip=upload_ip,
                upload_user_agent=upload_user_agent
            )
    except Exception as e:
        logger.warning(f"Failed to extract file metadata: {e}", exc_info=True)
        # Continue without metadata if extraction fails
    
    # Prepare metadata snapshot (user-provided metadata)
    metadata_snapshot = {
        "title": request.title or metadata["filename"],
        "tags": request.tags,
        "folder_id": request.folder_id,
        "retention_policy_id": request.retention_policy_id,
        "sensitivity": request.sensitivity,
        "auto_ai_tag": request.auto_ai_tag if request.auto_ai_tag is not None else True
    }
    
    # Merge file metadata into snapshot if available
    if file_metadata:
        metadata_snapshot["file_metadata"] = file_metadata
    
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
        sensitivity=request.sensitivity,
        file_metadata=file_metadata  # Store comprehensive metadata in Document
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
    # Create text extraction job for office/text files
    from ..models.ai import AIJob
    mime = metadata["mime"]
    
    if mime.startswith("image/") or mime == "application/pdf":
        # Create OCR job for images and PDFs
        auto_ai_tag_flag = request.auto_ai_tag if request.auto_ai_tag is not None else True
        # Get OCR provider from settings
        ocr_provider = await SettingsService.get_setting("ocr.provider", default="tesseract", session=session)
        ocr_job = AIJob(
            job_type="ocr",
            target={
                "document_id": doc.id,
                "version_id": version.id,
                "auto_ai_tag": auto_ai_tag_flag
            },
            provider=ocr_provider,
            status="queued"
        )
        session.add(ocr_job)
        await session.flush()
        
        # Job will be automatically processed by OCR worker service (Docker)
        # The worker will claim and process this job using SELECT FOR UPDATE SKIP LOCKED
    elif mime in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX
        "text/csv",
        "application/csv",
        "text/plain"
    ]:
        # Create text extraction job for office/text files
        auto_ai_tag_flag = request.auto_ai_tag if request.auto_ai_tag is not None else True
        text_extract_job = AIJob(
            job_type="text_extract",
            target={
                "document_id": doc.id,
                "version_id": version.id,
                "auto_ai_tag": auto_ai_tag_flag
            },
            provider="native",
            status="queued"
        )
        session.add(text_extract_job)
        await session.flush()
        
        # Job will be automatically processed by worker service
    
    # Get share permissions (default to ["view"] if not provided)
    share_permissions = request.share_permissions or ["view"]
    # Ensure view is always included
    if "view" not in share_permissions:
        share_permissions = ["view"] + share_permissions
    
    # Create shares for allowed users and roles
    if request.allowed_users:
        for user_id in request.allowed_users:
            # Verify user exists
            user_result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                share = Share(
                    document_id=doc.id,
                    target_type="user",
                    target_id=user_id,
                    permissions=share_permissions
                )
                session.add(share)
    
    if request.allowed_roles:
        for role_identifier in request.allowed_roles:
            if not role_identifier:
                continue
            
            # Handle both role ID (int) and role name (str)
            role_name = None
            if isinstance(role_identifier, int):
                # If it's an ID, look up the role name
                role_result = await session.execute(
                    select(Role).where(Role.id == role_identifier)
                )
                role = role_result.scalar_one_or_none()
                if role:
                    role_name = role.name
            elif isinstance(role_identifier, str) and role_identifier.strip():
                # If it's already a name, use it directly
                role_name = role_identifier.strip()
            
            if role_name:
                # Create share with role
                share = Share(
                    document_id=doc.id,
                    target_type="role",
                    target_id=0,
                    permissions={
                        "role_name": role_name,
                        "permissions": share_permissions
                    }
                )
                session.add(share)
    
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


@router.put("/{upload_id}/proxy")
async def proxy_upload(
    upload_id: str,
    request: Request,
    current_user: User = Depends(require_permission("upload")),
    session: AsyncSession = Depends(get_session)
):
    """Proxy upload endpoint for dev mode - uploads file through backend to MinIO."""
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
    
    # Read file data from request
    file_data = await request.body()
    
    # Upload to MinIO via backend
    from ..services.storage import upload_file_to_minio
    success = await upload_file_to_minio(
        file_data=file_data,
        object_name=metadata["object_name"],
        content_type=metadata["mime"]
    )
    
    if not success:
        return error_response(
            "Failed to upload file to storage",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return success_response({
        "upload_id": upload_id,
        "status": "uploaded"
    })



