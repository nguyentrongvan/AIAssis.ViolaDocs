"""
OCR Worker Service - Standalone service for processing OCR jobs
Uses database polling with SELECT FOR UPDATE SKIP LOCKED for atomic job claiming
"""
import asyncio
import uuid
import signal
import sys
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_

from ..db import AsyncSessionLocal
from ..models.ai import AIJob
from ..models.documents import DocumentVersion, Document
from ..services.ai import get_ocr_service
from ..services.storage import get_minio_client
from ..services.settings_service import SettingsService
from ..config import settings


class OCRWorkerService:
    """OCR Worker Service with DB locking and settings integration"""
    
    def __init__(
        self,
        worker_id: Optional[str] = None,
        poll_interval: int = 2,
        max_concurrent: int = 2,
        heartbeat_interval: int = 30,
        stuck_job_timeout_minutes: int = 10
    ):
        self.worker_id = worker_id or f"ocr-worker-{uuid.uuid4().hex[:8]}"
        self.poll_interval = poll_interval
        self.max_concurrent = max_concurrent
        self.heartbeat_interval = heartbeat_interval
        self.stuck_job_timeout_minutes = stuck_job_timeout_minutes
        
        self.running = False
        self.active_tasks = set()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # OCR settings cache
        self._ocr_settings_cache: Optional[Dict[str, Any]] = None
        self._ocr_settings_cache_time: Optional[datetime] = None
        self._ocr_settings_cache_ttl = timedelta(seconds=300)  # 5 minutes
    
    async def get_ocr_settings_from_db(self) -> Dict[str, Any]:
        """Get OCR settings from DB with caching"""
        now = datetime.utcnow()
        
        # Check cache
        if (self._ocr_settings_cache is not None and 
            self._ocr_settings_cache_time is not None and
            now - self._ocr_settings_cache_time < self._ocr_settings_cache_ttl):
            return self._ocr_settings_cache
        
        # Cache miss or expired, fetch from DB
        return await self._fetch_ocr_settings_from_db()
    
    async def _fetch_ocr_settings_from_db(self) -> Dict[str, Any]:
        """Fetch OCR settings from DB (internal method)"""
        async with AsyncSessionLocal() as session:
            provider = await SettingsService.get_setting(
                "ocr.provider",
                settings.ocr_provider,
                session
            )
            languages_str = await SettingsService.get_setting(
                "ocr.languages",
                settings.ocr_languages,
                session
            )
            
            # Parse languages
            if isinstance(languages_str, list):
                languages = languages_str
            elif isinstance(languages_str, str):
                languages = [lang.strip() for lang in languages_str.split(",")]
            else:
                languages = settings.ocr_lang_list
            
            settings_dict = {
                "provider": provider or "paddle",
                "languages": languages
            }
            
            # Update cache
            self._ocr_settings_cache = settings_dict
            self._ocr_settings_cache_time = datetime.utcnow()
            
            return settings_dict
    
    async def refresh_ocr_settings(self):
        """Force refresh OCR settings from DB (bypass cache)"""
        self._ocr_settings_cache = None
        self._ocr_settings_cache_time = None
        settings = await self._fetch_ocr_settings_from_db()
        print(f"[{self.worker_id}] OCR settings refreshed: provider={settings['provider']}, languages={settings['languages']}")
        return settings
    
    async def _periodic_settings_refresh(self):
        """Refresh settings periodically (every 5 minutes)"""
        try:
            while self.running:
                await asyncio.sleep(300)  # 5 minutes
                if self.running:
                    await self.refresh_ocr_settings()
        except asyncio.CancelledError:
            pass
    
    async def claim_job(self, session: AsyncSession) -> Optional[AIJob]:
        """Atomically claim a queued job (OCR or EMBED) using SELECT FOR UPDATE SKIP LOCKED"""
        # First, release stuck jobs
        await self._release_stuck_jobs(session)
        
        # Check how many queued jobs exist (for debugging)
        ocr_count_result = await session.execute(
            select(AIJob)
            .where(
                and_(
                    AIJob.job_type == "ocr",
                    AIJob.status == "queued"
                )
            )
        )
        text_extract_count_result = await session.execute(
            select(AIJob)
            .where(
                and_(
                    AIJob.job_type == "text_extract",
                    AIJob.status == "queued"
                )
            )
        )
        embed_count_result = await session.execute(
            select(AIJob)
            .where(
                and_(
                    AIJob.job_type == "embed",
                    AIJob.status == "queued"
                )
            )
        )
        ocr_count = len(ocr_count_result.scalars().all())
        text_extract_count = len(text_extract_count_result.scalars().all())
        embed_count = len(embed_count_result.scalars().all())
        
        if ocr_count > 0 or text_extract_count > 0 or embed_count > 0:
            print(f"[{self.worker_id}] Found {ocr_count} OCR, {text_extract_count} TEXT_EXTRACT, and {embed_count} EMBED job(s) in queue")
        
        # Try to claim OCR job first (priority), then TEXT_EXTRACT, then EMBED job
        for job_type in ["ocr", "text_extract", "embed"]:
            result = await session.execute(
                select(AIJob)
                .where(
                    and_(
                        AIJob.job_type == job_type,
                        AIJob.status == "queued"
                    )
                )
                .order_by(AIJob.created_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            job = result.scalar_one_or_none()
            
            if job:
                job.claim(self.worker_id)
                await session.commit()
                print(f"[{self.worker_id}] Successfully claimed {job_type.upper()} job {job.id}")
                return job
        
        if ocr_count > 0 or text_extract_count > 0 or embed_count > 0:
            print(f"[{self.worker_id}] Could not claim job (may be locked by another worker)")
        
        return None
    
    async def _release_stuck_jobs(self, session: AsyncSession):
        """Release jobs that are stuck (claimed but no heartbeat) - both OCR and EMBED"""
        timeout = timedelta(minutes=self.stuck_job_timeout_minutes)
        cutoff_time = datetime.utcnow() - timeout
        
        # Find stuck jobs (OCR, TEXT_EXTRACT, and EMBED)
        result = await session.execute(
            select(AIJob)
            .where(
                and_(
                    AIJob.job_type.in_(["ocr", "text_extract", "embed"]),
                    AIJob.status == "processing",
                    or_(
                        AIJob.last_heartbeat < cutoff_time,
                        and_(
                            AIJob.claimed_at < cutoff_time,
                            AIJob.last_heartbeat.is_(None)
                        )
                    )
                )
            )
        )
        stuck_jobs = result.scalars().all()
        
        for job in stuck_jobs:
            print(f"Releasing stuck job {job.id} (claimed by {job.worker_id})")
            job.release()
            job.status = "queued"  # Reset to queued for retry
            if job.can_retry():
                job.increment_retry()
            else:
                job.status = "failed"
                job.error = "Job stuck and max retries exceeded"
        
        if stuck_jobs:
            await session.commit()
    
    async def update_heartbeat(self, job_id: int):
        """Update heartbeat for a job"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AIJob).where(AIJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if job and job.worker_id == self.worker_id:
                job.update_heartbeat()
                await session.commit()
    
    async def process_ocr_job(self, job: AIJob):
        """Process a single OCR job"""
        async with self.semaphore:
            try:
                # Update heartbeat periodically during processing
                heartbeat_task = asyncio.create_task(
                    self._heartbeat_loop(job.id)
                )
                
                async with AsyncSessionLocal() as session:
                    # Refresh job to get latest state
                    result = await session.execute(
                        select(AIJob).where(AIJob.id == job.id)
                    )
                    job = result.scalar_one_or_none()
                    
                    if not job or job.status != "processing" or job.worker_id != self.worker_id:
                        heartbeat_task.cancel()
                        return
                    
                    # Get OCR settings from DB
                    ocr_settings = await self.get_ocr_settings_from_db()
                    provider_name = ocr_settings["provider"]
                    languages = ocr_settings["languages"]
                    
                    # Get document version
                    target = job.target
                    version_id = target.get("version_id")
                    
                    if not version_id:
                        raise ValueError("No version_id in target")
                    
                    result = await session.execute(
                        select(DocumentVersion).where(DocumentVersion.id == version_id)
                    )
                    version = result.scalar_one_or_none()
                    
                    if not version:
                        raise ValueError(f"Version {version_id} not found")
                    
                    # Download file from MinIO
                    minio_client = get_minio_client()
                    object_name = version.blob_uri
                    if object_name.startswith(f"minio://{settings.minio_bucket}/"):
                        object_name = object_name.replace(f"minio://{settings.minio_bucket}/", "")
                    
                    try:
                        file_data = minio_client.get_object(settings.minio_bucket, object_name)
                        file_bytes = file_data.read()
                        file_data.close()
                        file_data.release_conn()
                    except Exception as e:
                        raise ValueError(f"Failed to download file: {e}")
                    
                    # Get document to access mime type
                    doc_result = await session.execute(
                        select(Document).where(Document.id == version.document_id)
                    )
                    document = doc_result.scalar_one_or_none()
                    if not document:
                        raise ValueError(f"Document {version.document_id} not found")
                    mime = document.mime
                    
                    # Initialize OCR service - only Tesseract is supported
                    from ..services.ai.ocr_service import OcrService, TesseractOcrProvider
                    
                    ocr_provider = TesseractOcrProvider()
                    if ocr_provider.ocr is None:
                        raise ValueError("Tesseract OCR not available. Please install Tesseract OCR engine.")
                    
                    ocr_service = OcrService(provider=ocr_provider)
                    
                    # Track processing time
                    import time
                    processing_start = time.time()
                    
                    # Process OCR
                    if mime.startswith("image/"):
                        ocr_result = await ocr_service.process_image_async(file_bytes, languages)
                    elif mime == "application/pdf":
                        ocr_result = await ocr_service.process_pdf_async(file_bytes, languages)
                    else:
                        raise ValueError(f"Unsupported MIME type for OCR: {mime}")
                    
                    processing_time_ms = int((time.time() - processing_start) * 1000)
                    
                    if ocr_result.get("error"):
                        raise ValueError(ocr_result["error"])
                    
                    extracted_text = ocr_result.get("text", "")
                    
                    # Save extracted text to MinIO
                    text_object_name = f"renditions/{document.id}/{version_id}/text.txt"
                    from io import BytesIO
                    text_bytes = extracted_text.encode('utf-8')
                    try:
                        minio_client.put_object(
                            settings.minio_bucket,
                            text_object_name,
                            BytesIO(text_bytes),
                            length=len(text_bytes),
                            content_type="text/plain"
                        )
                    except Exception as e:
                        raise ValueError(f"Failed to save OCR text: {e}")
                    
                    # Update version with OCR URI
                    version.text_uri = text_object_name
                    version.ocr_uri = text_object_name
                    version.provider_info = {
                        "ocr": {
                            "provider": ocr_result.get("provider", provider_name),
                            "languages": languages
                        }
                    }
                    
                    # Add processing metadata to metadata_snapshot
                    from ..services.metadata_service import MetadataService
                    processing_meta = MetadataService.extract_processing_metadata(
                        processing_result=ocr_result,
                        processing_time_ms=processing_time_ms
                    )
                    processing_meta["ocr_provider"] = ocr_result.get("provider", provider_name)
                    processing_meta["text_length"] = len(extracted_text)
                    
                    # Merge processing metadata into existing metadata_snapshot
                    if version.metadata_snapshot is None:
                        version.metadata_snapshot = {}
                    if "processing" not in version.metadata_snapshot:
                        version.metadata_snapshot["processing"] = {}
                    version.metadata_snapshot["processing"].update(processing_meta)
                    
                    # Update document status
                    document.status = "ready"
                    
                    # Update job
                    job.status = "completed"
                    job.output_ref = {
                        "text_uri": version.text_uri,
                        "text_length": len(extracted_text)
                    }
                    job.release()  # Clear worker tracking
                    
                    await session.commit()
                    
                    # Generate auto AI tags if enabled
                    try:
                        auto_ai_tag = job.target.get("auto_ai_tag", True)  # Default to True if not specified
                        print(f"[OCR Worker Service] Auto AI Tag enabled: {auto_ai_tag} for document {document.id}")
                        if auto_ai_tag:
                            from ..services.ai import get_llm_service
                            from ..models.documents import Tag, DocumentTag
                            
                            # Load tag settings
                            max_tags = await SettingsService.get_setting("auto_tag.max_tags", default=3, session=session)
                            max_length = await SettingsService.get_setting("auto_tag.max_length", default=50, session=session)
                            prefix = await SettingsService.get_setting("auto_tag.prefix", default="auto_tag:", session=session)
                            ocr_text_limit = await SettingsService.get_setting("auto_tag.ocr_text_limit", default=5000, session=session)
                            
                            print(f"[OCR Worker Service] Tag settings - max_tags: {max_tags}, max_length: {max_length}, prefix: {prefix}, ocr_text_limit: {ocr_text_limit}")
                            
                            # Truncate OCR text if needed
                            text_for_tagging = extracted_text
                            if len(text_for_tagging) > ocr_text_limit:
                                text_for_tagging = text_for_tagging[:ocr_text_limit]
                                print(f"[OCR Worker Service] OCR text truncated from {len(extracted_text)} to {len(text_for_tagging)} characters")
                            
                            # Generate tags using LLM
                            llm_service = get_llm_service()
                            if llm_service:
                                print(f"[OCR Worker Service] Calling LLM to generate tags...")
                                tag_names = await llm_service.generate_tags_async(
                                    content=text_for_tagging,
                                    max_tags=max_tags,
                                    max_length=max_length,
                                    filename=document.title,
                                    session=session
                                )
                                
                                print(f"[OCR Worker Service] LLM returned {len(tag_names) if tag_names else 0} tags: {tag_names}")
                                
                                if tag_names:
                                    created_tags = []
                                    # Apply prefix and length limits, then create tags
                                    for tag_name in tag_names:
                                        # Truncate tag name if needed
                                        if len(tag_name) > max_length:
                                            tag_name = tag_name[:max_length]
                                        
                                        # Apply prefix
                                        final_tag_name = f"{prefix}{tag_name}" if prefix else tag_name
                                        
                                        # Check if tag exists
                                        tag_result = await session.execute(
                                            select(Tag).where(Tag.name == final_tag_name)
                                        )
                                        tag = tag_result.scalar_one_or_none()
                                        
                                        if not tag:
                                            # Create new tag
                                            tag = Tag(name=final_tag_name)
                                            session.add(tag)
                                            await session.flush()
                                            print(f"[OCR Worker Service] Created new tag: {final_tag_name}")
                                        
                                        # Check if document_tag association already exists
                                        doc_tag_result = await session.execute(
                                            select(DocumentTag).where(
                                                DocumentTag.document_id == document.id,
                                                DocumentTag.tag_id == tag.id
                                            )
                                        )
                                        doc_tag = doc_tag_result.scalar_one_or_none()
                                        
                                        if not doc_tag:
                                            # Create association
                                            doc_tag = DocumentTag(document_id=document.id, tag_id=tag.id)
                                            session.add(doc_tag)
                                            created_tags.append(final_tag_name)
                                    
                                    await session.commit()
                                    print(f"[OCR Worker Service] Successfully created {len(created_tags)} tags for document {document.id}: {created_tags}")
                                else:
                                    print(f"[OCR Worker Service] No tags generated by LLM")
                            else:
                                print(f"[OCR Worker Service] LLM service not available, skipping tag generation")
                    except Exception as e:
                        # Log error but don't fail OCR job
                        import traceback
                        print(f"[OCR Worker Service] Error generating auto AI tags: {e}")
                        print(f"[OCR Worker Service] Traceback: {traceback.format_exc()}")
                    
                    # Trigger embedding job
                    try:
                        embed_job = AIJob(
                            job_type="embed",
                            target={"document_id": document.id, "version_id": version.id},
                            provider="ollama",
                            status="queued"
                        )
                        session.add(embed_job)
                        await session.commit()
                    except Exception as e:
                        print(f"Failed to create embedding job: {e}")
                
                heartbeat_task.cancel()
                
            except Exception as e:
                heartbeat_task.cancel()
                error_msg = str(e)[:500]
                print(f"OCR job {job.id} failed: {error_msg}")
                
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(AIJob).where(AIJob.id == job.id)
                    )
                    job = result.scalar_one_or_none()
                    if job:
                        if job.can_retry():
                            job.increment_retry()
                            job.release()
                            job.status = "queued"  # Retry
                        else:
                            job.status = "failed"
                            job.error = error_msg
                            job.release()
                        await session.commit()
    
    async def process_text_extract_job(self, job: AIJob):
        """Process a single text extraction job"""
        async with self.semaphore:
            try:
                # Update heartbeat periodically during processing
                heartbeat_task = asyncio.create_task(
                    self._heartbeat_loop(job.id)
                )
                
                async with AsyncSessionLocal() as session:
                    # Refresh job to get latest state
                    result = await session.execute(
                        select(AIJob).where(AIJob.id == job.id)
                    )
                    job = result.scalar_one_or_none()
                    
                    if not job or job.status != "processing" or job.worker_id != self.worker_id:
                        heartbeat_task.cancel()
                        return
                    
                    # Get document version
                    target = job.target
                    version_id = target.get("version_id")
                    
                    if not version_id:
                        raise ValueError("No version_id in target")
                    
                    result = await session.execute(
                        select(DocumentVersion).where(DocumentVersion.id == version_id)
                    )
                    version = result.scalar_one_or_none()
                    
                    if not version:
                        raise ValueError(f"Version {version_id} not found")
                    
                    # Download file from MinIO
                    minio_client = get_minio_client()
                    object_name = version.blob_uri
                    if object_name.startswith(f"minio://{settings.minio_bucket}/"):
                        object_name = object_name.replace(f"minio://{settings.minio_bucket}/", "")
                    
                    try:
                        file_data = minio_client.get_object(settings.minio_bucket, object_name)
                        file_bytes = file_data.read()
                        file_data.close()
                        file_data.release_conn()
                    except Exception as e:
                        raise ValueError(f"Failed to download file: {e}")
                    
                    # Get document to access mime type
                    doc_result = await session.execute(
                        select(Document).where(Document.id == version.document_id)
                    )
                    document = doc_result.scalar_one_or_none()
                    if not document:
                        raise ValueError(f"Document {version.document_id} not found")
                    mime = document.mime
                    
                    # Extract text using TextExtractionService
                    from ..services.text_extraction_service import TextExtractionService
                    
                    # Track processing time
                    import time
                    processing_start = time.time()
                    
                    extract_result = await TextExtractionService.extract_text(mime, file_bytes)
                    
                    processing_time_ms = int((time.time() - processing_start) * 1000)
                    
                    if extract_result.get("error"):
                        raise ValueError(extract_result["error"])
                    
                    extracted_text = extract_result.get("text", "")
                    
                    if not extracted_text:
                        raise ValueError("No text extracted from file")
                    
                    # Save extracted text to MinIO
                    text_object_name = f"renditions/{document.id}/{version_id}/text.txt"
                    from io import BytesIO
                    text_bytes = extracted_text.encode('utf-8')
                    try:
                        minio_client.put_object(
                            settings.minio_bucket,
                            text_object_name,
                            BytesIO(text_bytes),
                            length=len(text_bytes),
                            content_type="text/plain"
                        )
                    except Exception as e:
                        raise ValueError(f"Failed to save extracted text: {e}")
                    
                    # Update version with text URI
                    version.text_uri = text_object_name
                    version.provider_info = {
                        "text_extraction": {
                            "provider": "native",
                            "mime": mime
                        }
                    }
                    
                    # Add processing metadata to metadata_snapshot
                    from ..services.metadata_service import MetadataService
                    processing_meta = MetadataService.extract_processing_metadata(
                        processing_result=extract_result,
                        processing_time_ms=processing_time_ms
                    )
                    processing_meta["text_extraction_method"] = "native"
                    processing_meta["text_length"] = len(extracted_text)
                    
                    # Merge processing metadata into existing metadata_snapshot
                    if version.metadata_snapshot is None:
                        version.metadata_snapshot = {}
                    if "processing" not in version.metadata_snapshot:
                        version.metadata_snapshot["processing"] = {}
                    version.metadata_snapshot["processing"].update(processing_meta)
                    
                    # Update document status
                    document.status = "ready"
                    
                    # Update job
                    job.status = "completed"
                    job.output_ref = {
                        "text_uri": version.text_uri,
                        "text_length": len(extracted_text)
                    }
                    job.release()  # Clear worker tracking
                    
                    await session.commit()
                    
                    # Generate auto AI tags if enabled
                    try:
                        auto_ai_tag = job.target.get("auto_ai_tag", True)  # Default to True if not specified
                        print(f"[OCR Worker Service] Auto AI Tag enabled: {auto_ai_tag} for document {document.id} (text extract)")
                        if auto_ai_tag:
                            from ..services.ai import get_llm_service
                            from ..models.documents import Tag, DocumentTag
                            
                            # Load tag settings
                            max_tags = await SettingsService.get_setting("auto_tag.max_tags", default=3, session=session)
                            max_length = await SettingsService.get_setting("auto_tag.max_length", default=50, session=session)
                            prefix = await SettingsService.get_setting("auto_tag.prefix", default="auto_tag:", session=session)
                            ocr_text_limit = await SettingsService.get_setting("auto_tag.ocr_text_limit", default=5000, session=session)
                            
                            print(f"[OCR Worker Service] Tag settings - max_tags: {max_tags}, max_length: {max_length}, prefix: {prefix}, ocr_text_limit: {ocr_text_limit}")
                            
                            # Truncate extracted text if needed
                            text_for_tagging = extracted_text
                            if len(text_for_tagging) > ocr_text_limit:
                                text_for_tagging = text_for_tagging[:ocr_text_limit]
                                print(f"[OCR Worker Service] Text truncated from {len(extracted_text)} to {len(text_for_tagging)} characters")
                            
                            # Generate tags using LLM
                            llm_service = get_llm_service()
                            if llm_service:
                                print(f"[OCR Worker Service] Calling LLM to generate tags (text extract)...")
                                tag_names = await llm_service.generate_tags_async(
                                    content=text_for_tagging,
                                    max_tags=max_tags,
                                    max_length=max_length,
                                    filename=document.title,
                                    session=session
                                )
                                
                                print(f"[OCR Worker Service] LLM returned {len(tag_names) if tag_names else 0} tags: {tag_names}")
                                
                                if tag_names:
                                    created_tags = []
                                    # Apply prefix and length limits, then create tags
                                    for tag_name in tag_names:
                                        # Truncate tag name if needed
                                        if len(tag_name) > max_length:
                                            tag_name = tag_name[:max_length]
                                        
                                        # Apply prefix
                                        final_tag_name = f"{prefix}{tag_name}" if prefix else tag_name
                                        
                                        # Check if tag exists
                                        tag_result = await session.execute(
                                            select(Tag).where(Tag.name == final_tag_name)
                                        )
                                        tag = tag_result.scalar_one_or_none()
                                        
                                        if not tag:
                                            # Create new tag
                                            tag = Tag(name=final_tag_name)
                                            session.add(tag)
                                            await session.flush()
                                            print(f"[OCR Worker Service] Created new tag: {final_tag_name}")
                                        
                                        # Check if document_tag association already exists
                                        doc_tag_result = await session.execute(
                                            select(DocumentTag).where(
                                                DocumentTag.document_id == document.id,
                                                DocumentTag.tag_id == tag.id
                                            )
                                        )
                                        doc_tag = doc_tag_result.scalar_one_or_none()
                                        
                                        if not doc_tag:
                                            # Create association
                                            doc_tag = DocumentTag(document_id=document.id, tag_id=tag.id)
                                            session.add(doc_tag)
                                            created_tags.append(final_tag_name)
                                    
                                    await session.commit()
                                    print(f"[OCR Worker Service] Successfully created {len(created_tags)} tags for document {document.id}: {created_tags}")
                                else:
                                    print(f"[OCR Worker Service] No tags generated by LLM")
                            else:
                                print(f"[OCR Worker Service] LLM service not available, skipping tag generation")
                    except Exception as e:
                        # Log error but don't fail text extraction job
                        import traceback
                        print(f"[OCR Worker Service] Error generating auto AI tags: {e}")
                        print(f"[OCR Worker Service] Traceback: {traceback.format_exc()}")
                    
                    # Trigger embedding job
                    try:
                        embed_job = AIJob(
                            job_type="embed",
                            target={"document_id": document.id, "version_id": version.id},
                            provider="ollama",
                            status="queued"
                        )
                        session.add(embed_job)
                        await session.commit()
                    except Exception as e:
                        print(f"Failed to create embedding job: {e}")
                    
                    heartbeat_task.cancel()
                    print(f"[{self.worker_id}] Text extraction job {job.id} completed")
                
            except Exception as e:
                heartbeat_task.cancel()
                error_msg = str(e)[:500]
                print(f"Text extraction job {job.id} failed: {error_msg}")
                
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(AIJob).where(AIJob.id == job.id)
                    )
                    job = result.scalar_one_or_none()
                    if job:
                        if job.can_retry():
                            job.increment_retry()
                            job.release()
                            job.status = "queued"  # Retry
                        else:
                            job.status = "failed"
                            job.error = error_msg
                            job.release()
                        await session.commit()
    
    async def process_embedding_job(self, job: AIJob):
        """Process a single embedding job"""
        async with self.semaphore:
            try:
                # Update heartbeat periodically during processing
                heartbeat_task = asyncio.create_task(
                    self._heartbeat_loop(job.id)
                )
                
                async with AsyncSessionLocal() as session:
                    # Refresh job to get latest state
                    result = await session.execute(
                        select(AIJob).where(AIJob.id == job.id)
                    )
                    job = result.scalar_one_or_none()
                    
                    if not job or job.status != "processing" or job.worker_id != self.worker_id:
                        heartbeat_task.cancel()
                        return
                    
                    # Log job claimed
                    target = job.target
                    doc_id = target.get("document_id")
                    version_id = target.get("version_id")
                    print(f"[{self.worker_id}] Processing EMBED job {job.id}: doc_id={doc_id}, version_id={version_id}")
                    
                    from ..services.ai import get_embedding_service
                    from ..services.ai.embedding_service import EmbeddingModelUnavailableError
                    
                    # Initialize embedding service
                    print(f"[{self.worker_id}] Initializing embedding service...")
                    embedding_service = get_embedding_service()
                    
                    if not embedding_service:
                        raise ValueError("Embedding service could not be initialized")
                    
                    if not embedding_service.is_available():
                        diagnostic = embedding_service.get_availability_diagnostic()
                        raise ValueError(f"Embedding provider not available: {diagnostic}")
                    
                    # Log embedding service status
                    store_type = "Qdrant"
                    has_client = bool(embedding_service.store and embedding_service.store.client)
                    print(f"[{self.worker_id}] ✓ Embedding service ready (store_type={store_type}, has_client={has_client})")
                    
                    if not version_id:
                        raise ValueError("No version_id in target")
                    
                    result = await session.execute(
                        select(DocumentVersion).where(DocumentVersion.id == version_id)
                    )
                    version = result.scalar_one_or_none()
                    
                    if not version:
                        raise ValueError(f"Version {version_id} not found")
                    
                    # Get document for metadata
                    doc_result = await session.execute(
                        select(Document).where(Document.id == version.document_id)
                    )
                    document = doc_result.scalar_one_or_none()
                    
                    # Get text from OCR result
                    if not version.text_uri:
                        raise ValueError("No OCR text available for embedding")
                    
                    print(f"[{self.worker_id}] Retrieving OCR text from MinIO: {version.text_uri}")
                    minio_client = get_minio_client()
                    text_object_name = version.text_uri
                    if text_object_name.startswith(f"minio://{settings.minio_bucket}/"):
                        text_object_name = text_object_name.replace(f"minio://{settings.minio_bucket}/", "")
                    
                    try:
                        file_data = minio_client.get_object(settings.minio_bucket, text_object_name)
                        text = file_data.read().decode('utf-8')
                        file_data.close()
                        file_data.release_conn()
                        print(f"[{self.worker_id}] ✓ Text retrieved: {len(text)} characters")
                    except Exception as e:
                        raise ValueError(f"Failed to read OCR text: {e}")
                    
                    # Load RAG settings for chunking
                    from ..services.settings_service import SettingsService
                    chunk_size = await SettingsService.get_setting(
                        "rag_chunk_size",
                        default=1024,
                        session=session
                    )
                    chunk_overlap = await SettingsService.get_setting(
                        "rag_chunk_overlap",
                        default=100,
                        session=session
                    )
                    
                    # Chunk text
                    from ..utils.text_chunker import get_default_chunker
                    chunker = get_default_chunker()
                    chunks = chunker.chunk_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
                    print(f"[{self.worker_id}] ✓ Text chunked into {len(chunks)} chunks (chunk_size={chunk_size}, overlap={chunk_overlap})")
                    
                    # Generate embeddings for each chunk
                    print(f"[{self.worker_id}] Generating embeddings for {len(chunks)} chunks...")
                    try:
                        # Generate embeddings in batch if possible, otherwise one by one
                        chunk_texts = [chunk["text"] for chunk in chunks]
                        if hasattr(embedding_service, 'generate_embeddings_batch'):
                            embedding_vectors = embedding_service.generate_embeddings_batch(chunk_texts)
                        else:
                            # Fallback: generate one by one
                            embedding_vectors = []
                            for chunk_text in chunk_texts:
                                embedding_vector = embedding_service.generate_embedding(chunk_text)
                                embedding_vectors.append(embedding_vector)
                        
                        embedding_dim = len(embedding_vectors[0]) if embedding_vectors else 0
                        print(f"[{self.worker_id}] ✓ Generated {len(embedding_vectors)} embeddings: dimension={embedding_dim}")
                    except EmbeddingModelUnavailableError as e:
                        raise ValueError(f"Embedding model unavailable: {str(e)}")
                    
                    # Prepare IDs and metadatas for all chunks
                    embed_ids = []
                    metadatas_list = []
                    
                    for idx, (chunk, embedding_vector) in enumerate(zip(chunks, embedding_vectors)):
                        embed_id = f"embed-{job.id}-chunk-{idx}"
                        embed_ids.append(embed_id)
                        
                        metadata = {
                            "doc_id": version.document_id,
                            "version_id": version_id,
                            "chunk_index": idx,
                            "chunk_text": chunk["text"],
                            "start_pos": chunk["start_pos"],
                            "end_pos": chunk["end_pos"],
                            "token_count": chunk["token_count"],
                            "owner_id": document.owner_id if document else None,
                            "provider": job.provider,
                            "text_length": len(chunk["text"])
                        }
                        metadatas_list.append(metadata)
                    
                    # Get collection count before upsert
                    collection_count_before = 0
                    if embedding_service.store and embedding_service.store.client:
                        try:
                            collection_count_before = embedding_service.store.count()
                        except:
                            pass
                    
                    print(f"[{self.worker_id}] Upserting {len(embed_ids)} chunk embeddings to Qdrant (collection count before: {collection_count_before})...")
                    embedding_service.upsert_embeddings(
                        ids=embed_ids,
                        embeddings=embedding_vectors,
                        metadatas=metadatas_list
                    )
                    
                    # Verify collection count after upsert
                    collection_count_after = 0
                    if embedding_service.store and embedding_service.store.client:
                        try:
                            collection_count_after = embedding_service.store.count()
                            print(f"[{self.worker_id}] ✓ Upsert completed (collection count after: {collection_count_after})")
                            if collection_count_after <= collection_count_before:
                                print(f"[{self.worker_id}] WARNING: Collection count did not increase!")
                        except Exception as e:
                            print(f"[{self.worker_id}] Warning: Could not verify collection count after upsert: {e}")
                    
                    # Update job
                    job.status = "completed"
                    job.output_ref = {
                        "embedding_ids": embed_ids,
                        "chunk_count": len(chunks),
                        "vector_dimension": embedding_dim if embedding_vectors else 0
                    }
                    job.release()  # Clear worker tracking
                    
                    await session.commit()
                    print(f"[{self.worker_id}] ✓ EMBED job {job.id} completed successfully")
                
                heartbeat_task.cancel()
                
            except Exception as e:
                heartbeat_task.cancel()
                error_msg = str(e)[:500]
                import traceback
                print(f"[{self.worker_id}] ERROR: EMBED job {job.id} failed: {error_msg}")
                print(f"[{self.worker_id}] Traceback:")
                traceback.print_exc()
                
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(AIJob).where(AIJob.id == job.id)
                    )
                    job = result.scalar_one_or_none()
                    if job:
                        if job.can_retry():
                            job.increment_retry()
                            job.release()
                            job.status = "queued"  # Retry
                            print(f"[{self.worker_id}] Job {job.id} will be retried (attempt {job.retry_count})")
                        else:
                            job.status = "failed"
                            job.error = error_msg
                            job.release()
                            print(f"[{self.worker_id}] Job {job.id} marked as failed (max retries reached)")
                        await session.commit()
    
    async def _heartbeat_loop(self, job_id: int):
        """Update heartbeat for a job periodically"""
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                await self.update_heartbeat(job_id)
        except asyncio.CancelledError:
            pass
    
    async def worker_loop(self):
        """Main worker loop"""
        self.running = True
        print(f"[{self.worker_id}] OCR Worker started")
        print(f"[{self.worker_id}]   Poll interval: {self.poll_interval}s")
        print(f"[{self.worker_id}]   Max concurrent: {self.max_concurrent}")
        print(f"[{self.worker_id}]   Heartbeat interval: {self.heartbeat_interval}s")
        print(f"[{self.worker_id}]   Stuck timeout: {self.stuck_job_timeout_minutes} minutes")
        print(f"[{self.worker_id}] Starting worker loop...")
        
        # Load settings when worker starts
        print(f"[{self.worker_id}] Loading OCR settings...")
        try:
            initial_settings = await self.get_ocr_settings_from_db()
            print(f"[{self.worker_id}] OCR settings loaded: provider={initial_settings['provider']}, languages={initial_settings['languages']}")
        except Exception as e:
            print(f"[{self.worker_id}] ERROR: Failed to load OCR settings: {e}")
            import traceback
            traceback.print_exc()
            # Continue anyway, will use defaults
        
        # Start periodic settings refresh task
        settings_refresh_task = asyncio.create_task(self._periodic_settings_refresh())
        
        try:
            while self.running:
                try:
                    # Clean up completed tasks
                    completed = [task for task in self.active_tasks if task.done()]
                    for task in completed:
                        self.active_tasks.discard(task)
                        try:
                            await task
                        except Exception as e:
                            print(f"Task error: {e}")
                    
                    # Claim and process jobs
                    async with AsyncSessionLocal() as session:
                        job = await self.claim_job(session)
                        
                        if job:
                            if job.job_type == "ocr":
                                task = asyncio.create_task(self.process_ocr_job(job))
                            elif job.job_type == "text_extract":
                                task = asyncio.create_task(self.process_text_extract_job(job))
                            elif job.job_type == "embed":
                                task = asyncio.create_task(self.process_embedding_job(job))
                            else:
                                print(f"[{self.worker_id}] Unknown job type: {job.job_type}, skipping")
                                await asyncio.sleep(self.poll_interval)
                                continue
                            
                            self.active_tasks.add(task)
                            print(f"[{self.worker_id}] Claimed {job.job_type.upper()} job {job.id}")
                        else:
                            # No jobs, wait (log periodically to show worker is alive)
                            await asyncio.sleep(self.poll_interval)
                
                except Exception as e:
                    print(f"[{self.worker_id}] Error in worker loop: {e}")
                    import traceback
                    traceback.print_exc()
                    await asyncio.sleep(self.poll_interval)
        finally:
            # Cancel settings refresh task
            settings_refresh_task.cancel()
            try:
                await settings_refresh_task
            except asyncio.CancelledError:
                pass
        
        # Wait for active tasks to complete
        print("Waiting for active tasks to complete...")
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
        print(f"OCR Worker {self.worker_id} stopped")
    
    async def run(self):
        """Run the worker"""
        await self.worker_loop()

