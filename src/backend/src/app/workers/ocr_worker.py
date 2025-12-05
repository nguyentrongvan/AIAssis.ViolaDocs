import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import AsyncSessionLocal
from ..models.ai import AIJob
from ..models.documents import DocumentVersion
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
            object_name = version.blob_uri.replace(f"minio://{settings.minio_bucket}/", "")
            
            try:
                file_data = minio_client.get_object(settings.minio_bucket, object_name)
                file_bytes = file_data.read()
                file_data.close()
                file_data.release_conn()
            except Exception as e:
                raise ValueError(f"Failed to download file: {e}")
            
            # Process with OCR service
            ocr_service = get_ocr_service()
            mime = version.document.mime if hasattr(version, 'document') else "application/pdf"
            
            if mime.startswith("image/"):
                ocr_result = ocr_service.process_image(file_bytes)
            elif mime == "application/pdf":
                ocr_result = ocr_service.process_pdf(file_bytes)
            else:
                raise ValueError(f"Unsupported MIME type for OCR: {mime}")
            
            if ocr_result.get("error"):
                raise ValueError(ocr_result["error"])
            
            extracted_text = ocr_result.get("text", "")
            
            # Save extracted text to MinIO
            text_object_name = f"ocr/{version_id}/text.txt"
            from io import BytesIO
            minio_client.put_object(
                settings.minio_bucket,
                text_object_name,
                BytesIO(extracted_text.encode('utf-8')),
                length=len(extracted_text.encode('utf-8')),
                content_type="text/plain"
            )
            
            # Update version with OCR URI
            version.text_uri = f"minio://{settings.minio_bucket}/{text_object_name}"
            version.provider_info = {
                "ocr": {
                    "provider": ocr_result.get("provider", "paddle"),
                    "languages": settings.ocr_lang_list
                }
            }
            
            # Update job
            job.status = "completed"
            job.output_ref = {
                "text_uri": version.text_uri,
                "text_length": len(extracted_text)
            }
            
            await session.commit()
            
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            await session.commit()
            print(f"OCR job {job_id} failed: {e}")


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
            from ..models.ai import Embedding
            
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
            
            # Get text from OCR result
            if not version.text_uri:
                raise ValueError("No OCR text available. Run OCR first.")
            
            minio_client = get_minio_client()
            text_object_name = version.text_uri.replace(f"minio://{settings.minio_bucket}/", "")
            
            try:
                file_data = minio_client.get_object(settings.minio_bucket, text_object_name)
                text = file_data.read().decode('utf-8')
                file_data.close()
                file_data.release_conn()
            except Exception as e:
                raise ValueError(f"Failed to read OCR text: {e}")
            
            # Generate embedding
            embedding_vector = embedding_service.generate_embedding(text)
            
            # Save embedding
            embedding = Embedding(
                doc_id=version.document_id,
                version_id=version_id,
                vector=embedding_vector,
                provider=job.provider,
                chunk_ref={"text_length": len(text)}
            )
            session.add(embedding)
            
            # Update job
            job.status = "completed"
            job.output_ref = {
                "embedding_id": embedding.id,
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
                
                if job:
                    if job.job_type == "ocr":
                        await process_ocr_job(job.id)
                    elif job.job_type == "embed":
                        await process_embedding_job(job.id)
                    # Add more job types as needed
                else:
                    # No jobs, wait a bit
                    await asyncio.sleep(5)
                    
        except Exception as e:
            print(f"Worker error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(worker_loop())

