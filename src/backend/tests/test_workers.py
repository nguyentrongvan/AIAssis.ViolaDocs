"""
Tests for Background Workers.

Covers:
- OCR worker (process_ocr_job)
- Embedding worker (process_embedding_job)
- Worker loop (worker_loop)
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from src.app.models.ai import AIJob
from src.app.models.documents import Document, DocumentVersion
from src.app.workers.ocr_worker import process_ocr_job, process_embedding_job


@pytest.mark.unit
class TestOCRWorker:
    """Tests for OCR worker process_ocr_job function."""
    
    @pytest.mark.asyncio
    async def test_process_ocr_job_success(self, test_db, regular_user):
        """Test successful OCR job processing."""
        # Create document and version
        doc = Document(
            title="Test PDF",
            source="web",
            owner_id=regular_user.id,
            mime="application/pdf",
            size=1024,
            status="processing"
        )
        test_db.add(doc)
        await test_db.flush()
        
        version = DocumentVersion(
            document_id=doc.id,
            version_no=1,
            blob_uri="test/test.pdf",
            created_by=regular_user.id,
            size=1024,
            status="processing"
        )
        test_db.add(version)
        await test_db.flush()
        
        job = AIJob(
            job_type="ocr",
            target={"version_id": version.id},
            provider="paddle",
            status="queued"
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        # Mock MinIO client and OCR service
        with patch('src.app.workers.ocr_worker.get_minio_client') as mock_minio, \
             patch('src.app.workers.ocr_worker.get_ocr_service') as mock_ocr:
            
            # Mock MinIO
            mock_client = MagicMock()
            mock_file = MagicMock()
            mock_file.read.return_value = b"fake pdf content"
            mock_client.get_object.return_value = mock_file
            mock_minio.return_value = mock_client
            
            # Mock OCR service
            mock_ocr_service = MagicMock()
            mock_ocr_service.process_pdf.return_value = {
                "text": "Extracted text from PDF",
                "provider": "paddle"
            }
            mock_ocr.return_value = mock_ocr_service
            
            # Process job
            await process_ocr_job(job.id)
            
            # Verify job completed
            await test_db.refresh(job)
            assert job.status == "completed"
            assert job.output_ref is not None
    
    @pytest.mark.asyncio
    async def test_process_ocr_job_not_found(self, test_db):
        """Test processing non-existent job."""
        await process_ocr_job(99999)
        # Should not raise error
    
    @pytest.mark.asyncio
    async def test_process_ocr_job_already_processing(self, test_db, regular_user):
        """Test processing job that's already in progress."""
        job = AIJob(
            job_type="ocr",
            target={"version_id": 1},
            provider="paddle",
            status="processing"
        )
        test_db.add(job)
        await test_db.commit()
        
        await process_ocr_job(job.id)
        # Should not process again
    
    @pytest.mark.asyncio
    async def test_process_ocr_job_failure(self, test_db, regular_user):
        """Test OCR job failure handling."""
        doc = Document(
            title="Test PDF",
            source="web",
            owner_id=regular_user.id,
            mime="application/pdf",
            size=1024,
            status="processing"
        )
        test_db.add(doc)
        await test_db.flush()
        
        version = DocumentVersion(
            document_id=doc.id,
            version_no=1,
            blob_uri="test/test.pdf",
            created_by=regular_user.id,
            size=1024,
            status="processing"
        )
        test_db.add(version)
        await test_db.flush()
        
        job = AIJob(
            job_type="ocr",
            target={"version_id": version.id},
            provider="paddle",
            status="queued"
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        # Mock MinIO to raise error
        with patch('src.app.workers.ocr_worker.get_minio_client') as mock_minio:
            mock_client = MagicMock()
            mock_client.get_object.side_effect = Exception("File not found")
            mock_minio.return_value = mock_client
            
            await process_ocr_job(job.id)
            
            await test_db.refresh(job)
            assert job.status == "failed"
            assert job.error is not None
    
    @pytest.mark.asyncio
    async def test_process_ocr_job_missing_version_id(self, test_db, regular_user):
        """Test OCR job with missing version_id in target."""
        job = AIJob(
            job_type="ocr",
            target={"document_id": 1},  # Missing version_id
            provider="paddle",
            status="queued"
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        await process_ocr_job(job.id)
        
        await test_db.refresh(job)
        assert job.status == "failed"


@pytest.mark.unit
class TestEmbeddingWorker:
    """Tests for embedding worker process_embedding_job function."""
    
    @pytest.mark.asyncio
    async def test_process_embedding_job_success(self, test_db, regular_user):
        """Test successful embedding job processing."""
        doc = Document(
            title="Test Document",
            source="web",
            owner_id=regular_user.id,
            mime="application/pdf",
            size=1024,
            status="ready"
        )
        test_db.add(doc)
        await test_db.flush()
        
        version = DocumentVersion(
            document_id=doc.id,
            version_no=1,
            blob_uri="test/test.pdf",
            text_uri="renditions/1/1/text.txt",
            created_by=regular_user.id,
            size=1024,
            status="ready"
        )
        test_db.add(version)
        await test_db.flush()
        
        job = AIJob(
            job_type="embed",
            target={"version_id": version.id},
            provider="openai",
            status="queued"
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        # Mock MinIO and embedding service
        with patch('src.app.workers.ocr_worker.get_minio_client') as mock_minio, \
             patch('src.app.workers.ocr_worker.get_embedding_service') as mock_embed:
            
            # Mock MinIO
            mock_client = MagicMock()
            mock_file = MagicMock()
            mock_file.read.return_value = b"Sample text content"
            mock_client.get_object.return_value = mock_file
            mock_minio.return_value = mock_client
            
            # Mock embedding service
            mock_embed_service = MagicMock()
            mock_embed_service.generate_embedding.return_value = [0.1] * 1536
            mock_embed.return_value = mock_embed_service
            
            await process_embedding_job(job.id)
            
            await test_db.refresh(job)
            assert job.status == "completed"
            assert job.output_ref is not None
    
    @pytest.mark.asyncio
    async def test_process_embedding_job_no_ocr_text(self, test_db, regular_user):
        """Test embedding job when OCR text is not available."""
        doc = Document(
            title="Test Document",
            source="web",
            owner_id=regular_user.id,
            mime="application/pdf",
            size=1024,
            status="ready"
        )
        test_db.add(doc)
        await test_db.flush()
        
        version = DocumentVersion(
            document_id=doc.id,
            version_no=1,
            blob_uri="test/test.pdf",
            # No text_uri
            created_by=regular_user.id,
            size=1024,
            status="ready"
        )
        test_db.add(version)
        await test_db.flush()
        
        job = AIJob(
            job_type="embed",
            target={"version_id": version.id},
            provider="openai",
            status="queued"
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        await process_embedding_job(job.id)
        
        await test_db.refresh(job)
        assert job.status == "failed"
        assert "No OCR text" in job.error
    
    @pytest.mark.asyncio
    async def test_process_embedding_job_provider_not_configured(self, test_db, regular_user):
        """Test embedding job when provider is not configured."""
        doc = Document(
            title="Test Document",
            source="web",
            owner_id=regular_user.id,
            mime="application/pdf",
            size=1024,
            status="ready"
        )
        test_db.add(doc)
        await test_db.flush()
        
        version = DocumentVersion(
            document_id=doc.id,
            version_no=1,
            blob_uri="test/test.pdf",
            text_uri="renditions/1/1/text.txt",
            created_by=regular_user.id,
            size=1024,
            status="ready"
        )
        test_db.add(version)
        await test_db.flush()
        
        job = AIJob(
            job_type="embed",
            target={"version_id": version.id},
            provider="openai",
            status="queued"
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        with patch('src.app.workers.ocr_worker.get_embedding_service') as mock_embed:
            mock_embed.return_value = None
            
            await process_embedding_job(job.id)
            
            await test_db.refresh(job)
            assert job.status == "failed"
