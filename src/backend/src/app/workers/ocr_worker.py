import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import AsyncSessionLocal
from ..models.ai import AIJob
from ..models.documents import DocumentVersion, Document
from ..services.ai import get_ocr_service
from ..services.storage import get_minio_client
from ..config import settings


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
            
            # Process OCR (use async methods to get latest settings)
            if mime.startswith("image/"):
                ocr_result = await ocr_service.process_image_async(file_bytes, languages)
            elif mime == "application/pdf":
                ocr_result = await ocr_service.process_pdf_async(file_bytes, languages)
            else:
                raise ValueError(f"Unsupported MIME type for OCR: {mime}")

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
            version.provider_info = {
                "ocr": {
                    "provider": ocr_result.get("provider", "paddle"),
                    "languages": settings.ocr_lang_list
                }
            }

            # Update document status to ready after OCR
            document.status = "ready"
            
            # Update job
            job.status = "completed"
            job.output_ref = {
                "text_uri": version.text_uri,
                "text_length": len(extracted_text)
            }
            
            await session.commit()
            
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
                raise ValueError(
                    "Embedding provider not configured or model not available. "
                    "Please configure Ollama and ensure the embedding model is pulled."
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
            print(f"Embedding job {job_id} failed: {e}")


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
    
    # Track active tasks
    active_tasks = set()
    
    async def process_job_with_semaphore(job_id: int, job_type: str):
        """Process a job with appropriate semaphore"""
        semaphore = ocr_semaphore if job_type == "ocr" else embed_semaphore
        async with semaphore:
            if job_type == "ocr":
                await process_ocr_job(job_id)
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
                print(f"Task completed with error: {e}")
    
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
            print(f"Error in worker loop: {e}")
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(worker_loop())

