from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.dependencies import get_current_active_user, get_current_user, get_db
from app.core.redis import delete_cache, get_redis
from app.models.document import DocumentType
from app.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.schemas.chat import SummaryOut, TopicOut
from app.schemas.document import DocumentListOut, DocumentOut, DocumentStatusOut
from app.services.file_service import delete_file, get_file_info, save_file, validate_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])
limiter = Limiter(key_func=get_remote_address)

_EXTENSION_TO_TYPE: dict[str, DocumentType] = {
    "pdf": DocumentType.PDF,
    "docx": DocumentType.DOCX,
    "txt": DocumentType.TXT,
    "mp3": DocumentType.AUDIO,
    "wav": DocumentType.AUDIO,
    "m4a": DocumentType.AUDIO,
    "webm": DocumentType.AUDIO,
    "mp4": DocumentType.VIDEO,
    "mov": DocumentType.VIDEO,
}


def _doc_cache_key(user_id: int) -> str:
    return f"doc:{user_id}:list"


# ---------------------------------------------------------------------------
# Background processing
# ---------------------------------------------------------------------------

async def _process_document(doc_id: int, db_url: str) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.services.document_service import DocumentService

    engine = create_async_engine(db_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        try:
            service = DocumentService(session)
            repo = DocumentRepository(session)
            doc = await repo.get_by_id(doc_id)
            if doc:
                await service.process(doc_id, doc.owner_id)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error("Background processing failed for doc %d: %s", doc_id, exc)
        finally:
            await session.close()
    await engine.dispose()


# ---------------------------------------------------------------------------
# POST /upload (single file)
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> DocumentOut:
    await validate_file(file)

    file_path = await save_file(file, current_user.id)
    ext = Path(file.filename).suffix.lstrip(".").lower()
    file_type = _EXTENSION_TO_TYPE.get(ext, DocumentType.TXT)
    info = get_file_info(file_path)

    repo = DocumentRepository(db)
    doc = await repo.create(
        user_id=current_user.id,
        filename=Path(file_path).name,
        file_type=file_type,
        file_path=file_path,
        file_size=info["size_bytes"],
        original_filename=file.filename,
    )

    await delete_cache(redis, _doc_cache_key(current_user.id))

    from app.core.config import settings
    background_tasks.add_task(_process_document, doc.id, settings.DATABASE_URL)

    return DocumentOut.model_validate(doc)


# ---------------------------------------------------------------------------
# POST /upload-multiple (multi-file upload)
# ---------------------------------------------------------------------------

@router.post("/upload-multiple", response_model=list[DocumentOut], status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def upload_multiple_documents(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> list[DocumentOut]:
    """Upload multiple files in parallel.
    
    Validates all files first, then processes them concurrently.
    Returns list of created documents.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 files per request"
        )
    
    # Validate all files first
    validation_tasks = [validate_file(file) for file in files]
    await asyncio.gather(*validation_tasks)
    
    # Save files in parallel
    save_tasks = [save_file(file, current_user.id) for file in files]
    file_paths = await asyncio.gather(*save_tasks)
    
    # Create database records
    repo = DocumentRepository(db)
    created_docs = []
    
    for file, file_path in zip(files, file_paths):
        ext = Path(file.filename).suffix.lstrip(".").lower()
        file_type = _EXTENSION_TO_TYPE.get(ext, DocumentType.TXT)
        info = get_file_info(file_path)
        
        doc = await repo.create(
            user_id=current_user.id,
            filename=Path(file_path).name,
            file_type=file_type,
            file_path=file_path,
            file_size=info["size_bytes"],
            original_filename=file.filename,
        )
        created_docs.append(doc)
    
    await delete_cache(redis, _doc_cache_key(current_user.id))
    
    # Schedule background processing for all documents
    from app.core.config import settings
    for doc in created_docs:
        background_tasks.add_task(_process_document, doc.id, settings.DATABASE_URL)
    
    return [DocumentOut.model_validate(doc) for doc in created_docs]


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

@router.get("/", response_model=DocumentListOut)
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentListOut:
    repo = DocumentRepository(db)
    docs = await repo.get_by_user(current_user.id)
    total = await repo.count_by_user(current_user.id)
    return DocumentListOut(
        documents=[DocumentOut.model_validate(d) for d in docs],
        total=total,
    )


# ---------------------------------------------------------------------------
# GET /{doc_id}
# ---------------------------------------------------------------------------

@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    repo = DocumentRepository(db)
    doc = await repo.get_by_id_and_owner(doc_id, current_user.id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )
    return DocumentOut.model_validate(doc)


# ---------------------------------------------------------------------------
# DELETE /{doc_id}
# ---------------------------------------------------------------------------

@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> None:
    repo = DocumentRepository(db)
    doc = await repo.get_by_id_and_owner(doc_id, current_user.id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )

    from app.core.config import settings
    file_path = str(Path(settings.UPLOAD_DIR) / str(current_user.id) / doc.filename)
    delete_file(file_path)

    await repo.delete(doc_id)
    await delete_cache(redis, _doc_cache_key(current_user.id))


# ---------------------------------------------------------------------------
# GET /{doc_id}/status
# ---------------------------------------------------------------------------

@router.get("/{doc_id}/status", response_model=DocumentStatusOut)
async def get_document_status(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentStatusOut:
    repo = DocumentRepository(db)
    doc = await repo.get_by_id_and_owner(doc_id, current_user.id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )
    return DocumentStatusOut.from_document(doc)


# ---------------------------------------------------------------------------
# GET /{doc_id}/summary
# ---------------------------------------------------------------------------

@router.get("/{doc_id}/summary", response_model=SummaryOut)
async def get_document_summary(
    doc_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> SummaryOut:
    repo = DocumentRepository(db)
    doc = await repo.get_by_id_and_owner(doc_id, current_user.id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )
    from app.services import chat_service
    return await chat_service.summarize_document(db=db, doc_id=doc_id, redis=redis)


# ---------------------------------------------------------------------------
# GET /{doc_id}/topics
# ---------------------------------------------------------------------------

@router.get("/{doc_id}/topics", response_model=list[TopicOut])
async def get_document_topics(
    doc_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[TopicOut]:
    repo = DocumentRepository(db)
    doc = await repo.get_by_id_and_owner(doc_id, current_user.id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )
    from app.services import chat_service
    return await chat_service.get_topics(db=db, doc_id=doc_id)


# ---------------------------------------------------------------------------
# GET /{doc_id}/transcript
# ---------------------------------------------------------------------------

@router.get("/{doc_id}/transcript")
async def get_document_transcript(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full transcript with timestamps for audio/video documents."""
    from sqlalchemy import select
    from app.models.transcript import Transcript
    from app.models.timestamp_chunk import TimestampChunk
    
    repo = DocumentRepository(db)
    doc = await repo.get_by_id_and_owner(doc_id, current_user.id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )
    
    # Get transcript
    result = await db.execute(
        select(Transcript).where(Transcript.document_id == doc_id)
    )
    transcript = result.scalar_one_or_none()
    
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No transcript available for this document"
        )
    
    # Get timestamp chunks
    result = await db.execute(
        select(TimestampChunk)
        .where(TimestampChunk.document_id == doc_id)
        .order_by(TimestampChunk.chunk_index)
    )
    chunks = list(result.scalars().all())
    
    return {
        "full_text": transcript.full_text,
        "language": transcript.language,
        "duration_seconds": transcript.duration_seconds,
        "chunks": [
            {
                "text": chunk.text_content,
                "start_time": chunk.start_time,
                "end_time": chunk.end_time,
                "chunk_index": chunk.chunk_index,
            }
            for chunk in chunks
        ]
    }
