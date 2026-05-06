from __future__ import annotations

import logging
from typing import Any

from openai import AsyncOpenAI
from pinecone import Pinecone, ServerlessSpec

from app.core.config import settings

logger = logging.getLogger(__name__)

_EMBED_BATCH_SIZE = 100
_UPSERT_BATCH_SIZE = 100


# ---------------------------------------------------------------------------
# Pinecone initialisation
# ---------------------------------------------------------------------------

def init_pinecone():
    """Return the Pinecone Index object, creating it if it doesn't exist.

    Creates a serverless index with dimension=1536 (text-embedding-3-small)
    and cosine metric if the index doesn't already exist.
    """
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    existing = [i.name for i in pc.list_indexes()]
    
    if settings.PINECONE_INDEX_NAME not in existing:
        logger.info("Creating Pinecone index: %s", settings.PINECONE_INDEX_NAME)
        pc.create_index(
            name=settings.PINECONE_INDEX_NAME,
            dimension=1536,  # text-embedding-3-small dimension
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region=settings.PINECONE_ENVIRONMENT
            )
        )
        # Wait for index to be ready
        import time
        while not pc.describe_index(settings.PINECONE_INDEX_NAME).status['ready']:
            time.sleep(1)
        logger.info("Pinecone index created and ready")
    
    return pc.Index(settings.PINECONE_INDEX_NAME)


# ---------------------------------------------------------------------------
# Embedding generation
# ---------------------------------------------------------------------------

async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Embed *texts* using OpenAI text-embedding-3-small.

    Batches requests in groups of ``_EMBED_BATCH_SIZE`` (100) to stay within
    the API's per-request token limits and avoid rate-limit errors.

    Returns a list of float vectors in the same order as *texts*.
    """
    if not texts:
        return []

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    all_embeddings: list[list[float]] = []

    for batch_start in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[batch_start: batch_start + _EMBED_BATCH_SIZE]
        # Strip empty strings — the API rejects them
        safe_batch = [t if t.strip() else " " for t in batch]

        response = await client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=safe_batch,
        )
        # Response data is ordered by index
        batch_vectors = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
        all_embeddings.extend(batch_vectors)
        logger.debug(
            "Embedded batch %d–%d (%d vectors)",
            batch_start,
            batch_start + len(batch) - 1,
            len(batch_vectors),
        )

    return all_embeddings


# ---------------------------------------------------------------------------
# Upsert to Pinecone
# ---------------------------------------------------------------------------

def upsert_chunks(
    index,
    doc_id: str,
    chunks: list[dict],
    embeddings: list[list[float]],
    user_id: int,
) -> None:
    """Upsert chunk embeddings into Pinecone with per-user namespace.

    Vector ID format: ``{doc_id}_chunk_{i}``

    Metadata stored per vector::

        {
            "doc_id": str,
            "text": str,          # first 1000 chars (Pinecone metadata limit)
            "chunk_index": int,
            "start_time": float | None,
            "end_time": float | None,
            "file_type": str,
        }

    Upserts in batches of ``_UPSERT_BATCH_SIZE`` (100) to namespace ``user_{user_id}``.
    """
    if not chunks or not embeddings:
        return

    if len(chunks) != len(embeddings):
        raise ValueError(
            f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) length mismatch"
        )

    vectors: list[dict[str, Any]] = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        metadata: dict[str, Any] = {
            "doc_id": str(doc_id),
            "user_id": str(user_id),  # Add user_id for double-check security
            "text": chunk.get("text", "")[:1000],
            "chunk_index": chunk.get("chunk_index", i),
            "start_time": chunk.get("start_time"),
            "end_time": chunk.get("end_time"),
            "file_type": chunk.get("file_type", ""),
        }
        # Pinecone rejects None metadata values — remove them
        metadata = {k: v for k, v in metadata.items() if v is not None}

        vectors.append({
            "id": f"{doc_id}_chunk_{i}",
            "values": embedding,
            "metadata": metadata,
        })

    namespace = f"user_{user_id}"
    for batch_start in range(0, len(vectors), _UPSERT_BATCH_SIZE):
        batch = vectors[batch_start: batch_start + _UPSERT_BATCH_SIZE]
        index.upsert(vectors=batch, namespace=namespace)
        logger.debug(
            "Upserted Pinecone batch %d–%d for doc %s in namespace %s",
            batch_start,
            batch_start + len(batch) - 1,
            doc_id,
            namespace,
        )


# ---------------------------------------------------------------------------
# Similarity search
# ---------------------------------------------------------------------------

def search_similar(
    index,
    query_embedding: list[float],
    doc_id: str,
    user_id: int,
    top_k: int = 5,
) -> list[dict]:
    """Query Pinecone for the *top_k* most similar chunks belonging to *doc_id* in user's namespace.

    Returns::

        [
            {
                "text": str,
                "score": float,
                "start_time": float | None,
                "end_time": float | None,
                "chunk_index": int,
            },
            ...
        ]
    """
    namespace = f"user_{user_id}"
    response = index.query(
        vector=query_embedding,
        top_k=top_k,
        filter={
            "doc_id": {"$eq": str(doc_id)},
            "user_id": {"$eq": str(user_id)}  # Double-check security layer
        },
        include_metadata=True,
        namespace=namespace,
    )

    results: list[dict] = []
    for match in response.get("matches", []):
        meta = match.get("metadata", {})
        results.append({
            "text": meta.get("text", ""),
            "score": float(match.get("score", 0.0)),
            "start_time": meta.get("start_time"),
            "end_time": meta.get("end_time"),
            "chunk_index": meta.get("chunk_index"),
        })

    return results
