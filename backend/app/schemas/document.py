from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

from app.models.document import DocumentStatus, DocumentType


class DocumentOut(BaseModel):
    id: int
    filename: str          # stored (uuid-prefixed) filename
    file_type: str         # maps from doc_type on the ORM model
    file_size: int
    status: DocumentStatus
    error_message: Optional[str] = None
    created_at: datetime
    user_id: int           # maps from owner_id on the ORM model

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _remap_orm_fields(cls, data: object) -> object:
        """Map ORM attribute names to schema field names.

        SQLAlchemy ORM objects expose ``doc_type`` and ``owner_id``;
        the schema presents them as ``file_type`` and ``user_id``.
        """
        if hasattr(data, "__dict__") or hasattr(data, "__mapper__"):
            # ORM instance — pull attributes directly
            return {
                "id": data.id,
                "filename": data.filename,
                "file_type": data.doc_type.value if hasattr(data.doc_type, "value") else str(data.doc_type),
                "file_size": data.file_size,
                "status": data.status,
                "error_message": data.error_message,
                "created_at": data.created_at,
                "user_id": data.owner_id,
            }
        # Plain dict (e.g. from tests) — accept both naming conventions
        if isinstance(data, dict):
            out = dict(data)
            if "doc_type" in out and "file_type" not in out:
                out["file_type"] = out.pop("doc_type")
            if "owner_id" in out and "user_id" not in out:
                out["user_id"] = out.pop("owner_id")
        return data


class DocumentStatusOut(BaseModel):
    doc_id: int
    status: DocumentStatus
    error_message: Optional[str] = None
    progress_percent: int  # 0 | 25 | 50 | 75 | 100 mapped from status

    model_config = {"from_attributes": True}

    @classmethod
    def from_document(cls, doc) -> "DocumentStatusOut":
        progress_map = {
            DocumentStatus.PENDING: 0,
            DocumentStatus.PROCESSING: 50,
            DocumentStatus.READY: 100,
            DocumentStatus.FAILED: 0,
        }
        return cls(
            doc_id=doc.id,
            status=doc.status,
            error_message=doc.error_message,
            progress_percent=progress_map.get(doc.status, 0),
        )


class DocumentListOut(BaseModel):
    documents: list[DocumentOut]
    total: int


# ---------------------------------------------------------------------------
# Legacy aliases — keep existing imports in document_service.py working
# ---------------------------------------------------------------------------
DocumentResponse = DocumentOut
DocumentListResponse = DocumentListOut
