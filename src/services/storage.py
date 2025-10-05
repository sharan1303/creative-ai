"""Storage management for campaign assets

Handles local file system storage with organized folder structure
and asset reuse capability.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class StorageManager:
    """Local file system storage manager

    Organizes outputs by:
    - Campaign ID
    - Product ID
    - Aspect ratio

    Enables asset reuse by checking for existing files before generation.
    """

    def __init__(self, base_path: Path = Path("outputs")):
        """Initialize storage manager

        Args:
            base_path: Root directory for storing generated assets
        """
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Storage Manager initialized at {self.base_path}")

    def get_asset(self, product_id: str, ratio_name: str, campaign_id: Optional[str] = None) -> Optional[bytes]:
        """Check if asset already exists and retrieve it

        Enables asset reuse to avoid redundant generation costs.

        Args:
            product_id: Product identifier
            ratio_name: Aspect ratio name (e.g., "1x1")
            campaign_id: Optional campaign ID for scoped search

        Returns:
            Asset bytes if found, None otherwise
        """
        # Build search path
        if campaign_id:
            search_dir = self.base_path / campaign_id / product_id / ratio_name
        else:
            search_dir = self.base_path / product_id / ratio_name

        if not search_dir.exists():
            logger.debug(f"No existing assets found at {search_dir}")
            return None

        # Look for PNG files
        png_files = list(search_dir.glob("*.png"))
        if png_files:
            asset_path = png_files[0]  # Use first match
            logger.info(f"Reusing existing asset: {asset_path}")
            return asset_path.read_bytes()

        return None

    def save_output(
        self,
        product_id: str,
        ratio_name: str,
        image_data: bytes,
        metadata: Dict[str, Any],
        campaign_id: Optional[str] = None,
    ) -> Path:
        """Save generated asset with metadata sidecar

        Creates organized folder structure:
        outputs/
          └── [campaign_id]/
              └── product_id/
                  └── ratio_name/
                      ├── image_TIMESTAMP.png
                      └── image_TIMESTAMP.json (metadata)

        Args:
            product_id: Product identifier
            ratio_name: Aspect ratio name
            image_data: Image bytes to save
            metadata: Generation metadata (prompt, model, etc.)
            campaign_id: Optional campaign ID for organization

        Returns:
            Path to saved image file
        """
        # Build output path
        if campaign_id:
            output_dir = self.base_path / campaign_id / product_id / ratio_name
        else:
            output_dir = self.base_path / product_id / ratio_name

        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{product_id}_{ratio_name}_{timestamp}.png"
        image_path = output_dir / filename

        # Save image
        image_path.write_bytes(image_data)
        logger.info(f"Saved image to {image_path}")

        # Save metadata sidecar
        metadata_path = image_path.with_suffix(".json")
        metadata_with_info = {
            **metadata,
            "file_path": str(image_path),
            "file_size_bytes": len(image_data),
            "created_at": datetime.now().isoformat(),
            "checksum_md5": hashlib.md5(image_data).hexdigest(),
        }

        metadata_path.write_text(json.dumps(metadata_with_info, indent=2))
        logger.debug(f"Saved metadata to {metadata_path}")

        return image_path

    def list_campaign_outputs(self, campaign_id: str) -> Dict[str, list]:
        """List all generated assets for a campaign

        Args:
            campaign_id: Campaign identifier

        Returns:
            Dictionary mapping product_id -> list of output paths
        """
        campaign_dir = self.base_path / campaign_id
        if not campaign_dir.exists():
            return {}

        outputs = {}
        for product_dir in campaign_dir.iterdir():
            if product_dir.is_dir():
                product_id = product_dir.name
                outputs[product_id] = list(product_dir.rglob("*.png"))

        return outputs
