"""Application configuration management using pydantic-settings

This module provides environment-based configuration with validation.
All settings can be overridden via .env file or environment variables.
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables

    Priority order: Environment variables > .env file > defaults
    """

    # API Keys for GenAI providers
    OPENAI_API_KEY: str = ""  # Primary provider
    HUGGINGFACE_TOKEN: Optional[str] = None  # Free fallback

    # API authentication for our FastAPI service (do NOT reuse provider keys)
    API_AUTH_TOKEN: Optional[str] = None

    # Google Cloud (optional provider)
    GOOGLE_PROJECT_ID: Optional[str] = None
    GOOGLE_LOCATION: Optional[str] = "us-central1"
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None  # Path to service account JSON

    # Google AI (API key-based Gemini Image API)
    GOOGLE_AI_API_KEY: Optional[str] = None
    GOOGLE_AI_IMAGE_MODEL: str = "gemini-2.5-flash-image"
    GOOGLE_AI_ENDPOINT: str = "https://generativelanguage.googleapis.com"

    # Storage configuration
    STORAGE_MODE: str = "local"  # Options: "local" | "azure" | "s3"
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None

    # Processing configuration
    MAX_CONCURRENT_GENERATIONS: int = 3  # Limit concurrent GenAI calls
    RETRY_MAX_ATTEMPTS: int = 3  # Retry failed API calls
    RETRY_BACKOFF_FACTOR: float = 2.0  # Exponential backoff multiplier

    # Celery / Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR

    # Provider selection and fallback chain
    GENAI_PROVIDER: str = "openai"  # Primary: openai | google | huggingface | mock
    GENAI_FALLBACKS: str = "google,huggingface,mock"  # Comma-separated fallback order

    # Image generation settings - DALL-E 3
    DEFAULT_IMAGE_QUALITY: str = "standard"  # Options: standard | hd

    # Agent monitoring settings
    AGENT_LLM_MODEL: str = "gpt-5-mini"  # Model for alert generation
    AGENT_CHECK_INTERVAL: int = 60  # Seconds between monitoring checks
    AGENT_SLA_THRESHOLD_MINUTES: int = 10  # Minutes before SLA breach alert

    # Email/SMTP settings (for agent alerts)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "noreply@company.com"
    STAKEHOLDER_EMAIL: str = "creative-lead@company.com"

    # Slack webhook (optional)
    SLACK_WEBHOOK_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore unknown env vars
    )


# Global settings instance
settings = Settings()
