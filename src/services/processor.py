"""Image processing service for resizing and text overlays

Handles all post-generation image manipulation including:
- Aspect ratio resizing with quality preservation
- Campaign message text overlays with brand styling
- Format conversions
"""

import io
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ImageProcessor:
    """Post-processing service for generated images

    Provides high-quality resizing and professional text overlays
    for campaign creative assets.
    """

    def __init__(self, font_path: Optional[str] = None):
        """Initialize image processor

        Args:
            font_path: Optional path to TTF font file. Falls back to default if not found.
        """
        self.font_path = font_path
        logger.info("Image Processor initialized")

    def _find_default_font_path(self) -> Optional[str]:
        """Attempt to locate a font within the project assets.

        Search order:
        1. /app/assets/fonts (inside container)
        2. assets/fonts (local/dev)
        Returns first matching .ttf/.otf/.ttc.
        """
        search_roots = [Path("/app/assets/fonts"), Path("assets/fonts")]
        for root in search_roots:
            if root.exists() and root.is_dir():
                candidates = []
                for pattern in ("*.ttf", "*.otf", "*.ttc"):
                    candidates.extend(sorted(root.glob(pattern)))
                if candidates:
                    return str(candidates[0])
        return None

    def resize(self, image_data: bytes, target_width: int, target_height: int) -> bytes:
        """Resize image to target dimensions with aspect ratio preservation

        Uses LANCZOS resampling for high-quality scaling. The image is scaled
        to cover the target dimensions, then center-cropped to exact size.
        This prevents stretching/distortion.

        Args:
            image_data: Original image bytes
            target_width: Desired width in pixels
            target_height: Desired height in pixels

        Returns:
            Resized image as PNG bytes
        """
        logger.info(f"Resizing image to {target_width}x{target_height}")

        img = Image.open(io.BytesIO(image_data))
        original_size = img.size

        # Only resize if dimensions don't match
        if img.size != (target_width, target_height):
            target_ratio = target_width / target_height
            current_ratio = img.width / img.height

            if current_ratio > target_ratio:
                new_height = target_height
                new_width = int(img.width * (target_height / img.height))
            else:
                new_width = target_width
                new_height = int(img.height * (target_width / img.width))

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            left = (new_width - target_width) // 2
            top = (new_height - target_height) // 2
            right = left + target_width
            bottom = top + target_height
            img = img.crop((left, top, right, bottom))

            logger.debug(
                f"Resized from {original_size} to {img.size} (aspect ratio preserved)"
            )
        else:
            logger.debug("Image already at target size, skipping resize")

        output = io.BytesIO()
        img.save(output, format="PNG", optimize=True)
        return output.getvalue()

    def add_text_overlay(
        self,
        image_data: bytes,
        text: str,
        position: str = "bottom",
        font_size: int = 48,
        bg_color: Tuple[int, int, int, int] = (0, 0, 0, 180),
        text_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    ) -> bytes:
        """Add campaign message as text overlay with semi-transparent background

        Args:
            image_data: Image bytes to overlay text on
            text: Campaign message text
            position: Text position ("bottom", "center", or "top")
            font_size: Font size in points
            bg_color: Background RGBA tuple (default: semi-transparent black)
            text_color: Text RGBA tuple (default: white)

        Returns:
            Image with text overlay as PNG bytes
        """
        logger.info(f"Adding text overlay: '{text[:30]}...' at {position}")

        img = Image.open(io.BytesIO(image_data))

        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # Create transparent overlay layer
        overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        try:
            if self.font_path:
                font = ImageFont.truetype(self.font_path, font_size)
            else:
                autodetected = self._find_default_font_path()
                if autodetected:
                    try:
                        logger.info(f"Using font: {autodetected}")
                        font = ImageFont.truetype(autodetected, font_size)
                    except Exception:
                        # Fall back to system fonts if autodetected fails
                        try:
                            font = ImageFont.truetype("arial.ttf", font_size)
                        except Exception:
                            try:
                                font = ImageFont.truetype(
                                    "/System/Library/Fonts/Helvetica.ttc", font_size
                                )
                            except Exception:
                                logger.warning(
                                    "Could not load custom font, using default"
                                )
                                font = ImageFont.load_default()
                else:
                    # Try common system fonts
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except Exception:
                        try:
                            font = ImageFont.truetype(
                                "/System/Library/Fonts/Helvetica.ttc", font_size
                            )
                        except Exception:
                            logger.warning("Could not load custom font, using default")
                            font = ImageFont.load_default()
        except Exception as e:
            logger.warning(f"Font loading failed: {e}, using default")
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        padding = 20
        if position == "bottom":
            x = (img.width - text_width) // 2
            y = img.height - text_height - 60
        elif position == "top":
            x = (img.width - text_width) // 2
            y = 60
        else:
            x = (img.width - text_width) // 2
            y = (img.height - text_height) // 2

        # Draw background rectangle with rounded corners
        bg_rect = [
            x - padding,
            y - padding,
            x + text_width + padding,
            y + text_height + padding,
        ]
        draw.rectangle(bg_rect, fill=bg_color)

        draw.text((x, y), text, font=font, fill=text_color)

        img = Image.alpha_composite(img, overlay)

        output = io.BytesIO()
        img.save(output, format="PNG", optimize=True)

        logger.debug(f"Text overlay applied at position {position}")
        return output.getvalue()
