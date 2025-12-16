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
            
            # Get languages from settings
            languages = settings.ocr_lang_list
            
            # Process OCR
            if mime.startswith("image/"):
                ocr_result = ocr_service.process_image(file_bytes, languages)
            elif mime == "application/pdf":
                ocr_result = ocr_service.process_pdf(file_bytes, languages)
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
            
            embedding_service = get_embedding_service()
            if not embedding_service:
                raise ValueError("Embedding provider not configured")
            
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
            embedding_vector = embedding_service.generate_embedding(text)
            
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
    """Main worker loop to process queued jobs"""
    processed_tasks = set()  # Track tasks being processed to avoid duplicates
    
    while True:
        try:
            async with AsyncSessionLocal() as session:
                # Get next queued job
                result = await session.execute(
                    select(AIJob)
                    .where(AIJob.status == "queued")
                    .order_by(AIJob.created_at.asc())
                    .limit(1)
                )
                job = result.scalar_one_or_none()
                
                if job and job.id not in processed_tasks:
                    # Mark as being processed
                    processed_tasks.add(job.id)
                    
                    # Process job asynchronously (don't await to allow parallel processing)
                    if job.job_type == "ocr":
                        asyncio.create_task(process_ocr_job(job.id))
                    elif job.job_type == "embed":
                        asyncio.create_task(process_embedding_job(job.id))
                    # Add more job types as needed
                    
                    # Small delay to avoid overwhelming the system
                    await asyncio.sleep(0.1)
                else:
                    # No jobs, wait a bit longer
                    if processed_tasks:
                        # Clear processed tasks periodically
                        processed_tasks.clear()
                    await asyncio.sleep(2)
                    
        except Exception as e:
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(worker_loop())

