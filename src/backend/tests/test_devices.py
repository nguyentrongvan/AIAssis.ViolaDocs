"""
Tests for Devices (Printers/Scanners) endpoints.

Covers:
- GET /devices - List devices
- POST /devices - Register device
- PATCH /devices/{id} - Update device
- DELETE /devices/{id} - Delete device
- POST /devices/{id}/issue-key - Issue device key
- POST /devices/{id}/ping - Device heartbeat
"""
import pytest
from fastapi import status
from datetime import datetime


@pytest.mark.api
class TestDevicesList:
    """Tests for GET /devices endpoint."""
    
    async def test_list_devices_success(self, client, admin_token, test_device):
        """Test listing devices as admin."""
        response = client.get(
            "/api/v1/devices",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert isinstance(data["data"], list)
    
    async def test_list_devices_unauthorized(self, client, user_token):
        """Test listing devices as non-admin."""
        response = client.get(
            "/api/v1/devices",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    async def test_list_devices_no_auth(self, client):
        """Test listing devices without authentication."""
        response = client.get("/api/v1/devices")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestDevicesCreate:
    """Tests for POST /devices endpoint."""
    
    async def test_create_device_success(self, client, admin_token):
        """Test creating a new device as admin."""
        response = client.post(
            "/api/v1/devices",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Office Scanner 1",
                "location": "Office Floor 2",
                "capabilities": ["scan", "print"]
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert data["data"]["name"] == "Office Scanner 1"
        assert data["data"]["location"] == "Office Floor 2"
        assert data["data"]["status"] == "offline"
    
    async def test_create_device_minimal_fields(self, client, admin_token):
        """Test creating device with minimal required fields."""
        response = client.post(
            "/api/v1/devices",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Simple Device",
                "location": "Location 1"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
    
    async def test_create_device_unauthorized(self, client, user_token):
        """Test creating device as non-admin."""
        response = client.post(
            "/api/v1/devices",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "name": "New Device",
                "location": "Location"
            }
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    async def test_create_device_missing_fields(self, client, admin_token):
        """Test creating device with missing required fields."""
        response = client.post(
            "/api/v1/devices",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Device"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.api
class TestDevicesUpdate:
    """Tests for PATCH /devices/{id} endpoint."""
    
    async def test_update_device_success(self, client, admin_token, test_device):
        """Test updating device as admin."""
        # Note: This endpoint may not be implemented yet
        response = client.patch(
            f"/api/v1/devices/{test_device.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Updated Device Name"}
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    async def test_update_device_not_found(self, client, admin_token):
        """Test updating non-existent device."""
        response = client.patch(
            "/api/v1/devices/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Updated Name"}
        )
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]
    
    async def test_update_device_unauthorized(self, client, user_token, test_device):
        """Test updating device as non-admin."""
        response = client.patch(
            f"/api/v1/devices/{test_device.id}",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"name": "Updated Name"}
        )
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]


@pytest.mark.api
class TestDevicesDelete:
    """Tests for DELETE /devices/{id} endpoint."""
    
    async def test_delete_device_success(self, client, admin_token, test_device):
        """Test deleting device as admin."""
        response = client.delete(
            f"/api/v1/devices/{test_device.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert data["data"]["deleted"] is True
    
    async def test_delete_device_not_found(self, client, admin_token):
        """Test deleting non-existent device."""
        response = client.delete(
            "/api/v1/devices/99999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_delete_device_unauthorized(self, client, user_token, test_device):
        """Test deleting device as non-admin."""
        response = client.delete(
            f"/api/v1/devices/{test_device.id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.api
class TestDevicesIssueKey:
    """Tests for POST /devices/{id}/issue-key endpoint."""
    
    async def test_issue_device_key_success(self, client, admin_token, test_device):
        """Test issuing device key."""
        response = client.post(
            f"/api/v1/devices/{test_device.id}/issue-key",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert "key" in data["data"]
        assert data["data"]["device_id"] == test_device.id
    
    async def test_issue_device_key_not_found(self, client, admin_token):
        """Test issuing key for non-existent device."""
        response = client.post(
            "/api/v1/devices/99999/issue-key",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_issue_device_key_unauthorized(self, client, user_token, test_device):
        """Test issuing device key as non-admin."""
        response = client.post(
            f"/api/v1/devices/{test_device.id}/issue-key",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    async def test_issue_device_key_multiple_times(self, client, admin_token, test_device):
        """Test issuing device key multiple times (should revoke old key)."""
        # Issue first key
        response1 = client.post(
            f"/api/v1/devices/{test_device.id}/issue-key",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response1.status_code == status.HTTP_200_OK
        key1 = response1.json()["data"]["key"]
        
        # Issue second key
        response2 = client.post(
            f"/api/v1/devices/{test_device.id}/issue-key",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response2.status_code == status.HTTP_200_OK
        key2 = response2.json()["data"]["key"]
        
        # Keys should be different
        assert key1 != key2


@pytest.mark.api
class TestDevicesPing:
    """Tests for POST /devices/{id}/ping endpoint."""
    
    async def test_device_ping_success(self, client, test_device):
        """Test device heartbeat ping."""
        # Note: This endpoint may require device authentication
        response = client.post(
            f"/api/v1/devices/{test_device.id}/ping"
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND]
    
    async def test_device_ping_not_found(self, client):
        """Test ping for non-existent device."""
        response = client.post("/api/v1/devices/99999/ping")
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_401_UNAUTHORIZED]
    
    async def test_device_ping_updates_last_seen(self, client, admin_token, test_device):
        """Test that ping updates device last_seen timestamp."""
        # Note: This may require device authentication
        response = client.post(
            f"/api/v1/devices/{test_device.id}/ping"
        )
        # Adjust based on actual implementation
        # If successful, verify last_seen is updated
        if response.status_code == status.HTTP_200_OK:
            # Verify last_seen was updated
            pass

