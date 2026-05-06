"""
Auth endpoint tests.

Fixtures are defined in conftest.py (in-memory SQLite + AsyncClient).
Redis is mocked via a lightweight fake so tests have no external dependencies.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.database import Base, get_db
from app.core.dependencies import get_current_user
from app.core.redis import get_redis

# ---------------------------------------------------------------------------
# In-memory DB + fake Redis shared across this module
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_engine = create_async_engine(TEST_DB_URL)
_SessionFactory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


def _make_fake_redis() -> AsyncMock:
    """Return a mock that behaves like an aioredis.Redis for auth tests."""
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
async def _reset_db():
    """Recreate all tables before each test and drop them after."""
    import app.models  # noqa: F401 — register models on Base.metadata
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """AsyncClient with DB and Redis overrides applied."""
    fake_redis = _make_fake_redis()

    async def _override_db():
        async with _SessionFactory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def _override_redis():
        return fake_redis

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_USER = {"email": "alice@example.com", "password": "Secure123"}
_VALID_USER_2 = {"email": "bob@example.com", "password": "Another456"}


async def _register(client: AsyncClient, payload: dict | None = None) -> dict:
    payload = payload or _VALID_USER
    r = await client.post("/api/v1/auth/register", json=payload)
    return r.json()


async def _login(client: AsyncClient, payload: dict | None = None) -> dict:
    payload = payload or _VALID_USER
    r = await client.post("/api/v1/auth/login", json=payload)
    return r.json()


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# Registration
# ===========================================================================

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    r = await client.post("/api/v1/auth/register", json=_VALID_USER)

    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20
    assert len(body["refresh_token"]) > 20
    # Embedded user object
    assert body["user"]["email"] == _VALID_USER["email"]
    assert body["user"]["is_active"] is True
    assert "id" in body["user"]
    assert "hashed_password" not in body["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await _register(client)
    r = await client.post("/api/v1/auth/register", json=_VALID_USER)

    assert r.status_code == 400
    assert "already exists" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "Secure123"},
    )

    assert r.status_code == 422
    errors = r.json()["detail"]
    assert any("email" in str(e).lower() for e in errors)


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "Ab1"},
    )

    assert r.status_code == 422
    errors = r.json()["detail"]
    assert any("8" in str(e) or "password" in str(e).lower() for e in errors)


# ===========================================================================
# Login
# ===========================================================================

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await _register(client)
    r = await client.post("/api/v1/auth/login", json=_VALID_USER)

    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20
    assert len(body["refresh_token"]) > 20
    assert body["user"]["email"] == _VALID_USER["email"]
    # access and refresh tokens must be different strings
    assert body["access_token"] != body["refresh_token"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await _register(client)
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": _VALID_USER["email"], "password": "WrongPass99"},
    )

    assert r.status_code == 401
    assert "incorrect" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "Secure123"},
    )

    # Same 401 as wrong password — no user enumeration
    assert r.status_code == 401
    assert "incorrect" in r.json()["detail"].lower()


# ===========================================================================
# /me
# ===========================================================================

@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient):
    tokens = await _register(client)
    r = await client.get("/api/v1/auth/me", headers=_auth_header(tokens["access_token"]))

    assert r.status_code == 200
    body = r.json()
    assert body["email"] == _VALID_USER["email"]
    assert body["is_active"] is True
    assert "id" in body
    assert "hashed_password" not in body


@pytest.mark.asyncio
async def test_get_me_no_token(client: AsyncClient):
    r = await client.get("/api/v1/auth/me")

    assert r.status_code == 401
    assert r.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_get_me_invalid_token(client: AsyncClient):
    r = await client.get(
        "/api/v1/auth/me",
        headers=_auth_header("this.is.not.a.valid.jwt"),
    )

    assert r.status_code == 401
    detail = r.json()["detail"].lower()
    assert "invalid" in detail or "token" in detail


# ===========================================================================
# Token refresh
# ===========================================================================

@pytest.mark.asyncio
async def test_refresh_tokens_success(client: AsyncClient):
    tokens = await _register(client)
    old_access = tokens["access_token"]
    old_refresh = tokens["refresh_token"]

    r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )

    assert r.status_code == 200
    body = r.json()
    assert len(body["access_token"]) > 20
    assert len(body["refresh_token"]) > 20
    # New tokens must differ from the originals (new jti + iat)
    assert body["access_token"] != old_access
    assert body["refresh_token"] != old_refresh
    assert body["user"]["email"] == _VALID_USER["email"]


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails(client: AsyncClient):
    """Passing an access token to /refresh must be rejected."""
    tokens = await _register(client)

    r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["access_token"]},  # wrong token type
    )

    assert r.status_code == 401
    assert "refresh" in r.json()["detail"].lower()


# ===========================================================================
# Logout
# ===========================================================================

@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient):
    tokens = await _register(client)
    access = tokens["access_token"]

    # 1. Confirm /me works before logout
    pre = await client.get("/api/v1/auth/me", headers=_auth_header(access))
    assert pre.status_code == 200

    # 2. Logout
    logout_r = await client.post("/api/v1/auth/logout", headers=_auth_header(access))
    assert logout_r.status_code == 200
    assert "logged out" in logout_r.json()["message"].lower()

    # 3. Same token must now be rejected
    post = await client.get("/api/v1/auth/me", headers=_auth_header(access))
    assert post.status_code == 401
    assert "revoked" in post.json()["detail"].lower()
