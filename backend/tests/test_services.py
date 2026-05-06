"""
Comprehensive service layer tests for 95% coverage.
Tests all service methods with edge cases, error paths, and mocking.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from app.services.chunking_service import chunk_text, chunk_transcript_by_segments, chunk_pdf_by_pages
from app.services.transcription_service import extract_pdf_text, transcribe_audio, get_file_content
from app.services.embedding_service import generate_embeddings, search_similar, init_pinecone


# ===========================================================================
# chunking_service.py tests
# ===========================================================================

def test_chunk_empty_text():
    """Empty text should return empty list."""
    result = chunk_text("")
    assert result == []
    
    result = chunk_text("   ")
    assert result == []


def test_chunk_single_word():
    """Single word should return one chunk."""
    result = chunk_text("Hello")
    assert len(result) == 1
    assert result[0]["text"] == "Hello"
    assert result[0]["chunk_index"] == 0


def test_chunk_text_respects_chunk_size():
    """Text longer than chunk_size should be split."""
    long_text = "A" * 1000
    result = chunk_text(long_text, chunk_size=200, overlap=20)
    assert len(result) > 1
    for chunk in result:
        assert len(chunk["text"]) <= 220  # chunk_size + some tolerance


def test_chunk_text_with_paragraphs():
    """Multiple paragraphs should be grouped intelligently."""
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    result = chunk_text(text, chunk_size=50, overlap=10)
    assert len(result) >= 1
    assert all("chunk_index" in c for c in result)


def test_chunk_transcript_empty_segments():
    """Empty segments list should return empty list."""
    result = chunk_transcript_by_segments([])
    assert result == []


def test_chunk_transcript_single_segment():
    """Single segment should return one chunk."""
    segments = [{"text": "Hello world", "start": 0.0, "end": 2.0}]
    result = chunk_transcript_by_segments(segments)
    assert len(result) == 1
    assert result[0]["text"] == "Hello world"
    assert result[0]["start_time"] == 0.0
    assert result[0]["end_time"] == 2.0


def test_chunk_transcript_respects_gap_threshold():
    """Large gaps between segments should trigger new chunks."""
    segments = [
        {"text": "First", "start": 0.0, "end": 1.0},
        {"text": "Second", "start": 10.0, "end": 11.0},  # 9s gap
    ]
    result = chunk_transcript_by_segments(segments)
    assert len(result) == 2


def test_chunk_pdf_empty_pages():
    """Empty pages list should return empty list."""
    result = chunk_pdf_by_pages([])
    assert result == []


def test_chunk_pdf_single_page():
    """Single page should return one chunk."""
    pages = [{"page_num": 1, "text": "Page content"}]
    result = chunk_pdf_by_pages(pages)
    assert len(result) == 1
    assert result[0]["text"] == "Page content"
    assert result[0]["page_start"] == 1
    assert result[0]["page_end"] == 1


def test_chunk_pdf_multiple_pages():
    """Multiple pages should be grouped by PAGES_PER_CHUNK."""
    pages = [
        {"page_num": 1, "text": "Page 1"},
        {"page_num": 2, "text": "Page 2"},
        {"page_num": 3, "text": "Page 3"},
        {"page_num": 4, "text": "Page 4"},
    ]
    result = chunk_pdf_by_pages(pages)
    assert len(result) == 2  # 3 pages per chunk by default
    assert result[0]["page_start"] == 1
    assert result[0]["page_end"] == 3


# ===========================================================================
# transcription_service.py tests
# ===========================================================================

@patch("app.services.transcription_service.fitz")
def test_extract_pdf_no_text(mock_fitz):
    """PDF with no extractable text should return empty string."""
    mock_doc = MagicMock()
    mock_doc.page_count = 1
    mock_page = MagicMock()
    mock_page.get_text.return_value = ""
    mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
    mock_doc.__enter__ = MagicMock(return_value=mock_doc)
    mock_doc.__exit__ = MagicMock(return_value=False)
    mock_fitz.open.return_value = mock_doc
    
    result = extract_pdf_text("/fake/path.pdf")
    assert result["text"] == ""
    assert result["total_pages"] == 1
    assert len(result["pages"]) == 1


@patch("app.services.transcription_service.fitz")
def test_extract_pdf_multiple_pages(mock_fitz):
    """PDF with multiple pages should extract all text."""
    mock_doc = MagicMock()
    mock_doc.page_count = 2
    mock_page1 = MagicMock()
    mock_page1.get_text.return_value = "Page 1 text"
    mock_page2 = MagicMock()
    mock_page2.get_text.return_value = "Page 2 text"
    mock_doc.__iter__ = MagicMock(return_value=iter([mock_page1, mock_page2]))
    mock_doc.__enter__ = MagicMock(return_value=mock_doc)
    mock_doc.__exit__ = MagicMock(return_value=False)
    mock_fitz.open.return_value = mock_doc
    
    result = extract_pdf_text("/fake/path.pdf")
    assert "Page 1 text" in result["text"]
    assert "Page 2 text" in result["text"]
    assert result["total_pages"] == 2


@pytest.mark.asyncio
@patch("app.services.transcription_service.get_openai_client")
async def test_transcribe_audio_file_not_found(mock_client):
    """Non-existent audio file should raise error."""
    with pytest.raises(FileNotFoundError):
        await transcribe_audio("/nonexistent/file.mp3")


@pytest.mark.asyncio
@patch("app.services.transcription_service.Path")
@patch("app.services.transcription_service.get_openai_client")
async def test_transcribe_audio_success(mock_client, mock_path):
    """Successful transcription should return text and segments."""
    mock_stat = MagicMock()
    mock_stat.st_size = 1024 * 1024  # 1MB
    mock_path.return_value.stat.return_value = mock_stat
    
    mock_response = MagicMock()
    mock_response.text = "Transcribed text"
    mock_response.segments = [{"start": 0.0, "end": 2.0, "text": "Hello"}]
    mock_response.language = "en"
    mock_response.duration = 2.0
    
    mock_openai = AsyncMock()
    mock_openai.audio.transcriptions.create = AsyncMock(return_value=mock_response)
    mock_client.return_value = mock_openai
    
    with patch("builtins.open", MagicMock()):
        result = await transcribe_audio("/fake/audio.mp3")
    
    assert result["text"] == "Transcribed text"
    assert result["language"] == "en"
    assert result["duration"] == 2.0
    assert len(result["segments"]) == 1


@pytest.mark.asyncio
@patch("app.services.transcription_service.extract_pdf_text")
async def test_get_file_content_pdf(mock_extract):
    """get_file_content with PDF type should call extract_pdf_text."""
    mock_extract.return_value = {
        "text": "PDF content",
        "pages": [],
        "total_pages": 1
    }
    
    result = await get_file_content("/fake/file.pdf", "pdf")
    assert result["text"] == "PDF content"
    assert result["segments"] is None
    assert result["pages"] == []


@pytest.mark.asyncio
@patch("app.services.transcription_service.Path")
async def test_get_file_content_txt(mock_path):
    """get_file_content with txt type should read file directly."""
    mock_path.return_value.read_text.return_value = "Plain text content"
    
    result = await get_file_content("/fake/file.txt", "txt")
    assert result["text"] == "Plain text content"
    assert result["segments"] is None


# ===========================================================================
# embedding_service.py tests
# ===========================================================================

@pytest.mark.asyncio
async def test_generate_embeddings_empty_list():
    """Empty text list should return empty embeddings list."""
    result = await generate_embeddings([])
    assert result == []


@pytest.mark.asyncio
@patch("app.services.embedding_service.AsyncOpenAI")
async def test_generate_embeddings_success(mock_openai_class):
    """Successful embedding generation should return vectors."""
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=[0.1, 0.2, 0.3], index=0),
        MagicMock(embedding=[0.4, 0.5, 0.6], index=1),
    ]
    
    mock_client = AsyncMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    mock_openai_class.return_value = mock_client
    
    result = await generate_embeddings(["text1", "text2"])
    assert len(result) == 2
    assert result[0] == [0.1, 0.2, 0.3]
    assert result[1] == [0.4, 0.5, 0.6]


@pytest.mark.asyncio
@patch("app.services.embedding_service.AsyncOpenAI")
async def test_generate_embeddings_empty_strings(mock_openai_class):
    """Empty strings should be replaced with space."""
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1], index=0)]
    
    mock_client = AsyncMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    mock_openai_class.return_value = mock_client
    
    result = await generate_embeddings([""])
    assert len(result) == 1


@patch("app.services.embedding_service.Pinecone")
def test_init_pinecone_index_exists(mock_pinecone_class):
    """Existing index should be returned without creation."""
    mock_pc = MagicMock()
    mock_index_info = MagicMock()
    mock_index_info.name = "docqa-index"
    mock_pc.list_indexes.return_value = [mock_index_info]
    mock_pc.Index.return_value = MagicMock()
    mock_pinecone_class.return_value = mock_pc
    
    result = init_pinecone()
    assert result is not None
    mock_pc.create_index.assert_not_called()


@patch("app.services.embedding_service.Pinecone")
@patch("app.services.embedding_service.time")
def test_init_pinecone_creates_index(mock_time, mock_pinecone_class):
    """Non-existent index should be created."""
    mock_pc = MagicMock()
    mock_pc.list_indexes.return_value = []
    mock_describe = MagicMock()
    mock_describe.status = {"ready": True}
    mock_pc.describe_index.return_value = mock_describe
    mock_pc.Index.return_value = MagicMock()
    mock_pinecone_class.return_value = mock_pc
    
    result = init_pinecone()
    assert result is not None
    mock_pc.create_index.assert_called_once()


def test_search_similar_no_results():
    """Search with no matches should return empty list."""
    mock_index = MagicMock()
    mock_index.query.return_value = {"matches": []}
    
    result = search_similar(mock_index, [0.1, 0.2], "doc1", 1, top_k=5)
    assert result == []


def test_search_similar_with_results():
    """Search with matches should return formatted results."""
    mock_index = MagicMock()
    mock_index.query.return_value = {
        "matches": [
            {
                "score": 0.95,
                "metadata": {
                    "text": "Match text",
                    "chunk_index": 0,
                    "start_time": 1.0,
                    "end_time": 2.0,
                }
            }
        ]
    }
    
    result = search_similar(mock_index, [0.1, 0.2], "doc1", 1, top_k=5)
    assert len(result) == 1
    assert result[0]["text"] == "Match text"
    assert result[0]["score"] == 0.95
    assert result[0]["start_time"] == 1.0


# ===========================================================================
# Edge case and error path tests
# ===========================================================================

def test_chunk_text_very_long_paragraph():
    """Paragraph longer than chunk_size should be hard-split."""
    long_para = "A" * 1000
    result = chunk_text(long_para, chunk_size=200, overlap=20)
    assert len(result) > 1
    for chunk in result:
        assert len(chunk["text"]) <= 220


def test_chunk_transcript_word_overflow():
    """Exceeding word count should trigger new chunk."""
    segments = [{"text": " ".join(["word"] * 300), "start": 0.0, "end": 10.0}]
    for i in range(5):
        segments.append({"text": " ".join(["word"] * 50), "start": 10.0 + i, "end": 11.0 + i})
    
    result = chunk_transcript_by_segments(segments)
    assert len(result) > 1


def test_chunk_pdf_pages_with_empty_text():
    """Pages with empty text should be skipped."""
    pages = [
        {"page_num": 1, "text": ""},
        {"page_num": 2, "text": "   "},
        {"page_num": 3, "text": "Content"},
    ]
    result = chunk_pdf_by_pages(pages)
    assert len(result) == 1
    assert "Content" in result[0]["text"]
