"""Command-line interface for Creative Automation Pipeline

Main entry point for running the campaign generation pipeline.
Orchestrates all services to transform campaign briefs into ready-to-use assets.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import questionary

from src.db.database import Database
from src.models.brief import ASPECT_RATIOS, CampaignBrief
from src.services.genai import GenAIOrchestrator
from src.services.google_image_client import GoogleImageClient
from src.services.openai_image_client import OpenAIImageClient
from src.services.processor import ImageProcessor
from src.services.storage import StorageManager
from src.services.variant_generation import generate_variant
from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def process_campaign(brief_path: str, provider: str, model: str) -> None:
    """Main pipeline execution orchestrator

    Workflow:
    1. Load and validate campaign brief
    2. Initialize all services (including database)
    3. Create campaign record in database
    4. For each product:
       - Generate/reuse base image
       - Create variants for all aspect ratios
       - Apply text overlays
       - Save with metadata
       - Record to database
    5. Update campaign status and cleanup

    Args:
        brief_path: Path to campaign brief JSON file
        provider: Image generation provider (openai/google)
        model: Model name to use
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

    # Step 2: Initialize services (including database)
    logger.info("\nInitializing services...")

    try:
        # Initialize database
        db = Database()
        logger.info("[OK] Database initialized")

        openai_client = None
        if settings.OPENAI_API_KEY:
            openai_client = OpenAIImageClient(api_key=settings.OPENAI_API_KEY)
        else:
            logger.warning("OPENAI_API_KEY not configured; OpenAI provider disabled")

        google_client = None
        if settings.GOOGLE_AI_API_KEY:
            google_client = GoogleImageClient()
        else:
            logger.warning("GOOGLE_AI_API_KEY not configured; Google provider disabled")

        orchestrator = GenAIOrchestrator(
            openai_client=openai_client, google_client=google_client
        )
        processor = ImageProcessor()
        storage = StorageManager(base_path=Path("outputs"))
        logger.info("[OK] All services initialized")
    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        sys.exit(1)

    # Step 3: Create campaign record in database
    try:
        product_ids = [p.id for p in brief.products]
        campaign = db.create_campaign(
            campaign_id=brief.campaign_id,
            name=getattr(brief, "name", None) or brief.campaign_id,
            product_ids=product_ids,
            target_market=brief.target_market,
            target_audience=brief.target_audience,
            campaign_message=brief.campaign_message,
            status="processing",
        )
        logger.info(f"[OK] Campaign record created in database: {campaign.id}")
    except Exception as e:
        logger.error(f"Failed to create campaign record: {e}")
        sys.exit(1)

    # Step 4: Process each product
    total_variants = 0
    total_reused = 0
    total_errors = 0

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
                providers_to_try=[provider],
                models_to_try=[model],
                database=db,  # Pass database connection
            )
            tasks.append(task)

        # Execute all aspect ratio generations in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures, record to database
        for ratio, result in zip(ASPECT_RATIOS, results):
            if isinstance(result, Exception):
                logger.error(f"  [FAILED] Variant generation failed: {result}")
                total_errors += 1
                # Log error to database
                try:
                    db.create_error(
                        campaign_id=brief.campaign_id,
                        product_id=product.id,
                        error_type="generation_failure",
                        error_message=str(result)[:500],  # Truncate long errors
                    )
                except Exception as e:
                    logger.warning(f"Failed to log error to database: {e}")
            elif result.get("reused"):
                total_reused += 1
                total_variants += 1
                logger.info(f"  [REUSED] {result['ratio']}")
                # Note: Reused variants are already in database from previous run
            else:
                total_variants += 1
                logger.info(f"  [OK] Generated: {result['ratio']}")
                # Variant already recorded by generate_variant function

    # Step 5: Update campaign status and cleanup
    try:
        if total_errors == 0:
            db.update_campaign_status(brief.campaign_id, "completed")
            logger.info("[OK] Campaign marked as completed")
        else:
            db.update_campaign_status(brief.campaign_id, "failed")
            logger.warning(
                f"[WARNING] Campaign marked as failed ({total_errors} errors)"
            )
    except Exception as e:
        logger.error(f"Failed to update campaign status: {e}")

    # Close database connection
    db.close()

    # Close API clients
    if openai_client is not None:
        await openai_client.close()
    if google_client is not None:
        await google_client.close()

    logger.info("\n" + "=" * 80)
    logger.info("Pipeline Execution Complete!")
    logger.info("=" * 80)
    logger.info(f"Campaign ID: {brief.campaign_id}")
    logger.info(f"Total Variants Generated: {total_variants}")
    logger.info(f"Assets Reused: {total_reused}")
    logger.info(f"New Generations: {total_variants - total_reused}")
    logger.info(f"Errors: {total_errors}")
    logger.info(f"\nOutputs saved to: outputs/{brief.campaign_id}/")
    logger.info(f"Database record: {db.db_path}")
    logger.info("=" * 80)


