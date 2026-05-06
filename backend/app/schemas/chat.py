from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models.chat import MessageRole


# ---------------------------------------------------------------------------
# Inbound
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    document_id: int


class SendMessageRequest(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def _validate_question(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1:
            raise ValueError("Question must not be empty")
        if len(v) > 2000:
            raise ValueError("Question must be at most 2000 characters")
        return v


# ---------------------------------------------------------------------------
# Outbound — messages
# ---------------------------------------------------------------------------

class MessageOut(BaseModel):
    id: int
    session_id: int
    role: MessageRole
    content: str
    timestamp_reference: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Outbound — sessions
# ---------------------------------------------------------------------------

class ChatSessionOut(BaseModel):
    id: int
    document_id: Optional[int]
    user_id: int
    created_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ChatSessionDetailOut(BaseModel):
    """Session with its last 50 messages."""
    id: int
    document_id: Optional[int]
    user_id: int
    created_at: datetime
    messages: list[MessageOut] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Outbound — chat response
# ---------------------------------------------------------------------------

class TimestampRef(BaseModel):
    start_time: float
    end_time: float
    text: str


class SourceRef(BaseModel):
    text: str
    chunk_index: Optional[int] = None
    score: float


class ChatResponseOut(BaseModel):
    answer: str
    sources: list[SourceRef] = []
    timestamp_references: list[TimestampRef] = []
    session_id: int
    message_id: int


# ---------------------------------------------------------------------------
# Outbound — summary / topics
# ---------------------------------------------------------------------------

class TopicOut(BaseModel):
    label: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    chunk_index: Optional[int] = None


class SummaryOut(BaseModel):
    summary: str
    topics: list[TopicOut] = []


# ---------------------------------------------------------------------------
# Legacy aliases — keep existing imports in old chat_service.py working
# ---------------------------------------------------------------------------
ChatRequest = SendMessageRequest
ChatResponse = ChatResponseOut
ChatSessionResponse = ChatSessionOut
ChatMessageResponse = MessageOut
