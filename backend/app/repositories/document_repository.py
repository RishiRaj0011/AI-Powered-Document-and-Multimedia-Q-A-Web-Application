from __future__ import annotations

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentStatus, DocumentType
from app.models.transcript import Transcript  # noqa: F401 — ensures backref is registered


class DocumentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create(
        self,
        user_id: int,
        filename: str,
        file_type: DocumentType,
        file_path: str,
        file_size: int,
        original_filename: str | None = None,
    ) -> Document:
        doc = Document(
            owner_id=user_id,
            filename=filename,
            original_filename=original_filename or filename,
            file_size=file_size,
            doc_type=file_type,
            status=DocumentStatus.PENDING,
            # file_path stored in filename column — model has no separate file_path
            # column; the full path is reconstructed from UPLOAD_DIR + filename
        )
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_by_id(self, doc_id: int) -> Document | None:
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_owner(self, doc_id: int, owner_id: int) -> Document | None:
        result = await self.db.execute(
            select(Document).where(
                Document.id == doc_id,
                Document.owner_id == owner_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: int) -> list[Document]:
        result = await self.db.execute(
            select(Document)
            .where(Document.owner_id == user_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_with_transcript(self, doc_id: int) -> Document | None:
        """Return the document with its Transcript eagerly loaded.

        The ``transcript`` attribute is a backref declared on the Transcript
        model.  SQLAlchemy registers it on Document at mapper-configuration
        time, so ``Document.transcript`` is valid after all models are imported.
        """
        import app.models  # noqa: F401 — ensure backref is registered
        result = await self.db.execute(
            select(Document)
            .options(selectinload(Document.transcript))
            .where(Document.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def count_by_user(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Document).where(Document.owner_id == user_id)
        )
        return result.scalar_one()

    # ------------------------------------------------------------------
    # Updates
    # ------------------------------------------------------------------

    async def update_status(
        self,
        doc_id: int,
        status: str,
        error_message: str | None = None,
        chunk_count: int | None = None,
        pinecone_namespace: str | None = None,
    ) -> None:
        values: dict = {"status": status}
        if error_message is not None:
            values["error_message"] = error_message
        if chunk_count is not None:
            values["chunk_count"] = chunk_count
        if pinecone_namespace is not None:
            values["pinecone_namespace"] = pinecone_namespace
        await self.db.execute(
            update(Document).where(Document.id == doc_id).values(**values)
        )
        await self.db.flush()

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete(self, doc_id: int) -> None:
        doc = await self.get_by_id(doc_id)
        if doc is not None:
            await self.db.delete(doc)
            await self.db.flush()
