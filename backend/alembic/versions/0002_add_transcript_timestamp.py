"""add transcript and timestamp_chunks tables

Revision ID: 0002_add_transcript_timestamp
Revises: 0001_initial
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "0002_add_transcript_timestamp"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transcripts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_transcripts_document_id", "transcripts", ["document_id"])

    op.create_table(
        "timestamp_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("topic_summary", sa.Text(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_timestamp_chunks_document_id", "timestamp_chunks", ["document_id"])
    op.create_index(
        "ix_timestamp_chunks_document_chunk",
        "timestamp_chunks",
        ["document_id", "chunk_index"],
    )


def downgrade() -> None:
    op.drop_index("ix_timestamp_chunks_document_chunk", table_name="timestamp_chunks")
    op.drop_index("ix_timestamp_chunks_document_id", table_name="timestamp_chunks")
    op.drop_table("timestamp_chunks")
    op.drop_index("ix_transcripts_document_id", table_name="transcripts")
    op.drop_table("transcripts")
