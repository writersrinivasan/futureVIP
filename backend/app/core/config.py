"""Application configuration using Pydantic Settings"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database — required; Railway injects DATABASE_URL automatically
    DATABASE_URL: str
    DATABASE_ECHO: bool = False

    # OpenAI — empty string means BYOK only (users supply key via Settings page)
    OPENAI_API_KEY: str = ""

    # Third-party job source keys — all optional; discovery skipped when absent
    ADZUNA_API_ID: str = ""
    ADZUNA_API_KEY: str = ""
    JSEARCH_API_KEY: str = ""
    GREENHOUSE_API_KEY: str = ""
    LEVER_API_KEY: str = ""

    # Redis — optional; caching silently disabled when unreachable
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_EXPIRY: int = 3600

    # JWT — SECRET_KEY required; generate with: openssl rand -hex 32
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ChromaDB — /tmp/chroma works on Railway; mount a volume for persistence
    CHROMA_DB_PATH: str = "/tmp/chroma"

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    # Set to your Vercel domain in production, e.g. "https://futurevip.vercel.app"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Celery — optional; background tasks disabled when broker URL is absent
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated allowed origins into a list."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
