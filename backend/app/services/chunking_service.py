from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Text chunking (generic — PDF plain text, DOCX, TXT)
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[dict]:
    """Split *text* into overlapping chunks, respecting paragraph boundaries.

    Strategy:
    1. Split on blank lines to get paragraphs.
    2. Accumulate paragraphs until the running character count exceeds
       *chunk_size*, then emit a chunk.
    3. The next chunk starts *overlap* characters back from the end of the
       previous chunk (character-level overlap, not paragraph-level).

    Each returned dict::

        {
            "text": str,
            "chunk_index": int,
            "char_start": int,
            "char_end": int,
        }
    """
    if not text or not text.strip():
        return []

    # Normalise line endings and split into paragraphs
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text.replace("\r\n", "\n"))]
    paragraphs = [p for p in paragraphs if p]

    chunks: list[dict] = []
    current_parts: list[str] = []
    current_len = 0
    char_cursor = 0  # tracks position in the original text

    def _emit(parts: list[str], start: int) -> int:
        """Flush accumulated parts as one chunk. Returns new char_cursor."""
        chunk_text_str = "\n\n".join(parts)
        end = start + len(chunk_text_str)
        chunks.append({
            "text": chunk_text_str,
            "chunk_index": len(chunks),
            "char_start": start,
            "char_end": end,
        })
        return end

    for para in paragraphs:
        para_len = len(para)

        # Paragraph alone exceeds chunk_size — hard-split it by characters
        if para_len > chunk_size:
            # Flush whatever we have first
            if current_parts:
                char_cursor = _emit(current_parts, char_cursor)
                # Apply overlap: step back by `overlap` chars for next chunk start
                char_cursor = max(0, char_cursor - overlap)
                current_parts = []
                current_len = 0

            # Hard-split the large paragraph
            pos = 0
            while pos < para_len:
                end = min(pos + chunk_size, para_len)
                slice_text = para[pos:end]
                chunks.append({
                    "text": slice_text,
                    "chunk_index": len(chunks),
                    "char_start": char_cursor + pos,
                    "char_end": char_cursor + end,
                })
                pos = end - overlap if end < para_len else end
            char_cursor += para_len
            continue

        # Adding this paragraph would exceed chunk_size — emit current batch first
        if current_len + para_len > chunk_size and current_parts:
            char_cursor = _emit(current_parts, char_cursor)
            char_cursor = max(0, char_cursor - overlap)
            current_parts = []
            current_len = 0

        current_parts.append(para)
        current_len += para_len

    # Flush remainder
    if current_parts:
        _emit(current_parts, char_cursor)

    return chunks


# ---------------------------------------------------------------------------
# Transcript chunking (audio / video — uses Whisper segment timestamps)
# ---------------------------------------------------------------------------

_MAX_WORDS_PER_CHUNK = 400
_GAP_THRESHOLD_SECONDS = 3.0


def chunk_transcript_by_segments(segments: list[dict]) -> list[dict]:
    """Group Whisper segments into topic-level chunks.

    A new chunk is started when either:
    - The gap between the end of the last segment and the start of the next
      exceeds ``_GAP_THRESHOLD_SECONDS`` (3 s), or
    - The accumulated word count exceeds ``_MAX_WORDS_PER_CHUNK`` (400 words).

    Each returned dict::

        {
            "text": str,
            "start_time": float,
            "end_time": float,
            "chunk_index": int,
        }
    """
    if not segments:
        return []

    chunks: list[dict] = []
    current_segs: list[dict] = []
    current_words = 0

    def _emit_chunk(segs: list[dict]) -> None:
        text = " ".join(s["text"].strip() for s in segs if s.get("text", "").strip())
        chunks.append({
            "text": text,
            "start_time": round(segs[0]["start"], 3),
            "end_time": round(segs[-1]["end"], 3),
            "chunk_index": len(chunks),
        })

    for i, seg in enumerate(segments):
        seg_text = seg.get("text", "").strip()
        seg_words = len(seg_text.split()) if seg_text else 0

        if current_segs:
            gap = seg.get("start", 0) - current_segs[-1].get("end", 0)
            word_overflow = (current_words + seg_words) > _MAX_WORDS_PER_CHUNK

            if gap > _GAP_THRESHOLD_SECONDS or word_overflow:
                _emit_chunk(current_segs)
                current_segs = []
                current_words = 0

        current_segs.append(seg)
        current_words += seg_words

    if current_segs:
        _emit_chunk(current_segs)

    return chunks


# ---------------------------------------------------------------------------
# PDF page chunking
# ---------------------------------------------------------------------------

_PAGES_PER_CHUNK = 3


def chunk_pdf_by_pages(pages: list[dict]) -> list[dict]:
    """Group PDF pages into chunks of at most ``_PAGES_PER_CHUNK`` pages.

    Each returned dict::

        {
            "text": str,
            "chunk_index": int,
            "page_start": int,
            "page_end": int,
        }
    """
    if not pages:
        return []

    chunks: list[dict] = []

    for batch_start in range(0, len(pages), _PAGES_PER_CHUNK):
        batch = pages[batch_start: batch_start + _PAGES_PER_CHUNK]
        text = "\n\n".join(p.get("text", "").strip() for p in batch if p.get("text", "").strip())
        if not text:
            continue
        chunks.append({
            "text": text,
            "chunk_index": len(chunks),
            "page_start": batch[0]["page_num"],
            "page_end": batch[-1]["page_num"],
        })

    return chunks
