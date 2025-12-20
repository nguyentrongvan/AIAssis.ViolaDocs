import asyncio
import logging
import traceback
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import AsyncSessionLocal
from ..models.ai import AIJob
from ..models.documents import DocumentVersion, Document
from ..services.ai import get_ocr_service
from ..services.storage import get_minio_client
from ..config import settings

logger = logging.getLogger(__name__)


async def process_ocr_job(job_id: int):
    """Process a single OCR job"""
    async with AsyncSessionLocal() as session:
        # Get job
        result = await session.execute(select(AIJob).where(AIJob.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job or job.status != "queued":
            return
        
        # Update status
        job.status = "processing"
        await session.commit()
        
        try:
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
            # blob_uri is just the object_name, not full URI
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
            
            # Process with OCR service
            ocr_service = get_ocr_service()
            
            # Check if OCR provider is available
            if not ocr_service.provider:
                raise ValueError("OCR service provider not available")
            
            # Get document to access mime type
            doc_result = await session.execute(
                select(Document).where(Document.id == version.document_id)
            )
            document = doc_result.scalar_one_or_none()
            if not document:
                raise ValueError(f"Document {version.document_id} not found")
            mime = document.mime
            
            # Get languages from DB settings (async)
            from ..config import get_ocr_languages_from_db
            languages = await get_ocr_languages_from_db()
            
            # Track processing time
            import time
            processing_start = time.time()
            
            # Process OCR (use async methods to get latest settings)
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
            version.text_uri = text_object_name  # Store just object name
            version.ocr_uri = text_object_name  # Also set ocr_uri
            # Get provider from result or use tesseract as default
            provider_name = ocr_result.get("provider", "tesseract")
            version.provider_info = {
                "ocr": {
                    "provider": provider_name,
                    "languages": settings.ocr_lang_list
                }
            }
            
            # Add processing metadata to metadata_snapshot
            import time
            processing_time_ms = int((time.time() - processing_start) * 1000) if 'processing_start' in locals() else None
            from ..services.metadata_service import MetadataService
            processing_meta = MetadataService.extract_processing_metadata(
                processing_result=ocr_result,
                processing_time_ms=processing_time_ms
            )
            processing_meta["ocr_provider"] = provider_name
            processing_meta["text_length"] = len(extracted_text)
            
            # Merge processing metadata into existing metadata_snapshot
            if version.metadata_snapshot is None:
                version.metadata_snapshot = {}
            if "processing" not in version.metadata_snapshot:
                version.metadata_snapshot["processing"] = {}
            version.metadata_snapshot["processing"].update(processing_meta)

            # Update document status to ready after OCR
            document.status = "ready"
            
            # Update job
            job.status = "completed"
            job.output_ref = {
                "text_uri": version.text_uri,
                "text_length": len(extracted_text)
            }
            
            await session.commit()
            
            # Generate auto AI tags if enabled
            try:
                auto_ai_tag = job.target.get("auto_ai_tag", True)  # Default to True if not specified
                logger.debug(f"[OCR Worker] Auto AI Tag enabled: {auto_ai_tag} for document {document.id}")
                if auto_ai_tag:
                    from ..services.settings_service import SettingsService
                    from ..services.ai import get_llm_service
                    from ..models.documents import Tag, DocumentTag
                    
                    # Load tag settings
                    max_tags = await SettingsService.get_setting("auto_tag.max_tags", default=3, session=session)
                    max_length = await SettingsService.get_setting("auto_tag.max_length", default=50, session=session)
                    prefix = await SettingsService.get_setting("auto_tag.prefix", default="auto_tag:", session=session)
                    ocr_text_limit = await SettingsService.get_setting("auto_tag.ocr_text_limit", default=5000, session=session)
                    
                    logger.debug(f"[OCR Worker] Tag settings - max_tags: {max_tags}, max_length: {max_length}, prefix: {prefix}, ocr_text_limit: {ocr_text_limit}")
                    
                    # Truncate OCR text if needed
                    text_for_tagging = extracted_text
                    if len(text_for_tagging) > ocr_text_limit:
                        text_for_tagging = text_for_tagging[:ocr_text_limit]
                        logger.debug(f"[OCR Worker] OCR text truncated from {len(extracted_text)} to {len(text_for_tagging)} characters")
                    
                    # Generate tags using LLM
                    llm_service = get_llm_service()
                    if llm_service:
                        logger.debug(f"[OCR Worker] Calling LLM to generate tags...")
                        tag_names = await llm_service.generate_tags_async(
                            content=text_for_tagging,
                            max_tags=max_tags,
                            max_length=max_length,
                            filename=document.title,
                            session=session
                        )
                        
                        logger.debug(f"[OCR Worker] LLM returned {len(tag_names) if tag_names else 0} tags: {tag_names}")
                        
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
                                    logger.debug(f"[OCR Worker] Created new tag: {final_tag_name}")
                                
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
                            logger.info(f"[OCR Worker] Successfully created {len(created_tags)} tags for document {document.id}: {created_tags}")
                        else:
                            logger.debug(f"[OCR Worker] No tags generated by LLM")
                    else:
                        logger.debug(f"[OCR Worker] LLM service not available, skipping tag generation")
            except Exception as e:
                # Log error but don't fail OCR job
                logger.error(f"[OCR Worker] Error generating auto AI tags: {e}", exc_info=True)
            
            # Trigger embedding job after OCR completes
            try:
                from ..models.ai import AIJob as EmbeddingJob
                embed_job = EmbeddingJob(
                    job_type="embed",
                    target={"document_id": document.id, "version_id": version.id},
                    provider="ollama",
                    status="queued"
                )
                session.add(embed_job)
                await session.commit()
                
                # Process embedding immediately in background
                asyncio.create_task(process_embedding_job(embed_job.id))
            except Exception as e:
                pass
            
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            await session.commit()


async def process_embedding_job(job_id: int):
    """Process a single embedding job"""
    async with AsyncSessionLocal() as session:
        # Get job
        result = await session.execute(select(AIJob).where(AIJob.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job or job.status != "queued":
            return
        
        job.status = "processing"
        await session.commit()
        
        try:
            from ..services.ai import get_embedding_service
            from ..services.ai.embedding_service import EmbeddingModelUnavailableError
            
            embedding_service = get_embedding_service()
            if not embedding_service or not embedding_service.is_available():
                diagnostic = ""
                if embedding_service:
                    diagnostic = embedding_service.get_availability_diagnostic()
                else:
                    diagnostic = (
                        "Embedding service could not be initialized. "
                        f"Ollama base URL: {settings.ollama_base_url}, "
                        f"Model: {settings.ollama_embedding_model}"
                    )
                raise ValueError(
                    f"Embedding provider not configured or model not available. {diagnostic}"
                )
            
            # Get text from OCR result or document
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
            
            # Get document for metadata (owner, group, etc.)
            doc_result = await session.execute(
                select(Document).where(Document.id == version.document_id)
            )
            document = doc_result.scalar_one_or_none()
            
            # Get text from OCR result
            if not version.text_uri:
                raise ValueError("No OCR text")
            
            minio_client = get_minio_client()
            # text_uri is just object name, not full URI
            text_object_name = version.text_uri
            if text_object_name.startswith(f"minio://{settings.minio_bucket}/"):
                text_object_name = text_object_name.replace(f"minio://{settings.minio_bucket}/", "")
            
            try:
                file_data = minio_client.get_object(settings.minio_bucket, text_object_name)
                text = file_data.read().decode('utf-8')
                file_data.close()
                file_data.release_conn()
            except Exception as e:
                raise ValueError(f"Failed to read OCR text: {e}")
            
            # Generate embedding
            try:
                embedding_vector = embedding_service.generate_embedding(text)
            except EmbeddingModelUnavailableError as e:
                raise ValueError(f"Embedding model unavailable: {str(e)}")
            
            # Save embedding to vector store
            embed_id = f"embed-{job.id}"
            
            embedding_service.upsert_embeddings(
                ids=[embed_id],
                embeddings=[embedding_vector],
                metadatas=[{
                    "doc_id": version.document_id,
                    "version_id": version_id,
                    "owner_id": document.owner_id if document else None,
                    "provider": job.provider,
                    "text_length": len(text)
                }]
            )
            
            # Update job
            job.status = "completed"
            job.output_ref = {
                "embedding_id": embed_id,
                "vector_dimension": len(embedding_vector)
            }
            
            await session.commit()
            
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            await session.commit()
            logger.error(f"Embedding job {job_id} failed: {e}", exc_info=True)


async def process_text_extract_job(job_id: int):
    """Process a single text extraction job"""
    async with AsyncSessionLocal() as session:
        # Get job
        result = await session.execute(select(AIJob).where(AIJob.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job or job.status != "queued":
            return
        
        # Update status
        job.status = "processing"
        await session.commit()
        
        try:
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
            
            await session.commit()
            
            # Generate auto AI tags if enabled
            try:
                auto_ai_tag = job.target.get("auto_ai_tag", True)  # Default to True if not specified
                logger.debug(f"[Text Extract Worker] Auto AI Tag enabled: {auto_ai_tag} for document {document.id}")
                if auto_ai_tag:
                    from ..services.settings_service import SettingsService
                    from ..services.ai import get_llm_service
                    from ..models.documents import Tag, DocumentTag
                    
                    # Load tag settings
                    max_tags = await SettingsService.get_setting("auto_tag.max_tags", default=3, session=session)
                    max_length = await SettingsService.get_setting("auto_tag.max_length", default=50, session=session)
                    prefix = await SettingsService.get_setting("auto_tag.prefix", default="auto_tag:", session=session)
                    ocr_text_limit = await SettingsService.get_setting("auto_tag.ocr_text_limit", default=5000, session=session)
                    
                    logger.debug(f"[Text Extract Worker] Tag settings - max_tags: {max_tags}, max_length: {max_length}, prefix: {prefix}, ocr_text_limit: {ocr_text_limit}")
                    
                    # Truncate extracted text if needed
                    text_for_tagging = extracted_text
                    if len(text_for_tagging) > ocr_text_limit:
                        text_for_tagging = text_for_tagging[:ocr_text_limit]
                        logger.debug(f"[Text Extract Worker] Text truncated from {len(extracted_text)} to {len(text_for_tagging)} characters")
                    
                    # Generate tags using LLM
                    llm_service = get_llm_service()
                    if llm_service:
                        logger.debug(f"[Text Extract Worker] Calling LLM to generate tags...")
                        tag_names = await llm_service.generate_tags_async(
                            content=text_for_tagging,
                            max_tags=max_tags,
                            max_length=max_length,
                            filename=document.title,
                            session=session
                        )
                        
                        logger.debug(f"[Text Extract Worker] LLM returned {len(tag_names) if tag_names else 0} tags: {tag_names}")
                        
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
                                    logger.debug(f"[Text Extract Worker] Created new tag: {final_tag_name}")
                                
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
                            logger.info(f"[Text Extract Worker] Successfully created {len(created_tags)} tags for document {document.id}: {created_tags}")
                        else:
                            logger.debug(f"[Text Extract Worker] No tags generated by LLM")
                    else:
                        logger.debug(f"[Text Extract Worker] LLM service not available, skipping tag generation")
            except Exception as e:
                # Log error but don't fail text extraction job
                logger.error(f"[Text Extract Worker] Error generating auto AI tags: {e}", exc_info=True)
            
            # Trigger embedding job after text extraction completes
            try:
                from ..models.ai import AIJob as EmbeddingJob
                embed_job = EmbeddingJob(
                    job_type="embed",
                    target={"document_id": document.id, "version_id": version.id},
                    provider="ollama",
                    status="queued"
                )
                session.add(embed_job)
                await session.commit()
                
                # Process embedding immediately in background
                asyncio.create_task(process_embedding_job(embed_job.id))
            except Exception as e:
                pass
            
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            await session.commit()
            logger.error(f"Text extraction job {job_id} failed: {e}", exc_info=True)


async def worker_loop():
    """Main worker loop to process queued jobs with parallel processing"""
    from ..config import settings
    
    # Configuration: max concurrent jobs per type
    MAX_CONCURRENT_OCR = settings.max_concurrent_ocr_jobs
    MAX_CONCURRENT_EMBED = settings.max_concurrent_embed_jobs
    BATCH_SIZE = settings.worker_batch_size  # Jobs to fetch per iteration
    
    # Semaphores to limit concurrent processing
    ocr_semaphore = asyncio.Semaphore(MAX_CONCURRENT_OCR)
    embed_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EMBED)
    text_extract_semaphore = asyncio.Semaphore(MAX_CONCURRENT_OCR)  # Use same limit as OCR
    
    # Track active tasks
    active_tasks = set()
    
    async def process_job_with_semaphore(job_id: int, job_type: str):
        """Process a job with appropriate semaphore"""
        if job_type == "ocr":
            semaphore = ocr_semaphore
        elif job_type == "text_extract":
            semaphore = text_extract_semaphore
        else:
            semaphore = embed_semaphore
        
        async with semaphore:
            if job_type == "ocr":
                await process_ocr_job(job_id)
            elif job_type == "text_extract":
                await process_text_extract_job(job_id)
            elif job_type == "embed":
                await process_embedding_job(job_id)
    
    async def cleanup_completed_tasks():
        """Remove completed tasks from active_tasks"""
        completed = [task for task in active_tasks if task.done()]
        for task in completed:
            active_tasks.discard(task)
            try:
                await task  # Get any exceptions
            except Exception as e:
                logger.error(f"Task completed with error: {e}", exc_info=True)
    
    while True:
        try:
            # Clean up completed tasks
            await cleanup_completed_tasks()
            
            async with AsyncSessionLocal() as session:
                # Get multiple queued jobs (batch processing)
                result = await session.execute(
                    select(AIJob)
                    .where(AIJob.status == "queued")
                    .order_by(AIJob.created_at.asc())
                    .limit(BATCH_SIZE)
                )
                jobs = result.scalars().all()
                
                if jobs:
                    # Process jobs in parallel
                    for job in jobs:
                        # Create task for this job (semaphore will handle concurrency limit)
                        task = asyncio.create_task(
                            process_job_with_semaphore(job.id, job.job_type)
                        )
                        active_tasks.add(task)
                    
                    # Small delay before next batch
                    await asyncio.sleep(0.5)
                else:
                    # No jobs, wait longer
                    await asyncio.sleep(2)
                    
        except Exception as e:
            logger.error(f"Error in worker loop: {e}", exc_info=True)
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(worker_loop())

