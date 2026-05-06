"""
Tests for transcription_service, chunking_service, embedding_service,
and the processing pipeline.

ALL external calls are mocked:
  - OpenAI (Whisper + embeddings)
  - Pinecone
  - fitz (PyMuPDF)
  - ffmpeg subprocess
  - filesystem reads/writes
  - DB session (in-memory SQLite via conftest)
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base

# ---------------------------------------------------------------------------
# Shared in-memory DB for pipeline tests
# ---------------------------------------------------------------------------

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_engine = create_async_engine(_TEST_DB_URL)
_SessionFactory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _reset_db():
    import app.models  # noqa: F401
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _whisper_response(text: str = "hello world", language: str = "en", duration: float = 5.0):
    """Fake Whisper verbose_json response object."""
    seg = SimpleNamespace(start=0.0, end=duration, text=text)
    return SimpleNamespace(
        text=text,
        language=language,
        duration=duration,
        segments=[seg],
    )


def _embed_response(texts: list[str], dim: int = 8):
    """Fake OpenAI embeddings response."""
    items = [
        SimpleNamespace(index=i, embedding=[0.1 * (i + 1)] * dim)
        for i in range(len(texts))
    ]
    return SimpleNamespace(data=items)


# ===========================================================================
# transcription_service — PDF
# ===========================================================================

def test_extract_pdf_text_success():
    from app.services.transcription_service import extract_pdf_text

    fake_page = MagicMock()
    fake_page.get_text.return_value = "  Page one content.  "

    fake_doc = MagicMock()
    fake_doc.page_count = 1
    fake_doc.__iter__ = MagicMock(return_value=iter([fake_page]))
    fake_doc.__enter__ = MagicMock(return_value=fake_doc)
    fake_doc.__exit__ = MagicMock(return_value=False)

    with patch("app.services.transcription_service.fitz") as mock_fitz:
        mock_fitz.open.return_value = fake_doc
        result = extract_pdf_text("/fake/doc.pdf")

    assert result["total_pages"] == 1
    assert result["text"] == "Page one content."
    assert result["pages"][0]["page_num"] == 1
    assert result["pages"][0]["text"] == "Page one content."


def test_extract_pdf_empty_pages():
    from app.services.transcription_service import extract_pdf_text

    fake_page = MagicMock()
    fake_page.get_text.return_value = "   "  # whitespace only

    fake_doc = MagicMock()
    fake_doc.page_count = 1
    fake_doc.__iter__ = MagicMock(return_value=iter([fake_page]))
    fake_doc.__enter__ = MagicMock(return_value=fake_doc)
    fake_doc.__exit__ = MagicMock(return_value=False)

    with patch("app.services.transcription_service.fitz") as mock_fitz:
        mock_fitz.open.return_value = fake_doc
        result = extract_pdf_text("/fake/empty.pdf")

    assert result["total_pages"] == 1
    assert result["text"] == ""          # no non-empty pages
    assert result["pages"][0]["text"] == ""


# ===========================================================================
# transcription_service — Audio
# ===========================================================================

@pytest.mark.asyncio
async def test_transcribe_audio_success():
    """Small file (< 25 MB) goes through _transcribe_single directly."""
    from app.services import transcription_service as ts

    fake_resp = _whisper_response("transcribed text", "en", 3.5)
    mock_client = AsyncMock()
    mock_client.audio.transcriptions.create = AsyncMock(return_value=fake_resp)

    with (
        patch.object(ts, "_openai_client", return_value=mock_client),
        patch("builtins.open", MagicMock()),
    ):
        result = await ts._transcribe_single("/fake/audio.mp3", time_offset=0.0)

    assert result["text"] == "transcribed text"
    assert result["language"] == "en"
    assert result["duration"] == 3.5
    assert len(result["segments"]) == 1
    assert result["segments"][0]["start"] == 0.0
    assert result["segments"][0]["end"] == 3.5
    assert result["segments"][0]["text"] == "transcribed text"


@pytest.mark.asyncio
async def test_transcribe_large_file_splits():
    """Files > 25 MB must be split; each chunk transcribed separately."""
    from app.services import transcription_service as ts

    chunk1 = _whisper_response("part one", "en", 600.0)
    chunk2 = _whisper_response("part two", "en", 400.0)

    call_count = 0

    async def _fake_transcribe_single(path, time_offset=0.0):
        nonlocal call_count
        resp = chunk1 if call_count == 0 else chunk2
        call_count += 1
        seg = resp.segments[0]
        return {
            "text": resp.text,
            "segments": [{"start": seg.start + time_offset, "end": seg.end + time_offset, "text": seg.text}],
            "language": resp.language,
            "duration": resp.duration,
        }

    fake_chunks = [("/tmp/chunk_000.mp3", 0), ("/tmp/chunk_001.mp3", 600)]

    with (
        patch.object(ts, "_split_audio", return_value=fake_chunks),
        patch.object(ts, "_transcribe_single", side_effect=_fake_transcribe_single),
        patch("pathlib.Path.unlink"),
    ):
        result = await ts._transcribe_large("/fake/big.mp3")

    assert call_count == 2
    assert "part one" in result["text"]
    assert "part two" in result["text"]
    assert len(result["segments"]) == 2


# ===========================================================================
# transcription_service — get_file_content router
# ===========================================================================

@pytest.mark.asyncio
async def test_get_file_content_pdf():
    from app.services.transcription_service import get_file_content

    pdf_result = {"text": "pdf text", "pages": [{"page_num": 1, "text": "pdf text"}], "total_pages": 1}

    with patch("app.services.transcription_service.extract_pdf_text", return_value=pdf_result):
        result = await get_file_content("/fake/doc.pdf", "pdf")

    assert result["text"] == "pdf text"
    assert result["segments"] is None
    assert result["language"] is None
    assert result["pages"][0]["page_num"] == 1
    assert result["total_pages"] == 1


@pytest.mark.asyncio
async def test_get_file_content_audio():
    from app.services.transcription_service import get_file_content

    audio_result = {
        "text": "audio text", "segments": [{"start": 0.0, "end": 5.0, "text": "audio text"}],
        "language": "en", "duration": 5.0,
    }

    with patch("app.services.transcription_service.transcribe_audio", new=AsyncMock(return_value=audio_result)):
        result = await get_file_content("/fake/audio.mp3", "audio")

    assert result["text"] == "audio text"
    assert result["language"] == "en"
    assert result["duration"] == 5.0
    assert len(result["segments"]) == 1
    assert result["pages"] is None


@pytest.mark.asyncio
async def test_get_file_content_video():
    from app.services.transcription_service import get_file_content

    audio_result = {
        "text": "video transcript", "segments": [{"start": 0.0, "end": 10.0, "text": "video transcript"}],
        "language": "en", "duration": 10.0,
    }

    with (
        patch("app.services.transcription_service.extract_video_audio", return_value="/tmp/extracted.mp3"),
        patch("app.services.transcription_service.transcribe_audio", new=AsyncMock(return_value=audio_result)),
        patch("pathlib.Path.unlink"),
    ):
        result = await get_file_content("/fake/video.mp4", "video")

    assert result["text"] == "video transcript"
    assert result["duration"] == 10.0
    assert result["pages"] is None


# ===========================================================================
# chunking_service
# ===========================================================================

def test_chunk_text_basic():
    from app.services.chunking_service import chunk_text

    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = chunk_text(text, chunk_size=40, overlap=5)

    assert len(chunks) >= 1
    # Every chunk must have required keys
    for c in chunks:
        assert "text" in c
        assert "chunk_index" in c
        assert "char_start" in c
        assert "char_end" in c
    # Indices must be sequential
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))
    # All text must be covered
    combined = " ".join(c["text"] for c in chunks)
    assert "First paragraph" in combined
    assert "Third paragraph" in combined


def test_chunk_text_overlap():
    from app.services.chunking_service import chunk_text

    # Long single paragraph — forces hard split
    text = "word " * 300  # 1500 chars
    chunks = chunk_text(text, chunk_size=200, overlap=20)

    assert len(chunks) > 1
    # char_end of chunk N should be > char_start of chunk N+1 (overlap)
    for i in range(len(chunks) - 1):
        assert chunks[i]["char_end"] > chunks[i + 1]["char_start"] or chunks[i + 1]["char_start"] == 0


def test_chunk_transcript_by_segments():
    from app.services.chunking_service import chunk_transcript_by_segments

    segments = [
        {"start": 0.0,  "end": 2.0,  "text": "Hello world"},
        {"start": 2.1,  "end": 4.0,  "text": "How are you"},
        # 5-second gap → new chunk
        {"start": 9.0,  "end": 11.0, "text": "New topic here"},
        {"start": 11.1, "end": 13.0, "text": "Continuing topic"},
    ]
    chunks = chunk_transcript_by_segments(segments)

    assert len(chunks) == 2
    assert chunks[0]["start_time"] == 0.0
    assert chunks[0]["end_time"] == 4.0
    assert "Hello world" in chunks[0]["text"]
    assert "How are you" in chunks[0]["text"]
    assert chunks[1]["start_time"] == 9.0
    assert "New topic here" in chunks[1]["text"]
    assert [c["chunk_index"] for c in chunks] == [0, 1]


# ===========================================================================
# embedding_service
# ===========================================================================

@pytest.mark.asyncio
async def test_generate_embeddings_batching():
    """250 texts → 3 API calls (batches of 100, 100, 50)."""
    from app.services.embedding_service import generate_embeddings

    texts = [f"text {i}" for i in range(250)]
    call_log: list[int] = []

    async def _fake_create(model, input):
        call_log.append(len(input))
        return _embed_response(input, dim=4)

    mock_client = AsyncMock()
    mock_client.embeddings.create.side_effect = _fake_create

    with patch("app.services.embedding_service.AsyncOpenAI", return_value=mock_client):
        result = await generate_embeddings(texts)

    assert call_log == [100, 100, 50]
    assert len(result) == 250
    assert len(result[0]) == 4  # embedding dimension


@pytest.mark.asyncio
async def test_generate_embeddings_batching_empty():
    from app.services.embedding_service import generate_embeddings

    result = await generate_embeddings([])
    assert result == []


def test_upsert_chunks_batching():
    """220 chunks → 3 upsert calls (100, 100, 20)."""
    from app.services.embedding_service import upsert_chunks

    chunks = [{"text": f"chunk {i}", "chunk_index": i} for i in range(220)]
    embeddings = [[0.1] * 8 for _ in range(220)]

    mock_index = MagicMock()
    upsert_chunks(mock_index, "doc-42", chunks, embeddings)

    assert mock_index.upsert.call_count == 3
    sizes = [len(c.kwargs["vectors"]) for c in mock_index.upsert.call_args_list]
    assert sizes == [100, 100, 20]

    # Verify vector ID format
    first_batch = mock_index.upsert.call_args_list[0].kwargs["vectors"]
    assert first_batch[0]["id"] == "doc-42_chunk_0"
    assert first_batch[0]["metadata"]["doc_id"] == "doc-42"
    assert first_batch[0]["metadata"]["chunk_index"] == 0


def test_search_similar():
    from app.services.embedding_service import search_similar

    mock_index = MagicMock()
    mock_index.query.return_value = {
        "matches": [
            {
                "score": 0.95,
                "metadata": {
                    "text": "relevant chunk",
                    "start_time": 10.0,
                    "end_time": 20.0,
                    "chunk_index": 3,
                },
            },
            {
                "score": 0.80,
                "metadata": {
                    "text": "another chunk",
                    "chunk_index": 7,
                },
            },
        ]
    }

    query_vec = [0.1] * 8
    results = search_similar(mock_index, query_vec, "doc-99", top_k=5)

    mock_index.query.assert_called_once_with(
        vector=query_vec,
        top_k=5,
        filter={"doc_id": {"$eq": "doc-99"}},
        include_metadata=True,
    )
    assert len(results) == 2
    assert results[0]["text"] == "relevant chunk"
    assert results[0]["score"] == 0.95
    assert results[0]["start_time"] == 10.0
    assert results[0]["end_time"] == 20.0
    assert results[0]["chunk_index"] == 3
    assert results[1]["start_time"] is None  # missing from metadata → None


# ===========================================================================
# processing_pipeline
# ===========================================================================

@pytest.mark.asyncio
async def test_process_document_success():
    """Happy path: all steps succeed, status ends as READY."""
    from app.tasks.processing_pipeline import process_document
    from app.models.document import Document, DocumentStatus, DocumentType
    from app.models.user import User

    # Seed DB with a user + document
    async with _SessionFactory() as db:
        user = User(email="pipe@example.com", hashed_password="x", is_active=True)
        db.add(user)
        await db.flush()
        doc = Document(
            owner_id=user.id,
            filename="test.pdf",
            original_filename="test.pdf",
            file_size=1024,
            doc_type=DocumentType.PDF,
            status=DocumentStatus.PENDING,
        )
        db.add(doc)
        await db.commit()
        doc_id = doc.id

    content = {
        "text": "page one text\n\npage two text",
        "segments": None,
        "language": None,
        "duration": None,
        "pages": [
            {"page_num": 1, "text": "page one text"},
            {"page_num": 2, "text": "page two text"},
        ],
        "total_pages": 2,
    }
    fake_embeddings = [[0.1] * 8, [0.2] * 8]
    mock_index = MagicMock()

    with (
        patch("app.tasks.processing_pipeline._make_session_factory", return_value=_SessionFactory),
        patch("app.tasks.processing_pipeline.get_file_content", new=AsyncMock(return_value=content)),
        patch("app.tasks.processing_pipeline.generate_embeddings", new=AsyncMock(return_value=fake_embeddings)),
        patch("app.tasks.processing_pipeline.init_pinecone", return_value=mock_index),
        patch("app.tasks.processing_pipeline.upsert_chunks"),
    ):
        await process_document(doc_id)

    # Verify final DB state
    async with _SessionFactory() as db:
        from sqlalchemy import select
        from app.models.document import Document as D
        from app.models.transcript import Transcript as T
        from app.models.timestamp_chunk import TimestampChunk as TC

        result = await db.execute(select(D).where(D.id == doc_id))
        final_doc = result.scalar_one()
        assert final_doc.status == DocumentStatus.READY
        assert final_doc.chunk_count > 0
        assert final_doc.pinecone_namespace == f"doc-{doc_id}"

        t_result = await db.execute(select(T).where(T.document_id == doc_id))
        transcript = t_result.scalar_one()
        assert "page one text" in transcript.full_text

        tc_result = await db.execute(select(TC).where(TC.document_id == doc_id))
        ts_chunks = tc_result.scalars().all()
        assert len(ts_chunks) > 0


@pytest.mark.asyncio
async def test_process_document_failure_updates_status():
    """If get_file_content raises, status must be set to FAILED with error_message."""
    from app.tasks.processing_pipeline import process_document
    from app.models.document import Document, DocumentStatus, DocumentType
    from app.models.user import User

    async with _SessionFactory() as db:
        user = User(email="fail@example.com", hashed_password="x", is_active=True)
        db.add(user)
        await db.flush()
        doc = Document(
            owner_id=user.id,
            filename="bad.mp3",
            original_filename="bad.mp3",
            file_size=512,
            doc_type=DocumentType.AUDIO,
            status=DocumentStatus.PENDING,
        )
        db.add(doc)
        await db.commit()
        doc_id = doc.id

    with (
        patch("app.tasks.processing_pipeline._make_session_factory", return_value=_SessionFactory),
        patch(
            "app.tasks.processing_pipeline.get_file_content",
            new=AsyncMock(side_effect=RuntimeError("Whisper API unavailable")),
        ),
    ):
        await process_document(doc_id)  # must NOT raise

    async with _SessionFactory() as db:
        from sqlalchemy import select
        from app.models.document import Document as D

        result = await db.execute(select(D).where(D.id == doc_id))
        final_doc = result.scalar_one()
        assert final_doc.status == DocumentStatus.FAILED
        assert "Whisper API unavailable" in (final_doc.error_message or "")
