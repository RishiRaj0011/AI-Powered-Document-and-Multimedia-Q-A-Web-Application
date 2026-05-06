from sqlalchemy import Integer, ForeignKey, DateTime, Text, Float, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base


class TimestampChunk(Base):
    __tablename__ = "timestamp_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    topic_summary: Mapped[str] = mapped_column(Text, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["Document"] = relationship("Document", backref="timestamp_chunks")

    __table_args__ = (
        Index("ix_timestamp_chunks_document_chunk", "document_id", "chunk_index"),
    )
