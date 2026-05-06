from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import HTTPException, status
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_cache, set_cache
from app.models.chat import ChatMessage, MessageRole
from app.models.document import DocumentStatus
from app.models.timestamp_chunk import TimestampChunk
from app.repositories.chat_repository import ChatRepository
from app.repositories.document_repository import DocumentRepository
from app.services.embedding_service import generate_embeddings, init_pinecone, search_similar
from app.schemas.chat import ChatResponseOut, MessageOut, SourceRef, SummaryOut, TimestampRef, TopicOut

logger = logging.getLogger(__name__)

_SUMMARY_CACHE_TTL = 3600  # 1 hour
_SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions about documents. "
    "Use only the provided context to answer. "
    "If the context does not contain enough information, say so clearly. "
    "Be concise and accurate."
)


_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    """Get or create the singleton OpenAI client."""
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not configured")
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


# ---------------------------------------------------------------------------
# Chat history formatting
# ---------------------------------------------------------------------------

def _format_chat_history(messages: list[ChatMessage]) -> list[BaseMessage]:
    """Convert DB ChatMessage rows to LangChain message objects."""
    result: list[BaseMessage] = []
    for msg in messages:
        if msg.role == MessageRole.USER:
            result.append(HumanMessage(content=msg.content))
        elif msg.role == MessageRole.ASSISTANT:
            result.append(AIMessage(content=msg.content))
        elif msg.role == MessageRole.SYSTEM:
            result.append(SystemMessage(content=msg.content))
    return result


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

async def _retrieve_chunks(doc_id: int, question: str, user_id: int) -> list[dict]:
    """Embed *question* and return top-5 similar chunks for *doc_id*."""
    embeddings = await generate_embeddings([question])
    if not embeddings:
        return []
    index = init_pinecone()
    return search_similar(index, embeddings[0], str(doc_id), user_id, top_k=5)


def _build_context(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(f"[{i}] {chunk['text']}")
    return "\n\n".join(parts)


def _extract_timestamp_refs(chunks: list[dict]) -> list[TimestampRef]:
    refs: list[TimestampRef] = []
    for chunk in chunks:
        if chunk.get("start_time") is not None and chunk.get("end_time") is not None:
            refs.append(TimestampRef(
                start_time=chunk["start_time"],
                end_time=chunk["end_time"],
                text=chunk["text"][:200],
            ))
    return refs


def _build_messages(
    question: str,
    context: str,
    history: list[BaseMessage],
) -> list[dict]:
    """Build the OpenAI messages list from system prompt, history, and question."""
    msgs: list[dict] = [{"role": "system", "content": _SYSTEM_PROMPT}]

    if context:
        msgs.append({
            "role": "system",
            "content": f"Relevant context from the document:\n\n{context}",
        })

    for msg in history:
        if isinstance(msg, HumanMessage):
            msgs.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            msgs.append({"role": "assistant", "content": msg.content})

    msgs.append({"role": "user", "content": question})
    return msgs


# ---------------------------------------------------------------------------
# ask_question  (non-streaming)
# ---------------------------------------------------------------------------

async def ask_question(
    db: AsyncSession,
    session_id: int,
    question: str,
    user_id: int,
) -> ChatResponseOut:
    repo = ChatRepository(db)
    doc_repo = DocumentRepository(db)

    session = await repo.get_session_with_owner_check(session_id, user_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Validate document is ready
    doc = await doc_repo.get_by_id_and_owner(session.document_id, user_id)
    if doc is None or doc.status != DocumentStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is not ready for querying",
        )

    history_msgs = await repo.get_recent_messages(session_id, limit=10)
    history = _format_chat_history(history_msgs)

    chunks = await _retrieve_chunks(session.document_id, question, user_id)
    context = _build_context(chunks)
    messages = _build_messages(question, context, history)

    client = get_openai_client()
    t0 = time.monotonic()
    response = await client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=messages,
        temperature=0.2,
    )
    latency_ms = (time.monotonic() - t0) * 1000

    answer = response.choices[0].message.content or ""
    tokens = response.usage.total_tokens if response.usage else 0

    # Persist messages
    await repo.add_message(session_id, MessageRole.USER, question)
    ai_msg = await repo.add_message(
        session_id,
        MessageRole.ASSISTANT,
        answer,
        tokens_used=tokens,
        latency_ms=round(latency_ms, 2),
    )

    sources = [
        SourceRef(
            text=c["text"][:300],
            chunk_index=c.get("chunk_index"),
            score=c.get("score", 0.0),
        )
        for c in chunks
    ]
    timestamp_refs = _extract_timestamp_refs(chunks)

    return ChatResponseOut(
        answer=answer,
        sources=sources,
        timestamp_references=timestamp_refs,
        session_id=session_id,
        message_id=ai_msg.id,
    )


