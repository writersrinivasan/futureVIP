"""API v1 router — aggregates all endpoint routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    analytics,
    applications,
    auth,
    career,
    health,
    interview,
    jobs,
    notifications,
    resumes,
    users,
)

api_router = APIRouter()

# Authentication (no prefix duplication — prefix lives inside each router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(resumes.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(notifications.router)
api_router.include_router(career.router)
api_router.include_router(interview.router)
api_router.include_router(analytics.router)
api_router.include_router(admin.router)
api_router.include_router(health.router)
