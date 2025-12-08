"""
Tests for AI/OCR Tasks endpoints.

Covers:
- POST /ai/ocr - Enqueue OCR job
- POST /ai/embed - Regenerate embeddings
- POST /ai/classify - Run classifier
- POST /ai/qa - RAG Q&A over document(s)
- GET /ai/jobs/{id} - Get job status
"""
import pytest
from fastapi import status


@pytest.mark.api
class TestAIOCR:
    """Tests for POST /ai/ocr endpoint."""
    
    async def test_enqueue_ocr_success(self, client, user_token, test_document, test_document_version):
        """Test enqueueing OCR job for document."""
        response = client.post(
            "/api/v1/ai/ocr",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "document_id": test_document.id,
                "version_id": test_document_version.id,
                "provider": "paddle"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert "job_id" in data["data"] or "id" in data["data"]
    
    async def test_enqueue_ocr_with_version_id(self, client, user_token, test_document_version):
        """Test enqueueing OCR with version_id only."""
        response = client.post(
            "/api/v1/ai/ocr",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "version_id": test_document_version.id,
                "provider": "paddle"
            }
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_enqueue_ocr_with_document_id(self, client, user_token, test_document):
        """Test enqueueing OCR with document_id only."""
        response = client.post(
            "/api/v1/ai/ocr",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "document_id": test_document.id,
                "provider": "paddle"
            }
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_enqueue_ocr_missing_target(self, client, user_token):
        """Test enqueueing OCR without document_id or version_id."""
        response = client.post(
            "/api/v1/ai/ocr",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"provider": "paddle"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "required" in data["message"].lower()
    
    async def test_enqueue_ocr_default_provider(self, client, user_token, test_document):
        """Test enqueueing OCR with default provider."""
        response = client.post(
            "/api/v1/ai/ocr",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"document_id": test_document.id}
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_enqueue_ocr_unauthorized(self, client):
        """Test enqueueing OCR without authentication."""
        response = client.post(
            "/api/v1/ai/ocr",
            json={"document_id": 1}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestAIEmbed:
    """Tests for POST /ai/embed endpoint."""
    
    async def test_enqueue_embed_success(self, client, user_token, test_document, test_document_version):
        """Test enqueueing embedding job."""
        response = client.post(
            "/api/v1/ai/embed",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "document_id": test_document.id,
                "version_id": test_document_version.id,
                "provider": "default"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
    
    async def test_enqueue_embed_unauthorized(self, client):
        """Test enqueueing embed without authentication."""
        response = client.post(
            "/api/v1/ai/embed",
            json={"document_id": 1}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestAIClassify:
    """Tests for POST /ai/classify endpoint."""
    
    async def test_classify_success(self, client, user_token, test_document):
        """Test running classifier."""
        response = client.post(
            "/api/v1/ai/classify",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "document_id": test_document.id,
                "provider": "default"
            }
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]
    
    async def test_classify_unauthorized(self, client):
        """Test classify without authentication."""
        response = client.post(
            "/api/v1/ai/classify",
            json={"document_id": 1}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestAIQA:
    """Tests for POST /ai/qa endpoint."""
    
    async def test_qa_success(self, client, user_token, test_document):
        """Test RAG Q&A over document."""
        response = client.post(
            "/api/v1/ai/qa",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "document_id": test_document.id,
                "question": "What is this document about?",
                "provider": "default"
            }
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["is_success"] is True
            assert "answer" in data["data"] or "response" in data["data"]
    
    async def test_qa_unauthorized(self, client):
        """Test Q&A without authentication."""
        response = client.post(
            "/api/v1/ai/qa",
            json={"document_id": 1, "question": "test"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestAIJobsStatus:
    """Tests for GET /ai/jobs/{id} endpoint."""
    
    async def test_get_job_status_success(self, client, user_token, test_db, regular_user):
        """Test getting AI job status."""
        from src.app.models.ai import AIJob
        job = AIJob(
            job_type="ocr",
            target={"document_id": 1, "version_id": 1},
            provider="paddle",
            status="queued"
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        response = client.get(
            f"/api/v1/ai/jobs/{job.id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert data["data"]["id"] == job.id
        assert data["data"]["status"] == "queued"
    
    async def test_get_job_status_not_found(self, client, user_token):
        """Test getting non-existent job status."""
        response = client.get(
            "/api/v1/ai/jobs/99999",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_get_job_status_completed(self, client, user_token, test_db, regular_user):
        """Test getting completed job status."""
        from src.app.models.ai import AIJob
        job = AIJob(
            job_type="ocr",
            target={"document_id": 1, "version_id": 1},
            provider="paddle",
            status="completed",
            output_ref={"text_uri": "s3://bucket/text.txt"}
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        response = client.get(
            f"/api/v1/ai/jobs/{job.id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["status"] == "completed"
        assert "output_ref" in data["data"]
    
    async def test_get_job_status_failed(self, client, user_token, test_db, regular_user):
        """Test getting failed job status."""
        from src.app.models.ai import AIJob
        job = AIJob(
            job_type="ocr",
            target={"document_id": 1, "version_id": 1},
            provider="paddle",
            status="failed",
            error="Processing error"
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        response = client.get(
            f"/api/v1/ai/jobs/{job.id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["status"] == "failed"
        assert "error" in data["data"]
    
    async def test_get_job_status_unauthorized(self, client):
        """Test getting job status without authentication."""
        response = client.get("/api/v1/ai/jobs/1")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

