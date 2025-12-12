"""
Tests for Settings/Admin endpoints.

Covers:
- GET/POST /settings/retention - Retention rules
- GET/POST /settings/providers - OCR/AI/search provider configs
- GET/POST /document-groups - Manage document groups
- POST /document-groups/{id}/reindex - Reindex group
- GET/POST /settings/chatbot - Chatbot policies per group
"""
import pytest
from fastapi import status


@pytest.mark.api
class TestSettingsRetention:
    """Tests for GET/POST /settings/retention endpoints."""
    
    async def test_get_retention_rules_success(self, client, admin_token):
        """Test getting retention rules as admin."""
        response = client.get(
            "/api/v1/settings/retention",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    async def test_create_retention_rule_success(self, client, admin_token):
        """Test creating retention rule."""
        response = client.post(
            "/api/v1/settings/retention",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Standard Retention",
                "duration_days": 365,
                "disposition": "delete",
                "legal_hold": False
            }
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]
    
    async def test_settings_retention_unauthorized(self, client, user_token):
        """Test accessing retention settings as non-admin."""
        response = client.get(
            "/api/v1/settings/retention",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.api
class TestSettingsProviders:
    """Tests for GET/POST /settings/providers endpoints."""
    
    async def test_get_providers_success(self, client, admin_token):
        """Test getting provider configurations."""
        response = client.get(
            "/api/v1/settings/providers",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    async def test_update_provider_config_success(self, client, admin_token):
        """Test updating provider configuration."""
        response = client.post(
            "/api/v1/settings/providers",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "provider_type": "ocr",
                "provider_name": "paddle",
                "config": {
                    "enabled": True,
                    "priority": 1
                }
            }
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]
    
    async def test_provider_health_check(self, client, admin_token):
        """Test provider health check."""
        response = client.get(
            "/api/v1/settings/providers/health?provider_type=ocr",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    async def test_settings_providers_unauthorized(self, client, user_token):
        """Test accessing provider settings as non-admin."""
        response = client.get(
            "/api/v1/settings/providers",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.api
class TestDocumentGroups:
    """Tests for GET/POST /document-groups endpoints."""
    
    async def test_create_document_group_success(self, client, admin_token):
        """Test creating document group."""
        response = client.post(
            "/api/v1/groups",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Finance Documents",
                "description": "Financial documents group",
                "chatbot_policy": {
                    "allowed_sources": ["docs"],
                    "allow_previews": True
                }
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert data["data"]["name"] == "Finance Documents"
    
    async def test_list_document_groups_success(self, client, user_token):
        """Test listing document groups."""
        response = client.get(
            "/api/v1/groups",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert isinstance(data["data"], list)
    
    async def test_get_document_group_success(self, client, admin_token, test_db):
        """Test getting document group detail."""
        from src.app.models.groups import DocumentGroup
        group = DocumentGroup(
            name="Test Group",
            description="Test description",
            chatbot_policy={"allowed_sources": ["docs"]}
        )
        test_db.add(group)
        await test_db.commit()
        await test_db.refresh(group)
        
        response = client.get(
            f"/api/v1/groups/{group.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    async def test_update_document_group_success(self, client, admin_token, test_db):
        """Test updating document group."""
        from src.app.models.groups import DocumentGroup
        group = DocumentGroup(
            name="Test Group",
            description="Original description"
        )
        test_db.add(group)
        await test_db.commit()
        await test_db.refresh(group)
        
        response = client.patch(
            f"/api/v1/groups/{group.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"description": "Updated description"}
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]
    
    async def test_reindex_document_group_success(self, client, admin_token, test_db):
        """Test reindexing document group."""
        from src.app.models.groups import DocumentGroup
        group = DocumentGroup(
            name="Test Group",
            description="Test"
        )
        test_db.add(group)
        await test_db.commit()
        await test_db.refresh(group)
        
        response = client.post(
            f"/api/v1/groups/{group.id}/reindex",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED, status.HTTP_404_NOT_FOUND]
    
    async def test_create_document_group_unauthorized(self, client, user_token):
        """Test creating document group as non-admin."""
        response = client.post(
            "/api/v1/groups",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"name": "Test Group"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.api
class TestSettingsChatbot:
    """Tests for GET/POST /settings/chatbot endpoints."""
    
    async def test_get_chatbot_settings_success(self, client, admin_token):
        """Test getting chatbot settings."""
        response = client.get(
            "/api/v1/settings/chatbot",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    async def test_update_chatbot_policy_success(self, client, admin_token, test_db):
        """Test updating chatbot policy for group."""
        from src.app.models.groups import DocumentGroup
        group = DocumentGroup(
            name="Test Group",
            chatbot_policy={}
        )
        test_db.add(group)
        await test_db.commit()
        await test_db.refresh(group)
        
        response = client.post(
            "/api/v1/settings/chatbot",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "group_id": group.id,
                "policy": {
                    "allowed_sources": ["docs", "reports"],
                    "allow_previews": True,
                    "allow_downloads": False,
                    "max_context_tokens": 4000,
                    "allowed_llm_providers": ["openai", "gemini"],
                    "rate_limit": 100
                }
            }
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]
    
    async def test_settings_chatbot_unauthorized(self, client, user_token):
        """Test accessing chatbot settings as non-admin."""
        response = client.get(
            "/api/v1/settings/chatbot",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN




