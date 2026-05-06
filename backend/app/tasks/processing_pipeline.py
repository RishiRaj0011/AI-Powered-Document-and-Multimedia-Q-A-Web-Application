from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.document import DocumentStatus, DocumentType
from app.models.timestamp_chunk import TimestampChunk
from app.models.transcript import Transcript
from app.repositories.document_repository import DocumentRepository
from app.services.chunking_service import (
    chunk_pdf_by_pages,
    chunk_text,
    chunk_transcript_by_segments,
)
from app.services.embedding_service import generate_embeddings, init_pinecone, upsert_chunks
from app.services.transcription_service import get_file_content

logger = logging.getLogger(__name__)

# Map DocumentType enum values to the string keys get_file_content expects
_TYPE_MAP: dict[DocumentType, str] = {
    DocumentType.PDF: "pdf",
    DocumentType.AUDIO: "audio",
    DocumentType.VIDEO: "video",
    DocumentType.DOCX: "docx",
    DocumentType.TXT: "txt",
}


async def process_document(document_id: int) -> None:
    """Full ingestion pipeline for a single document.

    Steps
    -----
    1. Update status → PROCESSING
    2. Fetch document record from DB
    3. Extract content (transcription / PDF / plain text)
    4. Save Transcript record
    5. Chunk content
    6. Save TimestampChunk records
    7. Generate embeddings
    8. Upsert to Pinecone
    9. Update status → READY (with chunk_count + namespace)

    On any exception: update status → FAILED with the error message.
    """
    async with AsyncSessionLocal() as db:
        try:
            await _run_pipeline(db, document_id)
        except Exception as e:
            await db.rollback()
            async with AsyncSessionLocal() as err_db:
                try:
                    await DocumentRepository(err_db).update_status(
                        document_id,
                        DocumentStatus.FAILED,
                        error_message=f"{type(e).__name__}: {e}"
                    )
                    await err_db.commit()
                except Exception as inner:
                    logger.error(
                        "Could not update FAILED status for doc %d: %s", document_id, inner
                    )


async def _run_pipeline(db: AsyncSession, document_id: int) -> None:
    """Execute the full processing pipeline within a session."""
    repo = DocumentRepository(db)

    # ── Step 1: mark as processing ────────────────────────────────────
    await repo.update_status(document_id, DocumentStatus.PROCESSING)
    await db.commit()

    # ── Step 2: fetch document ────────────────────────────────────
    doc = await repo.get_by_id(document_id)
    if doc is None:
        raise ValueError(f"Document {document_id} not found in database")

    file_path = str(Path(settings.UPLOAD_DIR) / str(doc.owner_id) / doc.filename)
    file_type_str = _TYPE_MAP.get(doc.doc_type, "txt")

    # ── Step 3: extract content ───────────────────────────────────
    logger.info("Extracting content for doc %d (%s)", document_id, file_type_str)
    content = await get_file_content(file_path, file_type_str)

    # ── Step 4: save Transcript ───────────────────────────────────
    transcript = Transcript(
        document_id=document_id,
        full_text=content["text"],
        language=content.get("language"),
        duration_seconds=content.get("duration"),
    )
    db.add(transcript)
    await db.flush()

    # ── Step 5: chunk content ─────────────────────────────────────
    logger.info("Chunking doc %d", document_id)
    chunks = _build_chunks(content, file_type_str)

    # ── Step 6: save TimestampChunk records ───────────────────────
    for chunk in chunks:
        ts_chunk = TimestampChunk(
            document_id=document_id,
            start_time=chunk.get("start_time", 0.0),
            end_time=chunk.get("end_time", 0.0),
            text_content=chunk["text"],
            topic_summary=None,
            chunk_index=chunk["chunk_index"],
        )
        db.add(ts_chunk)
    await db.flush()

    # ── Step 7: generate embeddings ───────────────────────────────
    logger.info("Generating embeddings for %d chunks (doc %d)", len(chunks), document_id)
    texts = [c["text"] for c in chunks]
    embeddings = await generate_embeddings(texts)

    # ── Step 8: upsert to Pinecone ────────────────────────────────
    logger.info("Upserting to Pinecone for doc %d", document_id)
    index = init_pinecone()
    namespace = f"user_{doc.owner_id}"
    # Annotate each chunk with file_type for metadata
    for chunk in chunks:
        chunk["file_type"] = file_type_str
    upsert_chunks(index, str(document_id), chunks, embeddings, doc.owner_id)

    # ── Step 9: mark as ready ─────────────────────────────────────
    await repo.update_status(
        document_id,
        DocumentStatus.READY,
        chunk_count=len(chunks),
        pinecone_namespace=namespace,
    )
    await db.commit()
    logger.info("Document %d processed successfully (%d chunks)", document_id, len(chunks))


def _build_chunks(content: dict, file_type: str) -> list[dict]:
    """Select the appropriate chunking strategy and return a list of chunk dicts."""
    segments = content.get("segments")
    pages = content.get("pages")

    if file_type in ("audio", "video") and segments:
        return chunk_transcript_by_segments(segments)

    if file_type == "pdf" and pages:
        page_chunks = chunk_pdf_by_pages(pages)
        if page_chunks:
            return page_chunks

    # Fallback: generic text chunking
    return chunk_text(content.get("text", ""))
