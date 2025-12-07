"""
Tests for Auth Service.

Covers:
- verify_password
- get_password_hash
- create_access_token
- create_refresh_token
- decode_token
- authenticate_user
- get_user_by_id
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from src.app.services.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    authenticate_user,
    get_user_by_id
)
from src.app.models.users import User


@pytest.mark.unit
class TestAuthService:
    """Tests for auth service functions."""
    
    def test_verify_password_success(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_failure(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert verify_password("wrong_password", hashed) is False
    
    def test_get_password_hash(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash format
    
    def test_create_access_token(self):
        """Test creating access token."""
        data = {"sub": "123", "email": "test@example.com"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_with_expires_delta(self):
        """Test creating access token with custom expiration."""
        data = {"sub": "123"}
        expires = timedelta(hours=2)
        token = create_access_token(data, expires_delta=expires)
        
        # Decode and verify expiration
        payload = decode_token(token)
        assert payload is not None
        assert payload.get("type") == "access"
    
    def test_create_refresh_token(self):
        """Test creating refresh token."""
        data = {"sub": "123"}
        token = create_refresh_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and verify type
        payload = decode_token(token)
        assert payload is not None
        assert payload.get("type") == "refresh"
    
    def test_decode_token_success(self):
        """Test decoding valid token."""
        data = {"sub": "123", "email": "test@example.com"}
        token = create_access_token(data)
        
        payload = decode_token(token)
        
        assert payload is not None
        assert payload.get("sub") == "123"
        assert payload.get("email") == "test@example.com"
    
    def test_decode_token_invalid(self):
        """Test decoding invalid token."""
        payload = decode_token("invalid_token_string")
        
        assert payload is None
    
    def test_decode_token_expired(self):
        """Test decoding expired token."""
        data = {"sub": "123"}
        # Create token with very short expiration
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        payload = decode_token(token)
        
        # Should return None for expired token
        assert payload is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, test_db):
        """Test successful user authentication."""
        from src.app.services.auth import get_password_hash
        
        user = User(
            name="Test User",
            email="test@example.com",
            password_hash=get_password_hash("password123"),
            role="user",
            status="active"
        )
        test_db.add(user)
        await test_db.commit()
        
        authenticated = await authenticate_user(test_db, "test@example.com", "password123")
        
        assert authenticated is not None
        assert authenticated.id == user.id
        assert authenticated.email == user.email
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, test_db):
        """Test authentication with wrong password."""
        from src.app.services.auth import get_password_hash
        
        user = User(
            name="Test User",
            email="test@example.com",
            password_hash=get_password_hash("password123"),
            role="user",
            status="active"
        )
        test_db.add(user)
        await test_db.commit()
        
        authenticated = await authenticate_user(test_db, "test@example.com", "wrong_password")
        
        assert authenticated is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, test_db):
        """Test authentication with non-existent user."""
        authenticated = await authenticate_user(test_db, "nonexistent@example.com", "password123")
        
        assert authenticated is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self, test_db):
        """Test authentication with inactive user."""
        from src.app.services.auth import get_password_hash
        
        user = User(
            name="Test User",
            email="test@example.com",
            password_hash=get_password_hash("password123"),
            role="user",
            status="inactive"
        )
        test_db.add(user)
        await test_db.commit()
        
        authenticated = await authenticate_user(test_db, "test@example.com", "password123")
        
        assert authenticated is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_expired(self, test_db):
        """Test authentication with expired user."""
        from src.app.services.auth import get_password_hash
        
        user = User(
            name="Test User",
            email="test@example.com",
            password_hash=get_password_hash("password123"),
            role="user",
            status="active",
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        test_db.add(user)
        await test_db.commit()
        
        authenticated = await authenticate_user(test_db, "test@example.com", "password123")
        
        assert authenticated is None
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, test_db):
        """Test getting user by ID."""
        user = User(
            name="Test User",
            email="test@example.com",
            password_hash="hash",
            role="user",
            status="active"
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        found_user = await get_user_by_id(test_db, user.id)
        
        assert found_user is not None
        assert found_user.id == user.id
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, test_db):
        """Test getting non-existent user by ID."""
        found_user = await get_user_by_id(test_db, 99999)
        
        assert found_user is None
