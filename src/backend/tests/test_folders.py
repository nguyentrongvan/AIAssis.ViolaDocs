"""
Tests for Folders endpoints.
"""
import pytest
from fastapi import status


@pytest.mark.api
class TestFoldersList:
    """Tests for GET /folders endpoint."""
    
    async def test_list_folders_success(self, client, user_token, test_db, regular_user):
        """Test listing folders."""
        from src.app.models.documents import Folder
        folder = Folder(
            name="Test Folder",
            owner_id=regular_user.id,
            created_by=regular_user.id
        )
        test_db.add(folder)
        await test_db.commit()
        
        response = client.get(
            "/api/v1/folders",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert isinstance(data["data"], list)
    
    async def test_list_folders_unauthorized(self, client):
        """Test listing folders without auth."""
        response = client.get("/api/v1/folders")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestFoldersCreate:
    """Tests for POST /folders endpoint."""
    
    async def test_create_folder_success(self, client, user_token, regular_user):
        """Test creating a folder."""
        response = client.post(
            "/api/v1/folders",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "name": "New Folder"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert data["data"]["name"] == "New Folder"
        assert data["data"]["owner_id"] == regular_user.id
    
    async def test_create_folder_with_parent(self, client, user_token, test_db, regular_user):
        """Test creating folder with parent."""
        from src.app.models.documents import Folder
        parent = Folder(
            name="Parent Folder",
            owner_id=regular_user.id,
            created_by=regular_user.id
        )
        test_db.add(parent)
        await test_db.commit()
        await test_db.refresh(parent)
        
        response = client.post(
            "/api/v1/folders",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "name": "Child Folder",
                "parent_id": parent.id
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["parent_id"] == parent.id


@pytest.mark.api
class TestFoldersGet:
    """Tests for GET /folders/{id} endpoint."""
    
    async def test_get_folder_success(self, client, user_token, test_db, regular_user):
        """Test getting folder details."""
        from src.app.models.documents import Folder
        folder = Folder(
            name="Test Folder",
            owner_id=regular_user.id,
            created_by=regular_user.id
        )
        test_db.add(folder)
        await test_db.commit()
        await test_db.refresh(folder)
        
        response = client.get(
            f"/api/v1/folders/{folder.id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert data["data"]["name"] == "Test Folder"
    
    async def test_get_folder_not_found(self, client, user_token):
        """Test getting non-existent folder."""
        response = client.get(
            "/api/v1/folders/999",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.api
class TestFoldersUpdate:
    """Tests for PATCH /folders/{id} endpoint."""
    
    async def test_update_folder_success(self, client, user_token, test_db, regular_user):
        """Test updating a folder."""
        from src.app.models.documents import Folder
        folder = Folder(
            name="Old Name",
            owner_id=regular_user.id,
            created_by=regular_user.id
        )
        test_db.add(folder)
        await test_db.commit()
        await test_db.refresh(folder)
        
        response = client.patch(
            f"/api/v1/folders/{folder.id}",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "name": "New Name"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["name"] == "New Name"

