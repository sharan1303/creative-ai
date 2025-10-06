"""Celery tasks for campaign processing.

The task reuses the same pipeline services as the FastAPI endpoint.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List

from src.celery_app import celery_app
from src.models.brief import ASPECT_RATIOS, CampaignBrief
from src.services.genai import GenAIOrchestrator
from src.services.openai_image_client import OpenAIImageClient
from src.services.processor import ImageProcessor
from src.services.storage import StorageManager
from src.services.variant_generation import generate_variant
from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(name="process_campaign_task")
def process_campaign_task(brief_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Run campaign processing synchronously in a worker thread.

    Note: Celery tasks are sync. We run async parts via asyncio.run.
    Returns a summary dict including per-variant results.
    """

    brief = CampaignBrief(**brief_dict)

    async def _run() -> Dict[str, Any]:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not configured")

        openai_client = OpenAIImageClient(api_key=settings.OPENAI_API_KEY)
        orchestrator = GenAIOrchestrator(openai_client=openai_client)
        processor = ImageProcessor()
        storage = StorageManager(base_path=Path("outputs"))

        total_variants = 0
        total_reused = 0
        results: List[Dict[str, Any]] = []

        async def _run_for_product(product):
            nonlocal total_variants, total_reused
            ratios = list(ASPECT_RATIOS)
            tasks = [
                _generate_variant(
                    orchestrator, processor, storage, product, brief, ratio
                )
                for ratio in ratios
            ]
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            for ratio, result in zip(ratios, task_results):
                if isinstance(result, Exception):
                    logger.error(
                        "Variant failed for %s/%s: %s", product.id, ratio.name, result
                    )
                    results.append(
                        {
                            "product_id": product.id,
                            "ratio": ratio.name,
                            "path": "",
                            "reused": False,
                            "success": False,
                            "error": str(result),
                        }
                    )
                else:
                    total_variants += 1
                    if result.get("reused"):
                        total_reused += 1
                    results.append(
                        {
                            "product_id": product.id,
                            "ratio": ratio.name,
                            "path": result.get("path", ""),
                            "reused": bool(result.get("reused")),
                            "success": True,
                        }
                    )

        for product in brief.products:
            await _run_for_product(product)

        await openai_client.close()
        return {
            "campaign_id": brief.campaign_id,
            "total_variants": total_variants,
            "assets_reused": total_reused,
            "new_generations": total_variants - total_reused,
            "results": results,
        }

    return asyncio.run(_run())


async def _generate_variant(
    orchestrator: GenAIOrchestrator,
    processor: ImageProcessor,
    storage: StorageManager,
    product,
    brief: CampaignBrief,
    ratio,
) -> Dict[str, Any]:
    return await generate_variant(
        orchestrator=orchestrator,
        processor=processor,
        storage=storage,
        product=product,
        brief=brief,
        ratio=ratio,
        offload_blocking=True,
    )
