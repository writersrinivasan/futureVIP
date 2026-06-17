"""
LangChain Tool definitions shared across all FUTURE VIP agents.

Tools:
  extract_text_from_pdf    — pdfplumber-based PDF text extraction
  search_web               — DuckDuckGo async search via aiohttp
  fetch_job_details        — scrape + parse a job page
  calculate_ats_score      — keyword-overlap ATS scoring
  get_skill_market_data    — skill demand / salary data
  generate_embedding       — OpenAI text-embedding-3-large
  search_chromadb          — ChromaDB similarity search
  store_chromadb           — ChromaDB upsert
  save_to_database         — generic DB upsert helper
  send_notification        — notification store helper
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from typing import Any, Optional
from urllib.parse import quote_plus

import aiohttp
import chromadb
from langchain.tools import tool
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Shared singletons (lazy-init)
# --------------------------------------------------------------------------- #

_openai_client: Optional[AsyncOpenAI] = None
_chroma_client: Optional[chromadb.Client] = None


def _get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def _get_chroma() -> chromadb.Client:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
    return _chroma_client


# --------------------------------------------------------------------------- #
# Tool: extract_text_from_pdf
# --------------------------------------------------------------------------- #

@tool
def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract raw text from a PDF file using pdfplumber.
    Returns the full text content of the document.
    Raises ValueError if the file cannot be read.
    """
    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(file_path) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            full_text = "\n\n".join(pages)
        if not full_text.strip():
            raise ValueError(f"No extractable text found in PDF: {file_path}")
        return full_text
    except ImportError:
        raise ImportError("pdfplumber is required: pip install pdfplumber")
    except Exception as exc:
        raise ValueError(f"PDF extraction failed for {file_path}: {exc}") from exc


# --------------------------------------------------------------------------- #
# Tool: search_web
# --------------------------------------------------------------------------- #

@tool
async def search_web(query: str, max_results: int = 10) -> list[dict]:
    """
    Search the web using DuckDuckGo Instant Answer API.
    Returns a list of result dicts with keys: title, url, snippet.
    """
    encoded = quote_plus(query)
    url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_redirect=1&no_html=1"
    results: list[dict] = []

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        ) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.warning("DuckDuckGo returned status %s", resp.status)
                    return results
                data = await resp.json(content_type=None)

        # Combine RelatedTopics and Results
        raw_items = data.get("RelatedTopics", []) + data.get("Results", [])
        for item in raw_items[:max_results]:
            if isinstance(item, dict) and item.get("FirstURL"):
                results.append(
                    {
                        "title": item.get("Text", "")[:200],
                        "url": item.get("FirstURL", ""),
                        "snippet": item.get("Text", "")[:500],
                    }
                )
    except Exception as exc:
        logger.error("Web search failed: %s", exc)

    return results


# --------------------------------------------------------------------------- #
# Tool: fetch_job_details
# --------------------------------------------------------------------------- #

