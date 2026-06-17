"""Resume management and analysis endpoints."""

import os
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import CurrentUser, DBSession, Pagination
from app.core.config import settings
from app.core.logging import get_logger
from app.db.database import get_db
from app.db.models import Resume
from app.db.schemas import (
    MessageResponse,
    PaginatedResponse,
    ResumeAnalysis,
    ResumeATSScore,
    ResumeOptimizeRequest,
    ResumeResponse,
)

router = APIRouter(prefix="/resumes", tags=["Resumes"])
logger = get_logger(__name__)

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

UPLOAD_DIR = Path("./data/resumes")


def _ensure_upload_dir() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def _get_resume_or_404(
    resume_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> Resume:
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return resume


@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new resume file",
)
async def upload_resume(
    current_user: CurrentUser,
    db: DBSession,
    file: UploadFile = File(...),
) -> ResumeResponse:
    """
    Upload a resume PDF/DOCX/TXT.

    The file is stored on disk and a background task is queued to parse,
    analyse, and embed the resume asynchronously.
    """
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file.content_type}. "
            f"Allowed: PDF, DOC, DOCX, TXT",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {MAX_FILE_SIZE_MB} MB",
        )

    _ensure_upload_dir()
    safe_name = f"{uuid.uuid4()}_{Path(file.filename or 'resume').name}"
    file_path = UPLOAD_DIR / safe_name
    file_path.write_bytes(content)

    # Determine next version number for this user
    version_result = await db.execute(
        select(Resume).where(Resume.user_id == current_user.id, Resume.is_active == True)
    )
    existing_count = len(version_result.scalars().all())

    resume = Resume(
        user_id=current_user.id,
        filename=file.filename or safe_name,
        file_path=str(file_path),
        file_size=len(content),
        version=existing_count + 1,
        is_active=True,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    # Queue background processing
    try:
        from app.tasks.resume_tasks import process_resume_task
        process_resume_task.delay(str(resume.id))
    except Exception as exc:
        logger.warning("Failed to queue resume processing task", extra={"error": str(exc)})

    logger.info(
        "Resume uploaded",
        extra={"user_id": str(current_user.id), "resume_id": str(resume.id)},
    )
    return ResumeResponse.model_validate(resume)


@router.get(
    "/",
    response_model=PaginatedResponse[ResumeResponse],
    summary="List current user's resumes",
)
async def list_resumes(
    current_user: CurrentUser,
    db: DBSession,
    pagination: Pagination,
) -> PaginatedResponse[ResumeResponse]:
    """Return a paginated list of the authenticated user's resumes."""
    from sqlalchemy import func

    query = select(Resume).where(Resume.user_id == current_user.id)
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        query.order_by(Resume.created_at.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    resumes = result.scalars().all()

    return PaginatedResponse.create(
        items=[ResumeResponse.model_validate(r) for r in resumes],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    summary="Get a specific resume",
)
async def get_resume(
    resume_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ResumeResponse:
    """Return details of a specific resume owned by the current user."""
    resume = await _get_resume_or_404(resume_id, current_user.id, db)
    return ResumeResponse.model_validate(resume)


@router.delete(
    "/{resume_id}",
    response_model=MessageResponse,
    summary="Delete a resume",
)
async def delete_resume(
    resume_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> MessageResponse:
    """Delete a resume and its associated file from disk."""
    resume = await _get_resume_or_404(resume_id, current_user.id, db)

    # Remove file from disk
    try:
        if os.path.exists(resume.file_path):
            os.remove(resume.file_path)
    except OSError as exc:
        logger.warning(
            "Could not delete resume file",
            extra={"path": resume.file_path, "error": str(exc)},
        )

    await db.delete(resume)
    await db.commit()
    return MessageResponse(message="Resume deleted successfully")


@router.post(
    "/{resume_id}/analyze",
    response_model=ResumeAnalysis,
    summary="Trigger resume analysis",
)
async def analyze_resume(
    resume_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ResumeAnalysis:
    """
    Run the AI-powered resume analysis pipeline synchronously and return results.

    For large resumes this may take a few seconds. Use the background task
    endpoint for fire-and-forget processing.
    """
    resume = await _get_resume_or_404(resume_id, current_user.id, db)

    if not resume.content_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resume text has not been extracted yet. "
            "Please wait for background processing to complete.",
        )

    # Lightweight heuristic analysis (AI analysis is in the background task)
    text = resume.content_text or ""
    words = text.split()
    word_count = len(words)

    # Section detection
    sections_keywords = {
        "Experience": ["experience", "work history", "employment"],
        "Education": ["education", "degree", "university", "college"],
        "Skills": ["skills", "technologies", "tech stack"],
        "Summary": ["summary", "objective", "profile", "about"],
        "Projects": ["projects", "portfolio"],
        "Certifications": ["certifications", "certificates"],
        "Awards": ["awards", "achievements", "honors"],
    }
    text_lower = text.lower()
    sections_detected = [
        section
        for section, keywords in sections_keywords.items()
        if any(kw in text_lower for kw in keywords)
    ]

    strengths = []
    weaknesses = []
    suggestions = []

    if word_count >= 400:
        strengths.append("Resume has sufficient content length")
    else:
        weaknesses.append("Resume appears too short")
        suggestions.append("Expand experience descriptions with measurable achievements")

    if "Experience" in sections_detected:
        strengths.append("Work experience section detected")
    else:
        weaknesses.append("No clear experience section found")

    if "Skills" in sections_detected:
        strengths.append("Skills section present")
    else:
        suggestions.append("Add a dedicated skills section")

    if "Education" in sections_detected:
        strengths.append("Education section present")

    # Simple ATS keyword extraction (common tech keywords)
    common_keywords = [
        "python", "java", "javascript", "typescript", "react", "node",
        "sql", "aws", "docker", "kubernetes", "api", "rest", "agile",
        "scrum", "machine learning", "data science", "cloud", "devops",
    ]
    found_keywords = [kw for kw in common_keywords if kw in text_lower]
    missing_keywords = [kw for kw in common_keywords if kw not in text_lower]

    # Calculate basic scores
    section_score = (len(sections_detected) / len(sections_keywords)) * 100
    keyword_score = min((len(found_keywords) / 10) * 100, 100)
    length_score = min((word_count / 600) * 100, 100)
    ats_score = round((section_score * 0.4 + keyword_score * 0.4 + length_score * 0.2), 1)
    resume_score = round((section_score * 0.5 + length_score * 0.3 + keyword_score * 0.2), 1)

    # Persist scores
    resume.ats_score = ats_score
    resume.resume_score = resume_score
    parsed_data = resume.parsed_data or {}
    parsed_data.update(
        {
            "sections": sections_detected,
            "word_count": word_count,
            "keywords_found": found_keywords,
        }
    )
    resume.parsed_data = parsed_data
    await db.commit()

    return ResumeAnalysis(
        resume_id=resume.id,
        ats_score=ats_score,
        resume_score=resume_score,
        strengths=strengths,
        weaknesses=weaknesses,
        suggestions=suggestions,
        keywords_found=found_keywords,
        keywords_missing=missing_keywords[:10],
        sections_detected=sections_detected,
        word_count=word_count,
        parsed_data=parsed_data,
    )


@router.get(
    "/{resume_id}/ats-score",
    response_model=ResumeATSScore,
    summary="Get ATS score for a resume",
)
async def get_ats_score(
    resume_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ResumeATSScore:
    """Return the stored ATS score and keyword analysis for a resume."""
    resume = await _get_resume_or_404(resume_id, current_user.id, db)

    parsed = resume.parsed_data or {}
    matched = parsed.get("keywords_found", [])
    common_keywords = [
        "python", "java", "javascript", "typescript", "react", "node",
        "sql", "aws", "docker", "kubernetes", "api", "rest", "agile",
        "scrum", "machine learning", "data science", "cloud", "devops",
    ]
    missing = [kw for kw in common_keywords if kw not in matched]

    recommendations = []
    if resume.ats_score is not None and resume.ats_score < 70:
        recommendations.append("Add more industry-relevant keywords to your resume")
    if "Skills" not in parsed.get("sections", []):
        recommendations.append("Include a dedicated Skills section")
    if len(matched) < 5:
        recommendations.append(
            "Incorporate more technical skills that appear in job descriptions"
        )

    return ResumeATSScore(
        resume_id=resume.id,
        ats_score=resume.ats_score or 0.0,
        job_title=None,
        matched_keywords=matched,
        missing_keywords=missing[:10],
        format_score=75.0,
        content_score=resume.resume_score or 0.0,
        recommendations=recommendations,
    )


@router.post(
    "/{resume_id}/optimize",
    response_model=ResumeAnalysis,
    summary="Optimize resume for a target role or job description",
)
async def optimize_resume(
    resume_id: uuid.UUID,
    optimize_request: ResumeOptimizeRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> ResumeAnalysis:
    """
    Generate AI-powered optimisation suggestions for the resume.

    Accepts an optional job description or target role to tailor the feedback.
    """
    resume = await _get_resume_or_404(resume_id, current_user.id, db)

    if not resume.content_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resume content not yet extracted",
        )

    text_lower = (resume.content_text or "").lower()
    sections_keywords = {
        "Experience": ["experience", "work history", "employment"],
        "Education": ["education", "degree", "university", "college"],
        "Skills": ["skills", "technologies", "tech stack"],
        "Summary": ["summary", "objective", "profile", "about"],
        "Projects": ["projects", "portfolio"],
        "Certifications": ["certifications", "certificates"],
        "Awards": ["awards", "achievements", "honors"],
    }
    sections_detected = [
        s for s, kws in sections_keywords.items() if any(kw in text_lower for kw in kws)
    ]

    suggestions = [
        "Quantify achievements with metrics (e.g., 'Reduced latency by 30%')",
        "Use strong action verbs at the start of each bullet point",
        "Tailor keywords to match the specific job description",
        "Ensure consistent formatting throughout all sections",
    ]
    if optimize_request.target_role:
        suggestions.append(
            f"Highlight experiences most relevant to '{optimize_request.target_role}'"
        )
    if optimize_request.job_description:
        suggestions.append(
            "Mirror language from the provided job description in your resume"
        )

    word_count = len((resume.content_text or "").split())
    common_keywords = [
        "python", "java", "javascript", "typescript", "react", "node",
        "sql", "aws", "docker", "kubernetes", "api", "rest", "agile",
    ]
    found = [kw for kw in common_keywords if kw in text_lower]
    missing = [kw for kw in common_keywords if kw not in text_lower]

    return ResumeAnalysis(
        resume_id=resume.id,
        ats_score=resume.ats_score or 0.0,
        resume_score=resume.resume_score or 0.0,
        strengths=["Content present for optimization"],
        weaknesses=[],
        suggestions=suggestions,
        keywords_found=found,
        keywords_missing=missing[:10],
        sections_detected=sections_detected,
        word_count=word_count,
        parsed_data=resume.parsed_data or {},
    )