async def run_monitoring_agent(check_interval: int, sla_threshold: int):
    """Run the monitoring agent"""
    from src.agent.monitor import run_monitor_agent

    logger.info("Starting monitoring agent...")
    await run_monitor_agent(
        check_interval=check_interval, sla_threshold_minutes=sla_threshold
    )


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Creative Automation Pipeline - Adobe FDE Take-Home",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version", action="version", version="Creative Automation Pipeline v1.0.0"
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Process command
    process_parser = subparsers.add_parser(
        "process",
        help="Process a campaign brief and generate assets",
        epilog="""
Examples:
  uv run -m src.cli process --brief examples/brief_single_product.json
  uv run -m src.cli process --brief examples/brief_multi_product.json
        """,
    )
    process_parser.add_argument(
        "--brief", required=True, help="Path to campaign brief JSON file"
    )

    # Monitor command
    monitor_parser = subparsers.add_parser(
        "monitor",
        help="Run the monitoring agent for campaign alerts",
        epilog="""
Examples:
  uv run -m src.cli monitor
  uv run -m src.cli monitor --interval 30 --sla-threshold 5
        """,
    )
    monitor_parser.add_argument(
        "--interval",
        type=int,
        default=settings.AGENT_CHECK_INTERVAL,
        help=f"Check interval in seconds (default: {settings.AGENT_CHECK_INTERVAL})",
    )
    monitor_parser.add_argument(
        "--sla-threshold",
        type=int,
        default=settings.AGENT_SLA_THRESHOLD_MINUTES,
        help=f"SLA threshold in minutes (default: {settings.AGENT_SLA_THRESHOLD_MINUTES})",
    )

    # Alerts command
    alerts_parser = subparsers.add_parser(
        "alerts",
        help="Show latest alert payload (optionally filtered by campaign)",
        epilog="""
Examples:
  uv run -m src.cli alerts
  uv run -m src.cli alerts --campaign summer-splash-eu-2025
        """,
    )
    alerts_parser.add_argument(
        "--campaign",
        help="Campaign ID to filter alerts",
        required=False,
        default=None,
    )
    alerts_parser.add_argument(
        "--text",
        action="store_true",
        help="Print the email body as plain text",
    )
    alerts_parser.add_argument(
        "--regenerate",
        action="store_true",
        help=(
            "Regenerate the email using mock provider (ignores stored content); "
            "useful if the stored payload is an SDK object string"
        ),
    )

    args = parser.parse_args()

    # Show help if no command specified
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Run appropriate command
    try:
        if args.command == "process":
            # Build provider choices based on available credentials
            provider_choices = []
            if settings.OPENAI_API_KEY:
                provider_choices.append("OpenAI")
            else:
                logger.info(
                    "OpenAI disabled: missing OPENAI_API_KEY in environment/.env"
                )

            if settings.GOOGLE_AI_API_KEY:
                provider_choices.append("Google")
            else:
                logger.info(
                    "Google disabled: missing GOOGLE_AI_API_KEY in environment/.env"
                )

            if not provider_choices:
                logger.error(
                    "No providers available. Set OPENAI_API_KEY and/or GOOGLE_AI_API_KEY."
                )
                sys.exit(1)

            if len(provider_choices) == 1:
                provider_choice = provider_choices[0]
            else:
                provider_choice = questionary.select(
                    "Select provider",
                    choices=provider_choices,
                ).ask()
            provider = (
                "openai" if str(provider_choice).lower() == "openai" else "google"
            )

            if provider == "openai":
                model = questionary.select(
                    "Select OpenAI image model",
                    choices=[
                        "dall-e-3",
                        "gpt-image-1",
                        "gpt-image-1-mini",
                    ],
                ).ask()
            else:
                model = questionary.select(
                    "Select Google model",
                    choices=[
                        "gemini-2.5-flash-image",
                    ],
                ).ask()

            asyncio.run(process_campaign(args.brief, provider, model))

        elif args.command == "monitor":
            asyncio.run(run_monitoring_agent(args.interval, args.sla_threshold))
        elif args.command == "alerts":
            db = Database()
            alert = db.get_latest_alert(args.campaign)
            if not alert:
                print(
                    "No alerts found"
                    + (f" for campaign {args.campaign}" if args.campaign else "")
                )
                sys.exit(0)
            if args.text or args.regenerate:
                # Optionally regenerate to ensure human-readable text
                if args.regenerate:
                    try:
                        # Force mock provider to guarantee plain text output
                        setattr(settings, "GENAI_PROVIDER", "google")
                    except Exception:
                        pass

                from src.agent.context import build_alert_context
                from src.agent.llm_client import generate_alert_email

                async def _render_email_text() -> str:
                    campaign = db.get_campaign(alert.campaign_id)
                    if campaign is None:
                        return alert.email_content
                    ctx = await build_alert_context(
                        campaign=campaign, issue_type=alert.issue_type, context={}
                    )
                    return await generate_alert_email(ctx)

                email_text = asyncio.run(_render_email_text())
                print(email_text)
            else:
                # Output as JSON for easy consumption
                payload = {
                    "id": alert.id,
                    "campaign_id": alert.campaign_id,
                    "issue_type": alert.issue_type,
                    "recipient": alert.recipient,
                    "sent_at": alert.sent_at.isoformat(),
                    "email_content": alert.email_content,
                }
                print(json.dumps(payload, indent=2))
    except KeyboardInterrupt:
        logger.info("\nPipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Command failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
