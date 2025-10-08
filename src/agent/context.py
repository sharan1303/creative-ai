"""
Context builder for agent alerts.

Gathers campaign metadata, variant status, and error logs to construct
structured context for LLM alert generation.
"""
from collections import Counter
from datetime import datetime
from typing import List

from src.agent.models import AlertContext, CampaignContext, ErrorLog, ProductStatus
from src.db.database import Campaign, get_db
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def build_alert_context(
    campaign: Campaign, issue_type: str, context: dict
) -> AlertContext:
    """
    Construct structured context for LLM alert generation.

    Args:
        campaign: Campaign database record
        issue_type: Type of issue detected
        context: Additional context data

    Returns:
        AlertContext with all information for LLM
    """
    db = get_db()

    # Gather campaign metadata
    campaign_info = CampaignContext(
        campaign_id=campaign.id,
        campaign_name=campaign.name or campaign.id,
        created_at=campaign.created_at.isoformat(),
        elapsed_time=str(datetime.now() - campaign.created_at),
        target_market=campaign.target_market or "Unknown",
        target_audience=campaign.target_audience,
        campaign_message=campaign.campaign_message,
        products=[],
    )

    # Add product details
    for product_id in campaign.product_ids:
        variants = db.get_variants(campaign.id, product_id)
        generated_ratios = [v.aspect_ratio for v in variants]
        missing_ratios = list(set(["1:1", "9:16", "16:9"]) - set(generated_ratios))

        product_name = variants[0].product_name if variants else None

        campaign_info.products.append(
            ProductStatus(
                product_id=product_id,
                product_name=product_name,
                variant_count=len(variants),
                ratios_generated=generated_ratios,
                ratios_missing=missing_ratios,
            )
        )

    # Fetch recent errors
    errors = db.get_recent_errors(campaign.id, window_minutes=10, limit=5)
    error_summary = [
        ErrorLog(
            timestamp=e.occurred_at.isoformat(),
            type=e.error_type,
            message=e.error_message[:100],  # Truncate long messages
        )
        for e in errors
    ]

    # Analyze root cause
    root_cause = _analyze_root_cause(errors)

    alert_context = AlertContext(
        issue_type=issue_type,
        campaign=campaign_info,
        errors=error_summary,
        root_cause=root_cause,
        context=context,
    )

    logger.debug(
        f"Built alert context for {campaign.id}: "
        f"{len(campaign_info.products)} products, {len(error_summary)} errors"
    )

    return alert_context


def _analyze_root_cause(errors: List) -> str:
    """
    Determine most likely root cause from error patterns.

    Args:
        errors: List of Error records

    Returns:
        Human-readable root cause description
    """
    if not errors:
        return "Unknown (no error logs available)"

    error_types = [e.error_type for e in errors]

    # Count error types
    type_counts = Counter(error_types)
    most_common = type_counts.most_common(1)[0]

    # Map error types to root causes
    root_cause_map = {
        "api_rate_limit": "API rate limit exceeded (quota exhausted)",
        "api_failure": "API service disruption or timeout",
        "quota_exceeded": "API quota limit reached for billing period",
        "compliance_violation": "Generated content failed brand compliance checks",
        "storage_error": "File system or storage service failure",
        "network_error": "Network connectivity issues",
        "timeout": "Request timeout (slow API response)",
        "invalid_request": "Invalid API request parameters",
    }

    return root_cause_map.get(
        most_common[0],
        f"Multiple errors of type: {most_common[0]} ({most_common[1]} occurrences)",
    )
