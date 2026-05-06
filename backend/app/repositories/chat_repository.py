from __future__ import annotations

from sqlalchemy import select, func, outerjoin
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession, MessageRole


class ChatRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    async def create_session(
        self,
        user_id: int,
        document_id: int | None = None,
        title: str | None = None,
    ) -> ChatSession:
        session = ChatSession(user_id=user_id, document_id=document_id, title=title)
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: int) -> ChatSession | None:
        """Get session without owner check — for internal use."""
        result = await self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_session_with_owner_check(
        self,
        session_id: int,
        user_id: int,
    ) -> ChatSession | None:
        """Get session only if it belongs to *user_id*."""
        result = await self.db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_sessions_by_user(
        self, user_id: int
    ) -> list[tuple[ChatSession, int]]:
        """Return (ChatSession, message_count) pairs for *user_id* in one query.

        Uses a LEFT OUTER JOIN with a COUNT subquery so the list endpoint
        never issues N+1 queries regardless of how many sessions exist.
        """
        msg_count = (
            select(
                ChatMessage.session_id,
                func.count(ChatMessage.id).label("cnt"),
            )
            .group_by(ChatMessage.session_id)
            .subquery()
        )

        stmt = (
            select(ChatSession, func.coalesce(msg_count.c.cnt, 0).label("message_count"))
            .outerjoin(msg_count, ChatSession.id == msg_count.c.session_id)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.created_at.desc())
        )

        result = await self.db.execute(stmt)
        return [(row.ChatSession, row.message_count) for row in result.all()]

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    async def add_message(
        self,
        session_id: int,
        role: MessageRole,
        content: str,
        timestamp_reference: float | None = None,
        tokens_used: int | None = None,
        latency_ms: float | None = None,
    ) -> ChatMessage:
        msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            timestamp_reference=timestamp_reference,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        return msg

    async def get_messages(
        self,
        session_id: int,
        limit: int = 20,
    ) -> list[ChatMessage]:
        """Return the last *limit* messages ordered by created_at DESC."""
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_messages(
        self,
        session_id: int,
        limit: int = 10,
    ) -> list[ChatMessage]:
        """Return the last *limit* messages ordered ASC (oldest first).

        Fetches DESC with LIMIT (index-efficient), then reverses in Python.
        Used to build chat history for the LLM — must be chronological.
        """
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        return list(reversed(list(result.scalars().all())))

    async def count_messages(self, session_id: int) -> int:
        """Single COUNT query — used by the session detail endpoint."""
        result = await self.db.execute(
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.session_id == session_id)
        )
        return result.scalar_one()