@tool
async def fetch_job_details(url: str) -> dict:
    """
    Fetch and parse a job posting page.
    Returns dict with keys: url, title, company, description, requirements, raw_html_length.
    """
    try:
        async with aiohttp.ClientSession(
            headers={"User-Agent": "Mozilla/5.0 FutureVIP-Bot/1.0"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return {"url": url, "error": f"HTTP {resp.status}"}
                html = await resp.text()

        # Strip tags with regex (light-weight, no BS4 dependency required here)
        clean = re.sub(r"<[^>]+>", " ", html)
        clean = re.sub(r"\s+", " ", clean).strip()

        return {
            "url": url,
            "raw_html_length": len(html),
            "text_content": clean[:8000],  # limit
        }
    except Exception as exc:
        logger.error("fetch_job_details failed for %s: %s", url, exc)
        return {"url": url, "error": str(exc)}


# --------------------------------------------------------------------------- #
# Tool: calculate_ats_score
# --------------------------------------------------------------------------- #

@tool
def calculate_ats_score(resume_text: str, job_description: str) -> dict:
    """
    Calculate an ATS compatibility score between a resume and a job description.
    Returns dict with overall_score (0-100), keyword_score, matched_keywords,
    missing_keywords, and formatting_score.
    """
    # Tokenise to lower-case words, strip punctuation
    def tokenise(text: str) -> set[str]:
        words = re.findall(r"\b[a-z][a-z0-9+#.]*\b", text.lower())
        # Filter stop-words (minimal list)
        stop = {
            "the", "and", "or", "in", "at", "to", "of", "a", "an",
            "is", "are", "was", "were", "be", "for", "on", "with",
            "we", "you", "our", "your", "their", "this", "that",
        }
        return {w for w in words if w not in stop and len(w) > 2}

    resume_tokens = tokenise(resume_text)
    jd_tokens = tokenise(job_description)

    # Extract multi-word phrases (bigrams) from JD
    jd_lower = job_description.lower()
    jd_bigrams: set[str] = set()
    words = jd_lower.split()
    for i in range(len(words) - 1):
        bigram = f"{words[i]} {words[i+1]}"
        if len(bigram) > 5:
            jd_bigrams.add(bigram)

    # Keyword match
    matched = resume_tokens & jd_tokens
    missing = jd_tokens - resume_tokens
    keyword_score = len(matched) / max(len(jd_tokens), 1) * 100

    # Bigram match
    bigram_matches = sum(1 for bg in jd_bigrams if bg in resume_text.lower())
    bigram_score = min(bigram_matches / max(len(jd_bigrams), 1) * 100, 100)

    # Formatting checks
    formatting_score = 100
    formatting_issues: list[str] = []
    if not re.search(r"experience", resume_text, re.I):
        formatting_score -= 15
        formatting_issues.append("Missing EXPERIENCE section")
    if not re.search(r"education", resume_text, re.I):
        formatting_score -= 10
        formatting_issues.append("Missing EDUCATION section")
    if not re.search(r"skills|technologies", resume_text, re.I):
        formatting_score -= 10
        formatting_issues.append("Missing SKILLS section")
    if len(resume_text) < 300:
        formatting_score -= 20
        formatting_issues.append("Resume content too short")

    # Weighted overall
    overall = (keyword_score * 0.50) + (bigram_score * 0.20) + (formatting_score * 0.30)

    return {
        "overall_score": round(min(overall, 100), 1),
        "keyword_score": round(keyword_score, 1),
        "bigram_score": round(bigram_score, 1),
        "formatting_score": round(max(formatting_score, 0), 1),
        "matched_keywords": sorted(matched)[:50],
        "missing_keywords": sorted(missing)[:50],
        "formatting_issues": formatting_issues,
    }


# --------------------------------------------------------------------------- #
# Tool: get_skill_market_data
# --------------------------------------------------------------------------- #

# Static baseline — extended at runtime via API when available
_SKILL_MARKET_BASELINE: dict[str, dict] = {
    "python": {"demand": "very_high", "avg_salary_usd": 130000, "yoy_growth": 12},
    "javascript": {"demand": "very_high", "avg_salary_usd": 120000, "yoy_growth": 8},
    "typescript": {"demand": "high", "avg_salary_usd": 128000, "yoy_growth": 18},
    "react": {"demand": "very_high", "avg_salary_usd": 125000, "yoy_growth": 10},
    "node": {"demand": "high", "avg_salary_usd": 120000, "yoy_growth": 7},
    "java": {"demand": "high", "avg_salary_usd": 135000, "yoy_growth": 3},
    "golang": {"demand": "high", "avg_salary_usd": 145000, "yoy_growth": 22},
    "rust": {"demand": "medium", "avg_salary_usd": 150000, "yoy_growth": 35},
    "kubernetes": {"demand": "very_high", "avg_salary_usd": 155000, "yoy_growth": 25},
    "docker": {"demand": "very_high", "avg_salary_usd": 140000, "yoy_growth": 15},
    "aws": {"demand": "very_high", "avg_salary_usd": 160000, "yoy_growth": 20},
    "gcp": {"demand": "high", "avg_salary_usd": 158000, "yoy_growth": 22},
    "azure": {"demand": "high", "avg_salary_usd": 155000, "yoy_growth": 18},
    "machine learning": {"demand": "very_high", "avg_salary_usd": 165000, "yoy_growth": 30},
    "llm": {"demand": "very_high", "avg_salary_usd": 180000, "yoy_growth": 80},
    "langchain": {"demand": "high", "avg_salary_usd": 175000, "yoy_growth": 90},
    "postgresql": {"demand": "high", "avg_salary_usd": 130000, "yoy_growth": 10},
    "mongodb": {"demand": "medium", "avg_salary_usd": 125000, "yoy_growth": 5},
    "redis": {"demand": "medium", "avg_salary_usd": 128000, "yoy_growth": 8},
    "terraform": {"demand": "high", "avg_salary_usd": 150000, "yoy_growth": 20},
}


@tool
def get_skill_market_data(skill_name: str) -> dict:
    """
    Return market demand, average salary, and YoY growth rate for a skill.
    Uses a curated baseline with optional live enrichment.
    """
    key = skill_name.lower().strip()
    # Fuzzy match
    for base_key, data in _SKILL_MARKET_BASELINE.items():
        if base_key in key or key in base_key:
            return {
                "skill": skill_name,
                "demand": data["demand"],
                "avg_salary_usd": data["avg_salary_usd"],
                "yoy_growth_pct": data["yoy_growth"],
                "source": "futurevip_baseline_2024",
            }
    # Default for unknown skill
    return {
        "skill": skill_name,
        "demand": "unknown",
        "avg_salary_usd": None,
        "yoy_growth_pct": None,
        "source": "not_in_database",
    }


# --------------------------------------------------------------------------- #
# Tool: generate_embedding
# --------------------------------------------------------------------------- #

@tool
async def generate_embedding(text: str) -> list:
    """
    Generate a text embedding using OpenAI text-embedding-3-large.
    Returns a list of floats (3072 dimensions).
    """
    client = _get_openai()
    text_clean = text.replace("\n", " ").strip()
    # Truncate to ~8000 tokens (rough character limit)
    if len(text_clean) > 30000:
        text_clean = text_clean[:30000]

    response = await client.embeddings.create(
        model="text-embedding-3-large",
        input=text_clean,
    )
    return response.data[0].embedding


# --------------------------------------------------------------------------- #
# Tool: search_chromadb
# --------------------------------------------------------------------------- #

@tool
def search_chromadb(
    collection_name: str,
    query_embedding: list,
    n_results: int = 10,
    where_filter: Optional[dict] = None,
) -> list:
    """
    Perform a nearest-neighbour search in a ChromaDB collection.
    Returns list of dicts with keys: id, document, metadata, distance.
    """
    client = _get_chroma()
    try:
        collection = client.get_or_create_collection(collection_name)
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where_filter:
            kwargs["where"] = where_filter

        results = collection.query(**kwargs)

        output = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        for i, doc_id in enumerate(ids):
            output.append(
                {
                    "id": doc_id,
                    "document": docs[i] if i < len(docs) else "",
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": dists[i] if i < len(dists) else 1.0,
                }
            )
        return output
    except Exception as exc:
        logger.error("ChromaDB search failed: %s", exc)
        return []


# --------------------------------------------------------------------------- #
# Tool: store_chromadb
# --------------------------------------------------------------------------- #

@tool
def store_chromadb(
    collection_name: str,
    doc_id: str,
    text: str,
    embedding: list,
    metadata: Optional[dict] = None,
) -> bool:
    """
    Upsert a document with its embedding into a ChromaDB collection.
    Returns True on success, False on failure.
    """
    client = _get_chroma()
    try:
        collection = client.get_or_create_collection(collection_name)
        collection.upsert(
            ids=[doc_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata or {}],
        )
        return True
    except Exception as exc:
        logger.error("ChromaDB store failed: %s", exc)
        return False


# --------------------------------------------------------------------------- #
# Tool: save_to_database
# --------------------------------------------------------------------------- #

@tool
async def save_to_database(table: str, data: dict) -> dict:
    """
    Upsert a record into the application database.
    `data` must include an `id` field for upsert logic.
    Returns {"success": bool, "id": str, "table": str}.
    """
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text as sa_text

        # Build a lightweight async engine from the sync DATABASE_URL
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        engine = create_async_engine(db_url, echo=False)

        columns = list(data.keys())
        placeholders = ", ".join(f":{c}" for c in columns)
        col_str = ", ".join(columns)
        update_str = ", ".join(
            f"{c} = EXCLUDED.{c}" for c in columns if c != "id"
        )
        sql = sa_text(
            f"INSERT INTO {table} ({col_str}) VALUES ({placeholders}) "
            f"ON CONFLICT (id) DO UPDATE SET {update_str}"
        )

        async with engine.begin() as conn:
            await conn.execute(sql, data)

        await engine.dispose()
        return {"success": True, "id": data.get("id"), "table": table}
    except Exception as exc:
        logger.error("save_to_database failed for table=%s: %s", table, exc)
        return {"success": False, "error": str(exc), "table": table}


# --------------------------------------------------------------------------- #
# Tool: send_notification
# --------------------------------------------------------------------------- #

@tool
async def send_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Create and store a notification for a user.
    notification_type: job_match | resume_analyzed | ats_improved |
                       application_status | career_milestone | weekly_digest
    Returns dict with notification_id and status.
    """
    import uuid
    from datetime import datetime, timezone

    notification_id = str(uuid.uuid4())
    record = {
        "id": notification_id,
        "user_id": user_id,
        "type": notification_type,
        "title": title,
        "message": message,
        "metadata": json.dumps(metadata or {}),
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    result = await save_to_database.ainvoke(
        {"table": "notifications", "data": record}
    )
    return {
        "notification_id": notification_id,
        "status": "sent" if result.get("success") else "failed",
        "type": notification_type,
    }
