"""Google Image Generation client (Google AI Images API)

Requires ``settings.GOOGLE_AI_API_KEY`` to be configured. No stub mode.
"""

from __future__ import annotations

import base64
from typing import Tuple

import httpx

from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleImageClient:
    """Client for Google AI Images API"""

    def __init__(self) -> None:
        self.api_key = (settings.GOOGLE_AI_API_KEY or "").strip()
        self.model_default = (
            settings.GOOGLE_AI_IMAGE_MODEL or "gemini-2.5-flash-image"
        ).strip()
        self.endpoint_base = (
            settings.GOOGLE_AI_ENDPOINT or "https://generativelanguage.googleapis.com"
        ).rstrip("/")
        self._http: httpx.AsyncClient | None = None

        if not self.api_key:
            raise ValueError("GOOGLE_AI_API_KEY is required for Google Image Client")

        self._http = httpx.AsyncClient(
            base_url=self.endpoint_base,
            headers={
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )
        logger.info("Google Image Client initialized (Gemini API)")

    async def generate(
        self, *, prompt: str, size: str, quality: str, model: str
    ) -> bytes:
        """Generate an image via Google AI Images API or stub.

        Args:
            prompt: Text description
            size: "<width>x<height>"
            quality: Provider-specific quality hint
            model: Model name (e.g., "imagen-3.0-fast-generate-001")

        Returns:
            PNG bytes
        """
        width, height = self._parse_size(size)

        model_name = (model or self.model_default).strip() or self.model_default

        # Build request for Gemini API
        # API reference: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
        url_path = f"/v1beta/models/{model_name}:generateContent"

        body = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"{prompt}. Generate image at {width}x{height} resolution."
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
            },
        }

        try:
            response = await self._http.post(
                url_path, params={"key": self.api_key}, json=body
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Gemini API error: %s - %s",
                e.response.status_code,
                e.response.text,
            )
            raise
        except Exception as e:
            logger.error("Unexpected error calling Gemini API: %s", e)
            raise

        # Parse response following Gemini format
        # Expected: data["candidates"][0]["content"]["parts"][0]["image_bytes_base64"]
        try:
            if not isinstance(data, dict):
                raise ValueError(f"Response is not a dict: {type(data)}")

            candidates = data.get("candidates")
            if not isinstance(candidates, list) or not candidates:
                raise ValueError(
                    f"No candidates in response. Keys: {list(data.keys())}"
                )

            first_candidate = candidates[0]
            content = first_candidate.get("content")
            if not isinstance(content, dict):
                raise ValueError(f"Content is not a dict: {type(content)}")

            parts = content.get("parts")
            if not isinstance(parts, list) or not parts:
                raise ValueError(f"No parts in content. Keys: {list(content.keys())}")

            first_part = parts[0]
            b64_data = (
                first_part.get("image_bytes_base64")
                or first_part.get("bytes_base64")
                or first_part.get("inline_data", {}).get("data")
                or first_part.get("inlineData", {}).get("data")
            )

            if not isinstance(b64_data, str) or not b64_data:
                raise ValueError(
                    f"No base64 image data found. Part keys: {list(first_part.keys())}"
                )

            logger.info(
                f"Successfully received image from Gemini API ({len(b64_data)} base64 chars)"
            )
            return base64.b64decode(b64_data)

        except Exception as e:
            logger.error("Failed to parse Gemini API response: %s", e)
            logger.debug(f"Response data: {data}")
            raise

    async def close(self):
        """Close the HTTP client connection"""
        if self._http:
            await self._http.aclose()
            logger.info("Google Image Client closed")

    def _parse_size(self, size: str) -> Tuple[int, int]:
        try:
            w_str, h_str = size.lower().split("x", 1)
            width = int(w_str)
            height = int(h_str)
            return width, height
        except Exception as e:
            logger.warning(f"Invalid size '{size}', defaulting to 1024x1024: {e}")
            return 1024, 1024
