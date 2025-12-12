"""
Tests for Comments/Annotations endpoints.
"""
import pytest
from fastapi import status


@pytest.mark.api
class TestCommentsCreate:
    """Tests for POST /documents/{id}/comments endpoint."""
    
    async def test_create_comment_success(self, client, user_token, test_document, regular_user):
        """Test creating a comment."""
        response = client.post(
            f"/api/v1/documents/{test_document.id}/comments",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "content": "This is a comment",
                "type": "comment"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert data["data"]["content"] == "This is a comment"
        assert data["data"]["type"] == "comment"
    
    async def test_create_annotation_success(self, client, user_token, test_document, regular_user):
        """Test creating an annotation."""
        response = client.post(
            f"/api/v1/documents/{test_document.id}/comments",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "content": "This is an annotation",
                "type": "annotation",
                "position": {"page": 1, "x": 100, "y": 200}
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["type"] == "annotation"
        assert data["data"]["position"] is not None


@pytest.mark.api
class TestCommentsList:
    """Tests for GET /documents/{id}/comments endpoint."""
    
    async def test_list_comments_success(self, client, user_token, test_document, test_db, regular_user):
        """Test listing comments."""
        from src.app.models.documents import Comment
        comment = Comment(
            document_id=test_document.id,
            user_id=regular_user.id,
            content="Test comment",
            type="comment"
        )
        test_db.add(comment)
        await test_db.commit()
        
        response = client.get(
            f"/api/v1/documents/{test_document.id}/comments",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0


@pytest.mark.api
class TestCommentsUpdate:
    """Tests for PATCH /documents/{id}/comments/{comment_id} endpoint."""
    
    async def test_update_comment_success(self, client, user_token, test_document, test_db, regular_user):
        """Test updating a comment."""
        from src.app.models.documents import Comment
        comment = Comment(
            document_id=test_document.id,
            user_id=regular_user.id,
            content="Original comment",
            type="comment"
        )
        test_db.add(comment)
        await test_db.commit()
        await test_db.refresh(comment)
        
        response = client.patch(
            f"/api/v1/documents/{test_document.id}/comments/{comment.id}",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "content": "Updated comment"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["content"] == "Updated comment"


@pytest.mark.api
class TestCommentsDelete:
    """Tests for DELETE /documents/{id}/comments/{comment_id} endpoint."""
    
    async def test_delete_comment_success(self, client, user_token, test_document, test_db, regular_user):
        """Test deleting a comment."""
        from src.app.models.documents import Comment
        comment = Comment(
            document_id=test_document.id,
            user_id=regular_user.id,
            content="Comment to delete",
            type="comment"
        )
        test_db.add(comment)
        await test_db.commit()
        await test_db.refresh(comment)
        
        response = client.delete(
            f"/api/v1/documents/{test_document.id}/comments/{comment.id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["deleted"] is True

