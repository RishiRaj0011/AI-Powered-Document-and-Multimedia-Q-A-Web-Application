"""
Chat endpoint tests.

All external calls are mocked:
  - OpenAI (chat completions, streaming, embeddings)
  - Pinecone (search_similar, init_pinecone)
  - Redis (via conftest fake)

DB uses in-memory SQLite via conftest fixtures.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
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
from app.models.timestamp_chunk import TimestampChunk
from app.models.user import User

# ---------------------------------------------------------------------------
# Test DB
# ---------------------------------------------------------------------------

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_engine = create_async_engine(_TEST_DB_URL)
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
    # Expose store for assertions
    fake._store = _store
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
async def fake_redis():
    return _make_fake_redis()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, fake_redis: AsyncMock):
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

async def _register_and_login(client: AsyncClient, email: str = "chat@example.com") -> tuple[int, str]:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Chat1234"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["user"]["id"], body["access_token"]


async def _seed_ready_document(db: AsyncSession, user_id: int) -> int:
    doc = Document(
        owner_id=user_id,
        filename="test.pdf",
        original_filename="test.pdf",
        file_size=1024,
        doc_type=DocumentType.PDF,
        status=DocumentStatus.READY,
        pinecone_namespace="doc-1",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc.id


async def _seed_timestamp_chunks(db: AsyncSession, doc_id: int) -> None:
    for i in range(3):
        chunk = TimestampChunk(
            document_id=doc_id,
            start_time=float(i * 10),
            end_time=float(i * 10 + 9),
            text_content=f"Chunk {i} content about topic {i}",
            topic_summary=f"Topic {i}",
            chunk_index=i,
        )
        db.add(chunk)
    await db.commit()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# Patch targets
_GENERATE_EMBEDDINGS = "app.services.chat_service.generate_embeddings"
_INIT_PINECONE = "app.services.chat_service.init_pinecone"
_SEARCH_SIMILAR = "app.services.chat_service.search_similar"
_OPENAI_CLIENT = "app.services.chat_service._openai_client"

_FAKE_CHUNKS = [
    {"text": "relevant content", "score": 0.95, "chunk_index": 0, "start_time": 0.0, "end_time": 9.0},
    {"text": "more content", "score": 0.80, "chunk_index": 1, "start_time": 10.0, "end_time": 19.0},
]


def _mock_openai_response(answer: str = "The answer is 42.") -> AsyncMock:
    usage = SimpleNamespace(total_tokens=150)
    choice = SimpleNamespace(message=SimpleNamespace(content=answer))
    response = SimpleNamespace(choices=[choice], usage=usage)
    mock = AsyncMock()
    mock.chat.completions.create = AsyncMock(return_value=response)
    return mock


# ===========================================================================
# Session creation
# ===========================================================================

@pytest.mark.asyncio
async def test_create_session_success(client: AsyncClient, db_session: AsyncSession):
    user_id, token = await _register_and_login(client)
    doc_id = await _seed_ready_document(db_session, user_id)

    r = await client.post(
        "/api/v1/chat/sessions",
        json={"document_id": doc_id},
        headers=_auth(token),
    )

    assert r.status_code == 201, r.text
    body = r.json()
    assert body["document_id"] == doc_id
    assert body["user_id"] == user_id
    assert body["message_count"] == 0
    assert "id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_create_session_document_not_found(client: AsyncClient):
    _, token = await _register_and_login(client)

    r = await client.post(
        "/api/v1/chat/sessions",
        json={"document_id": 99999},
        headers=_auth(token),
    )

    assert r.status_code == 404
    assert "99999" in r.json()["detail"]


# ===========================================================================
# List sessions
# ===========================================================================

@pytest.mark.asyncio
async def test_list_sessions_empty(client: AsyncClient):
    _, token = await _register_and_login(client)

    r = await client.get("/api/v1/chat/sessions", headers=_auth(token))

    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_sessions_with_data(client: AsyncClient, db_session: AsyncSession):
    user_id, token = await _register_and_login(client)
    doc_id = await _seed_ready_document(db_session, user_id)

    # Create two sessions
    for _ in range(2):
        await client.post(
            "/api/v1/chat/sessions",
            json={"document_id": doc_id},
            headers=_auth(token),
        )

    r = await client.get("/api/v1/chat/sessions", headers=_auth(token))

    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    for s in body:
        assert s["document_id"] == doc_id
        assert "message_count" in s
        assert "created_at" in s


# ===========================================================================
# Send message
# ===========================================================================

@pytest.mark.asyncio
async def test_send_message_success(client: AsyncClient, db_session: AsyncSession):
    user_id, token = await _register_and_login(client)
    doc_id = await _seed_ready_document(db_session, user_id)

    session_r = await client.post(
        "/api/v1/chat/sessions",
        json={"document_id": doc_id},
        headers=_auth(token),
    )
    session_id = session_r.json()["id"]

    mock_client = _mock_openai_response("The answer is 42.")

    with (
        patch(_GENERATE_EMBEDDINGS, new=AsyncMock(return_value=[[0.1] * 8])),
        patch(_INIT_PINECONE, return_value=MagicMock()),
        patch(_SEARCH_SIMILAR, return_value=_FAKE_CHUNKS),
        patch(_OPENAI_CLIENT, return_value=mock_client),
    ):
        r = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"question": "What is the answer?"},
            headers=_auth(token),
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answer"] == "The answer is 42."
    assert body["session_id"] == session_id
    assert "message_id" in body
    assert isinstance(body["sources"], list)
    assert len(body["sources"]) == 2
    assert body["sources"][0]["score"] == 0.95
    assert isinstance(body["timestamp_references"], list)


@pytest.mark.asyncio
async def test_send_message_with_timestamps(client: AsyncClient, db_session: AsyncSession):
    """Chunks with start_time/end_time must appear in timestamp_references."""
    user_id, token = await _register_and_login(client)
    doc_id = await _seed_ready_document(db_session, user_id)

    session_r = await client.post(
        "/api/v1/chat/sessions",
        json={"document_id": doc_id},
        headers=_auth(token),
    )
    session_id = session_r.json()["id"]

    mock_client = _mock_openai_response("At 0:10 the speaker says...")

    with (
        patch(_GENERATE_EMBEDDINGS, new=AsyncMock(return_value=[[0.1] * 8])),
        patch(_INIT_PINECONE, return_value=MagicMock()),
        patch(_SEARCH_SIMILAR, return_value=_FAKE_CHUNKS),
        patch(_OPENAI_CLIENT, return_value=mock_client),
    ):
        r = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"question": "What happens at 10 seconds?"},
            headers=_auth(token),
        )

    assert r.status_code == 200
    body = r.json()
    ts_refs = body["timestamp_references"]
    assert len(ts_refs) == 2
    assert ts_refs[0]["start_time"] == 0.0
    assert ts_refs[0]["end_time"] == 9.0
    assert ts_refs[1]["start_time"] == 10.0


@pytest.mark.asyncio
async def test_send_message_invalid_session(client: AsyncClient):
    _, token = await _register_and_login(client)

    r = await client.post(
        "/api/v1/chat/sessions/99999/messages",
        json={"question": "Hello?"},
        headers=_auth(token),
    )

    assert r.status_code == 404
    assert "Session" in r.json()["detail"] or "not found" in r.json()["detail"].lower()


# ===========================================================================
# Streaming
# ===========================================================================

@pytest.mark.asyncio
async def test_stream_question_success(client: AsyncClient, db_session: AsyncSession):
    """SSE stream must yield data: lines with token content."""
    user_id, token = await _register_and_login(client)
    doc_id = await _seed_ready_document(db_session, user_id)

    session_r = await client.post(
        "/api/v1/chat/sessions",
        json={"document_id": doc_id},
        headers=_auth(token),
    )
    session_id = session_r.json()["id"]

    # Build a fake async streaming context manager
    tokens = ["Hello", " world", "!"]

    async def _fake_stream_gen():
        for tok in tokens:
            choice = SimpleNamespace(delta=SimpleNamespace(content=tok))
            yield SimpleNamespace(choices=[choice])

    class _FakeStream:
        async def __aenter__(self):
            return _fake_stream_gen()

        async def __aexit__(self, *args):
            pass

    mock_client = AsyncMock()
    mock_client.chat.completions.stream.return_value = _FakeStream()

    with (
        patch(_GENERATE_EMBEDDINGS, new=AsyncMock(return_value=[[0.1] * 8])),
        patch(_INIT_PINECONE, return_value=MagicMock()),
        patch(_SEARCH_SIMILAR, return_value=_FAKE_CHUNKS),
        patch(_OPENAI_CLIENT, return_value=mock_client),
    ):
        r = await client.get(
            f"/api/v1/chat/sessions/{session_id}/stream",
            params={"question": "Tell me something"},
            headers=_auth(token),
        )

    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]

    lines = r.text.strip().split("\n\n")
    # Filter non-empty lines
    data_lines = [l for l in lines if l.startswith("data:")]
    assert len(data_lines) >= 1

    # All non-DONE lines must be "data: <something>"
    content_lines = [l for l in data_lines if l != "data: [DONE]"]
    for line in content_lines:
        assert line.startswith("data: ")
        assert len(line) > len("data: ")


@pytest.mark.asyncio
async def test_stream_question_yields_done(client: AsyncClient, db_session: AsyncSession):
    """The final SSE event must be 'data: [DONE]'."""
    user_id, token = await _register_and_login(client)
    doc_id = await _seed_ready_document(db_session, user_id)

    session_r = await client.post(
        "/api/v1/chat/sessions",
        json={"document_id": doc_id},
        headers=_auth(token),
    )
    session_id = session_r.json()["id"]

    async def _fake_stream_gen():
        choice = SimpleNamespace(delta=SimpleNamespace(content="answer"))
        yield SimpleNamespace(choices=[choice])

    class _FakeStream:
        async def __aenter__(self):
            return _fake_stream_gen()

        async def __aexit__(self, *args):
            pass

    mock_client = AsyncMock()
    mock_client.chat.completions.stream.return_value = _FakeStream()

    with (
        patch(_GENERATE_EMBEDDINGS, new=AsyncMock(return_value=[[0.1] * 8])),
        patch(_INIT_PINECONE, return_value=MagicMock()),
        patch(_SEARCH_SIMILAR, return_value=_FAKE_CHUNKS),
        patch(_OPENAI_CLIENT, return_value=mock_client),
    ):
        r = await client.get(
            f"/api/v1/chat/sessions/{session_id}/stream",
            params={"question": "Stream this"},
            headers=_auth(token),
        )

    assert r.status_code == 200
    # Last non-empty SSE event must be [DONE]
    events = [e for e in r.text.split("\n\n") if e.strip()]
    assert events[-1].strip() == "data: [DONE]"


# ===========================================================================
# Summary
# ===========================================================================

@pytest.mark.asyncio
async def test_get_summary_cached(
    client: AsyncClient,
    db_session: AsyncSession,
    fake_redis: AsyncMock,
):
    """When Redis has a cached summary, OpenAI must NOT be called."""
    user_id, token = await _register_and_login(client)
    doc_id = await _seed_ready_document(db_session, user_id)

    cached_value = json.dumps({
        "summary": "Cached summary text",
        "topics": [{"label": "Topic A", "start_time": 0.0, "end_time": None, "chunk_index": None}],
    })
    fake_redis._store[f"summary:{doc_id}"] = cached_value

    with patch(_OPENAI_CLIENT) as mock_oc:
        r = await client.get(
            f"/api/v1/documents/{doc_id}/summary",
            headers=_auth(token),
        )
        mock_oc.assert_not_called()

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"] == "Cached summary text"
    assert body["topics"][0]["label"] == "Topic A"


@pytest.mark.asyncio
async def test_get_summary_not_cached(
    client: AsyncClient,
    db_session: AsyncSession,
    fake_redis: AsyncMock,
):
    """Cache miss: OpenAI is called, result is cached, response is correct."""
    user_id, token = await _register_and_login(client)
    doc_id = await _seed_ready_document(db_session, user_id)
    await _seed_timestamp_chunks(db_session, doc_id)

    openai_payload = json.dumps({
        "summary": "This document covers three topics.",
        "topics": [
            {"label": "Introduction", "start_time": 0.0},
            {"label": "Main content", "start_time": 10.0},
        ],
    })
    choice = SimpleNamespace(message=SimpleNamespace(content=openai_payload))
    response = SimpleNamespace(choices=[choice], usage=SimpleNamespace(total_tokens=200))
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=response)

    with patch(_OPENAI_CLIENT, return_value=mock_client):
        r = await client.get(
            f"/api/v1/documents/{doc_id}/summary",
            headers=_auth(token),
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"] == "This document covers three topics."
    assert len(body["topics"]) == 2
    assert body["topics"][0]["label"] == "Introduction"
    assert body["topics"][0]["start_time"] == 0.0

    # Verify result was cached
    cache_key = f"summary:{doc_id}"
    assert cache_key in fake_redis._store
    cached = json.loads(fake_redis._store[cache_key])
    assert cached["summary"] == "This document covers three topics."


# ===========================================================================
# Topics
# ===========================================================================

@pytest.mark.asyncio
async def test_get_topics_success(client: AsyncClient, db_session: AsyncSession):
    user_id, token = await _register_and_login(client)
    doc_id = await _seed_ready_document(db_session, user_id)
    await _seed_timestamp_chunks(db_session, doc_id)

    r = await client.get(
        f"/api/v1/documents/{doc_id}/topics",
        headers=_auth(token),
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 3
    # Ordered by chunk_index
    assert body[0]["label"] == "Topic 0"
    assert body[0]["start_time"] == 0.0
    assert body[0]["end_time"] == 9.0
    assert body[0]["chunk_index"] == 0
    assert body[1]["label"] == "Topic 1"


@pytest.mark.asyncio
async def test_get_topics_empty(client: AsyncClient, db_session: AsyncSession):
    """Document with no timestamp chunks returns empty list."""
    user_id, token = await _register_and_login(client)
    doc_id = await _seed_ready_document(db_session, user_id)
    # No chunks seeded

    r = await client.get(
        f"/api/v1/documents/{doc_id}/topics",
        headers=_auth(token),
    )

    assert r.status_code == 200
    assert r.json() == []
