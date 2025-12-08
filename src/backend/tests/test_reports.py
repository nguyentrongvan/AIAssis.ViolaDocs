"""
Tests for Reports endpoints.

Covers:
- GET /reports/audit - Audit/export of user actions
- GET /reports/usage - Usage metrics
- GET /reports/workflow - Workflow SLA metrics
- GET /reports/quality - Data quality metrics
"""
import pytest
from fastapi import status
from datetime import datetime, timedelta


@pytest.mark.api
class TestReportsAudit:
    """Tests for GET /reports/audit endpoint."""
    
    async def test_get_audit_report_success(self, client, admin_token):
        """Test getting audit report as admin."""
        from_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        to_date = datetime.utcnow().isoformat()
        
        response = client.get(
            f"/api/v1/reports/audit?from_date={from_date}&to_date={to_date}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
    
    async def test_get_audit_report_with_filters(self, client, admin_token, test_db, regular_user):
        """Test getting audit report with filters."""
        response = client.get(
            f"/api/v1/reports/audit?actor_id={regular_user.id}&action=create",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_get_audit_report_unauthorized(self, client, user_token):
        """Test getting audit report as non-admin."""
        response = client.get(
            "/api/v1/reports/audit",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    async def test_get_audit_report_no_auth(self, client):
        """Test getting audit report without authentication."""
        response = client.get("/api/v1/reports/audit")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestReportsUsage:
    """Tests for GET /reports/usage endpoint."""
    
    async def test_get_usage_report_success(self, client, admin_token):
        """Test getting usage metrics report."""
        response = client.get(
            "/api/v1/reports/usage",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        # Should contain usage metrics
        assert "data" in data
    
    async def test_get_usage_report_with_time_range(self, client, admin_token):
        """Test getting usage report with time range."""
        from_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        to_date = datetime.utcnow().isoformat()
        
        response = client.get(
            f"/api/v1/reports/usage?from_date={from_date}&to_date={to_date}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_get_usage_report_with_rollup(self, client, admin_token):
        """Test getting usage report with time rollup."""
        response = client.get(
            "/api/v1/reports/usage?rollup=day",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_get_usage_report_unauthorized(self, client, user_token):
        """Test getting usage report as non-admin."""
        response = client.get(
            "/api/v1/reports/usage",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.api
class TestReportsWorkflow:
    """Tests for GET /reports/workflow endpoint."""
    
    async def test_get_workflow_report_success(self, client, admin_token):
        """Test getting workflow SLA report."""
        response = client.get(
            "/api/v1/reports/workflow",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
    
    async def test_get_workflow_report_with_filters(self, client, admin_token):
        """Test getting workflow report with filters."""
        response = client.get(
            "/api/v1/reports/workflow?template=approval&assignee_id=1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_get_workflow_report_unauthorized(self, client, user_token):
        """Test getting workflow report as non-admin."""
        response = client.get(
            "/api/v1/reports/workflow",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.api
class TestReportsDataQuality:
    """Tests for GET /reports/quality endpoint."""
    
    async def test_get_data_quality_report_success(self, client, admin_token):
        """Test getting data quality report."""
        response = client.get(
            "/api/v1/reports/quality",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        # Should contain quality metrics like:
        # - reindex job failures
        # - stale index count
        # - purge backlog
        # - virus-scan failures
    
    async def test_get_data_quality_report_unauthorized(self, client, user_token):
        """Test getting data quality report as non-admin."""
        response = client.get(
            "/api/v1/reports/quality",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

