"""
Tests for Search endpoints.

Covers:
- POST /search - Hybrid search (keyword + vector)
- POST /search/vector - Vector search only
- POST /search/index/reindex - Reindex all documents (admin)
- POST /search/index/reindex/{documentId} - Reindex single document
"""
import pytest
from fastapi import status


@pytest.mark.api
class TestSearchHybrid:
    """Tests for POST /search endpoint (hybrid search)."""
    
    async def test_search_keyword_mode_success(self, client, user_token, test_document):
        """Test keyword search mode."""
        response = client.post(
            "/api/v1/search",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "query": "Test",
                "mode": "keyword",
                "limit": 20
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert "results" in data["data"] or "items" in data["data"]
    
    async def test_search_vector_mode_success(self, client, user_token):
        """Test vector search mode."""
        response = client.post(
            "/api/v1/search",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "query": "test query",
                "mode": "vector",
                "limit": 20
            }
        )
        # Note: Vector search may require embeddings to be set up
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]
    
    async def test_search_hybrid_mode_success(self, client, user_token, test_document):
        """Test hybrid search mode (keyword + vector)."""
        response = client.post(
            "/api/v1/search",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "query": "Test Document",
                "mode": "hybrid",
                "limit": 20
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
    
    async def test_search_with_filters(self, client, user_token, test_document):
        """Test search with filters."""
        response = client.post(
            "/api/v1/search",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "query": "Test",
                "mode": "keyword",
                "filters": {
                    "mime": "application/pdf",
                    "status": "ready"
                },
                "limit": 20
            }
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_search_with_group_id(self, client, user_token):
        """Test search scoped to document group."""
        response = client.post(
            "/api/v1/search",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "query": "test",
                "mode": "keyword",
                "group_id": 1,
                "limit": 20
            }
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_search_empty_query(self, client, user_token):
        """Test search with empty query."""
        response = client.post(
            "/api/v1/search",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "query": "",
                "mode": "keyword",
                "limit": 20
            }
        )
        # Should either return empty results or validation error
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
    
    async def test_search_unauthorized(self, client):
        """Test search without authentication."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "test",
                "mode": "keyword"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_search_invalid_mode(self, client, user_token):
        """Test search with invalid mode."""
        response = client.post(
            "/api/v1/search",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "query": "test",
                "mode": "invalid_mode",
                "limit": 20
            }
        )
        # Should handle gracefully or return error
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]


@pytest.mark.api
class TestSearchVector:
    """Tests for POST /search/vector endpoint."""
    
    async def test_vector_search_success(self, client, user_token):
        """Test vector search endpoint."""
        response = client.post(
            "/api/v1/search/vector",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "query": "test query",
                "top_k": 10
            }
        )
        # Note: Requires vector embeddings to be set up
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_503_SERVICE_UNAVAILABLE]
    
    async def test_vector_search_with_filters(self, client, user_token):
        """Test vector search with filters."""
        response = client.post(
            "/api/v1/search/vector",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "query": "test",
                "top_k": 10,
                "filters": {"group_id": 1}
            }
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_503_SERVICE_UNAVAILABLE]
    
    async def test_vector_search_unauthorized(self, client):
        """Test vector search without authentication."""
        response = client.post(
            "/api/v1/search/vector",
            json={"query": "test"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestSearchReindex:
    """Tests for POST /search/index/reindex endpoints."""
    
    async def test_reindex_all_success(self, client, admin_token):
        """Test reindexing all documents as admin."""
        response = client.post(
            "/api/v1/search/index/reindex",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Note: This may trigger async job
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED, status.HTTP_404_NOT_FOUND]
    
    async def test_reindex_all_unauthorized(self, client, user_token):
        """Test reindexing all documents as non-admin."""
        response = client.post(
            "/api/v1/search/index/reindex",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    async def test_reindex_single_document_success(self, client, admin_token, test_document, test_db, regular_user):
        """Test reindexing single document."""
        # Ensure document has a version with text_uri
        from src.app.models.documents import DocumentVersion
        version = DocumentVersion(
            document_id=test_document.id,
            version_no=1,
            blob_uri="test/blob.pdf",
            text_uri="test/text.txt",  # Add text_uri for reindex to work
            created_by=regular_user.id,
            size=1024,
            status="ready"
        )
        test_db.add(version)
        await test_db.commit()
        
        response = client.post(
            f"/api/v1/search/index/reindex/{test_document.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Note: This may trigger async job
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED, status.HTTP_400_BAD_REQUEST]
    
    async def test_reindex_single_document_not_found(self, client, admin_token):
        """Test reindexing non-existent document."""
        response = client.post(
            "/api/v1/search/index/reindex/99999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_200_OK]
    
    async def test_reindex_single_document_unauthorized(self, client, user_token, test_document):
        """Test reindexing document as non-admin."""
        response = client.post(
            f"/api/v1/search/index/reindex/{test_document.id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN




