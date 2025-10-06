"""Command-line interface for Creative Automation Pipeline

Main entry point for running the campaign generation pipeline.
Orchestrates all services to transform campaign briefs into ready-to-use assets.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from src.models.brief import ASPECT_RATIOS, CampaignBrief
from src.services.genai import GenAIOrchestrator
from src.services.openai_image_client import OpenAIImageClient
from src.services.processor import ImageProcessor
from src.services.storage import StorageManager
from src.services.variant_generation import generate_variant
from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def process_campaign(brief_path: str) -> None:
    """Main pipeline execution orchestrator

    Workflow:
    1. Load and validate campaign brief
    2. Initialize all services
    3. For each product:
       - Generate/reuse base image
       - Create variants for all aspect ratios
       - Apply text overlays
       - Save with metadata
    4. Cleanup and report results

    Args:
        brief_path: Path to campaign brief JSON file
    """
    logger.info("=" * 80)
    logger.info("Creative Automation Pipeline - Starting")
    logger.info("=" * 80)

    # Step 1: Load and validate campaign brief
    logger.info(f"Loading campaign brief from: {brief_path}")
    try:
        with open(brief_path, "r", encoding="utf-8") as f:
            brief_data = json.load(f)
        brief = CampaignBrief(**brief_data)
        logger.info(f"[OK] Campaign Brief validated: {brief.campaign_id}")
        logger.info(f"  - Products: {len(brief.products)}")
        logger.info(f"  - Target Market: {brief.target_market}")
        logger.info(f"  - Target Audience: {brief.target_audience}")
        logger.info(f"  - Campaign Message: {brief.campaign_message}")
    except FileNotFoundError:
        logger.error(f"Campaign brief not found: {brief_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in campaign brief: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Campaign brief validation failed: {e}")
        sys.exit(1)

    # Step 2: Initialize services
    logger.info("\nInitializing services...")

    # Check for API key
    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not configured!")
        logger.error("Please set OPENAI_API_KEY in .env file or environment")
        sys.exit(1)

    try:
        openai_client = OpenAIImageClient(api_key=settings.OPENAI_API_KEY)
        orchestrator = GenAIOrchestrator(openai_client=openai_client)
        processor = ImageProcessor()
        storage = StorageManager(base_path=Path("outputs"))
        logger.info("[OK] All services initialized")
    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        sys.exit(1)

    # Step 3: Process each product
    total_variants = 0
    total_reused = 0

    logger.info(f"\nProcessing {len(brief.products)} products...")
    logger.info("-" * 80)

    for idx, product in enumerate(brief.products, 1):
        logger.info(f"\n[{idx}/{len(brief.products)}] Processing: {product.name}")
        logger.info(f"  Product ID: {product.id}")

        # Generate for each aspect ratio in parallel
        tasks = []
        for ratio in ASPECT_RATIOS:
            task = generate_variant(
                orchestrator=orchestrator,
                processor=processor,
                storage=storage,
                product=product,
                brief=brief,
                ratio=ratio,
            )
            tasks.append(task)

        # Execute all aspect ratio generations in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"  [FAILED] Variant generation failed: {result}")
            elif result.get("reused"):
                total_reused += 1
                total_variants += 1
                logger.info(f"  [REUSED] {result['ratio']}")
            else:
                total_variants += 1
                logger.info(f"  [OK] Generated: {result['ratio']}")

    # Step 4: Cleanup and summary
    await openai_client.close()

    logger.info("\n" + "=" * 80)
    logger.info("Pipeline Execution Complete!")
    logger.info("=" * 80)
    logger.info(f"Campaign ID: {brief.campaign_id}")
    logger.info(f"Total Variants Generated: {total_variants}")
    logger.info(f"Assets Reused: {total_reused}")
    logger.info(f"New Generations: {total_variants - total_reused}")
    logger.info(f"\nOutputs saved to: outputs/{brief.campaign_id}/")
    logger.info("=" * 80)




def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Creative Automation Pipeline - Adobe FDE Take-Home",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run -m src.cli --brief examples/brief_single_product.json
  uv run -m src.cli --brief examples/brief_multi_product.json

Environment Variables:
  OPENAI_API_KEY       Required - OpenAI API key for image generation
  LOG_LEVEL           Optional - Logging level (default: INFO)
  GENAI_PROVIDER      Optional - Primary provider (default: openai)
        """,
    )

    parser.add_argument(
        "--brief", required=True, help="Path to campaign brief JSON file"
    )

    parser.add_argument(
        "--version", action="version", version="Creative Automation Pipeline v1.0.0"
    )

    args = parser.parse_args()

    # Run async pipeline
    try:
        asyncio.run(process_campaign(args.brief))
    except KeyboardInterrupt:
        logger.info("\nPipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Pipeline failed with unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
