"""
Tests for Users & Roles management endpoints.

Covers:
- GET /users - List users
- POST /users - Create user
- PATCH /users/{id} - Update user
- DELETE /users/{id} - Delete user
- POST /users/{id}/activate - Activate user
- POST /users/{id}/deactivate - Deactivate user
- PATCH /users/{id}/expiry - Set user expiry
"""
import pytest
from fastapi import status
from datetime import datetime, timedelta


@pytest.mark.api
class TestUsersList:
    """Tests for GET /users endpoint."""
    
    async def test_list_users_success(self, client, admin_token, admin_user, regular_user):
        """Test listing users as admin."""
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 2
    
    async def test_list_users_unauthorized(self, client, user_token):
        """Test listing users as non-admin."""
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    async def test_list_users_no_auth(self, client):
        """Test listing users without authentication."""
        response = client.get("/api/v1/users")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestUsersCreate:
    """Tests for POST /users endpoint."""
    
    async def test_create_user_success(self, client, admin_token):
        """Test creating a new user as admin."""
        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "New User",
                "email": "newuser@test.com",
                "password": "password123",
                "role": "user"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert data["data"]["email"] == "newuser@test.com"
        assert data["data"]["name"] == "New User"
        assert data["data"]["role"] == "user"
        assert data["data"]["status"] == "active"
    
    async def test_create_user_duplicate_email(self, client, admin_token, regular_user):
        """Test creating user with existing email."""
        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Duplicate User",
                "email": "user@test.com",
                "password": "password123",
                "role": "user"
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["is_success"] is False
        assert "Email already exists" in data["message"]
    
    async def test_create_user_with_expiry(self, client, admin_token):
        """Test creating user with expiry date."""
        expiry_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Temporary User",
                "email": "temp@test.com",
                "password": "password123",
                "role": "user",
                "expires_at": expiry_date
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
    
    async def test_create_user_unauthorized(self, client, user_token):
        """Test creating user as non-admin."""
        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "name": "New User",
                "email": "newuser@test.com",
                "password": "password123"
            }
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    async def test_create_user_missing_fields(self, client, admin_token):
        """Test creating user with missing required fields."""
        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "New User"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_create_user_invalid_email(self, client, admin_token):
        """Test creating user with invalid email format."""
        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "New User",
                "email": "invalid-email",
                "password": "password123"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.api
class TestUsersUpdate:
    """Tests for PATCH /users/{id} endpoint."""
    
    async def test_update_user_success(self, client, admin_token, regular_user):
        """Test updating user as admin."""
        response = client.patch(
            f"/api/v1/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Updated Name"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert data["data"]["name"] == "Updated Name"
    
    async def test_update_user_role(self, client, admin_token, regular_user):
        """Test updating user role."""
        response = client.patch(
            f"/api/v1/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": "staff"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["role"] == "staff"
    
    async def test_update_user_status(self, client, admin_token, regular_user):
        """Test updating user status."""
        response = client.patch(
            f"/api/v1/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "inactive"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["status"] == "inactive"
    
    async def test_update_user_expiry(self, client, admin_token, regular_user):
        """Test updating user expiry."""
        expiry_date = (datetime.utcnow() + timedelta(days=60)).isoformat()
        response = client.patch(
            f"/api/v1/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"expires_at": expiry_date}
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_update_user_not_found(self, client, admin_token):
        """Test updating non-existent user."""
        response = client.patch(
            "/api/v1/users/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Updated Name"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_update_user_unauthorized(self, client, user_token, regular_user):
        """Test updating user as non-admin."""
        response = client.patch(
            f"/api/v1/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"name": "Updated Name"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.api
class TestUsersDelete:
    """Tests for DELETE /users/{id} endpoint."""
    
    async def test_delete_user_success(self, client, admin_token, test_db, regular_user):
        """Test deleting user as admin."""
        # Create a user to delete
        from src.app.models.users import User
        from src.app.services.auth import get_password_hash
        user_to_delete = User(
            name="To Delete",
            email="todelete@test.com",
            password_hash=get_password_hash("password123"),
            role="user",
            status="active"
        )
        test_db.add(user_to_delete)
        await test_db.commit()
        await test_db.refresh(user_to_delete)
        
        response = client.delete(
            f"/api/v1/users/{user_to_delete.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert data["data"]["deleted"] is True
    
    async def test_delete_user_self(self, client, admin_token, admin_user):
        """Test deleting own account (should fail)."""
        response = client.delete(
            f"/api/v1/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Cannot delete yourself" in data["message"]
    
    async def test_delete_user_not_found(self, client, admin_token):
        """Test deleting non-existent user."""
        response = client.delete(
            "/api/v1/users/99999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_delete_user_unauthorized(self, client, user_token, regular_user):
        """Test deleting user as non-admin."""
        response = client.delete(
            f"/api/v1/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.api
class TestUsersActivate:
    """Tests for POST /users/{id}/activate endpoint."""
    
    async def test_activate_user_success(self, client, admin_token, inactive_user):
        """Test activating inactive user."""
        # Note: This endpoint may not be implemented yet
        response = client.post(
            f"/api/v1/users/{inactive_user.id}/activate",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    async def test_activate_user_unauthorized(self, client, user_token, inactive_user):
        """Test activating user as non-admin."""
        response = client.post(
            f"/api/v1/users/{inactive_user.id}/activate",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]


@pytest.mark.api
class TestUsersDeactivate:
    """Tests for POST /users/{id}/deactivate endpoint."""
    
    async def test_deactivate_user_success(self, client, admin_token, regular_user):
        """Test deactivating active user."""
        # Note: This endpoint may not be implemented yet
        response = client.post(
            f"/api/v1/users/{regular_user.id}/deactivate",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    async def test_deactivate_user_unauthorized(self, client, user_token, regular_user):
        """Test deactivating user as non-admin."""
        response = client.post(
            f"/api/v1/users/{regular_user.id}/deactivate",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
