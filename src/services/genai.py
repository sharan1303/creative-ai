"""GenAI orchestrator with multi-provider and multi-model support

Handles provider selection, model iteration, size mapping, retries, and
graceful degradation/fallback across providers and models.
"""

from typing import List, Optional

from src.services.google_image_client import GoogleImageClient
from src.services.openai_image_client import OpenAIImageClient
from src.utils.logger import get_logger
from src.utils.retry import async_retry

logger = get_logger(__name__)


class GenAIOrchestrator:
    """Orchestrates GenAI image generation across multiple providers

    Strategy:
    1. Try primary provider (OpenAI)
    2. Fall back to secondary providers if primary fails
    3. Apply retry logic with exponential backoff
    4. Map arbitrary dimensions to provider-supported sizes
    """

    def __init__(
        self,
        openai_client: Optional[OpenAIImageClient] = None,
        google_client: Optional[GoogleImageClient] = None,
    ):
        """Initialize orchestrator with available providers

        Args:
            openai_client: OpenAI client instance (primary provider)
            google_client: Google client instance (optional provider)
        """
        self.openai = openai_client
        self.google = google_client
        self.providers = []

        if self.openai:
            self.providers.append("openai")
            logger.info("GenAI Orchestrator initialized with OpenAI provider")
        if self.google:
            self.providers.append("google")
            logger.info("GenAI Orchestrator initialized with Google provider")
        else:
            logger.warning("No GenAI providers configured!")

    @async_retry(max_attempts=3, backoff_factor=2.0)
    async def generate_image(
        self,
        prompt: str,
        width: int,
        height: int,
        product_id: str,
        *,
        providers: Optional[List[str]] = None,
        models: Optional[List[str]] = None,
        quality: str = "standard",
    ) -> bytes:
        """Generate image with automatic provider selection and retry

        Args:
            prompt: Text description for image generation
            width: Target width in pixels
            height: Target height in pixels
            product_id: Product identifier for logging

        Returns:
            Generated image as PNG bytes

        Raises:
            Exception: If all providers and retries fail
        """
        if not self.providers:
            raise RuntimeError("No GenAI providers available")

        logger.info(f"Generating image for {product_id} at {width}x{height}")

        providers_to_try = [p.lower() for p in (providers or self.providers)]
        if not providers_to_try:
            raise RuntimeError("No providers to try")

        # Default model order if none supplied
        default_models = ["gpt-image-1", "dall-e-3"]
        models_to_try = models or default_models

        last_error: Optional[Exception] = None

        for provider in providers_to_try:
            if provider == "openai" and self.openai:
                for model in models_to_try:
                    try:
                        size = self._map_size_for_openai_model(model, width, height)
                        model_quality = self._normalize_openai_quality(model, quality)
                        logger.info(
                            f"Trying provider=openai, model={model}, size={size}, quality={model_quality}"
                        )
                        image_data = await self.openai.generate(
                            prompt=prompt,
                            size=size,
                            quality=model_quality,
                            model=model,
                        )
                        logger.info(
                            f"Successfully generated image for {product_id} with openai/{model}"
                        )
                        return image_data
                    except Exception as e:
                        last_error = e
                        logger.warning(
                            f"openai/{model} failed, trying next: {e}", exc_info=True
                        )
                continue

            if provider == "google" and self.google:
                # Google client handles its own size mapping; pass desired
                size = f"{width}x{height}"
                for model in models_to_try:
                    try:
                        logger.info(
                            f"Trying provider=google, model={model}, size={size}"
                        )
                        image_data = await self.google.generate(
                            prompt=prompt, size=size, quality=quality, model=model
                        )
                        logger.info(
                            f"Successfully generated image for {product_id} with google/{model}"
                        )
                        return image_data
                    except Exception as e:
                        last_error = e
                        logger.warning(
                            f"google/{model} failed, trying next: {e}", exc_info=True
                        )
                continue

            logger.debug(f"Provider not available or unknown: {provider}")

        if last_error is not None:
            raise last_error
        raise RuntimeError("All generation attempts failed")

    def _map_size_for_openai_model(self, model: str, width: int, height: int) -> str:
        """Map dimensions to allowed sizes for a given OpenAI model.

        dall-e-3 supports:
        1024x1024 (standard)
        1792x1024 (landscape)
        1024x1792 (portrait)
        
        gpt-image-1 / gpt-image-1-mini support:
        1024x1024 (standard)
        1536x1024 (landscape)
        1024x1536 (portrait)
        Args:
            model: Model name (dall-e-3 or gpt-image-1)
            width: Desired width
            height: Desired height

        Returns:
            Closest supported size string
        """
        ratio = width / height
        model_lc = model.lower()
        if model_lc == "dall-e-3":
            if abs(ratio - 1.0) < 0.1:
                return "1024x1024"
            elif ratio > 1.5:
                return "1792x1024"
            else:
                return "1024x1792"
        # Default to gpt-image family constraints
        if abs(ratio - 1.0) < 0.1:
            return "1024x1024"
        elif ratio > 1.5:
            return "1536x1024"
        else:
            return "1024x1536"

    def _normalize_openai_quality(self, model: str, quality: str) -> str:
        """Normalize quality value per OpenAI model family."""
        model_lc = model.lower()
        q = (quality or "").strip().lower()
        if model_lc == "dall-e-3":
            return q if q in {"standard", "hd"} else "standard"
        # gpt-image family
        return q if q in {"low", "medium", "high", "auto"} else "auto"
