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
    """Split *text* into overlapping chunks with character-level overlap.

    Strategy:
    1. Flatten text into a single string (preserving paragraph breaks)
    2. Use sliding window with character-level overlap
    3. Ensure no semantic gaps between chunks

    Each returned dict::

        {
            "text": str,
            "chunk_index": int,
            "char_start": int,
            "char_end": int,
            "topic_summary": str,  # 100-char snippet as default
        }
    """
    if not text or not text.strip():
        return []

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text_len = len(text)
    
    chunks: list[dict] = []
    start = 0
    
    while start < text_len:
        # Calculate end position for this chunk
        end = min(start + chunk_size, text_len)
        
        # Extract chunk text
        chunk_text = text[start:end]
        
        # If not at the end, try to break at a natural boundary (newline, space, punctuation)
        if end < text_len:
            # Look for paragraph break first (double newline)
            last_para_break = chunk_text.rfind("\n\n")
            if last_para_break > chunk_size * 0.5:  # Only if it's in the latter half
                end = start + last_para_break + 2
                chunk_text = text[start:end]
            else:
                # Look for single newline
                last_newline = chunk_text.rfind("\n")
                if last_newline > chunk_size * 0.5:
                    end = start + last_newline + 1
                    chunk_text = text[start:end]
                else:
                    # Look for space
                    last_space = chunk_text.rfind(" ")
                    if last_space > chunk_size * 0.5:
                        end = start + last_space + 1
                        chunk_text = text[start:end]
        
        # Generate topic_summary as 100-char snippet
        topic_summary = chunk_text.strip()[:100]
        if len(chunk_text.strip()) > 100:
            topic_summary += "..."
        
        chunks.append({
            "text": chunk_text.strip(),
            "chunk_index": len(chunks),
            "char_start": start,
            "char_end": end,
            "topic_summary": topic_summary,
        })
        
        # Move start position with overlap
        # Ensure overlap is applied at character level across boundaries
        start = end - overlap
        
        # Prevent infinite loop if overlap >= chunk_size
        if start <= chunks[-1]["char_start"]:
            start = end
        
        # Skip if remaining text is too small
        if text_len - start < overlap:
            break
    
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
            "topic_summary": str,  # 100-char snippet as default
        }
    """
    if not segments:
        return []

    chunks: list[dict] = []
    current_segs: list[dict] = []
    current_words = 0

    def _emit_chunk(segs: list[dict]) -> None:
        text = " ".join(s["text"].strip() for s in segs if s.get("text", "").strip())
        # Generate topic_summary as 100-char snippet
        topic_summary = text[:100].strip()
        if len(text) > 100:
            topic_summary += "..."
        chunks.append({
            "text": text,
            "start_time": round(segs[0]["start"], 3),
            "end_time": round(segs[-1]["end"], 3),
            "chunk_index": len(chunks),
            "topic_summary": topic_summary,
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
            "topic_summary": str,  # 100-char snippet as default
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
        # Generate topic_summary as 100-char snippet
        topic_summary = text[:100].strip()
        if len(text) > 100:
            topic_summary += "..."
        chunks.append({
            "text": text,
            "chunk_index": len(chunks),
            "page_start": batch[0]["page_num"],
            "page_end": batch[-1]["page_num"],
            "topic_summary": topic_summary,
        })

    return chunks
