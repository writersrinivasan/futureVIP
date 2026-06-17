"""
Celery tasks for the resume processing pipeline.

Pipeline stages:
  1. Text extraction (PDF / DOCX / TXT)
  2. AI-powered parsing (contact info, experience, education, skills)
  3. ATS scoring & keyword analysis
  4. Embedding generation and upsert into ChromaDB
  5. Semantic job matching trigger
  6. User notification
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine inside a synchronous Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _extract_text_from_file(file_path: str) -> str:
    """
    Extract plain text from a PDF, DOCX, or TXT file.

    Falls back gracefully when optional extraction libraries are missing.
    """
    import os

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return _extract_pdf(file_path)
    if ext in (".doc", ".docx"):
        return _extract_docx(file_path)
    # Plain text fallback
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _extract_pdf(file_path: str) -> str:
    """Extract text from a PDF using pdfminer or PyPDF2 as fallback."""
    try:
        from pdfminer.high_level import extract_text

        return extract_text(file_path) or ""
    except ImportError:
        pass

    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(file_path)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    except Exception as exc:
        logger.warning("PDF extraction failed", extra={"path": file_path, "error": str(exc)})
        return ""


def _extract_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    try:
        from docx import Document

        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception as exc:
        logger.warning("DOCX extraction failed", extra={"path": file_path, "error": str(exc)})
        return ""


async def _ai_parse_resume(text: str) -> dict[str, Any]:
    """
    Use the OpenAI API to extract structured data from resume text.

    Returns a dict with keys: name, email, phone, skills, experience,
    education, summary, certifications.
    """
    from openai import AsyncOpenAI

    client = AsyncOpenAI()

    prompt = (
        "You are a professional resume parser. Extract structured information "
        "from the following resume text and return valid JSON with these keys: "
        "name (string), email (string), phone (string), "
        "skills (list of strings), "
        "experience (list of objects with: title, company, duration, description), "
        "education (list of objects with: degree, institution, year), "
        "summary (string), "
        "certifications (list of strings). "
        "If a field is not found, use null or an empty list. "
        "Return ONLY valid JSON, no markdown.\n\n"
        f"Resume text:\n{text[:6000]}"
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        import json

        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)
    except Exception as exc:
        logger.error("AI resume parsing failed", extra={"error": str(exc)})
        # Return a minimal structure on failure
        return {
            "name": None,
            "email": None,
            "phone": None,
            "skills": [],
            "experience": [],
            "education": [],
            "summary": None,
            "certifications": [],
        }


def _compute_ats_score(text: str, parsed: dict[str, Any]) -> tuple[float, float]:
    """
    Compute ATS score and resume quality score from text + parsed data.

    Returns (ats_score, resume_score) in the range [0, 100].
    """
    text_lower = text.lower()
    word_count = len(text.split())

    # Section detection
    sections = {
        "experience": any(kw in text_lower for kw in ["experience", "work history"]),
        "education": any(kw in text_lower for kw in ["education", "degree", "university"]),
        "skills": any(kw in text_lower for kw in ["skills", "technologies"]),
        "summary": any(kw in text_lower for kw in ["summary", "objective", "profile"]),
        "contact": bool(parsed.get("email") or parsed.get("phone")),
    }
    section_score = (sum(sections.values()) / len(sections)) * 100

    # Keyword density
    tech_keywords = [
        "python", "java", "javascript", "typescript", "react", "node",
        "sql", "aws", "docker", "kubernetes", "api", "rest", "agile",
        "machine learning", "data science", "cloud", "devops", "git",
    ]
    found = [kw for kw in tech_keywords if kw in text_lower]
    keyword_score = min((len(found) / 8) * 100, 100)

    # Length score
    length_score = min((word_count / 600) * 100, 100)

    # Parsed skills
    skill_count = len(parsed.get("skills") or [])
    skill_score = min((skill_count / 10) * 100, 100)

    ats = round(
        section_score * 0.35 + keyword_score * 0.35 + length_score * 0.15 + skill_score * 0.15,
        1,
    )
    resume_q = round(
        section_score * 0.45 + length_score * 0.25 + skill_score * 0.30,
        1,
    )
    return ats, resume_q


@celery_app.task(
    name="app.tasks.resume_tasks.process_resume_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=240,
    time_limit=480,
)
def process_resume_task(self: Task, resume_id: str) -> dict[str, Any]:
    """
    Full resume processing pipeline.

    Stages:
      1. Load resume row from DB
      2. Extract text from file on disk
      3. AI-parse into structured data
      4. Compute ATS / quality scores
      5. Generate embeddings and store in ChromaDB
      6. Trigger semantic job matching for the owner
      7. Notify the user

    Returns a summary dict with counts and scores.
    """
    logger.info("process_resume_task started", extra={"resume_id": resume_id})

    async def _run() -> dict[str, Any]:
        from sqlalchemy import select

        from app.db.database import AsyncSessionLocal
        from app.db.models import Resume
        from app.services.vector_store import upsert_resume_embeddings
        from openai import AsyncOpenAI

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Resume).where(Resume.id == resume_id))
            resume = result.scalar_one_or_none()
            if not resume:
                logger.error("Resume not found", extra={"resume_id": resume_id})
                return {"status": "error", "reason": "resume not found"}

            # Stage 1: Text extraction
            try:
                text = _extract_text_from_file(resume.file_path)
            except Exception as exc:
                logger.error(
                    "Text extraction failed",
                    extra={"resume_id": resume_id, "error": str(exc)},
                )
                text = ""

            resume.content_text = text

            # Stage 2: AI parsing
            parsed: dict[str, Any] = {}
            if text.strip():
                parsed = await _ai_parse_resume(text)

            # Merge text-derived keyword info into parsed_data
            text_lower = text.lower()
            tech_keywords = [
                "python", "java", "javascript", "typescript", "react", "node",
                "sql", "aws", "docker", "kubernetes", "api", "rest", "agile",
            ]
            found_keywords = [kw for kw in tech_keywords if kw in text_lower]
            parsed["keywords_found"] = found_keywords
            parsed["word_count"] = len(text.split())

            resume.parsed_data = parsed

            # Stage 3: Score computation
            ats_score, resume_score = _compute_ats_score(text, parsed)
            resume.ats_score = ats_score
            resume.resume_score = resume_score

            await db.commit()
            await db.refresh(resume)

            user_id = str(resume.user_id)

        # Stage 4: Embedding generation (outside DB session to avoid timeout)
        if text.strip():
            try:
                openai_client = AsyncOpenAI()
                chunk_size = 500
                chunks = [
                    text[i: i + chunk_size]
                    for i in range(0, min(len(text), 8000), chunk_size)
                ]
                chunks = [c for c in chunks if c.strip()]

                if chunks:
                    embed_response = await openai_client.embeddings.create(
                        model="text-embedding-3-small",
                        input=chunks,
                    )
                    embeddings = [item.embedding for item in embed_response.data]
                    upsert_resume_embeddings(
                        resume_id=resume_id,
                        chunks=chunks,
                        embeddings=embeddings,
                        metadata={"user_id": user_id},
                    )
            except Exception as exc:
                logger.error(
                    "Embedding generation failed",
                    extra={"resume_id": resume_id, "error": str(exc)},
                )

        # Stage 5: Trigger semantic matching
        from app.tasks.job_tasks import match_jobs_for_user_task, send_notification_task

        match_jobs_for_user_task.delay(user_id=user_id)

        # Stage 6: Notify user
        send_notification_task.delay(
            user_id=user_id,
            notification_type="resume_analyzed",
            title="Resume Analysis Complete",
            message=(
                f"Your resume has been analysed. "
                f"ATS Score: {ats_score}/100 | Resume Score: {resume_score}/100"
            ),
            data={
                "resume_id": resume_id,
                "ats_score": ats_score,
                "resume_score": resume_score,
            },
        )

        return {
            "status": "success",
            "resume_id": resume_id,
            "ats_score": ats_score,
            "resume_score": resume_score,
            "word_count": parsed.get("word_count", 0),
            "skills_found": len(parsed.get("skills") or []),
        }

    try:
        result = _run_async(_run())
        logger.info("process_resume_task complete", extra=result)
        return result
    except SoftTimeLimitExceeded:
        logger.warning("process_resume_task: soft time limit exceeded", extra={"resume_id": resume_id})
        raise
    except Exception as exc:
        logger.error(
            "process_resume_task failed",
            extra={"resume_id": resume_id, "error": str(exc)},
        )
        raise self.retry(exc=exc)
