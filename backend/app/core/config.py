"""Application configuration using Pydantic Settings"""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    DATABASE_URL: str
    DATABASE_ECHO: bool = False

    # API Keys
    OPENAI_API_KEY: str
    ADZUNA_API_ID: str
    ADZUNA_API_KEY: str
    JSEARCH_API_KEY: str
    GREENHOUSE_API_KEY: str
    LEVER_API_KEY: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_EXPIRY: int = 3600

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ChromaDB
    CHROMA_DB_PATH: str = "./data/chroma"

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse allowed origins into a list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