# ---------------------------------------------------------------------------
# stream_question  (SSE streaming)
# ---------------------------------------------------------------------------

async def stream_question(
    db: AsyncSession,
    session_id: int,
    question: str,
    user_id: int,
) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted tokens, then save the full response to DB.

    Yields ``data: <token>\\n\\n`` for each streamed token.
    Final yield is ``data: [DONE]\\n\\n``.
    """
    repo = ChatRepository(db)
    doc_repo = DocumentRepository(db)

    session = await repo.get_session_with_owner_check(session_id, user_id)
    if session is None:
        yield "data: [ERROR] Session not found\n\n"
        return

    doc = await doc_repo.get_by_id_and_owner(session.document_id, user_id)
    if doc is None or doc.status != DocumentStatus.READY:
        yield "data: [ERROR] Document not ready\n\n"
        return

    history_msgs = await repo.get_recent_messages(session_id, limit=10)
    history = _format_chat_history(history_msgs)

    chunks = await _retrieve_chunks(session.document_id, question, user_id)
    context = _build_context(chunks)
    messages = _build_messages(question, context, history)

    client = get_openai_client()
    full_response: list[str] = []

    await repo.add_message(session_id, MessageRole.USER, question)

    try:
        async with client.chat.completions.stream(
            model=settings.OPENAI_CHAT_MODEL,
            messages=messages,
            temperature=0.2,
        ) as stream:
            async for event in stream:
                delta = event.choices[0].delta.content if event.choices else None
                if delta:
                    full_response.append(delta)
                    # Escape newlines inside the SSE data field
                    safe = delta.replace("\n", "\\n")
                    yield f"data: {safe}\n\n"
    except Exception as exc:
        logger.error("Streaming error for session %d: %s", session_id, exc)
        yield f"data: [ERROR] {exc}\n\n"
        return

    # Persist the complete response after streaming finishes
    answer = "".join(full_response)
    await repo.add_message(session_id, MessageRole.ASSISTANT, answer)

    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# summarize_document
# ---------------------------------------------------------------------------

async def summarize_document(
    db: AsyncSession,
    doc_id: int,
    redis: Any,
) -> SummaryOut:
    cache_key = f"summary:{doc_id}"
    cached = await get_cache(redis, cache_key)
    if cached is not None:
        return SummaryOut(**cached)

    # Fetch timestamp chunks for context
    result = await db.execute(
        select(TimestampChunk)
        .where(TimestampChunk.document_id == doc_id)
        .order_by(TimestampChunk.chunk_index)
        .limit(30)  # cap to avoid token overflow
    )
    ts_chunks = list(result.scalars().all())

    if not ts_chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No content found for this document",
        )

    # Build a condensed text sample for the summary prompt
    sample_parts = [c.text_content[:400] for c in ts_chunks[:15]]
    sample_text = "\n\n".join(sample_parts)

    prompt = (
        "You are a document analyst. Given the following excerpts from a document, "
        "produce a JSON object with exactly two keys:\n"
        '  "summary": a 2-3 sentence overview of the document\n'
        '  "topics": a list of up to 8 key topics, each as '
        '{"label": str, "start_time": float_or_null}\n\n'
        "Return ONLY valid JSON, no markdown fences.\n\n"
        f"Document excerpts:\n{sample_text}"
    )

    client = get_openai_client()
    response = await client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"summary": raw, "topics": []}

    summary_str = parsed.get("summary", "")
    raw_topics = parsed.get("topics", [])
    topics = [
        TopicOut(
            label=t.get("label", ""),
            start_time=t.get("start_time"),
        )
        for t in raw_topics
        if t.get("label")
    ]

    result_obj = SummaryOut(summary=summary_str, topics=topics)
    await set_cache(redis, cache_key, result_obj.model_dump(), ttl=_SUMMARY_CACHE_TTL)
    return result_obj


# ---------------------------------------------------------------------------
# get_topics
# ---------------------------------------------------------------------------

async def get_topics(db: AsyncSession, doc_id: int) -> list[TopicOut]:
    """Return TimestampChunks that have a topic_summary, as TopicOut objects."""
    result = await db.execute(
        select(TimestampChunk)
        .where(
            TimestampChunk.document_id == doc_id,
            TimestampChunk.topic_summary.isnot(None),
        )
        .order_by(TimestampChunk.chunk_index)
    )
    chunks = list(result.scalars().all())
    return [
        TopicOut(
            label=c.topic_summary,
            start_time=c.start_time,
            end_time=c.end_time,
            chunk_index=c.chunk_index,
        )
        for c in chunks
    ]
