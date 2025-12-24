"""Application configuration management."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str

    # Security
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:8501"

    # AWS (optional for local development)
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET: str = "social-analytics-exports"
    USE_AWS_SECRETS_MANAGER: bool = False

    # APScheduler
    SCHEDULER_EXECUTORS_DEFAULT_MAX_WORKERS: int = 10
    SCHEDULER_JOB_DEFAULTS_COALESCE: bool = False
    SCHEDULER_JOB_DEFAULTS_MAX_INSTANCES: int = 3

    # API
    API_BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:8501"

    # Application
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS comma-separated string into list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


# Global settings instance
settings = Settings()
