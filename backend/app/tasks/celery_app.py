"""Celery application configuration with Redis broker and beat schedule."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# ---------------------------------------------------------------------------
# Celery instance
# ---------------------------------------------------------------------------

celery_app = Celery(
    "futurevip",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.job_tasks",
        "app.tasks.resume_tasks",
    ],
)

# ---------------------------------------------------------------------------
# General configuration
# ---------------------------------------------------------------------------

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task result expiry (24 hours)
    result_expires=86400,
    # Worker concurrency & prefetch
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    # Retry policy defaults
    task_max_retries=3,
    task_default_retry_delay=60,  # seconds
    # Soft/hard time limits (seconds)
    task_soft_time_limit=300,  # 5 minutes — triggers SoftTimeLimitExceeded
    task_time_limit=600,        # 10 minutes — SIGKILL
    # Visibility timeout (must be >= longest expected task duration)
    broker_transport_options={"visibility_timeout": 3600},
)

# ---------------------------------------------------------------------------
# Task routing
# ---------------------------------------------------------------------------

celery_app.conf.task_routes = {
    # High-priority: job discovery and user-facing tasks
    "app.tasks.job_tasks.discover_jobs_task": {"queue": "jobs"},
    "app.tasks.job_tasks.match_jobs_for_user_task": {"queue": "matching"},
    "app.tasks.job_tasks.generate_embeddings_task": {"queue": "embeddings"},
    "app.tasks.job_tasks.send_notification_task": {"queue": "notifications"},
    "app.tasks.job_tasks.cleanup_old_jobs_task": {"queue": "maintenance"},
    # Resume processing pipeline
    "app.tasks.resume_tasks.process_resume_task": {"queue": "resumes"},
}

celery_app.conf.task_default_queue = "default"

# ---------------------------------------------------------------------------
# Beat schedule (periodic tasks)
# ---------------------------------------------------------------------------

celery_app.conf.beat_schedule = {
    # Discover new jobs from all sources every 6 hours
    "discover-jobs-every-6h": {
        "task": "app.tasks.job_tasks.discover_jobs_task",
        "schedule": crontab(minute=0, hour="*/6"),
        "kwargs": {
            "query": "software engineer",
            "location": None,
            "limit_per_source": 50,
        },
        "options": {"queue": "jobs"},
    },
    # Refresh embedding index every 24 hours
    "refresh-job-embeddings-daily": {
        "task": "app.tasks.job_tasks.generate_embeddings_task",
        "schedule": crontab(minute=30, hour=2),  # 02:30 UTC daily
        "kwargs": {"resume_id": None},
        "options": {"queue": "embeddings"},
    },
    # Remove jobs older than 30 days every day at 03:00 UTC
    "cleanup-old-jobs-daily": {
        "task": "app.tasks.job_tasks.cleanup_old_jobs_task",
        "schedule": crontab(minute=0, hour=3),
        "options": {"queue": "maintenance"},
    },
}
