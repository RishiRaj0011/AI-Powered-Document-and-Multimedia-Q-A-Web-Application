from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore[assignment]

from fastapi import HTTPException, status
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# Whisper hard limit is 25 MB
_WHISPER_MAX_BYTES = 25 * 1024 * 1024
# Target chunk duration when splitting (seconds)
_SPLIT_CHUNK_SECONDS = 600  # 10 min


_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    """Get or create the singleton OpenAI client."""
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not configured")
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


# ---------------------------------------------------------------------------
# FFmpeg availability check
# ---------------------------------------------------------------------------

async def _check_ffmpeg() -> bool:
    """Check if ffmpeg is available on the system."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-version",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.communicate()
        return proc.returncode == 0
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.warning(f"FFmpeg check failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Audio transcription
# ---------------------------------------------------------------------------

async def transcribe_audio(file_path: str) -> dict:
    """Transcribe an audio file using OpenAI Whisper.

    If the file exceeds 25 MB it is split into ≤10-minute chunks via ffmpeg,
    each chunk is transcribed separately, and the results are merged.

    Returns::

        {
            "text": str,
            "segments": [{"start": float, "end": float, "text": str}, ...],
            "language": str,
            "duration": float,
        }
    """
    file_size = Path(file_path).stat().st_size
    if file_size > _WHISPER_MAX_BYTES:
        return await _transcribe_large(file_path)
    return await _transcribe_single(file_path, time_offset=0.0)


async def _transcribe_single(file_path: str, time_offset: float = 0.0) -> dict:
    client = get_openai_client()
    with open(file_path, "rb") as fh:
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=fh,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    segments = []
    raw_segments = getattr(response, "segments", None) or []
    for seg in raw_segments:
        segments.append({
            "start": round(float(seg.get("start", 0)) + time_offset, 3),
            "end": round(float(seg.get("end", 0)) + time_offset, 3),
            "text": seg.get("text", "").strip(),
        })

    duration = float(getattr(response, "duration", 0) or 0)
    return {
        "text": (getattr(response, "text", "") or "").strip(),
        "segments": segments,
        "language": getattr(response, "language", "en") or "en",
        "duration": duration,
    }


async def _transcribe_large(file_path: str) -> dict:
    """Split file into chunks and transcribe each, merging results."""
    if not await _check_ffmpeg():
        # Fallback: try to send full file if under 25MB
        logger.warning("ffmpeg not available, attempting full file transcription")
        return await _transcribe_single(file_path, time_offset=0.0)
    
    chunk_paths = await _split_audio(file_path, _SPLIT_CHUNK_SECONDS)
    try:
        merged_text: list[str] = []
        merged_segments: list[dict] = []
        total_duration = 0.0
        language = "en"

        for chunk_path, time_offset in chunk_paths:
            result = await _transcribe_single(chunk_path, time_offset=time_offset)
            merged_text.append(result["text"])
            merged_segments.extend(result["segments"])
            total_duration = max(total_duration, time_offset + result["duration"])
            language = result["language"]

        return {
            "text": " ".join(merged_text),
            "segments": merged_segments,
            "language": language,
            "duration": total_duration,
        }
    finally:
        for chunk_path, _ in chunk_paths:
            Path(chunk_path).unlink(missing_ok=True)


async def _split_audio(file_path: str, chunk_seconds: int) -> list[tuple[str, float]]:
    """Use ffmpeg to split *file_path* into fixed-duration chunks.

    Returns list of (chunk_path, time_offset_seconds).
    Raises HTTPException if ffmpeg is not available.
    """
    tmp_dir = tempfile.mkdtemp(prefix="docqa_split_")
    pattern = os.path.join(tmp_dir, "chunk_%03d.mp3")

    cmd = [
        "ffmpeg", "-y",
        "-i", file_path,
        "-f", "segment",
        "-segment_time", str(chunk_seconds),
        "-c", "copy",
        pattern,
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg split failed: {result.stderr}")
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Video processing unavailable: ffmpeg not installed. Please upload audio files directly."
        )

    chunks = sorted(Path(tmp_dir).glob("chunk_*.mp3"))
    if not chunks:
        raise RuntimeError("ffmpeg produced no output chunks")

    return [(str(p), i * chunk_seconds) for i, p in enumerate(chunks)]


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def extract_pdf_text(file_path: str) -> dict:
    """Extract text from a PDF using PyMuPDF.

    Returns::

        {
            "text": str,
            "pages": [{"page_num": int, "text": str}, ...],
            "total_pages": int,
        }
    """
    if fitz is None:  # pragma: no cover
        raise RuntimeError("PyMuPDF is not installed. Run: pip install PyMuPDF")

    pages: list[dict] = []
    full_parts: list[str] = []

    with fitz.open(file_path) as doc:
        total_pages = doc.page_count
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            text = text.strip()
            pages.append({"page_num": page_num, "text": text})
            if text:
                full_parts.append(text)

    return {
        "text": "\n\n".join(full_parts),
        "pages": pages,
        "total_pages": total_pages,
    }


# ---------------------------------------------------------------------------
# Video audio extraction
# ---------------------------------------------------------------------------

async def extract_video_audio(file_path: str) -> str:
    """Extract the audio track from a video file to a temp .mp3.

    Returns the path to the extracted audio file.
    Raises HTTPException if ffmpeg is not available or fails.
    """
    if not await _check_ffmpeg():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Video processing unavailable: ffmpeg not installed. Please upload audio files directly."
        )
    
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp3", prefix="docqa_audio_")
    os.close(tmp_fd)

    cmd = [
        "ffmpeg", "-y",
        "-i", file_path,
        "-vn",                  # drop video stream
        "-acodec", "libmp3lame",
        "-q:a", "4",
        tmp_path,
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            Path(tmp_path).unlink(missing_ok=True)
            raise RuntimeError(f"ffmpeg audio extraction failed: {result.stderr}")
    except FileNotFoundError:
        Path(tmp_path).unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Video processing unavailable: ffmpeg not installed. Please upload audio files directly."
        )

    return tmp_path


# ---------------------------------------------------------------------------
# Unified router
# ---------------------------------------------------------------------------

async def get_file_content(file_path: str, file_type: str) -> dict:
    """Dispatch to the correct extractor and return a unified content dict.

    Args:
        file_path: Absolute path to the file on disk.
        file_type: One of ``"pdf"``, ``"audio"``, ``"video"``,
                   ``"docx"``, ``"txt"``.

    Returns::

        {
            "text": str,
            "segments": list[dict] | None,   # None for non-audio/video
            "language": str | None,
            "duration": float | None,
            "pages": list[dict] | None,      # None for non-PDF
            "total_pages": int | None,
        }
    """
    ft = file_type.lower()

    if ft == "pdf":
        result = await asyncio.to_thread(extract_pdf_text, file_path)
        return {
            "text": result["text"],
            "segments": None,
            "language": None,
            "duration": None,
            "pages": result["pages"],
            "total_pages": result["total_pages"],
        }

    if ft == "audio":
        result = await transcribe_audio(file_path)
        return {
            "text": result["text"],
            "segments": result["segments"],
            "language": result["language"],
            "duration": result["duration"],
            "pages": None,
            "total_pages": None,
        }

    if ft == "video":
        audio_path = await asyncio.to_thread(extract_video_audio, file_path)
        try:
            result = await transcribe_audio(audio_path)
        finally:
            Path(audio_path).unlink(missing_ok=True)
        return {
            "text": result["text"],
            "segments": result["segments"],
            "language": result["language"],
            "duration": result["duration"],
            "pages": None,
            "total_pages": None,
        }

    # docx / txt — plain text read; callers should pre-extract with LangChain loaders
    # but we provide a fallback here so the pipeline never hard-fails on these types
    text = await asyncio.to_thread(Path(file_path).read_text, errors="replace")
    return {
        "text": text,
        "segments": None,
        "language": None,
        "duration": None,
        "pages": None,
        "total_pages": None,
    }
