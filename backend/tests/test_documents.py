"""
Document endpoint tests.

File system operations (validate_file, save_file, delete_file, get_file_info)
are patched so no real files are created or read during the test run.
The background processing task is also patched to a no-op.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db as db_get_db
from app.core.dependencies import get_db as dep_get_db
from app.core.redis import get_redis
from app.main import app
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.user import User
from app.repositories.user_repository import UserRepository

# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_engine = create_async_engine(TEST_DB_URL)
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

    fake.set.side_effect = _set
    fake.exists.side_effect = _exists
    fake.get.side_effect = _get
    fake.delete.side_effect = _delete
    return fake


@pytest_asyncio.fixture(autouse=True)
async def _reset_db():
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

    app.dependency_overrides[db_get_db] = _override_db
    app.dependency_overrides[dep_get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_user_and_token(client: AsyncClient) -> tuple[int, str]:
    """Register a user and return (user_id, access_token)."""
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "uploader@example.com", "password": "Upload123"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["user"]["id"], body["access_token"]


async def _create_second_user_and_token(client: AsyncClient) -> tuple[int, str]:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "Other1234"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["user"]["id"], body["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _pdf_file(name: str = "test.pdf", size: int = 512) -> tuple:
    return ("file", (name, io.BytesIO(b"%PDF-1.4 " + b"x" * size), "application/pdf"))


def _mp3_file(name: str = "audio.mp3", size: int = 512) -> tuple:
    return ("file", (name, io.BytesIO(b"ID3" + b"\x00" * size), "audio/mpeg"))


def _fake_file_info(size: int = 1024, ext: str = "pdf") -> dict:
    return {
        "size_bytes": size,
        "extension": ext,
        "is_audio": ext in {"mp3", "wav", "m4a", "webm"},
        "is_video": ext in {"mp4", "mov"},
        "is_pdf": ext == "pdf",
        "duration_seconds": None,
    }


# Patch targets — functions imported into the router module
_VALIDATE = "app.api.v1.documents.validate_file"
_SAVE = "app.api.v1.documents.save_file"
_DELETE_FILE = "app.api.v1.documents.delete_file"
_GET_INFO = "app.api.v1.documents.get_file_info"
_PROCESS_BG = "app.api.v1.documents._process_document"


# ===========================================================================
# Upload
# ===========================================================================

@pytest.mark.asyncio
async def test_upload_pdf_success(client: AsyncClient):
    _, token = await _create_user_and_token(client)

    with (
        patch(_VALIDATE, new=AsyncMock(return_value=None)),
        patch(_SAVE, new=AsyncMock(return_value="/uploads/1/abc_test.pdf")),
        patch(_GET_INFO, return_value=_fake_file_info(2048, "pdf")),
        patch(_PROCESS_BG, new=AsyncMock(return_value=None)),
    ):
        r = await client.post(
            "/api/v1/documents/upload",
            headers=_auth(token),
            files=[_pdf_file()],
        )

    assert r.status_code == 201, r.text
    body = r.json()
    assert body["file_type"] == "pdf"
    assert body["status"] == "pending"
    assert body["file_size"] == 2048
    assert "id" in body
    assert body["user_id"] is not None


@pytest.mark.asyncio
async def test_upload_audio_success(client: AsyncClient):
    _, token = await _create_user_and_token(client)

    with (
        patch(_VALIDATE, new=AsyncMock(return_value=None)),
        patch(_SAVE, new=AsyncMock(return_value="/uploads/1/abc_audio.mp3")),
        patch(_GET_INFO, return_value=_fake_file_info(4096, "mp3")),
        patch(_PROCESS_BG, new=AsyncMock(return_value=None)),
    ):
        r = await client.post(
            "/api/v1/documents/upload",
            headers=_auth(token),
            files=[_mp3_file()],
        )

    assert r.status_code == 201, r.text
    body = r.json()
    assert body["file_type"] == "audio"
    assert body["status"] == "pending"
    assert body["file_size"] == 4096


@pytest.mark.asyncio
async def test_upload_invalid_extension(client: AsyncClient):
    _, token = await _create_user_and_token(client)

    from fastapi import HTTPException
    async def _reject(_):
        raise HTTPException(
            status_code=422,
            detail="File extension '.exe' is not allowed. Accepted: mp3, mp4, pdf, wav",
        )

    with patch(_VALIDATE, new=_reject):
        r = await client.post(
            "/api/v1/documents/upload",
            headers=_auth(token),
            files=[("file", ("malware.exe", io.BytesIO(b"MZ"), "application/octet-stream"))],
        )

    assert r.status_code == 422
    assert ".exe" in r.json()["detail"]


@pytest.mark.asyncio
async def test_upload_file_too_large(client: AsyncClient):
    _, token = await _create_user_and_token(client)

    from fastapi import HTTPException
    async def _too_large(_):
        raise HTTPException(
            status_code=422,
            detail="File size 60.0 MB exceeds the 50 MB limit",
        )

    with patch(_VALIDATE, new=_too_large):
        r = await client.post(
            "/api/v1/documents/upload",
            headers=_auth(token),
            files=[_pdf_file(size=1)],
        )

    assert r.status_code == 422
    assert "50 MB" in r.json()["detail"]


@pytest.mark.asyncio
async def test_upload_unauthenticated(client: AsyncClient):
    r = await client.post(
        "/api/v1/documents/upload",
        files=[_pdf_file()],
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Not authenticated"


# ===========================================================================
# List
# ===========================================================================

@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient):
    _, token = await _create_user_and_token(client)

    r = await client.get("/api/v1/documents/", headers=_auth(token))

    assert r.status_code == 200
    body = r.json()
    assert body["documents"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_list_documents_with_items(client: AsyncClient):
    _, token = await _create_user_and_token(client)

    # Upload two documents
    for name, ext, ftype in [("a.pdf", "pdf", "pdf"), ("b.mp3", "mp3", "mp3")]:
        with (
            patch(_VALIDATE, new=AsyncMock(return_value=None)),
            patch(_SAVE, new=AsyncMock(return_value=f"/uploads/1/x_{name}")),
            patch(_GET_INFO, return_value=_fake_file_info(1024, ext)),
            patch(_PROCESS_BG, new=AsyncMock(return_value=None)),
        ):
            await client.post(
                "/api/v1/documents/upload",
                headers=_auth(token),
                files=[("file", (name, io.BytesIO(b"data"), "application/octet-stream"))],
            )

    r = await client.get("/api/v1/documents/", headers=_auth(token))

    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert len(body["documents"]) == 2
    file_types = {d["file_type"] for d in body["documents"]}
    assert "pdf" in file_types
    assert "audio" in file_types


# ===========================================================================
# Get single
# ===========================================================================

@pytest.mark.asyncio
async def test_get_document_success(client: AsyncClient):
    _, token = await _create_user_and_token(client)

    with (
        patch(_VALIDATE, new=AsyncMock(return_value=None)),
        patch(_SAVE, new=AsyncMock(return_value="/uploads/1/x_test.pdf")),
        patch(_GET_INFO, return_value=_fake_file_info(1024, "pdf")),
        patch(_PROCESS_BG, new=AsyncMock(return_value=None)),
    ):
        upload_r = await client.post(
            "/api/v1/documents/upload",
            headers=_auth(token),
            files=[_pdf_file()],
        )
    doc_id = upload_r.json()["id"]

    r = await client.get(f"/api/v1/documents/{doc_id}", headers=_auth(token))

    assert r.status_code == 200
    body = r.json()
    assert body["id"] == doc_id
    assert body["file_type"] == "pdf"
    assert body["status"] == "pending"


@pytest.mark.asyncio
async def test_get_document_not_found(client: AsyncClient):
    _, token = await _create_user_and_token(client)

    r = await client.get("/api/v1/documents/99999", headers=_auth(token))

    assert r.status_code == 404
    assert "99999" in r.json()["detail"]


@pytest.mark.asyncio
async def test_get_document_wrong_user(client: AsyncClient):
    """User A uploads; User B must get 404, not the document."""
    _, token_a = await _create_user_and_token(client)
    _, token_b = await _create_second_user_and_token(client)

    with (
        patch(_VALIDATE, new=AsyncMock(return_value=None)),
        patch(_SAVE, new=AsyncMock(return_value="/uploads/1/x_test.pdf")),
        patch(_GET_INFO, return_value=_fake_file_info(1024, "pdf")),
        patch(_PROCESS_BG, new=AsyncMock(return_value=None)),
    ):
        upload_r = await client.post(
            "/api/v1/documents/upload",
            headers=_auth(token_a),
            files=[_pdf_file()],
        )
    doc_id = upload_r.json()["id"]

    r = await client.get(f"/api/v1/documents/{doc_id}", headers=_auth(token_b))

    assert r.status_code == 404  # not 403 — don't leak existence


# ===========================================================================
# Delete
# ===========================================================================

@pytest.mark.asyncio
async def test_delete_document_success(client: AsyncClient):
    _, token = await _create_user_and_token(client)

    with (
        patch(_VALIDATE, new=AsyncMock(return_value=None)),
        patch(_SAVE, new=AsyncMock(return_value="/uploads/1/x_test.pdf")),
        patch(_GET_INFO, return_value=_fake_file_info(1024, "pdf")),
        patch(_PROCESS_BG, new=AsyncMock(return_value=None)),
    ):
        upload_r = await client.post(
            "/api/v1/documents/upload",
            headers=_auth(token),
            files=[_pdf_file()],
        )
    doc_id = upload_r.json()["id"]

    with patch(_DELETE_FILE, return_value=None):
        del_r = await client.delete(f"/api/v1/documents/{doc_id}", headers=_auth(token))

    assert del_r.status_code == 204

    # Confirm it's gone
    get_r = await client.get(f"/api/v1/documents/{doc_id}", headers=_auth(token))
    assert get_r.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_not_found(client: AsyncClient):
    _, token = await _create_user_and_token(client)

    r = await client.delete("/api/v1/documents/99999", headers=_auth(token))

    assert r.status_code == 404
    assert "99999" in r.json()["detail"]


# ===========================================================================
# Status polling
# ===========================================================================

@pytest.mark.asyncio
async def test_get_status_pending(client: AsyncClient):
    _, token = await _create_user_and_token(client)

    with (
        patch(_VALIDATE, new=AsyncMock(return_value=None)),
        patch(_SAVE, new=AsyncMock(return_value="/uploads/1/x_test.pdf")),
        patch(_GET_INFO, return_value=_fake_file_info(1024, "pdf")),
        patch(_PROCESS_BG, new=AsyncMock(return_value=None)),
    ):
        upload_r = await client.post(
            "/api/v1/documents/upload",
            headers=_auth(token),
            files=[_pdf_file()],
        )
    doc_id = upload_r.json()["id"]

    r = await client.get(f"/api/v1/documents/{doc_id}/status", headers=_auth(token))

    assert r.status_code == 200
    body = r.json()
    assert body["doc_id"] == doc_id
    assert body["status"] == "pending"
    assert body["progress_percent"] == 0
    assert body["error_message"] is None


@pytest.mark.asyncio
async def test_get_status_ready(client: AsyncClient, db_session: AsyncSession):
    _, token = await _create_user_and_token(client)

    with (
        patch(_VALIDATE, new=AsyncMock(return_value=None)),
        patch(_SAVE, new=AsyncMock(return_value="/uploads/1/x_test.pdf")),
        patch(_GET_INFO, return_value=_fake_file_info(1024, "pdf")),
        patch(_PROCESS_BG, new=AsyncMock(return_value=None)),
    ):
        upload_r = await client.post(
            "/api/v1/documents/upload",
            headers=_auth(token),
            files=[_pdf_file()],
        )
    doc_id = upload_r.json()["id"]

    # Manually flip status to READY in the test DB session
    from app.repositories.document_repository import DocumentRepository
    repo = DocumentRepository(db_session)
    await repo.update_status(doc_id, DocumentStatus.READY)
    await db_session.commit()

    r = await client.get(f"/api/v1/documents/{doc_id}/status", headers=_auth(token))

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["progress_percent"] == 100
    assert body["error_message"] is None
