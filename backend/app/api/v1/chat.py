from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.chat import (
    ChatResponseOut,
    ChatSessionDetailOut,
    ChatSessionOut,
    CreateSessionRequest,
    MessageOut,
    SendMessageRequest,
)
from app.services import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# POST /chat/sessions
# ---------------------------------------------------------------------------

@router.post("/sessions", response_model=ChatSessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatSessionOut:
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id_and_owner(body.document_id, current_user.id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {body.document_id} not found",
        )

    repo = ChatRepository(db)
    session = await repo.create_session(
        user_id=current_user.id,
        document_id=body.document_id,
    )
    return ChatSessionOut(
        id=session.id,
        document_id=session.document_id,
        user_id=session.user_id,
        created_at=session.created_at,
        message_count=0,
    )


# ---------------------------------------------------------------------------
# GET /chat/sessions
# ---------------------------------------------------------------------------

@router.get("/sessions", response_model=list[ChatSessionOut])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChatSessionOut]:
    repo = ChatRepository(db)
    # Single query returns (ChatSession, message_count) tuples — no N+1
    rows = await repo.get_sessions_by_user(current_user.id)
    return [
        ChatSessionOut(
            id=session.id,
            document_id=session.document_id,
            user_id=session.user_id,
            created_at=session.created_at,
            message_count=count,
        )
        for session, count in rows
    ]


# ---------------------------------------------------------------------------
# GET /chat/sessions/{session_id}
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}", response_model=ChatSessionDetailOut)
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatSessionDetailOut:
    repo = ChatRepository(db)
    session = await repo.get_session_with_owner_check(session_id, current_user.id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    # get_messages returns DESC; reverse for chronological display
    messages = list(reversed(await repo.get_messages(session_id, limit=50)))
    return ChatSessionDetailOut(
        id=session.id,
        document_id=session.document_id,
        user_id=session.user_id,
        created_at=session.created_at,
        messages=[MessageOut.model_validate(m) for m in messages],
    )


# ---------------------------------------------------------------------------
# POST /chat/sessions/{session_id}/messages
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/messages", response_model=ChatResponseOut)
@limiter.limit("60/minute")
async def send_message(
    request: Request,
    session_id: int,
    body: SendMessageRequest,
    search_all: bool = Query(False, description="Search across all user documents"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponseOut:
    return await chat_service.ask_question(
        db=db,
        session_id=session_id,
        question=body.question,
        user_id=current_user.id,
        search_all_docs=search_all,
    )


# ---------------------------------------------------------------------------
# GET /chat/sessions/{session_id}/stream
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/stream")
@limiter.limit("30/minute")
async def stream_message(
    request: Request,
    session_id: int,
    question: str = Query(..., min_length=1, max_length=2000),
    search_all: bool = Query(False, description="Search across all user documents"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    return StreamingResponse(
        chat_service.stream_question(
            db=db,
            session_id=session_id,
            question=question,
            user_id=current_user.id,
            search_all_docs=search_all,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
