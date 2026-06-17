"""Career roadmap, skills management, and insights endpoints."""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.v1.deps import CurrentUser, DBSession
from app.core.logging import get_logger
from app.db.models import CareerRoadmap, Resume, UserSkill
from app.db.schemas import (
    CareerInsights,
    CareerRoadmapGenerateRequest,
    CareerRoadmapResponse,
    CareerRoadmapUpdate,
    MessageResponse,
    SkillAnalysisRequest,
    SkillGapAnalysis,
    UserSkillCreate,
    UserSkillResponse,
)

router = APIRouter(prefix="/career", tags=["Career"])
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Roadmap endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/roadmap",
    response_model=CareerRoadmapResponse,
    summary="Get the active career roadmap for the current user",
)
async def get_roadmap(
    current_user: CurrentUser,
    db: DBSession,
) -> CareerRoadmapResponse:
    """Return the most recent career roadmap for the current user."""
    result = await db.execute(
        select(CareerRoadmap)
        .where(CareerRoadmap.user_id == current_user.id)
        .order_by(CareerRoadmap.updated_at.desc())
        .limit(1)
    )
    roadmap = result.scalar_one_or_none()
    if roadmap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No career roadmap found. Generate one to get started.",
        )
    return CareerRoadmapResponse.model_validate(roadmap)


