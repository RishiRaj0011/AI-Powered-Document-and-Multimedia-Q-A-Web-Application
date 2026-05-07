from __future__ import annotations

import logging
from typing import Any

from pinecone import Pinecone, ServerlessSpec

from app.core.config import settings
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

_EMBED_BATCH_SIZE = 100
_UPSERT_BATCH_SIZE = 100


# ---------------------------------------------------------------------------
# Pinecone initialisation
# ---------------------------------------------------------------------------

def init_pinecone():
    """Return the Pinecone Index object, creating it if it doesn't exist.

    Creates a serverless index with appropriate dimension based on LLM provider:
    - OpenAI: 1536 (text-embedding-3-small)
    - Gemini: 768 (embedding-001)
    """
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    existing = [i.name for i in pc.list_indexes()]
    
    if settings.PINECONE_INDEX_NAME not in existing:
        # Get embedding dimension from LLM service
        llm = get_llm_service()
        dimension = llm.get_embedding_dimension()
        
        logger.info("Creating Pinecone index: %s (dimension=%d)", settings.PINECONE_INDEX_NAME, dimension)
        pc.create_index(
            name=settings.PINECONE_INDEX_NAME,
            dimension=dimension,
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
    """Embed *texts* using configured LLM provider (OpenAI or Gemini).

    Batches requests in groups of ``_EMBED_BATCH_SIZE`` (100) to stay within
    the API's per-request token limits and avoid rate-limit errors.

    Returns a list of float vectors in the same order as *texts*.
    """
    if not texts:
        return []

    llm = get_llm_service()
    all_embeddings: list[list[float]] = []

    for batch_start in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[batch_start: batch_start + _EMBED_BATCH_SIZE]
        # Strip empty strings — the API rejects them
        safe_batch = [t if t.strip() else " " for t in batch]

        batch_vectors = await llm.generate_embeddings(safe_batch)
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
    doc_id: str | None,
    user_id: int,
    top_k: int = 5,
) -> list[dict]:
    """Query Pinecone for the *top_k* most similar chunks in user's namespace.

    Args:
        index: Pinecone index
        query_embedding: Query vector
        doc_id: Document ID to filter by, or None to search all documents
        user_id: User ID for namespace isolation
        top_k: Number of results to return

    Returns::

        [
            {
                "text": str,
                "score": float,
                "start_time": float | None,
                "end_time": float | None,
                "chunk_index": int,
                "doc_id": str,  # Included when searching across documents
            },
            ...
        ]
    """
    namespace = f"user_{user_id}"
    
    # Build filter - always include user_id, optionally include doc_id
    filter_dict = {"user_id": {"$eq": str(user_id)}}
    if doc_id is not None:
        filter_dict["doc_id"] = {"$eq": str(doc_id)}
    
    response = index.query(
        vector=query_embedding,
        top_k=top_k,
        filter=filter_dict,
        include_metadata=True,
        namespace=namespace,
    )

    results: list[dict] = []
    for match in response.get("matches", []):
        meta = match.get("metadata", {})
        result = {
            "text": meta.get("text", ""),
            "score": float(match.get("score", 0.0)),
            "start_time": meta.get("start_time"),
            "end_time": meta.get("end_time"),
            "chunk_index": meta.get("chunk_index"),
        }
        # Include doc_id when searching across documents
        if doc_id is None:
            result["doc_id"] = meta.get("doc_id")
        results.append(result)

    return results
