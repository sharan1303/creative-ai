"""OpenAI Image Generation API client (DALL-E 3 / gpt-image-1)

Wraps the OpenAI Images API for generating high-quality product imagery.
Supports both DALL-E 3 (base64) and gpt-image-1 (URL-based) models.
"""

import httpx

from src.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIImageClient:
    """Client for OpenAI image generation API

    Supports:
    - DALL-E 3: 1024x1024, 1024x1792, 1792x1024 (quality: standard, hd)
    - gpt-image-1: 1024x1024, 1024x1536, 1536x1024 (quality: low, medium, high, auto)
    - Automatic format handling (base64 for DALL-E 3, URL for gpt-image-1)
    """

    BASE_URL = "https://api.openai.com/v1"

    def __init__(self, api_key: str):
        """Initialize OpenAI client

        Args:
            api_key: OpenAI API key with image generation access
        """
        if not api_key:
            raise ValueError("OpenAI API key is required")

        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0,  # Image generation can take 30-60s
        )
        logger.info("OpenAI Image Client initialized")

    async def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        model: str = "dall-e-3",
    ) -> bytes:
        """Generate image using OpenAI Image Generation API

        Args:
            prompt: Text description of desired image
            size: Image dimensions (1024x1024, 1024x1792, 1792x1024)
            quality: Image quality (standard or hd for dall-e-3; low, medium, high, auto for gpt-image-1)
            model: Model to use (dall-e-3 or gpt-image-1)

        Returns:
            Raw image bytes (PNG format)

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        logger.info(f"Generating image with OpenAI: {size}, quality={quality}")
        logger.debug(f"Prompt: {prompt[:100]}...")

        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n": 1,
        }

        # Prefer base64 when available to avoid a second download request
        # Some models (including gpt-image family) may also return b64_json
        if model == "dall-e-3":
            payload["response_format"] = "b64_json"

        try:
            response = await self.client.post("/images/generations", json=payload)
            response.raise_for_status()

            data = response.json()

            # Handle different response formats generically
            entries = data.get("data") or []
            if not isinstance(entries, list) or not entries:
                raise ValueError(
                    f"Unexpected OpenAI image response: missing 'data' array (keys: {list(data.keys())})"
                )
            first = entries[0]

            # Prefer base64 if present
            if "b64_json" in first and first["b64_json"]:
                import base64

                image_b64 = first["b64_json"]
                image_bytes = base64.b64decode(image_b64)
            elif "url" in first and first["url"]:
                image_url = first["url"]
                logger.debug(f"Downloading image from: {image_url}")
                image_response = await self.client.get(image_url)
                image_response.raise_for_status()
                image_bytes = image_response.content
            else:
                raise ValueError(
                    f"OpenAI image response missing 'b64_json' and 'url' (entry keys: {list(first.keys())})"
                )

            logger.info(f"Successfully generated image ({len(image_bytes)} bytes)")
            return image_bytes

        except httpx.HTTPStatusError as e:
            logger.error(
                f"OpenAI API error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"Unexpected error during image generation: {e}")
            raise

    async def close(self):
        """Close the HTTP client connection"""
        await self.client.aclose()
        logger.info("OpenAI Image Client closed")
