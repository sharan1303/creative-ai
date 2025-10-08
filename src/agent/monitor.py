"""
Campaign monitoring agent with AI-driven alerting.

This module implements the core monitoring loop that:
1. Polls database for active campaigns
2. Evaluates SLA compliance and variant counts
3. Triggers AI-generated alerts for issues
"""

import asyncio
from datetime import datetime, timedelta

from src.agent.alerting import deliver_alert
from src.agent.context import build_alert_context
from src.agent.llm_client import generate_alert_email
from src.db.database import Campaign, get_db
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CampaignMonitorAgent:
    """AI-driven monitoring agent for creative automation pipeline"""

    def __init__(
        self,
        check_interval: int = 60,
        sla_threshold_minutes: int = 10,
        max_concurrent_checks: int = 5,
    ):
        """
        Initialize monitoring agent.

        Args:
            check_interval: Seconds between checks
            sla_threshold_minutes: Maximum generation time before alert
            max_concurrent_checks: Max campaigns to check in parallel
        """
        self.check_interval = check_interval
        self.sla_threshold = timedelta(minutes=sla_threshold_minutes)
        self.max_concurrent = max_concurrent_checks
        self.db = get_db()
        self._running = False

    async def start(self):
        """Start the monitoring agent"""
        logger.info("🤖 Campaign Monitor Agent starting...")
        logger.info(f"Check interval: {self.check_interval}s")
        logger.info(
            f"SLA threshold: {self.sla_threshold.total_seconds() / 60:.1f} minutes"
        )

        self._running = True

        try:
            await self.run()
        except KeyboardInterrupt:
            logger.info("Agent stopped by user")
        except Exception as e:
            logger.error(f"Agent crashed: {e}", exc_info=True)
            raise
        finally:
            self._running = False
            await self.cleanup()

    async def stop(self):
        """Stop the monitoring agent"""
        logger.info("Stopping monitoring agent...")
        self._running = False

    async def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up agent resources...")
        self.db.close()

    async def run(self):
        """Main monitoring loop"""
        while self._running:
            try:
                start_time = datetime.now()

                # Check all active campaigns
                await self.check_all_campaigns()

                # Calculate next cycle
                elapsed = (datetime.now() - start_time).total_seconds()
                sleep_time = max(0, self.check_interval - elapsed)

                logger.debug(
                    f"Check completed in {elapsed:.2f}s, " f"sleeping {sleep_time:.2f}s"
                )
                await asyncio.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Monitor loop error: {e}", exc_info=True)
                await asyncio.sleep(10)  # Brief pause before retry

    async def check_all_campaigns(self):
        """Check all active campaigns concurrently"""
        active_campaigns = self.db.get_active_campaigns()

        if not active_campaigns:
            logger.debug("No active campaigns to monitor")
            return

        logger.info(f"Checking {len(active_campaigns)} active campaigns")

        # Process campaigns in batches to limit concurrency
        tasks = [self.check_campaign(campaign) for campaign in active_campaigns]

        for i in range(0, len(tasks), self.max_concurrent):
            batch = tasks[i : i + self.max_concurrent]
            results = await asyncio.gather(*batch, return_exceptions=True)

            # Log any exceptions
            for j, result in enumerate(results):
                if isinstance(result, Exception):
                    campaign_id = active_campaigns[i + j].id
                    logger.error(
                        f"Error checking campaign {campaign_id}: {result}",
                        exc_info=result,
                    )

    async def check_campaign(self, campaign: Campaign):
        """
        Evaluate single campaign health.

        Args:
            campaign: Campaign to check
        """
        try:
            logger.debug(f"Checking campaign {campaign.id}")

            # Check variant counts against SLA
            await self._check_variant_counts(campaign)

            # Check for error patterns
            await self._check_error_patterns(campaign)

        except Exception as e:
            logger.error(f"Error checking campaign {campaign.id}: {e}", exc_info=True)
            raise

    async def _check_variant_counts(self, campaign: Campaign):
        """
        Verify all products have required variants.

        Args:
            campaign: Campaign to check
        """
        for product_id in campaign.product_ids:
            variants = self.db.get_variants(campaign.id, product_id)
            variant_count = len(variants)

            if variant_count < 3:
                elapsed = datetime.now() - campaign.created_at

                if elapsed > self.sla_threshold:
                    logger.warning(
                        f"SLA breach: Campaign {campaign.id}, "
                        f"product {product_id} has {variant_count}/3 variants "
                        f"after {elapsed}"
                    )
                    await self._trigger_alert(
                        campaign=campaign,
                        issue_type="insufficient_variants",
                        context={
                            "product_id": product_id,
                            "variant_count": variant_count,
                            "required_count": 3,
                            "elapsed_time": str(elapsed),
                        },
                    )

    async def _check_error_patterns(self, campaign: Campaign):
        """
        Detect repeated failures.

        Args:
            campaign: Campaign to check
        """
        recent_errors = self.db.get_recent_errors(campaign.id, window_minutes=10)

        if len(recent_errors) > 3:
            logger.warning(
                f"Repeated failures: Campaign {campaign.id} "
                f"has {len(recent_errors)} errors in 10 minutes"
            )
            await self._trigger_alert(
                campaign=campaign,
                issue_type="repeated_failures",
                context={"error_count": len(recent_errors)},
            )

    async def _trigger_alert(self, campaign: Campaign, issue_type: str, context: dict):
        """
        Generate and send alert.

        Args:
            campaign: Campaign with issue
            issue_type: Type of issue detected
            context: Additional context data
        """
        # Check if already alerted recently (avoid spam)
        last_alert = self.db.get_last_alert_time(campaign.id, issue_type)
        if last_alert and (datetime.now() - last_alert) < timedelta(hours=1):
            logger.debug(
                f"Skipping duplicate alert for {campaign.id} "
                f"(last alert: {last_alert})"
            )
            return

        logger.info(f"Triggering alert for campaign {campaign.id}: {issue_type}")

        try:
            # Build context for LLM
            alert_context = await build_alert_context(
                campaign=campaign, issue_type=issue_type, context=context
            )

            # Generate email content using LLM
            email_content = await generate_alert_email(alert_context)

            # Deliver alert
            await deliver_alert(
                email_content=email_content, campaign=campaign, context=alert_context
            )

            logger.info(f"✅ Alert sent for campaign {campaign.id}")

        except Exception as e:
            logger.error(
                f"Failed to send alert for campaign {campaign.id}: {e}", exc_info=True
            )
            # Don't re-raise - continue monitoring other campaigns


async def run_monitor_agent(check_interval: int = 60, sla_threshold_minutes: int = 10):
    """
    Run the monitoring agent (convenience function).

    Args:
        check_interval: Seconds between checks
        sla_threshold_minutes: Maximum generation time before alert
    """
    agent = CampaignMonitorAgent(
        check_interval=check_interval, sla_threshold_minutes=sla_threshold_minutes
    )
    await agent.start()
