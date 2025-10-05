"""Image processing service for resizing and text overlays

Handles all post-generation image manipulation including:
- Aspect ratio resizing with quality preservation
- Campaign message text overlays with brand styling
- Format conversions
"""

import io
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

    def resize(self, image_data: bytes, target_width: int, target_height: int) -> bytes:
        """Resize image to target dimensions with quality preservation

        Uses LANCZOS resampling for high-quality downscaling.

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
            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            logger.debug(f"Resized from {original_size} to {img.size}")
        else:
            logger.debug("Image already at target size, skipping resize")

        # Convert to PNG
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

        # Convert to RGBA for transparency support
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # Create transparent overlay layer
        overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        # Load font
        try:
            if self.font_path:
                font = ImageFont.truetype(self.font_path, font_size)
            else:
                # Try common system fonts
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except(Exception):
                    try:
                        font = ImageFont.truetype(
                            "/System/Library/Fonts/Helvetica.ttc", font_size
                        )
                    except(Exception):
                        logger.warning("Could not load custom font, using default")
                        font = ImageFont.load_default()
        except Exception as e:
            logger.warning(f"Font loading failed: {e}, using default")
            font = ImageFont.load_default()

        # Calculate text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Calculate position
        padding = 20
        if position == "bottom":
            x = (img.width - text_width) // 2
            y = img.height - text_height - 60
        elif position == "top":
            x = (img.width - text_width) // 2
            y = 60
        else:  # center
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

        # Draw text
        draw.text((x, y), text, font=font, fill=text_color)

        # Composite overlay onto original image
        img = Image.alpha_composite(img, overlay)

        # Save as PNG
        output = io.BytesIO()
        img.save(output, format="PNG", optimize=True)

        logger.debug(f"Text overlay applied at position {position}")
        return output.getvalue()
