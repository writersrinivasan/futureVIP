"""Pydantic v2 request/response schemas for FUTURE VIP platform."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.db.models import ApplicationStatus, JobType, NotificationType, ProficiencyLevel

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list wrapper."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: list[T]
    total: int
    skip: int
    limit: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(cls, items: list[T], total: int, skip: int, limit: int) -> "PaginatedResponse[T]":
        return cls(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            has_next=(skip + limit) < total,
            has_prev=skip > 0,
        )


class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Auth / Token
# ---------------------------------------------------------------------------


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Seconds until access token expires")


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]


class UserAdminResponse(UserResponse):
    """Extended user details for admin endpoints."""
    pass


# ---------------------------------------------------------------------------
# Resume schemas
# ---------------------------------------------------------------------------


class ResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    filename: str
    file_size: Optional[int]
    ats_score: Optional[float]
    resume_score: Optional[float]
    version: int
    is_active: bool
    created_at: datetime
    parsed_data: Optional[dict[str, Any]]


class ResumeAnalysis(BaseModel):
    resume_id: uuid.UUID
    ats_score: float = Field(ge=0, le=100)
    resume_score: float = Field(ge=0, le=100)
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    keywords_found: list[str]
    keywords_missing: list[str]
    sections_detected: list[str]
    word_count: int
    parsed_data: dict[str, Any]


class ResumeOptimizeRequest(BaseModel):
    job_description: Optional[str] = None
    target_role: Optional[str] = None


class ResumeATSScore(BaseModel):
    resume_id: uuid.UUID
    ats_score: float
    job_title: Optional[str]
    matched_keywords: list[str]
    missing_keywords: list[str]
    format_score: float
    content_score: float
    recommendations: list[str]


# ---------------------------------------------------------------------------
# Job schemas
# ---------------------------------------------------------------------------


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_id: Optional[str]
    source: str
    title: str
    company: str
    location: Optional[str]
    description: Optional[str]
    requirements: Optional[str]
    salary_min: Optional[float]
    salary_max: Optional[float]
    job_type: Optional[JobType]
    remote: bool
    url: Optional[str]
    posted_at: Optional[datetime]
    scraped_at: datetime
    metadata_: Optional[dict[str, Any]] = Field(None, alias="metadata_")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class JobSearchParams(BaseModel):
    query: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    remote: Optional[bool] = None
    job_type: Optional[JobType] = None
    source: Optional[str] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class JobDiscoverRequest(BaseModel):
    query: str
    location: Optional[str] = None
    remote: Optional[bool] = None
    limit_per_source: int = Field(default=25, ge=1, le=100)


# ---------------------------------------------------------------------------
# Job Match schemas
# ---------------------------------------------------------------------------


class JobMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    resume_id: uuid.UUID
    match_score: float
    ats_score: Optional[float]
    skill_gap: Optional[dict[str, Any]]
    reasoning: Optional[str]
    created_at: datetime
    job: Optional[JobResponse] = None


# ---------------------------------------------------------------------------
# Application schemas
# ---------------------------------------------------------------------------


class ApplicationCreate(BaseModel):
    job_id: uuid.UUID
    status: ApplicationStatus = ApplicationStatus.SAVED
    notes: Optional[str] = None
    follow_up_date: Optional[datetime] = None


class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    notes: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    applied_at: Optional[datetime] = None


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    status: ApplicationStatus
    applied_at: Optional[datetime]
    notes: Optional[str]
    follow_up_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    job: Optional[JobResponse] = None


class ApplicationStats(BaseModel):
    total: int
    saved: int
    applied: int
    screening: int
    interview: int
    offer: int
    rejected: int
    withdrawn: int
    conversion_rate: float


# ---------------------------------------------------------------------------
# Notification schemas
# ---------------------------------------------------------------------------


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    title: str
    message: str
    is_read: bool
    data: Optional[dict[str, Any]]
    created_at: datetime


# ---------------------------------------------------------------------------
# User Skill schemas
# ---------------------------------------------------------------------------


class UserSkillCreate(BaseModel):
    skill_name: str = Field(max_length=255)
    proficiency_level: ProficiencyLevel = ProficiencyLevel.INTERMEDIATE
    years_experience: Optional[float] = Field(default=None, ge=0)


class UserSkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    skill_name: str
    proficiency_level: ProficiencyLevel
    years_experience: Optional[float]
    is_verified: bool


class SkillAnalysisRequest(BaseModel):
    target_role: str
    current_skills: Optional[list[str]] = None


class SkillGapAnalysis(BaseModel):
    target_role: str
    current_skills: list[str]
    required_skills: list[str]
    missing_skills: list[str]
    gap_score: float = Field(ge=0, le=100)
    recommendations: list[str]
    learning_resources: list[dict[str, str]]


# ---------------------------------------------------------------------------
# Career Roadmap schemas
# ---------------------------------------------------------------------------


class CareerRoadmapGenerateRequest(BaseModel):
    current_role: str
    target_role: str
    timeline_months: Optional[int] = Field(default=12, ge=1, le=60)


class CareerRoadmapUpdate(BaseModel):
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    roadmap_data: Optional[dict[str, Any]] = None


class CareerRoadmapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    current_role: Optional[str]
    target_role: Optional[str]
    roadmap_data: Optional[dict[str, Any]]
    progress: int
    created_at: datetime
    updated_at: datetime


class CareerInsights(BaseModel):
    top_in_demand_skills: list[str]
    salary_range: dict[str, float]
    job_market_trend: str
    recommended_certifications: list[str]
    career_paths: list[dict[str, Any]]
    industry_growth_rate: float


# ---------------------------------------------------------------------------
# Interview schemas
# ---------------------------------------------------------------------------


class InterviewStartRequest(BaseModel):
    job_id: Optional[uuid.UUID] = None
    interview_type: str = Field(
        default="behavioral",
        description="behavioral, technical, system_design, hr",
    )
    difficulty: str = Field(default="medium", description="easy, medium, hard")
    num_questions: int = Field(default=5, ge=1, le=20)


class InterviewAnswerRequest(BaseModel):
    question_id: str
    answer: str = Field(min_length=1, max_length=5000)


class InterviewQuestionResponse(BaseModel):
    question_id: str
    question: str
    category: str
    difficulty: str
    follow_up_hints: Optional[list[str]] = None


class InterviewSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: Optional[uuid.UUID]
    session_data: Optional[dict[str, Any]]
    score: Optional[float]
    feedback: Optional[str]
    created_at: datetime


class InterviewFeedback(BaseModel):
    session_id: uuid.UUID
    overall_score: float = Field(ge=0, le=100)
    category_scores: dict[str, float]
    strengths: list[str]
    areas_for_improvement: list[str]
    detailed_feedback: list[dict[str, Any]]
    recommended_resources: list[str]


# ---------------------------------------------------------------------------
# Analytics schemas
# ---------------------------------------------------------------------------


class DashboardMetrics(BaseModel):
    ats_score: Optional[float]
    resume_score: Optional[float]
    match_score: Optional[float]
    career_progress: int
    saved_jobs: int
    applied_jobs: int
    weekly_opportunities: int
    total_matches: int
    interviews_scheduled: int
    offers_received: int
    skill_gap_insights: dict[str, Any]
    application_funnel: dict[str, int]
    activity_timeline: list[dict[str, Any]]
    top_matching_jobs: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Admin schemas
# ---------------------------------------------------------------------------


class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_jobs: int
    total_applications: int
    total_resumes: int
    total_matches: int
    new_users_today: int
    new_jobs_today: int


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[dict[str, Any]]
    ip_address: Optional[str]
    created_at: datetime


# ---------------------------------------------------------------------------
# Health schemas
# ---------------------------------------------------------------------------


class ServiceStatus(BaseModel):
    status: str  # "ok" | "degraded" | "down"
    latency_ms: Optional[float] = None
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    environment: str
    services: dict[str, ServiceStatus]
    timestamp: datetime
