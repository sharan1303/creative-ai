"""Shared helpers for variant generation and prompt building

Centralises logic used by both the CLI and FastAPI layers to avoid duplication.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from src.models.brief import AspectRatio, CampaignBrief, Product
from src.services.genai import GenAIOrchestrator
from src.services.processor import ImageProcessor
from src.services.storage import StorageManager
from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def build_generation_prompt(product: Product, brief: CampaignBrief) -> str:
    """Build an optimised prompt for GenAI image generation.

    Strategy:
    - Product name and description
    - Target audience context
    - Market/locale hints
    - Style and quality keywords
    """
    parts = [product.name]

    if product.description:
        parts.append(product.description)

    # Audience and market context
    parts.extend(
        [
            f"for {brief.target_audience}",
            f"in {brief.target_market} market",
        ]
    )

    # Style keywords
    parts.extend(
        [
            "professional product photography",
            "high quality",
            "marketing campaign",
            "clean background",
        ]
    )

    prompt = ", ".join(parts)

    # Truncate to a safe length for providers
    if len(prompt) > 1000:
        prompt = prompt[:1000]

    return prompt


async def generate_variant(
    orchestrator: GenAIOrchestrator,
    processor: ImageProcessor,
    storage: StorageManager,
    product: Product,
    brief: CampaignBrief,
    ratio: AspectRatio,
    *,
    providers_to_try: Optional[List[str]] = None,
    models_to_try: Optional[List[str]] = None,
    offload_blocking: bool = False,
) -> Dict[str, Any]:
    """Generate and post-process a single variant, then save output.

    Args:
        orchestrator: GenAI orchestration service (async)
        processor: Image processing service (sync API)
        storage: Storage management service (sync API)
        product: Product information
        brief: Campaign brief
        ratio: Target aspect ratio
        offload_blocking: If True, run blocking calls in threads (for FastAPI)

    Returns:
        Dictionary with generation result metadata
    """
    # Step 1: Check for existing asset (cache hit)
    if offload_blocking:
        existing_path = await asyncio.to_thread(
            storage.get_asset, product.id, ratio.name, brief.campaign_id
        )
    else:
        existing_path = storage.get_asset(
            product_id=product.id, ratio_name=ratio.name, campaign_id=brief.campaign_id
        )

    # If asset exists, return immediately without reprocessing
    if existing_path is not None:
        logger.info(
            f"Cache hit for {product.id}/{ratio.name}, skipping generation and overlay"
        )
        return {
            "success": True,
            "ratio": ratio.name,
            "path": str(existing_path),
            "reused": True,
        }

    # Step 2: Generate new image
    prompt = build_generation_prompt(product, brief)
    logger.debug(f"Prompt for {product.id}: {prompt[:100]}...")
    image_data = await orchestrator.generate_image(
        prompt=prompt,
        width=ratio.width,
        height=ratio.height,
        product_id=product.id,
        providers=providers_to_try,
        models=models_to_try,
        quality=settings.DEFAULT_IMAGE_QUALITY,
    )

    # Step 3: Resize to exact target
    if offload_blocking:
        image_data = await asyncio.to_thread(
            processor.resize, image_data, ratio.width, ratio.height
        )
    else:
        image_data = processor.resize(image_data, ratio.width, ratio.height)

    # Step 4: Add text overlay (only for new generations)
    if offload_blocking:
        image_data = await asyncio.to_thread(
            processor.add_text_overlay, image_data, brief.campaign_message, "bottom"
        )
    else:
        image_data = processor.add_text_overlay(
            image_data=image_data, text=brief.campaign_message, position="bottom"
        )

    # Step 5: Save output (only for new generations)
    if offload_blocking:
        output_path = await asyncio.to_thread(
            storage.save_output,
            product.id,
            ratio.name,
            image_data,
            {
                "campaign_id": brief.campaign_id,
                "product_id": product.id,
                "product_name": product.name,
                "aspect_ratio": ratio.name,
                "dimensions": f"{ratio.width}x{ratio.height}",
                "platform": ratio.platform,
                "target_market": brief.target_market,
                "target_audience": brief.target_audience,
                "campaign_message": brief.campaign_message,
                "reused": False,
            },
            brief.campaign_id,
        )
    else:
        output_path = storage.save_output(
            product_id=product.id,
            ratio_name=ratio.name,
            image_data=image_data,
            campaign_id=brief.campaign_id,
            metadata={
                "campaign_id": brief.campaign_id,
                "product_id": product.id,
                "product_name": product.name,
                "aspect_ratio": ratio.name,
                "dimensions": f"{ratio.width}x{ratio.height}",
                "platform": ratio.platform,
                "target_market": brief.target_market,
                "target_audience": brief.target_audience,
                "campaign_message": brief.campaign_message,
                "reused": False,
            },
        )

    return {
        "success": True,
        "ratio": ratio.name,
        "path": str(output_path),
        "reused": False,
    }
