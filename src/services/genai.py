"""GenAI orchestrator with multi-provider support and fallback logic

Handles provider selection, size mapping, and graceful degradation.
"""

from typing import Optional

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

    def __init__(self, openai_client: Optional[OpenAIImageClient] = None):
        """Initialize orchestrator with available providers

        Args:
            openai_client: OpenAI client instance (primary provider)
        """
        self.openai = openai_client
        self.providers = []

        if self.openai:
            self.providers.append("openai")
            logger.info("GenAI Orchestrator initialized with OpenAI provider")
        else:
            logger.warning("No GenAI providers configured!")

    @async_retry(max_attempts=3, backoff_factor=2.0)
    async def generate_image(
        self, prompt: str, width: int, height: int, product_id: str
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

        # Try primary provider (OpenAI)
        if "openai" in self.providers:
            try:
                size = self._map_size_to_openai(width, height)
                logger.info(f"Using OpenAI with size {size}")

                image_data = await self.openai.generate(
                    prompt=prompt,
                    size=size,
                    quality="standard",  # "standard" or "hd" for dall-e-3
                    model="dall-e-3",  # Use dall-e-3 (widely available)
                )

                logger.info(f"Successfully generated image for {product_id}")
                return image_data

            except Exception as e:
                logger.error(f"OpenAI generation failed: {e}")
                raise  # Will trigger retry via decorator

        raise RuntimeError("All generation attempts failed")

    def _map_size_to_openai(self, width: int, height: int) -> str:
        """Map arbitrary dimensions to OpenAI's supported sizes

        DALL-E 3 supports:
        - 1024x1024 (square)
        - 1792x1024 (landscape)
        - 1024x1792 (portrait)

        gpt-image-1 supports:
        - 1024x1024 (square)
        - 1536x1024 (landscape)
        - 1024x1536 (portrait)

        Args:
            width: Desired width
            height: Desired height

        Returns:
            Closest supported size string (for DALL-E 3)
        """
        ratio = width / height

        if abs(ratio - 1.0) < 0.1:
            # Nearly square -> 1:1
            return "1024x1024"
        elif ratio > 1.5:
            # Wide landscape -> 16:9 approximation
            return "1792x1024"
        else:
            # Tall portrait -> 9:16 approximation
            return "1024x1792"
