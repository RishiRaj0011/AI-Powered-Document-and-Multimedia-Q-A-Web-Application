"""
Shared pytest fixtures.

- In-memory SQLite replaces PostgreSQL for all tests.
- A lightweight AsyncMock replaces Redis so no real Redis is needed.
- Both get_db import paths (core.database and core.dependencies) are overridden
  so every router that uses either one gets the test session.
"""
from __future__ import annotations

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.database import Base, get_db as db_get_db
from app.core.dependencies import get_db as dep_get_db
from app.core.redis import get_redis

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_engine = create_async_engine(TEST_DATABASE_URL)
_SessionFactory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


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


@pytest_asyncio.fixture(autouse=True)
async def setup_db(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    import app.models  # noqa: F401
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with _SessionFactory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
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