@router.post(
    "/roadmap/generate",
    response_model=CareerRoadmapResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new AI-powered career roadmap",
)
async def generate_roadmap(
    request: CareerRoadmapGenerateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> CareerRoadmapResponse:
    """
    Generate a structured career roadmap from current role to target role.

    The roadmap is stored and returned immediately. An async refinement task
    can enrich it further using the AI service.
    """
    # Build a structured roadmap data skeleton
    timeline_months = request.timeline_months or 12
    phases = []
    phase_size = max(1, timeline_months // 3)

    phase_templates = [
        {
            "phase": 1,
            "name": "Foundation & Assessment",
            "duration_months": phase_size,
            "objectives": [
                f"Deep-dive into requirements for {request.target_role}",
                "Identify skill gaps vs current skillset",
                "Set up learning plan and milestones",
            ],
            "milestones": ["Skill audit complete", "Learning resources identified"],
            "resources": [
                {"type": "course", "title": "Role-specific foundations course"},
                {"type": "book", "title": "Industry reference guide"},
            ],
        },
        {
            "phase": 2,
            "name": "Skill Building",
            "duration_months": phase_size,
            "objectives": [
                "Complete core technical training",
                "Build 1-2 portfolio projects",
                "Network with professionals in target role",
            ],
            "milestones": ["First project completed", "Completed key certifications"],
            "resources": [
                {"type": "project", "title": "Hands-on capstone project"},
                {"type": "community", "title": "Industry Slack / Discord community"},
            ],
        },
        {
            "phase": 3,
            "name": "Application & Transition",
            "duration_months": timeline_months - (phase_size * 2),
            "objectives": [
                f"Apply to {request.target_role} positions",
                "Ace interviews through targeted preparation",
                "Negotiate and accept offer",
            ],
            "milestones": ["Resume tailored for target role", "10+ applications sent"],
            "resources": [
                {"type": "tool", "title": "Interview prep platform"},
                {"type": "service", "title": "Resume review service"},
            ],
        },
    ]
    phases = [p for p in phase_templates if p["duration_months"] > 0]

    roadmap_data = {
        "phases": phases,
        "total_duration_months": timeline_months,
        "current_role": request.current_role,
        "target_role": request.target_role,
        "key_skills_to_acquire": [],
        "estimated_salary_increase": "20-40%",
    }

    roadmap = CareerRoadmap(
        user_id=current_user.id,
        current_role=request.current_role,
        target_role=request.target_role,
        roadmap_data=roadmap_data,
        progress=0,
    )
    db.add(roadmap)
    await db.commit()
    await db.refresh(roadmap)

    logger.info(
        "Career roadmap generated",
        extra={
            "user_id": str(current_user.id),
            "roadmap_id": str(roadmap.id),
            "target_role": request.target_role,
        },
    )
    return CareerRoadmapResponse.model_validate(roadmap)


@router.put(
    "/roadmap",
    response_model=CareerRoadmapResponse,
    summary="Update the active career roadmap",
)
async def update_roadmap(
    updates: CareerRoadmapUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> CareerRoadmapResponse:
    """Update progress or data on the most recent roadmap."""
    result = await db.execute(
        select(CareerRoadmap)
        .where(CareerRoadmap.user_id == current_user.id)
        .order_by(CareerRoadmap.updated_at.desc())
        .limit(1)
    )
    roadmap = result.scalar_one_or_none()
    if roadmap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No career roadmap found",
        )

    if updates.progress is not None:
        roadmap.progress = updates.progress
    if updates.roadmap_data is not None:
        roadmap.roadmap_data = updates.roadmap_data

    await db.commit()
    await db.refresh(roadmap)
    return CareerRoadmapResponse.model_validate(roadmap)


# ---------------------------------------------------------------------------
# Skills endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/skills",
    response_model=list[UserSkillResponse],
    summary="List the current user's skills",
)
async def list_skills(
    current_user: CurrentUser,
    db: DBSession,
) -> list[UserSkillResponse]:
    """Return all skills associated with the current user."""
    result = await db.execute(
        select(UserSkill)
        .where(UserSkill.user_id == current_user.id)
        .order_by(UserSkill.skill_name)
    )
    skills = result.scalars().all()
    return [UserSkillResponse.model_validate(s) for s in skills]


@router.post(
    "/skills",
    response_model=UserSkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a skill to the current user's profile",
)
async def add_skill(
    skill_data: UserSkillCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> UserSkillResponse:
    """Add a skill entry for the current user."""
    # Check for duplicate
    existing = await db.execute(
        select(UserSkill).where(
            UserSkill.user_id == current_user.id,
            UserSkill.skill_name == skill_data.skill_name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Skill '{skill_data.skill_name}' already exists on your profile",
        )

    skill = UserSkill(
        user_id=current_user.id,
        skill_name=skill_data.skill_name,
        proficiency_level=skill_data.proficiency_level,
        years_experience=skill_data.years_experience,
    )
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    return UserSkillResponse.model_validate(skill)


@router.post(
    "/skills/analyze",
    response_model=SkillGapAnalysis,
    summary="Analyse skill gaps against a target role",
)
async def analyze_skill_gaps(
    request: SkillAnalysisRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> SkillGapAnalysis:
    """
    Compare the user's current skills against the requirements for a target role
    and return a gap analysis with recommendations.
    """
    result = await db.execute(
        select(UserSkill).where(UserSkill.user_id == current_user.id)
    )
    user_skills_rows = result.scalars().all()
    current_skills_list = (
        request.current_skills
        if request.current_skills
        else [s.skill_name.lower() for s in user_skills_rows]
    )

    # Simplified role-to-skills mapping (in production this comes from AI/DB)
    role_skill_map: dict[str, list[str]] = {
        "software engineer": ["python", "java", "javascript", "sql", "git", "docker", "api design"],
        "data scientist": ["python", "machine learning", "sql", "statistics", "tensorflow", "pandas"],
        "devops engineer": ["docker", "kubernetes", "terraform", "aws", "ci/cd", "linux", "bash"],
        "product manager": ["roadmapping", "agile", "stakeholder management", "analytics", "user research"],
        "frontend developer": ["javascript", "react", "css", "html", "typescript", "figma"],
        "backend developer": ["python", "java", "node.js", "sql", "rest api", "docker", "aws"],
        "machine learning engineer": ["python", "tensorflow", "pytorch", "mlops", "kubernetes", "sql"],
    }

    target_lower = request.target_role.lower()
    required_skills: list[str] = []
    for role_key, skills in role_skill_map.items():
        if role_key in target_lower or any(w in target_lower for w in role_key.split()):
            required_skills = skills
            break

    if not required_skills:
        required_skills = ["communication", "problem-solving", "teamwork", "adaptability"]

    current_lower = [s.lower() for s in current_skills_list]
    missing_skills = [s for s in required_skills if s not in current_lower]
    matched_count = len(required_skills) - len(missing_skills)
    gap_score = round((matched_count / max(len(required_skills), 1)) * 100, 1)

    recommendations = []
    if missing_skills:
        recommendations.append(
            f"Focus on acquiring: {', '.join(missing_skills[:3])}"
        )
    recommendations.append(
        f"Consider certifications relevant to {request.target_role}"
    )
    recommendations.append("Build portfolio projects demonstrating required skills")

    learning_resources = [
        {"platform": "Coursera", "url": "https://coursera.org", "type": "MOOC"},
        {"platform": "Udemy", "url": "https://udemy.com", "type": "Video course"},
        {"platform": "LinkedIn Learning", "url": "https://linkedin.com/learning", "type": "Professional"},
        {"platform": "freeCodeCamp", "url": "https://freecodecamp.org", "type": "Free"},
    ]

    return SkillGapAnalysis(
        target_role=request.target_role,
        current_skills=current_skills_list,
        required_skills=required_skills,
        missing_skills=missing_skills,
        gap_score=gap_score,
        recommendations=recommendations,
        learning_resources=learning_resources,
    )


# ---------------------------------------------------------------------------
# Insights endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/insights",
    response_model=CareerInsights,
    summary="Get market insights for career planning",
)
async def get_career_insights(
    current_user: CurrentUser,
    db: DBSession,
    target_role: Optional[str] = Query(default=None),
) -> CareerInsights:
    """Return current job market insights and trend data for career planning."""
    # In production, this data would come from the AI layer + job data analytics
    role = target_role or "Software Engineer"

    return CareerInsights(
        top_in_demand_skills=[
            "Python", "React", "AWS", "TypeScript", "Kubernetes",
            "Machine Learning", "GraphQL", "Terraform",
        ],
        salary_range={"min": 90000, "median": 130000, "max": 180000},
        job_market_trend="growing",
        recommended_certifications=[
            "AWS Certified Solutions Architect",
            "Google Professional Cloud Architect",
            "Certified Kubernetes Administrator",
        ],
        career_paths=[
            {
                "path": f"Senior {role}",
                "timeline": "2-3 years",
                "salary_increase": "15-25%",
            },
            {
                "path": f"Lead {role}",
                "timeline": "4-6 years",
                "salary_increase": "30-50%",
            },
            {
                "path": "Engineering Manager",
                "timeline": "6-8 years",
                "salary_increase": "40-70%",
            },
        ],
        industry_growth_rate=12.5,
    )
