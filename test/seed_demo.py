"""Seed a demo campaign into the local SQLite database.

Usage:
  uv run -m src.seed_demo
"""

from __future__ import annotations

from datetime import datetime

from src.db.database import Database
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    db = Database()

    campaign_id = "demo-monitor-001"

    existing = db.get_campaign(campaign_id)
    if existing is None:
        logger.info("Seeding demo campaign %s", campaign_id)
        db.create_campaign(
            campaign_id=campaign_id,
            name="Demo Monitoring Campaign",
            product_ids=["prod_a", "prod_b"],
            target_market="EU",
            target_audience="Demo audience",
            campaign_message="Demo Sale!",
            status="processing",
        )
    else:
        logger.info(
            "Campaign %s already exists; ensuring status is processing", campaign_id
        )
        db.update_campaign_status(campaign_id, "processing")

    # repeated_failures error seeded
    for i in range(4):
        db.create_error(
            campaign_id=campaign_id,
            error_type="api_rate_limit",
            error_message=f"Seeded error {i+1} at {datetime.now().isoformat(timespec='seconds')}",
            product_id=None,
        )

    logger.info("Seed complete. Campaign '%s' ready for monitoring.", campaign_id)


if __name__ == "__main__":
    main()

