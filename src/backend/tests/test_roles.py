"""
Tests for Roles endpoints.
"""
import pytest
from fastapi import status


@pytest.mark.api
class TestRolesList:
    """Tests for GET /roles endpoint."""
    
    async def test_list_roles_success(self, client, admin_token):
        """Test listing roles as admin."""
        response = client.get(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert isinstance(data["data"], list)
    
    async def test_list_roles_unauthorized(self, client, user_token):
        """Test listing roles as non-admin."""
        response = client.get(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.api
class TestRolesCreate:
    """Tests for POST /roles endpoint."""
    
    async def test_create_role_success(self, client, admin_token):
        """Test creating a role."""
        response = client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Editor",
                "permissions": ["read", "write"]
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert data["data"]["name"] == "Editor"
        assert "read" in data["data"]["permissions"]
    
    async def test_create_role_duplicate_name(self, client, admin_token, test_db):
        """Test creating role with duplicate name."""
        from src.app.models.roles import Role
        role = Role(name="Editor", permissions=["read"])
        test_db.add(role)
        await test_db.commit()
        
        response = client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Editor",
                "permissions": ["read", "write"]
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    async def test_create_role_unauthorized(self, client, user_token):
        """Test creating role as non-admin."""
        response = client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "name": "Editor",
                "permissions": ["read"]
            }
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.api
class TestRolesUpdate:
    """Tests for PATCH /roles/{id} endpoint."""
    
    async def test_update_role_success(self, client, admin_token, test_db):
        """Test updating a role."""
        from src.app.models.roles import Role
        role = Role(name="Editor", permissions=["read"])
        test_db.add(role)
        await test_db.commit()
        await test_db.refresh(role)
        
        response = client.patch(
            f"/api/v1/roles/{role.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "permissions": ["read", "write", "delete"]
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert "delete" in data["data"]["permissions"]
    
    async def test_update_role_not_found(self, client, admin_token):
        """Test updating non-existent role."""
        response = client.patch(
            "/api/v1/roles/999",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "New Name"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.api
class TestRolesPermissions:
    """Tests for POST /roles/{id}/permissions endpoint."""
    
    async def test_set_role_permissions_success(self, client, admin_token, test_db):
        """Test setting permissions for a role."""
        from src.app.models.roles import Role
        role = Role(name="Editor", permissions=["read"])
        test_db.add(role)
        await test_db.commit()
        await test_db.refresh(role)
        
        response = client.post(
            f"/api/v1/roles/{role.id}/permissions",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "permissions": ["read", "write", "delete"]
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]["permissions"]) == 3

