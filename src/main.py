"""FastAPI application for Creative Automation Pipeline

Provides HTTP endpoints for health checks and campaign processing that
reuse the existing pipeline services.
"""

from __future__ import annotations

import asyncio
import secrets
from pathlib import Path
from typing import Any, Dict, List, Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from src.celery_app import celery_app
from src.models.brief import ASPECT_RATIOS, CampaignBrief
from src.services.genai import GenAIOrchestrator
from src.services.google_image_client import GoogleImageClient
from src.services.openai_image_client import OpenAIImageClient
from src.services.processor import ImageProcessor
from src.services.storage import StorageManager
from src.services.variant_generation import generate_variant
from src.tasks import process_campaign_task
from src.utils.config import runtime_config, settings
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


class ModelSelectionRequest(BaseModel):
    provider: Literal["openai", "google"]
    model: str


class ModelSelectionResponse(BaseModel):
    provider: str
    model: str
    message: str = "Model configuration updated successfully"


# -----------------------
# Simple API key auth
# -----------------------

API_KEY_HEADER_NAME = "X-API-Key"


def require_api_key(
    x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER_NAME),
) -> None:
    expected = settings.API_AUTH_TOKEN or ""
    if not expected:
        # If not configured, leave open but warn
        logger.warning("API key not configured; skipping auth")
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/select-model", response_model=ModelSelectionResponse)
async def select_model(request: ModelSelectionRequest) -> ModelSelectionResponse:
    """Select the provider and model for image generation

    Args:
        request: Model selection request containing provider and model

    Returns:
        Updated model configuration
    """
    try:
        runtime_config.update(request.provider, request.model)
        logger.info(
            f"Model config updated: provider={request.provider}, model={request.model}"
        )

        return ModelSelectionResponse(provider=request.provider, model=request.model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/current-model", response_model=ModelSelectionResponse)
async def get_current_model() -> ModelSelectionResponse:
    """Get the current provider and model configuration

    Returns:
        Current model configuration
    """
    config = runtime_config.to_dict()
    return ModelSelectionResponse(
        provider=config["provider"],
        model=config["model"],
        message="Current model configuration",
    )


@app.post(
    "/campaigns/process",
    response_model=CampaignProcessResponse,
    dependencies=[Depends(require_api_key)],
)
async def process_campaign(brief: CampaignBrief) -> CampaignProcessResponse:
    """Process a campaign brief and generate creative assets.

    This endpoint executes a similar workflow as the CLI pipeline but operates on
    the provided JSON payload instead of a file.
    """
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY not configured")

    # Initialize services
    openai_client: OpenAIImageClient | None = None
    try:
        openai_client = OpenAIImageClient(api_key=settings.OPENAI_API_KEY)
        google_client = GoogleImageClient()
        orchestrator = GenAIOrchestrator(
            openai_client=openai_client, google_client=google_client
        )
        processor = ImageProcessor()
        storage = StorageManager(base_path=Path("outputs"))
    except Exception as e:  # pragma: no cover - defensive
        logger.exception("Failed to initialise services")
        raise HTTPException(
            status_code=500, detail="Service initialisation failed"
        ) from e

    total_variants = 0
    total_reused = 0
    results: List[VariantResult] = []

    # Build tasks across all products/ratios
    async def _run_for_product(product):
        nonlocal total_variants, total_reused, results
        tasks = []
        ratios = list(ASPECT_RATIOS)
        for ratio in ratios:
            tasks.append(
                _generate_variant(
                    orchestrator=orchestrator,
                    processor=processor,
                    storage=storage,
                    product=product,
                    brief=brief,
                    ratio=ratio,
                    providers_to_try=[runtime_config.provider],
                    models_to_try=[runtime_config.model],
                )
            )
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        for ratio, result in zip(ratios, task_results):
            if isinstance(result, Exception):
                logger.error(
                    "[FAILED] Variant generation failed for product %s: %s",
                    product.id,
                    result,
                )
                results.append(
                    VariantResult(
                        product_id=product.id,
                        ratio=ratio.name,
                        path="",
                        reused=False,
                        success=False,
                        error=str(result),
                    )
                )
            else:
                total_variants += 1
                if result.get("reused"):
                    total_reused += 1
                results.append(
                    VariantResult(
                        product_id=product.id,
                        ratio=ratio.name,
                        path=result.get("path", ""),
                        reused=bool(result.get("reused")),
                        success=True,
                    )
                )

    try:
        await asyncio.gather(*[_run_for_product(product) for product in brief.products])
    finally:
        if openai_client is not None:
            await openai_client.close()

    return CampaignProcessResponse(
        campaign_id=brief.campaign_id,
        total_variants=total_variants,
        assets_reused=total_reused,
        new_generations=total_variants - total_reused,
        results=results,
    )


# -----------------------
# Background job handling (Celery + Redis)
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
    results: List[VariantResult] | None = None


@app.post(
    "/campaigns/jobs",
    response_model=JobCreateResponse,
    status_code=202,
    dependencies=[Depends(require_api_key)],
)
async def create_job(brief: CampaignBrief) -> JobCreateResponse:
    # Pass current model configuration to the Celery task
    task = process_campaign_task.delay(
        brief.model_dump(), provider=runtime_config.provider, model=runtime_config.model
    )
    return JobCreateResponse(job_id=task.id, status="pending")


@app.get(
    "/campaigns/jobs/{job_id}",
    response_model=JobStatusResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_job(job_id: str) -> JobStatusResponse:
    result = celery_app.AsyncResult(job_id)
    state_map = {
        "PENDING": "pending",
        "STARTED": "running",
        "RETRY": "retry",
        "FAILURE": "failed",
        "SUCCESS": "succeeded",
    }
    status = state_map.get(result.state, result.state.lower())

    payload = result.result if result.ready() and result.successful() else None
    finished = None
    try:
        finished = (
            result.date_done.isoformat() if getattr(result, "date_done", None) else None
        )
    except Exception as e:
        logger.debug("Could not retrieve date_done for job %s: %s", job_id, e)
        finished = None

    return JobStatusResponse(
        job_id=job_id,
        status=status,
        campaign_id=(payload or {}).get("campaign_id") if payload else None,
        total_variants=(payload or {}).get("total_variants") if payload else None,
        assets_reused=(payload or {}).get("assets_reused") if payload else None,
        new_generations=(payload or {}).get("new_generations") if payload else None,
        started_at=None,
        finished_at=finished,
        results=(payload or {}).get("results") if payload else None,
    )


async def _generate_variant(
    orchestrator: GenAIOrchestrator,
    processor: ImageProcessor,
    storage: StorageManager,
    product,
    brief,
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
