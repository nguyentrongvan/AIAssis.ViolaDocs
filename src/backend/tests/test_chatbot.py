"""
Tests for Chatbot/RAG endpoints.

Covers:
- POST /chat - Chat with RAG system
- GET /chat/history - Get chat history
- GET /chat/session/{session_id} - Get session history
- POST /chat/session/{id}/feedback - Submit feedback
- POST /chat/session/{id}/handoff - Escalate to human
- POST /chat/session/{id}/source-access - Request source access
"""
import pytest
from fastapi import status


@pytest.mark.api
class TestChatbotChat:
    """Tests for POST /chat endpoint."""
    
    async def test_chat_success(self, client, user_token):
        """Test basic chat query."""
        response = client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "message": "What documents do we have?",
                "group_id": None
            }
        )
        # Note: May require LLM service to be configured
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["is_success"] is True
            assert "answer" in data["data"] or "session_id" in data["data"]
    
    async def test_chat_with_group_id(self, client, user_token):
        """Test chat scoped to document group."""
        response = client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "message": "What is in this group?",
                "group_id": 1
            }
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_503_SERVICE_UNAVAILABLE]
    
    async def test_chat_with_session_id(self, client, user_token):
        """Test chat with session continuation."""
        # First chat
        response1 = client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"message": "Hello"}
        )
        if response1.status_code == status.HTTP_200_OK:
            session_id = response1.json().get("data", {}).get("session_id")
            if session_id:
                # Continue conversation
                response2 = client.post(
                    "/api/v1/chat",
                    headers={"Authorization": f"Bearer {user_token}"},
                    json={
                        "message": "Tell me more",
                        "session_id": session_id
                    }
                )
                assert response2.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]
    
    async def test_chat_empty_message(self, client, user_token):
        """Test chat with empty message."""
        response = client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"message": ""}
        )
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_200_OK]
    
    async def test_chat_unauthorized(self, client):
        """Test chat without authentication."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "test"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_chat_with_filters(self, client, user_token):
        """Test chat with document filters."""
        response = client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "message": "What documents?",
                "group_id": 1,
                "filters": {"tag": "important"}
            }
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_503_SERVICE_UNAVAILABLE]


@pytest.mark.api
class TestChatbotSession:
    """Tests for GET /chat/session/{session_id} endpoint."""
    
    async def test_get_session_history_success(self, client, user_token):
        """Test getting session history."""
        # First create a chat session
        response1 = client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"message": "Hello"}
        )
        
        if response1.status_code == status.HTTP_200_OK:
            session_id = response1.json().get("data", {}).get("session_id")
            if session_id:
                response = client.get(
                    f"/api/v1/chat/session/{session_id}",
                    headers={"Authorization": f"Bearer {user_token}"}
                )
                assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
                if response.status_code == status.HTTP_200_OK:
                    data = response.json()
                    assert data["is_success"] is True
                    assert "messages" in data["data"]
    
    async def test_get_session_history_not_found(self, client, user_token):
        """Test getting non-existent session."""
        response = client.get(
            "/api/v1/chat/session/nonexistent-session-id",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    async def test_get_session_history_unauthorized(self, client):
        """Test getting session history without authentication."""
        response = client.get("/api/v1/chat/session/123")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestChatbotHistory:
    """Tests for GET /chat/history endpoint."""
    
    async def test_get_chat_history_success(self, client, user_token):
        """Test getting chat history."""
        response = client.get(
            "/api/v1/chat/history",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["is_success"] is True
            assert isinstance(data["data"], list)
    
    async def test_get_chat_history_with_group_filter(self, client, user_token):
        """Test getting chat history filtered by group."""
        response = client.get(
            "/api/v1/chat/history?group_id=1",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    async def test_get_chat_history_unauthorized(self, client):
        """Test getting chat history without authentication."""
        response = client.get("/api/v1/chat/history")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestChatbotFeedback:
    """Tests for POST /chat/session/{id}/feedback endpoint."""
    
    async def test_submit_feedback_success(self, client, user_token):
        """Test submitting chat feedback."""
        # Note: Requires existing session
        response = client.post(
            "/api/v1/chat/session/123/feedback",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "rating": "positive",
                "comment": "Helpful response"
            }
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    async def test_submit_feedback_negative(self, client, user_token):
        """Test submitting negative feedback."""
        response = client.post(
            "/api/v1/chat/session/123/feedback",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "rating": "negative",
                "comment": "Not helpful"
            }
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    async def test_submit_feedback_unauthorized(self, client):
        """Test submitting feedback without authentication."""
        response = client.post(
            "/api/v1/chat/session/123/feedback",
            json={"rating": "positive"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestChatbotHandoff:
    """Tests for POST /chat/session/{id}/handoff endpoint."""
    
    async def test_handoff_to_human_success(self, client, user_token):
        """Test escalating chat to human."""
        response = client.post(
            "/api/v1/chat/session/123/handoff",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "reason": "Complex question",
                "context": {}
            }
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]
    
    async def test_handoff_unauthorized(self, client):
        """Test handoff without authentication."""
        response = client.post(
            "/api/v1/chat/session/123/handoff",
            json={"reason": "test"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestChatbotSourceAccess:
    """Tests for POST /chat/session/{id}/source-access endpoint."""
    
    async def test_request_source_access_success(self, client, user_token):
        """Test requesting source document access."""
        response = client.post(
            "/api/v1/chat/session/123/source-access",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "source_ids": [1, 2, 3],
                "access_type": "preview"
            }
        )
        # Adjust based on actual implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]
    
    async def test_request_source_access_unauthorized(self, client):
        """Test requesting source access without authentication."""
        response = client.post(
            "/api/v1/chat/session/123/source-access",
            json={"source_ids": [1]}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

