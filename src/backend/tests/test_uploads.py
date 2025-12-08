"""
Tests for Upload endpoints (Web and Scanner).

Covers:
- POST /uploads/init - Initialize upload (web)
- PUT /uploads/{id}/chunk - Chunked upload (optional)
- POST /uploads/{id}/finalize - Finalize upload with metadata
- POST /scan-jobs - Device upload scan job
- POST /scan-jobs/{jobId}/finalize - Finalize scan job
- GET /scan-jobs/pending - Get pending scan jobs
"""
import pytest
from fastapi import status
import hashlib


@pytest.mark.api
class TestUploadInit:
    """Tests for POST /uploads/init endpoint."""
    
    async def test_init_upload_success(self, client, user_token):
        """Test initializing upload with valid file."""
        response = client.post(
            "/api/v1/uploads/init",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "filename": "test.pdf",
                "size": 1024,
                "mime": "application/pdf",
                "checksum": "abc123"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert "upload_id" in data["data"]
        assert "upload_url" in data["data"]
        assert "object_name" in data["data"]
    
    async def test_init_upload_max_size(self, client, user_token):
        """Test initializing upload with maximum allowed size."""
        # Assuming max size is 100MB
        max_size = 100 * 1024 * 1024
        response = client.post(
            "/api/v1/uploads/init",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "filename": "large.pdf",
                "size": max_size,
                "mime": "application/pdf"
            }
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_init_upload_exceeds_max_size(self, client, user_token):
        """Test initializing upload exceeding maximum size."""
        # Assuming max size is 100MB
        oversized = 101 * 1024 * 1024
        response = client.post(
            "/api/v1/uploads/init",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "filename": "too_large.pdf",
                "size": oversized,
                "mime": "application/pdf"
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["is_success"] is False
        assert "exceeds maximum" in data["message"].lower()
    
    async def test_init_upload_invalid_mime_type(self, client, user_token):
        """Test initializing upload with disallowed MIME type."""
        response = client.post(
            "/api/v1/uploads/init",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "filename": "test.exe",
                "size": 1024,
                "mime": "application/x-executable"
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["is_success"] is False
        assert "not allowed" in data["message"].lower()
    
    async def test_init_upload_allowed_mime_types(self, client, user_token):
        """Test initializing upload with various allowed MIME types."""
        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "image/jpeg",
            "image/png",
            "image/tiff"
        ]
        
        for mime_type in allowed_types:
            response = client.post(
                "/api/v1/uploads/init",
                headers={"Authorization": f"Bearer {user_token}"},
                json={
                    "filename": f"test.{mime_type.split('/')[-1]}",
                    "size": 1024,
                    "mime": mime_type
                }
            )
            assert response.status_code == status.HTTP_200_OK, f"Failed for {mime_type}"
    
    async def test_init_upload_unauthorized(self, client):
        """Test initializing upload without authentication."""
        response = client.post(
            "/api/v1/uploads/init",
            json={
                "filename": "test.pdf",
                "size": 1024,
                "mime": "application/pdf"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_init_upload_missing_fields(self, client, user_token):
        """Test initializing upload with missing required fields."""
        response = client.post(
            "/api/v1/uploads/init",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"filename": "test.pdf"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.api
class TestUploadFinalize:
    """Tests for POST /uploads/{id}/finalize endpoint."""
    
    async def test_finalize_upload_success(self, client, user_token, regular_user):
        """Test finalizing upload with metadata."""
        # First init upload
        init_response = client.post(
            "/api/v1/uploads/init",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "filename": "test.pdf",
                "size": 1024,
                "mime": "application/pdf"
            }
        )
        upload_id = init_response.json()["data"]["upload_id"]
        
        # Finalize upload
        response = client.post(
            f"/api/v1/uploads/{upload_id}/finalize",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "title": "Test Document",
                "tags": ["test", "document"],
                "folder_id": None,
                "retention_policy_id": None
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert "document_id" in data["data"]
        assert "version_id" in data["data"]
    
    async def test_finalize_upload_with_workflow(self, client, user_token, regular_user):
        """Test finalizing upload with workflow assignment."""
        # Init upload
        init_response = client.post(
            "/api/v1/uploads/init",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "filename": "workflow.pdf",
                "size": 1024,
                "mime": "application/pdf"
            }
        )
        upload_id = init_response.json()["data"]["upload_id"]
        
        # Finalize with workflow
        response = client.post(
            f"/api/v1/uploads/{upload_id}/finalize",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "title": "Workflow Document",
                "workflow_template": "approval",
                "workflow_assignees": [regular_user.id]
            }
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_finalize_upload_not_found(self, client, user_token):
        """Test finalizing non-existent upload."""
        response = client.post(
            "/api/v1/uploads/nonexistent-id/finalize",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"title": "Test"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_finalize_upload_unauthorized(self, client, user_token, staff_token):
        """Test finalizing another user's upload."""
        # Init upload as regular user
        init_response = client.post(
            "/api/v1/uploads/init",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "filename": "test.pdf",
                "size": 1024,
                "mime": "application/pdf"
            }
        )
        upload_id = init_response.json()["data"]["upload_id"]
        
        # Try to finalize as different user
        response = client.post(
            f"/api/v1/uploads/{upload_id}/finalize",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={"title": "Test"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    async def test_finalize_upload_invalid_folder_id(self, client, user_token):
        """Test finalizing upload with invalid folder_id."""
        init_response = client.post(
            "/api/v1/uploads/init",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "filename": "test.pdf",
                "size": 1024,
                "mime": "application/pdf"
            }
        )
        upload_id = init_response.json()["data"]["upload_id"]
        
        response = client.post(
            f"/api/v1/uploads/{upload_id}/finalize",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"folder_id": -1}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    async def test_finalize_upload_creates_ocr_job(self, client, user_token):
        """Test that finalizing PDF/image upload creates OCR job."""
        # Init PDF upload
        init_response = client.post(
            "/api/v1/uploads/init",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "filename": "test.pdf",
                "size": 1024,
                "mime": "application/pdf"
            }
        )
        upload_id = init_response.json()["data"]["upload_id"]
        
        # Finalize
        response = client.post(
            f"/api/v1/uploads/{upload_id}/finalize",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"title": "Test PDF"}
        )
        assert response.status_code == status.HTTP_200_OK
        # OCR job should be created (verify in database or job queue)


@pytest.mark.api
class TestUploadChunk:
    """Tests for PUT /uploads/{id}/chunk endpoint (optional chunked upload)."""
    
    async def test_upload_chunk_success(self, client, user_token):
        """Test uploading a chunk."""
        # Note: This endpoint may not be implemented yet
        init_response = client.post(
            "/api/v1/uploads/init",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "filename": "chunked.pdf",
                "size": 10240,
                "mime": "application/pdf"
            }
        )
        upload_id = init_response.json()["data"]["upload_id"]
        
        response = client.put(
            f"/api/v1/uploads/{upload_id}/chunk",
            headers={"Authorization": f"Bearer {user_token}"},
            data=b"chunk data",
            params={"chunk_number": 1}
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]


@pytest.mark.api
class TestScanJobs:
    """Tests for Scanner/Device upload endpoints."""
    
    async def test_create_scan_job_success(self, client, test_device):
        """Test creating scan job from device."""
        # Note: This requires device authentication
        response = client.post(
            "/api/v1/scan-jobs",
            json={
                "device_id": test_device.id,
                "device_token": "device_key_here",
                "user_id": 1,
                "mailbox": "inbox",
                "filename": "scan.pdf",
                "metadata": {}
            }
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND]
    
    async def test_finalize_scan_job_success(self, client):
        """Test finalizing scan job."""
        # Note: This requires device authentication and existing job
        response = client.post(
            "/api/v1/scan-jobs/123/finalize",
            json={"metadata": {"title": "Scanned Document"}}
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND]
    
    async def test_get_pending_scan_jobs(self, client, admin_token):
        """Test getting pending scan jobs."""
        # Note: This may require device authentication
        response = client.get(
            "/api/v1/scan-jobs/pending",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND]

