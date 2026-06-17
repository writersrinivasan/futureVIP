"""Analytics and dashboard metrics endpoints."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.v1.deps import CurrentUser, DBSession
from app.core.logging import get_logger
from app.db.models import (
    Application,
    ApplicationStatus,
    CareerRoadmap,
    InterviewSession,
    Job,
    JobMatch,
    Notification,
    Resume,
)
from app.db.schemas import DashboardMetrics

router = APIRouter(prefix="/analytics", tags=["Analytics"])
logger = get_logger(__name__)


@router.get(
    "/dashboard",
    response_model=DashboardMetrics,
    summary="Get all dashboard metrics for the current user",
)
async def get_dashboard(
    current_user: CurrentUser,
    db: DBSession,
) -> DashboardMetrics:
    """
    Aggregate all metrics required by the dashboard in a single call.

    Returns ATS / resume / match scores, application funnel, recent activity
    timeline, top matching jobs, and skill-gap insights.
    """
    # ---- Resume scores ----
    resume_result = await db.execute(
        select(Resume)
        .where(Resume.user_id == current_user.id, Resume.is_active == True)  # noqa: E712
        .order_by(Resume.created_at.desc())
        .limit(1)
    )
    latest_resume = resume_result.scalar_one_or_none()
    ats_score = latest_resume.ats_score if latest_resume else None
    resume_score = latest_resume.resume_score if latest_resume else None

    # ---- Best job match score ----
    match_result = await db.execute(
        select(func.max(JobMatch.match_score)).where(
            JobMatch.user_id == current_user.id
        )
    )
    match_score_val = match_result.scalar_one_or_none()
    match_score = round(match_score_val * 100, 1) if match_score_val else None

    # ---- Career progress ----
    roadmap_result = await db.execute(
        select(CareerRoadmap)
        .where(CareerRoadmap.user_id == current_user.id)
        .order_by(CareerRoadmap.updated_at.desc())
        .limit(1)
    )
    latest_roadmap = roadmap_result.scalar_one_or_none()
    career_progress = latest_roadmap.progress if latest_roadmap else 0

    # ---- Application funnel counts ----
    funnel_result = await db.execute(
        select(Application.status, func.count(Application.id).label("cnt"))
        .where(Application.user_id == current_user.id)
        .group_by(Application.status)
    )
    funnel_rows = funnel_result.all()
    funnel: dict[str, int] = {row.status.value: row.cnt for row in funnel_rows}

    saved_jobs = funnel.get(ApplicationStatus.SAVED.value, 0)
    applied_jobs = funnel.get(ApplicationStatus.APPLIED.value, 0)
    interviews_scheduled = funnel.get(ApplicationStatus.INTERVIEW.value, 0)
    offers_received = funnel.get(ApplicationStatus.OFFER.value, 0)

    # ---- Weekly opportunities (new jobs in last 7 days) ----
    week_ago = datetime.now(tz=timezone.utc) - timedelta(days=7)
    weekly_result = await db.execute(
        select(func.count(Job.id)).where(Job.scraped_at >= week_ago)
    )
    weekly_opportunities = weekly_result.scalar_one() or 0

    # ---- Total job matches ----
    total_matches_result = await db.execute(
        select(func.count(JobMatch.id)).where(JobMatch.user_id == current_user.id)
    )
    total_matches = total_matches_result.scalar_one() or 0

    # ---- Skill gap insights ----
    skill_gap_insights: dict = {}
    if latest_resume and latest_resume.parsed_data:
        parsed = latest_resume.parsed_data
        found = parsed.get("keywords_found", [])
        common_keywords = [
            "python", "java", "javascript", "typescript", "react", "node",
            "sql", "aws", "docker", "kubernetes", "api", "rest", "agile",
        ]
        missing = [k for k in common_keywords if k not in found]
        skill_gap_insights = {
            "skills_found": found,
            "skills_missing": missing[:5],
            "gap_percentage": round((len(missing) / max(len(common_keywords), 1)) * 100, 1),
            "top_recommendation": (
                f"Add {missing[0]} to your resume" if missing else "Great keyword coverage!"
            ),
        }

    # ---- Activity timeline (last 10 events) ----
    timeline: list[dict] = []

    # Applications
    apps_result = await db.execute(
        select(Application)
        .where(Application.user_id == current_user.id)
        .order_by(Application.updated_at.desc())
        .limit(5)
    )
    for app in apps_result.scalars().all():
        timeline.append(
            {
                "type": "application",
                "event": f"Application status: {app.status.value}",
                "timestamp": app.updated_at.isoformat(),
                "resource_id": str(app.id),
            }
        )

    # Interview sessions
    iv_result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.created_at.desc())
        .limit(3)
    )
    for iv in iv_result.scalars().all():
        timeline.append(
            {
                "type": "interview",
                "event": f"Mock interview session (score: {iv.score or 'pending'})",
                "timestamp": iv.created_at.isoformat(),
                "resource_id": str(iv.id),
            }
        )

    # Sort timeline newest first
    timeline.sort(key=lambda x: x["timestamp"], reverse=True)
    timeline = timeline[:10]

    # ---- Top matching jobs ----
    top_matches_result = await db.execute(
        select(JobMatch, Job)
        .join(Job, JobMatch.job_id == Job.id)
        .where(JobMatch.user_id == current_user.id)
        .order_by(JobMatch.match_score.desc())
        .limit(5)
    )
    top_matching_jobs = [
        {
            "job_id": str(row.Job.id),
            "title": row.Job.title,
            "company": row.Job.company,
            "location": row.Job.location,
            "match_score": round(row.JobMatch.match_score * 100, 1),
            "remote": row.Job.remote,
        }
        for row in top_matches_result.all()
    ]

    return DashboardMetrics(
        ats_score=ats_score,
        resume_score=resume_score,
        match_score=match_score,
        career_progress=career_progress,
        saved_jobs=saved_jobs,
        applied_jobs=applied_jobs,
        weekly_opportunities=weekly_opportunities,
        total_matches=total_matches,
        interviews_scheduled=interviews_scheduled,
        offers_received=offers_received,
        skill_gap_insights=skill_gap_insights,
        application_funnel={**funnel},
        activity_timeline=timeline,
        top_matching_jobs=top_matching_jobs,
    )
