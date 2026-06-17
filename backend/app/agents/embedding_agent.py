"""
EmbeddingVectorizationAgent

Generates OpenAI text-embedding-3-large embeddings for:
  - The full resume text  → stored in state["resume_embedding"]
  - Each resume chunk     → stored in ChromaDB collection "resumes"
  - Discovered jobs       → stored in ChromaDB collection "jobs"
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.agents.base_agent import BaseAgent
from app.agents.state import AgentState
from app.agents.tools import store_chromadb
from app.core.config import settings

logger = logging.getLogger(__name__)

_EMBED_MODEL = "text-embedding-3-large"
_BATCH_SIZE = 20   # embeddings per API call


class EmbeddingVectorizationAgent(BaseAgent):
    """
    Generates and stores embeddings for resumes and jobs.
    """

    def __init__(self) -> None:
        super().__init__()
        self._embed_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def run(self, state: AgentState) -> AgentState:
        try:
            raw_text: Optional[str] = state.get("resume_raw_text")
            chunks: list[str] = state.get("resume_chunks") or []
            user_id: str = state.get("user_id", "unknown")
            resume_id: str = state.get("resume_id") or self._hash_id(raw_text or "")

            errors_occurred = False

            # ---------------------------------------------------------------- #
            # 1. Full-resume embedding
            # ---------------------------------------------------------------- #
            if raw_text:
                try:
                    full_embedding = await self._embed_single(raw_text[:30000])
                    state["resume_embedding"] = full_embedding

                    # Store full resume in ChromaDB
                    store_chromadb.invoke({
                        "collection_name": "resumes",
                        "doc_id": f"resume_{resume_id}",
                        "text": raw_text[:10000],
                        "embedding": full_embedding,
                        "metadata": {
                            "user_id": user_id,
                            "resume_id": resume_id,
                            "type": "full_resume",
                        },
                    })
                    logger.info("[EmbeddingAgent] Full resume embedding stored — dim=%d", len(full_embedding))
                except Exception as exc:
                    state = self._log_error(state, f"Full resume embedding failed: {exc}")
                    errors_occurred = True
            else:
                logger.warning("[EmbeddingAgent] No resume_raw_text — skipping full embedding")

            # ---------------------------------------------------------------- #
            # 2. Per-chunk embeddings
            # ---------------------------------------------------------------- #
            if chunks:
                try:
                    chunk_embeddings = await self._embed_batch(chunks)
                    for idx, (chunk, emb) in enumerate(zip(chunks, chunk_embeddings)):
                        chunk_id = f"chunk_{resume_id}_{idx:04d}"
                        store_chromadb.invoke({
                            "collection_name": "resumes",
                            "doc_id": chunk_id,
                            "text": chunk,
                            "embedding": emb,
                            "metadata": {
                                "user_id": user_id,
                                "resume_id": resume_id,
                                "chunk_index": idx,
                                "type": "resume_chunk",
                            },
                        })
                    logger.info("[EmbeddingAgent] %d chunk embeddings stored", len(chunks))
                except Exception as exc:
                    state = self._log_error(state, f"Chunk embedding failed: {exc}")
                    errors_occurred = True

            # ---------------------------------------------------------------- #
            # 3. Job embeddings (if discovered jobs present)
            # ---------------------------------------------------------------- #
            discovered_jobs: list[dict] = state.get("discovered_jobs") or []
            if discovered_jobs:
                try:
                    job_texts = [self._job_to_text(j) for j in discovered_jobs]
                    job_embeddings = await self._embed_batch(job_texts)
                    for job, emb in zip(discovered_jobs, job_embeddings):
                        job["embedding"] = emb
                        job_id = job.get("external_id") or self._hash_id(job.get("title", "") + job.get("company_name", ""))
                        store_chromadb.invoke({
                            "collection_name": "jobs",
                            "doc_id": job_id,
                            "text": self._job_to_text(job)[:5000],
                            "embedding": emb,
                            "metadata": {
                                "job_id": job_id,
                                "title": job.get("title", ""),
                                "company": job.get("company_name", ""),
                                "source": job.get("source", ""),
                            },
                        })
                    state["discovered_jobs"] = discovered_jobs
                    logger.info("[EmbeddingAgent] %d job embeddings stored", len(discovered_jobs))
                except Exception as exc:
                    state = self._log_error(state, f"Job embedding failed: {exc}")
                    errors_occurred = True

            # ---------------------------------------------------------------- #
            # Confidence
            # ---------------------------------------------------------------- #
            has_resume_emb = bool(state.get("resume_embedding"))
            confidence = 0.95 if (has_resume_emb and not errors_occurred) else (0.6 if has_resume_emb else 0.1)
            state = self._update_confidence(state, confidence)
            state = self._append_message(
                state,
                role="system",
                content=f"EmbeddingVectorizationAgent: confidence={confidence:.2f}",
            )

        except Exception as exc:
            state = self._log_error(state, f"Unexpected error: {exc}")
            state = self._update_confidence(state, 0.0)

        return state

    # ---------------------------------------------------------------------- #
    # Embedding helpers
    # ---------------------------------------------------------------------- #

    async def _embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        text_clean = text.replace("\n", " ").strip()
        response = await self._embed_client.embeddings.create(
            model=_EMBED_MODEL,
            input=text_clean,
        )
        return response.data[0].embedding

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts in batches.
        Returns a list of embedding vectors in the same order.
        """
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = [t.replace("\n", " ").strip()[:8000] for t in texts[i: i + _BATCH_SIZE]]
            response = await self._embed_client.embeddings.create(
                model=_EMBED_MODEL,
                input=batch,
            )
            # API preserves order when sending list
            sorted_data = sorted(response.data, key=lambda d: d.index)
            all_embeddings.extend(d.embedding for d in sorted_data)
            if i + _BATCH_SIZE < len(texts):
                await asyncio.sleep(0.1)  # light rate-limit buffer
        return all_embeddings

    @staticmethod
    def _job_to_text(job: dict) -> str:
        """Convert a job dict to a single embedding-friendly string."""
        parts = [
            job.get("title", ""),
            job.get("company_name", ""),
            job.get("location", ""),
            job.get("description", ""),
            " ".join(job.get("requirements", [])),
        ]
        return " | ".join(p for p in parts if p)[:8000]

    @staticmethod
    def _hash_id(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()[:16]
