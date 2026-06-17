"""ChromaDB vector store service for resume and job embeddings."""

from __future__ import annotations

import uuid
from typing import Any, Optional

import chromadb
from chromadb import Collection
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Collection names
RESUME_COLLECTION = "resume_embeddings"
JOB_COLLECTION = "job_embeddings"

_chroma_client: Optional[chromadb.ClientAPI] = None


def init_chroma_client() -> chromadb.ClientAPI:
    """
    Initialise (or return an existing) ChromaDB persistent client.

    The client is module-level singleton so it is created once at startup
    and reused across requests.
    """
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    _chroma_client = chromadb.PersistentClient(
        path=settings.CHROMA_DB_PATH,
        settings=ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True,
        ),
    )
    # Pre-create collections so later calls don't need to branch on existence
    _chroma_client.get_or_create_collection(
        name=RESUME_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    _chroma_client.get_or_create_collection(
        name=JOB_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info("ChromaDB client initialised", extra={"path": settings.CHROMA_DB_PATH})
    return _chroma_client


def _get_client() -> chromadb.ClientAPI:
    if _chroma_client is None:
        return init_chroma_client()
    return _chroma_client


def _get_collection(name: str) -> Collection:
    return _get_client().get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------------------
# Resume operations
# ---------------------------------------------------------------------------


def upsert_resume_embeddings(
    resume_id: str,
    chunks: list[str],
    embeddings: list[list[float]],
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """
    Store or update text chunks and their embeddings for a resume.

    Args:
        resume_id: UUID string of the resume.
        chunks:    List of text chunks extracted from the resume.
        embeddings: Corresponding embedding vectors (same length as chunks).
        metadata:  Optional extra metadata stored alongside each chunk.
    """
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must have the same length"
        )

    collection = _get_collection(RESUME_COLLECTION)

    ids = [f"{resume_id}__chunk_{i}" for i in range(len(chunks))]
    metas = [
        {**(metadata or {}), "resume_id": resume_id, "chunk_index": i}
        for i in range(len(chunks))
    ]

    collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metas,
    )
    logger.info(
        "Resume embeddings upserted",
        extra={"resume_id": resume_id, "chunks": len(chunks)},
    )


def search_similar_resumes(
    query_embedding: list[float],
    top_k: int = 10,
    where: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """
    Find the most semantically similar resume chunks.

    Returns a list of dicts with keys: id, document, metadata, distance.
    """
    collection = _get_collection(RESUME_COLLECTION)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    output: list[dict[str, Any]] = []
    for i, doc_id in enumerate(results["ids"][0]):
        output.append(
            {
                "id": doc_id,
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            }
        )
    return output


def delete_resume_embeddings(resume_id: str) -> None:
    """Remove all embedding chunks associated with a resume."""
    collection = _get_collection(RESUME_COLLECTION)
    results = collection.get(where={"resume_id": resume_id})
    ids_to_delete = results.get("ids", [])
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
        logger.info(
            "Resume embeddings deleted",
            extra={"resume_id": resume_id, "count": len(ids_to_delete)},
        )


# ---------------------------------------------------------------------------
# Job operations
# ---------------------------------------------------------------------------


def upsert_job_embeddings(
    job_id: str,
    text: str,
    embedding: list[float],
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """
    Store or update the embedding for a single job posting.

    Each job is stored as a single document (not chunked).
    """
    collection = _get_collection(JOB_COLLECTION)
    collection.upsert(
        ids=[job_id],
        documents=[text],
        embeddings=[embedding],
        metadatas=[{**(metadata or {}), "job_id": job_id}],
    )
    logger.debug("Job embedding upserted", extra={"job_id": job_id})


def search_matching_jobs(
    resume_embedding: list[float],
    top_k: int = 20,
    filters: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """
    Find job postings that best match a resume embedding.

    Args:
        resume_embedding: Vector representation of the resume or a query.
        top_k:            Number of results to return.
        filters:          Optional ChromaDB ``where`` filter dict.

    Returns:
        List of dicts with: job_id, document, metadata, distance, score.
    """
    collection = _get_collection(JOB_COLLECTION)

    query_kwargs: dict[str, Any] = {
        "query_embeddings": [resume_embedding],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if filters:
        query_kwargs["where"] = filters

    results = collection.query(**query_kwargs)

    output: list[dict[str, Any]] = []
    for i, doc_id in enumerate(results["ids"][0]):
        distance = results["distances"][0][i]
        # Convert cosine distance [0,2] → similarity score [0,1]
        score = max(0.0, 1.0 - (distance / 2.0))
        output.append(
            {
                "job_id": doc_id,
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": distance,
                "score": round(score, 4),
            }
        )
    return output


def delete_job_embeddings(job_id: str) -> None:
    """Remove the embedding for a specific job posting."""
    collection = _get_collection(JOB_COLLECTION)
    collection.delete(ids=[job_id])
    logger.debug("Job embedding deleted", extra={"job_id": job_id})


def get_collection_stats() -> dict[str, Any]:
    """Return item counts for all collections (useful for health checks)."""
    resume_col = _get_collection(RESUME_COLLECTION)
    job_col = _get_collection(JOB_COLLECTION)
    return {
        "resume_embeddings_count": resume_col.count(),
        "job_embeddings_count": job_col.count(),
    }
