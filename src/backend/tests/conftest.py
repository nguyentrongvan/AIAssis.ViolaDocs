"""
Pytest configuration and shared fixtures for all tests.
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.main import create_app
from src.app.db import get_session
from src.app.models.base import Base
from src.app.models.users import User
from src.app.models.documents import Document, DocumentVersion
from src.app.models.devices import Device
from src.app.models.groups import DocumentGroup
from src.app.models.workflows import Workflow, Task
from src.app.models.ai import AIJob
from src.app.models.audit import AuditEvent
from src.app.services.auth import get_password_hash, create_access_token


# Test database URL (in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with in-memory SQLite."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session_maker() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
def client(test_db: AsyncSession) -> Generator[TestClient, None, None]:
    """Create a test client with overridden database session."""
    app = create_app()
    
    async def override_get_session():
        yield test_db
    
    app.dependency_overrides[get_session] = override_get_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_user(test_db: AsyncSession) -> User:
    """Create an admin user for testing."""
    user = User(
        name="Admin User",
        email="admin@test.com",
        password_hash=get_password_hash("admin123"),
        role="admin",
        status="active"
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def staff_user(test_db: AsyncSession) -> User:
    """Create a staff user for testing."""
    user = User(
        name="Staff User",
        email="staff@test.com",
        password_hash=get_password_hash("staff123"),
        role="staff",
        status="active"
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def regular_user(test_db: AsyncSession) -> User:
    """Create a regular user for testing."""
    user = User(
        name="Regular User",
        email="user@test.com",
        password_hash=get_password_hash("user123"),
        role="user",
        status="active"
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def inactive_user(test_db: AsyncSession) -> User:
    """Create an inactive user for testing."""
    user = User(
        name="Inactive User",
        email="inactive@test.com",
        password_hash=get_password_hash("inactive123"),
        role="user",
        status="inactive"
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def expired_user(test_db: AsyncSession) -> User:
    """Create an expired user for testing."""
    user = User(
        name="Expired User",
        email="expired@test.com",
        password_hash=get_password_hash("expired123"),
        role="user",
        status="active",
        expires_at=datetime.utcnow() - timedelta(days=1)
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Generate access token for admin user."""
    return create_access_token(data={"sub": str(admin_user.id), "email": admin_user.email})


@pytest.fixture
def staff_token(staff_user: User) -> str:
    """Generate access token for staff user."""
    return create_access_token(data={"sub": str(staff_user.id), "email": staff_user.email})


@pytest.fixture
def user_token(regular_user: User) -> str:
    """Generate access token for regular user."""
    return create_access_token(data={"sub": str(regular_user.id), "email": regular_user.email})


@pytest.fixture
async def test_document(test_db: AsyncSession, regular_user: User) -> Document:
    """Create a test document."""
    doc = Document(
        title="Test Document",
        source="web",
        owner_id=regular_user.id,
        mime="application/pdf",
        size=1024,
        checksum="abc123",
        status="ready"
    )
    test_db.add(doc)
    await test_db.commit()
    await test_db.refresh(doc)
    return doc


@pytest.fixture
async def test_document_version(test_db: AsyncSession, test_document: Document, regular_user: User) -> DocumentVersion:
    """Create a test document version."""
    version = DocumentVersion(
        document_id=test_document.id,
        version_no=1,
        blob_uri="s3://bucket/doc.pdf",
        created_by=regular_user.id,
        checksum="abc123",
        size=1024,
        status="ready"
    )
    test_db.add(version)
    await test_db.commit()
    await test_db.refresh(version)
    return version


@pytest.fixture
async def test_device(test_db: AsyncSession) -> Device:
    """Create a test device."""
    device = Device(
        name="Test Scanner",
        location="Office 1",
        capabilities=["scan", "print"],
        status="online"
    )
    test_db.add(device)
    await test_db.commit()
    await test_db.refresh(device)
    return device
