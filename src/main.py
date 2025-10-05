"""FastAPI application for Creative Automation Pipeline

Provides HTTP endpoints for health checks and campaign processing that
reuse the existing pipeline services.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List
import uuid
from datetime import datetime, timezone

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.models.brief import ASPECT_RATIOS, CampaignBrief
from src.services.genai import GenAIOrchestrator
from src.services.openai_image_client import OpenAIImageClient
from src.services.processor import ImageProcessor
from src.services.storage import StorageManager
from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Creative AI - Campaign Automation API",
    description=(
        "HTTP API for generating marketing creative assets from campaign briefs."
    ),
    version="1.0.0",
)


class HealthResponse(BaseModel):
    status: str


class VariantResult(BaseModel):
    product_id: str
    ratio: str
    path: str
    reused: bool
    success: bool = True
    error: str | None = None


class CampaignProcessResponse(BaseModel):
    campaign_id: str
    total_variants: int
    assets_reused: int
    new_generations: int
    results: List[VariantResult] = Field(default_factory=list)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/campaigns/process", response_model=CampaignProcessResponse)
async def process_campaign(brief: CampaignBrief) -> CampaignProcessResponse:
    """Process a campaign brief and generate creative assets.

    This endpoint executes a similar workflow as the CLI pipeline but operates on
    the provided JSON payload instead of a file.
    """
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY not configured")

    # Initialize services
    try:
        openai_client = OpenAIImageClient(api_key=settings.OPENAI_API_KEY)
        orchestrator = GenAIOrchestrator(openai_client=openai_client)
        processor = ImageProcessor()
        storage = StorageManager(base_path=Path("outputs"))
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to initialize services: %s", exc)
        raise HTTPException(status_code=500, detail="Service initialization failed")

    total_variants = 0
    total_reused = 0

    # Build tasks across all products/ratios
    async def _run_for_product(product_idx: int, total_products: int, product):
        nonlocal total_variants, total_reused
        tasks = []
        for ratio in ASPECT_RATIOS:
            tasks.append(
                _generate_variant(
                    orchestrator=orchestrator,
                    processor=processor,
                    storage=storage,
                    product=product,
                    brief=brief,
                    ratio=ratio,
                )
            )
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.error(
                    "[FAILED] Variant generation failed for product %s: %s",
                    product.id,
                    result,
                )
            else:
                total_variants += 1
                if result.get("reused"):
                    total_reused += 1

    try:
        await asyncio.gather(
            *[
                _run_for_product(idx + 1, len(brief.products), product)
                for idx, product in enumerate(brief.products)
            ]
        )
    finally:
        await openai_client.close()

    return CampaignProcessResponse(
        campaign_id=brief.campaign_id,
        total_variants=total_variants,
        assets_reused=total_reused,
        new_generations=total_variants - total_reused,
    )


# -----------------------
# Background job handling
# -----------------------

class JobCreateResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    campaign_id: str | None = None
    total_variants: int | None = None
    assets_reused: int | None = None
    new_generations: int | None = None
    started_at: str | None = None
    finished_at: str | None = None
    # results will be added in a later change


_JOB_STORE: Dict[str, Dict[str, Any]] = {}


@app.post("/campaigns/jobs", response_model=JobCreateResponse, status_code=202)
async def create_job(brief: CampaignBrief, background_tasks: BackgroundTasks) -> JobCreateResponse:
    job_id = str(uuid.uuid4())
    _JOB_STORE[job_id] = {
        "status": "pending",
        "campaign_id": brief.campaign_id,
        "started_at": None,
        "finished_at": None,
        "total_variants": None,
        "assets_reused": None,
        "new_generations": None,
    }

    # Schedule background execution
    background_tasks.add_task(_run_job, job_id, brief.model_dump())

    return JobCreateResponse(job_id=job_id, status="pending")


@app.get("/campaigns/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str) -> JobStatusResponse:
    job = _JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        campaign_id=job.get("campaign_id"),
        total_variants=job.get("total_variants"),
        assets_reused=job.get("assets_reused"),
        new_generations=job.get("new_generations"),
        started_at=job.get("started_at"),
        finished_at=job.get("finished_at"),
    )


async def _run_job(job_id: str, brief_dict: Dict[str, Any]) -> None:
    job = _JOB_STORE[job_id]
    job["status"] = "running"
    job["started_at"] = datetime.now(timezone.utc).isoformat()

    # Reconstruct brief
    brief = CampaignBrief(**brief_dict)

    # Initialize services
    try:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not configured")

        openai_client = OpenAIImageClient(api_key=settings.OPENAI_API_KEY)
        orchestrator = GenAIOrchestrator(openai_client=openai_client)
        processor = ImageProcessor()
        storage = StorageManager(base_path=Path("outputs"))
    except Exception as exc:
        logger.error("Job %s initialization failed: %s", job_id, exc)
        job["status"] = "failed"
        job["finished_at"] = datetime.now(timezone.utc).isoformat()
        return

    total_variants = 0
    total_reused = 0

    async def _run_for_product(product):
        nonlocal total_variants, total_reused
        tasks = [
            _generate_variant(
                orchestrator=orchestrator,
                processor=processor,
                storage=storage,
                product=product,
                brief=brief,
                ratio=ratio,
            )
            for ratio in ASPECT_RATIOS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.error("Job %s: variant failed for product %s: %s", job_id, product.id, result)
            else:
                total_variants += 1
                if result.get("reused"):
                    total_reused += 1

    try:
        await asyncio.gather(*[_run_for_product(product) for product in brief.products])
        job["status"] = "succeeded"
    except Exception as exc:  # pragma: no cover
        logger.error("Job %s failed: %s", job_id, exc)
        job["status"] = "failed"
    finally:
        await openai_client.close()
        job["finished_at"] = datetime.now(timezone.utc).isoformat()
        job["campaign_id"] = brief.campaign_id
        job["total_variants"] = total_variants
        job["assets_reused"] = total_reused
        job["new_generations"] = total_variants - total_reused


# Internal helpers (duplicated lightly to avoid importing CLI module in API layer)
from src.cli import build_generation_prompt  # noqa: E402  (import after FastAPI app)
from src.models.brief import AspectRatio, Product  # noqa: E402


async def _generate_variant(
    orchestrator: GenAIOrchestrator,
    processor: ImageProcessor,
    storage: StorageManager,
    product: Product,
    brief: CampaignBrief,
    ratio: AspectRatio,
) -> Dict[str, Any]:
    """Generate and post-process a single variant, then save output."""
    reused = False

    # Step 1: Reuse if available
    existing_asset = storage.get_asset(
        product_id=product.id, ratio_name=ratio.name, campaign_id=brief.campaign_id
    )
    if existing_asset:
        image_data = existing_asset
        reused = True
    else:
        # Step 2: Generate
        prompt = build_generation_prompt(product, brief)
        image_data = await orchestrator.generate_image(
            prompt=prompt,
            width=ratio.width,
            height=ratio.height,
            product_id=product.id,
        )
        # Step 3: Resize to exact target
        image_data = processor.resize(image_data, ratio.width, ratio.height)

    # Step 4: Add text overlay
    image_data = processor.add_text_overlay(
        image_data=image_data, text=brief.campaign_message, position="bottom"
    )

    # Step 5: Save
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
            "reused": reused,
        },
    )

    return {"success": True, "ratio": ratio.name, "path": str(output_path), "reused": reused}
