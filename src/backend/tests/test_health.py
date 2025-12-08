"""
Tests for Health check endpoint.

Covers:
- GET /health - Health check endpoint
"""
import pytest
from fastapi import status


@pytest.mark.api
class TestHealthCheck:
    """Tests for GET /health endpoint."""
    
    async def test_health_check_success(self, client):
        """Test health check endpoint returns OK."""
        response = client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert data["data"]["status"] == "ok"
    
    async def test_health_check_no_auth_required(self, client):
        """Test that health check doesn't require authentication."""
        response = client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK

