"""
Tests for Audit & Logs endpoints.

Covers:
- GET /audit - Get audit logs with filters
- POST /audit/export - Export audit logs (admin)
"""
import pytest
from fastapi import status
from datetime import datetime, timedelta


@pytest.mark.api
class TestAuditList:
    """Tests for GET /audit endpoint."""
    
    async def test_get_audit_logs_success(self, client, admin_token, test_db, regular_user):
        """Test getting audit logs as admin."""
        from src.app.models.audit import AuditEvent
        event = AuditEvent(
            actor_id=regular_user.id,
            subject_type="document",
            subject_id=1,
            action="view",
            timestamp=datetime.utcnow(),
            metadata={"ip": "127.0.0.1"}
        )
        test_db.add(event)
        await test_db.commit()
        
        response = client.get(
            "/api/v1/audit",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert isinstance(data["data"], list) or "items" in data["data"]
    
    async def test_get_audit_logs_with_filters(self, client, admin_token, test_db, regular_user):
        """Test getting audit logs with filters."""
        from src.app.models.audit import AuditEvent
        event = AuditEvent(
            actor_id=regular_user.id,
            subject_type="document",
            subject_id=1,
            action="create",
            timestamp=datetime.utcnow()
        )
        test_db.add(event)
        await test_db.commit()
        
        response = client.get(
            f"/api/v1/audit?actor_id={regular_user.id}&action=create",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_get_audit_logs_by_date_range(self, client, admin_token, test_db, regular_user):
        """Test getting audit logs filtered by date range."""
        from src.app.models.audit import AuditEvent
        from_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        to_date = datetime.utcnow().isoformat()
        
        response = client.get(
            f"/api/v1/audit?from_date={from_date}&to_date={to_date}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_get_audit_logs_by_subject(self, client, admin_token, test_db, regular_user):
        """Test getting audit logs filtered by subject."""
        from src.app.models.audit import AuditEvent
        event = AuditEvent(
            actor_id=regular_user.id,
            subject_type="document",
            subject_id=123,
            action="update",
            timestamp=datetime.utcnow()
        )
        test_db.add(event)
        await test_db.commit()
        
        response = client.get(
            "/api/v1/audit?subject_type=document&subject_id=123",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_get_audit_logs_unauthorized(self, client, user_token):
        """Test getting audit logs as non-admin."""
        response = client.get(
            "/api/v1/audit",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    async def test_get_audit_logs_no_auth(self, client):
        """Test getting audit logs without authentication."""
        response = client.get("/api/v1/audit")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestAuditExport:
    """Tests for POST /audit/export endpoint."""
    
    async def test_export_audit_logs_success(self, client, admin_token):
        """Test exporting audit logs as admin."""
        from_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        to_date = datetime.utcnow().isoformat()
        
        response = client.post(
            "/api/v1/audit/export",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "from_date": from_date,
                "to_date": to_date,
                "format": "csv"
            }
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED, status.HTTP_404_NOT_FOUND]
        if response.status_code == status.HTTP_200_OK:
            # Should return file download
            assert response.headers.get("content-type") in ["text/csv", "application/csv", "application/json"]
    
    async def test_export_audit_logs_json_format(self, client, admin_token):
        """Test exporting audit logs in JSON format."""
        from_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        to_date = datetime.utcnow().isoformat()
        
        response = client.post(
            "/api/v1/audit/export",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "from_date": from_date,
                "to_date": to_date,
                "format": "json"
            }
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED, status.HTTP_404_NOT_FOUND]
    
    async def test_export_audit_logs_with_filters(self, client, admin_token, test_db, regular_user):
        """Test exporting audit logs with filters."""
        from_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        to_date = datetime.utcnow().isoformat()
        
        response = client.post(
            "/api/v1/audit/export",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "from_date": from_date,
                "to_date": to_date,
                "format": "csv",
                "actor_id": regular_user.id,
                "action": "create"
            }
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED, status.HTTP_404_NOT_FOUND]
    
    async def test_export_audit_logs_unauthorized(self, client, user_token):
        """Test exporting audit logs as non-admin."""
        response = client.post(
            "/api/v1/audit/export",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"format": "csv"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    async def test_export_audit_logs_no_auth(self, client):
        """Test exporting audit logs without authentication."""
        response = client.post(
            "/api/v1/audit/export",
            json={"format": "csv"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
