from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import uuid
from pathlib import Path

import aiofiles
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

logger = logging.getLogger(__name__)

_AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "webm", "ogg", "flac"}
_VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}
_CHUNK_SIZE = 1024 * 1024  # 1 MB


def _extension(filename: str) -> str:
    return Path(filename).suffix.lstrip(".").lower()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

async def validate_file(file: UploadFile) -> None:
    """Raise HTTPException 422 for disallowed extension or oversized file.

    Reads only the first byte to check Content-Length / actual size without
    buffering the whole file into memory.  The real size check happens after
    streaming in save_file(); this guard catches obviously bad requests early.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file has no filename",
        )

    ext = _extension(file.filename)
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"File extension '.{ext}' is not allowed. "
                f"Accepted: {', '.join(sorted(settings.ALLOWED_EXTENSIONS))}"
            ),
        )

    # Content-Length header check (not always present, but cheap when it is)
    content_length = file.size  # set by Starlette from Content-Length header
    if content_length is not None:
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if content_length > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"File size {content_length / 1024 / 1024:.1f} MB exceeds "
                    f"the {settings.MAX_FILE_SIZE_MB} MB limit"
                ),
            )


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

async def save_file(file: UploadFile, user_id: int | str) -> str:
    """Stream *file* to disk and return the saved absolute path.

    Path format: ``{UPLOAD_DIR}/{user_id}/{uuid4}_{original_filename}``

    Raises HTTPException 422 if the file exceeds MAX_FILE_SIZE_MB after
    streaming (catches cases where Content-Length was absent or spoofed).
    """
    ext = _extension(file.filename)
    safe_name = f"{uuid.uuid4()}_{Path(file.filename).name}"
    dest_dir = Path(settings.UPLOAD_DIR) / str(user_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / safe_name

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    written = 0

    try:
        async with aiofiles.open(dest_path, "wb") as out:
            while True:
                chunk = await file.read(_CHUNK_SIZE)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    # Clean up partial file before raising
                    await out.close()
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"File exceeds the {settings.MAX_FILE_SIZE_MB} MB limit"
                        ),
                    )
                await out.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        dest_path.unlink(missing_ok=True)
        logger.error("Failed to save uploaded file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save uploaded file",
        ) from exc

    return str(dest_path)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def delete_file(file_path: str) -> None:
    """Delete *file_path* from disk.  Silently ignores missing files."""
    try:
        Path(file_path).unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Could not delete file %r: %s", file_path, exc)


# ---------------------------------------------------------------------------
# File info
# ---------------------------------------------------------------------------

def get_file_info(file_path: str) -> dict:
    """Return metadata about the file at *file_path*.

    Returns::

        {
            "size_bytes": int,
            "extension": str,
            "is_audio": bool,
            "is_video": bool,
            "is_pdf": bool,
            "duration_seconds": float | None,   # audio/video only
        }

    ``duration_seconds`` is populated via ``ffprobe`` when available.
    If ffprobe is not installed or fails, ``duration_seconds`` is ``None``
    and a warning is logged — the caller must handle ``None`` gracefully.
    """
    path = Path(file_path)
    ext = path.suffix.lstrip(".").lower()

    is_audio = ext in _AUDIO_EXTENSIONS
    is_video = ext in _VIDEO_EXTENSIONS
    duration: float | None = None

    if is_audio or is_video:
        duration = _probe_duration(file_path)

    return {
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "extension": ext,
        "is_audio": is_audio,
        "is_video": is_video,
        "is_pdf": ext == "pdf",
        "duration_seconds": duration,
    }


def _probe_duration(file_path: str) -> float | None:
    """Run ffprobe to extract duration.  Returns None on any failure."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        file_path,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            logger.warning("ffprobe non-zero exit for %r: %s", file_path, result.stderr)
            return None
        data = json.loads(result.stdout)
        raw = data.get("format", {}).get("duration")
        return float(raw) if raw is not None else None
    except FileNotFoundError:
        logger.warning("ffprobe not found — duration will be unavailable")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("ffprobe timed out for %r", file_path)
        return None
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        logger.warning("ffprobe output parse error for %r: %s", file_path, exc)
        return None
