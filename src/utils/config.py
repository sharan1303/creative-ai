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

    # Model selection per provider
    OPENAI_DEFAULT_MODEL: str = "gpt-image-1"  # Options: dall-e-3, gpt-image-1, gpt-image-1-mini
    GOOGLE_DEFAULT_MODEL: str = "gemini-2.5-flash-image"  # Google AI model

    # Image generation settings
    DEFAULT_IMAGE_QUALITY: str = "low"  # Options: standard | hd (OpenAI), low/medium/high/auto (gpt-image)
    DEFAULT_IMAGE_WIDTH: int = 1024  # Default image width
    DEFAULT_IMAGE_HEIGHT: int = 1024  # Default image height

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


class RuntimeConfig:
    """Runtime configuration for session-based model selection

    This allows API-based configuration changes that persist for the application
    session without modifying environment variables.
    """

    def __init__(self):
        # Initialize with validated provider and aligned model
        self._provider = "openai"
        self._model = self._get_default_model_for_provider(self._provider)
        # Apply environment override via setter (validates and aligns model)
        self.provider = settings.GENAI_PROVIDER

    @property
    def provider(self) -> str:
        return self._provider

    @provider.setter
    def provider(self, value: str) -> None:
        if value not in ["openai", "google"]:
            raise ValueError(f"Invalid provider: {value}. Must be 'openai' or 'google'")
        self._provider = value
        # Update model to match provider if not explicitly set
        self._model = self._get_default_model_for_provider(value)

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        self._model = value

    def update(self, provider: str, model: str) -> None:
        """Update both provider and model atomically"""
        if provider not in ["openai", "google"]:
            raise ValueError(
                f"Invalid provider: {provider}. Must be 'openai' or 'google'"
            )
        self._provider = provider
        self._model = model

    def _get_default_model_for_provider(self, provider: str) -> str:
        """Get default model for a given provider"""
        if provider == "openai":
            return settings.OPENAI_DEFAULT_MODEL
        elif provider == "google":
            return settings.GOOGLE_DEFAULT_MODEL
        return "gpt-image-1"  # fallback

    def to_dict(self) -> dict:
        """Export configuration as dictionary"""
        return {"provider": self._provider, "model": self._model}


# Global runtime configuration instance
runtime_config = RuntimeConfig()
