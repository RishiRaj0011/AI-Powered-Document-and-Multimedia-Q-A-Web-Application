"""
Shared pytest fixtures.

- Uses Dockerized PostgreSQL for testing to ensure PG-specific features (JSONB, Enums) are validated
- A lightweight AsyncMock replaces Redis so no real Redis is needed
- Both get_db import paths (core.database and core.dependencies) are overridden
  so every router that uses either one gets the test session
"""
from __future__ import annotations

import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from testcontainers.postgres import PostgresContainer

from app.main import app
from app.core.database import Base, get_db as db_get_db
from app.core.dependencies import get_db as dep_get_db
from app.core.redis import get_redis

# Use PostgreSQL test container for production parity
_postgres_container: PostgresContainer | None = None
_test_engine = None
_SessionFactory = None


def _make_fake_redis() -> AsyncMock:
    fake = AsyncMock()
    _store: dict[str, str] = {}

    async def _set(key, value, ex=None):
        _store[key] = str(value)

    async def _exists(key):
        return 1 if key in _store else 0

    async def _get(key):
        return _store.get(key)

    async def _delete(key):
        _store.pop(key, None)

    async def _ping():
        return True

    fake.set.side_effect = _set
    fake.exists.side_effect = _exists
    fake.get.side_effect = _get
    fake.delete.side_effect = _delete
    fake.ping.side_effect = _ping
    return fake


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgres_container():
    """Start a PostgreSQL container for the entire test session."""
    global _postgres_container
    
    # Check if we should use a real PostgreSQL container or fallback to SQLite
    use_postgres = os.getenv("USE_POSTGRES_TESTS", "true").lower() == "true"
    
    if not use_postgres:
        # Fallback to SQLite for environments without Docker
        yield None
        return
    
    _postgres_container = PostgresContainer("postgres:15-alpine")
    _postgres_container.start()
    
    yield _postgres_container
    
    _postgres_container.stop()


@pytest_asyncio.fixture(scope="session")
async def test_engine(postgres_container):
    """Create a test database engine."""
    global _test_engine, _SessionFactory
    
    if postgres_container:
        # Use PostgreSQL container
        connection_url = postgres_container.get_connection_url().replace(
            "psycopg2", "asyncpg"
        )
    else:
        # Fallback to SQLite
        connection_url = "sqlite+aiosqlite:///:memory:"
    
    _test_engine = create_async_engine(connection_url, echo=False)
    _SessionFactory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)
    
    # Create all tables
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield _test_engine
    
    # Drop all tables
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await _test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def setup_db(test_engine, monkeypatch):
    """Setup database for each test."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    
    # Import models to ensure they're registered
    import app.models  # noqa: F401
    
    yield
    
    # Clean up tables after each test
    async with test_engine.begin() as conn:
        # Truncate all tables instead of dropping/recreating for better performance
        await conn.execute(Base.metadata.drop_all(bind=conn))
        await conn.execute(Base.metadata.create_all(bind=conn))


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Provide a database session for a test."""
    async with _SessionFactory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Provide an HTTP client with overridden dependencies."""
    fake_redis = _make_fake_redis()

    async def _override_db():
        yield db_session

    async def _override_redis():
        return fake_redis

    # Override both import paths for get_db
    app.dependency_overrides[db_get_db] = _override_db
    app.dependency_overrides[dep_get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
