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

    # Storage configuration
    STORAGE_MODE: str = "local"  # Options: "local" | "azure" | "s3"
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None

    # Processing configuration
    MAX_CONCURRENT_GENERATIONS: int = 3  # Limit concurrent GenAI calls
    RETRY_MAX_ATTEMPTS: int = 3  # Retry failed API calls
    RETRY_BACKOFF_FACTOR: float = 2.0  # Exponential backoff multiplier

    # Logging
    LOG_LEVEL: str = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR

    # Provider selection and fallback chain
    GENAI_PROVIDER: str = "openai"  # Primary: openai | google | huggingface | mock
    GENAI_FALLBACKS: str = "google,huggingface,mock"  # Comma-separated fallback order

    # Image generation settings - DALL-E 3
    DEFAULT_IMAGE_QUALITY: str = "standard"  # Options: standard | hd

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore unknown env vars
    )


# Global settings instance
settings = Settings()
