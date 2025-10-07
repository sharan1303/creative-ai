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
from src.services.google_image_client import GoogleImageClient
from src.services.openai_image_client import OpenAIImageClient
from src.services.processor import ImageProcessor
from src.services.storage import StorageManager
from src.services.variant_generation import generate_variant
from src.utils.config import runtime_config, settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(name="process_campaign_task")
def process_campaign_task(
    brief_dict: Dict[str, Any], provider: str | None = None, model: str | None = None
) -> Dict[str, Any]:
    """Run campaign processing synchronously in a worker thread.

    Note: Celery tasks are sync. We run async parts via asyncio.run.
    Returns a summary dict including per-variant results.

    Args:
        brief_dict: Campaign brief as dictionary
        provider: Image generation provider (openai or google). If None, uses runtime_config.
        model: Model name. If None, uses runtime_config.
    """

    brief = CampaignBrief(**brief_dict)

    # Use passed provider/model or fall back to runtime config
    selected_provider = provider or runtime_config.provider
    selected_model = model or runtime_config.model

    async def _run() -> Dict[str, Any]:
        # Validate and instantiate only the required client(s) based on provider
        openai_client = None
        google_client = None

        try:
            if selected_provider == "openai":
                if not settings.OPENAI_API_KEY:
                    raise RuntimeError(
                        "OPENAI_API_KEY not configured for provider 'openai'"
                    )
                openai_client = OpenAIImageClient(api_key=settings.OPENAI_API_KEY)
            elif selected_provider == "google":
                if not settings.GOOGLE_AI_API_KEY:
                    raise RuntimeError(
                        "GOOGLE_AI_API_KEY not configured for provider 'google'"
                    )
                google_client = GoogleImageClient()
            else:
                raise RuntimeError(f"Unknown provider: {selected_provider}")

            orchestrator = GenAIOrchestrator(
                openai_client=openai_client, google_client=google_client
            )
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
                        orchestrator,
                        processor,
                        storage,
                        product,
                        brief,
                        ratio,
                        providers_to_try=[selected_provider],
                        models_to_try=[selected_model],
                    )
                    for ratio in ratios
                ]
                task_results = await asyncio.gather(*tasks, return_exceptions=True)
                for ratio, result in zip(ratios, task_results):
                    if isinstance(result, Exception):
                        logger.error(
                            "Variant failed for %s/%s: %s",
                            product.id,
                            ratio.name,
                            result,
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

            return {
                "campaign_id": brief.campaign_id,
                "total_variants": total_variants,
                "assets_reused": total_reused,
                "new_generations": total_variants - total_reused,
                "results": results,
            }
        finally:
            # Ensure all instantiated clients are properly closed
            if openai_client:
                await openai_client.close()
            if google_client:
                await google_client.close()

    return asyncio.run(_run())


async def _generate_variant(
    orchestrator: GenAIOrchestrator,
    processor: ImageProcessor,
    storage: StorageManager,
    product,
    brief: CampaignBrief,
    ratio,
    providers_to_try: List[str] | None = None,
    models_to_try: List[str] | None = None,
) -> Dict[str, Any]:
    return await generate_variant(
        orchestrator=orchestrator,
        processor=processor,
        storage=storage,
        product=product,
        brief=brief,
        ratio=ratio,
        providers_to_try=providers_to_try,
        models_to_try=models_to_try,
        offload_blocking=True,
    )
