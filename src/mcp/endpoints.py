"""
MCP-enabled FastAPI endpoints for campaign data access.

These endpoints will be automatically converted to MCP tools by fastapi-mcp.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.db.database import get_db
from src.mcp.models import (
    AlertHistoryEntry,
    CampaignDetails,
    ErrorLogEntry,
    ProductVariants,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/mcp/tools", tags=["MCP Tools"])


class CampaignDetailsRequest(BaseModel):
    """Request model for campaign details"""

    campaign_id: str


class ProductVariantsRequest(BaseModel):
    """Request model for product variants"""

    campaign_id: str
    product_id: Optional[str] = None


class RecentErrorsRequest(BaseModel):
    """Request model for recent errors"""

    campaign_id: str
    minutes: int = 30
    limit: int = 10


class AlertHistoryRequest(BaseModel):
    """Request model for alert history"""

    campaign_id: str
    hours: int = 24


class RootCauseRequest(BaseModel):
    """Request model for root cause analysis"""

    campaign_id: str


@router.post("/get_campaign_details", response_model=CampaignDetails)
async def get_campaign_details(request: CampaignDetailsRequest) -> CampaignDetails:
    """
    Get campaign metadata, status, timeline, and product list.

    This tool provides comprehensive campaign information including:
    - Basic metadata (name, status, creation time)
    - Timeline information (elapsed time since creation)
    - Target market and audience details
    - List of associated product IDs
    """
    try:
        db = get_db()
        campaign = db.get_campaign(request.campaign_id)

        if not campaign:
            raise HTTPException(
                status_code=404, detail=f"Campaign {request.campaign_id} not found"
            )

        elapsed = datetime.now() - campaign.created_at

        return CampaignDetails(
            campaign_id=campaign.id,
            campaign_name=campaign.name or campaign.id,
            status=campaign.status,
            created_at=campaign.created_at.isoformat(),
            elapsed_time=str(elapsed),
            target_market=campaign.target_market or "Unknown",
            target_audience=campaign.target_audience,
            campaign_message=campaign.campaign_message,
            product_ids=campaign.product_ids,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign details: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving campaign details: {str(e)}"
        )


@router.post("/get_product_variants", response_model=List[ProductVariants])
async def get_product_variants(
    request: ProductVariantsRequest,
) -> List[ProductVariants]:
    """
    Get variant counts and aspect ratios for campaign products.

    This tool provides detailed variant information including:
    - Number of variants generated per product
    - Which aspect ratios have been generated (1:1, 9:16, 16:9)
    - Which aspect ratios are still missing
    - Individual variant details with timestamps
    """
    try:
        db = get_db()
        campaign = db.get_campaign(request.campaign_id)

        if not campaign:
            raise HTTPException(
                status_code=404, detail=f"Campaign {request.campaign_id} not found"
            )

        product_ids = (
            [request.product_id] if request.product_id else campaign.product_ids
        )
        results = []

        for pid in product_ids:
            variants = db.get_variants(request.campaign_id, pid)
            generated_ratios = [v.aspect_ratio for v in variants]
            missing_ratios = list(set(["1:1", "9:16", "16:9"]) - set(generated_ratios))

            product_name = variants[0].product_name if variants else None

            variant_data = ProductVariants(
                product_id=pid,
                product_name=product_name,
                variant_count=len(variants),
                ratios_generated=generated_ratios,
                ratios_missing=missing_ratios,
                variants=[
                    {
                        "id": v.id,
                        "aspect_ratio": v.aspect_ratio,
                        "status": getattr(v, "status", "completed"),
                        "created_at": v.generated_at.isoformat(),
                    }
                    for v in variants
                ],
            )
            results.append(variant_data)

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product variants: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving product variants: {str(e)}"
        )


@router.post("/get_recent_errors", response_model=List[ErrorLogEntry])
async def get_recent_errors(request: RecentErrorsRequest) -> List[ErrorLogEntry]:
    """
    Get recent error logs with filtering options.

    This tool provides error information including:
    - Error timestamps and types
    - Error messages (truncated for readability)
    - Associated campaign and product IDs
    - Configurable time window and result limit
    """
    try:
        db = get_db()
        errors = db.get_recent_errors(
            request.campaign_id, request.minutes, request.limit
        )

        return [
            ErrorLogEntry(
                timestamp=e.occurred_at.isoformat(),
                error_type=e.error_type,
                error_message=e.error_message[:200],
                campaign_id=e.campaign_id,
                product_id=getattr(e, "product_id", None),
            )
            for e in errors
        ]

    except Exception as e:
        logger.error(f"Error getting recent errors: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving recent errors: {str(e)}"
        )


@router.post("/get_alert_history", response_model=List[AlertHistoryEntry])
async def get_alert_history(request: AlertHistoryRequest) -> List[AlertHistoryEntry]:
    """
    Get previous alerts to prevent duplicate notifications.

    This tool provides alert history including:
    - Previous alert timestamps and types
    - Recipients of past alerts
    - Resolution status
    - Configurable time window for lookback
    """
    try:
        db = get_db()
        since = datetime.now() - timedelta(hours=request.hours)
        alerts = db.get_alerts_since(request.campaign_id, since)

        return [
            AlertHistoryEntry(
                alert_id=str(a.id),
                campaign_id=a.campaign_id,
                issue_type=a.issue_type,
                created_at=a.sent_at.isoformat(),
                recipient=a.recipient,
                resolved=getattr(a, "resolved", False),
            )
            for a in alerts
        ]

    except Exception as e:
        logger.error(f"Error getting alert history: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving alert history: {str(e)}"
        )


@router.post("/analyze_root_cause")
async def analyze_root_cause(request: RootCauseRequest) -> dict:
    """
    Perform error pattern analysis to identify root causes.

    This tool provides root cause analysis including:
    - Error pattern identification and frequency
    - Timeline analysis of error occurrences
    - Suggested root causes based on error types
    - Percentage breakdown of error categories
    """
    try:
        db = get_db()
        errors = db.get_recent_errors(request.campaign_id, window_minutes=60, limit=50)

        if not errors:
            return {
                "analysis": "No recent errors to analyze",
                "error_patterns": [],
                "timeline": None,
                "recommendations": [],
            }

        from collections import Counter

        error_types = [e.error_type for e in errors]
        type_counts = Counter(error_types)
        most_common = type_counts.most_common(3)

        root_cause_map = {
            "api_rate_limit": "API rate limit exceeded - quota exhausted or too many concurrent requests",
            "api_failure": "API service disruption - external service downtime or connectivity issues",
            "quota_exceeded": "API quota limit reached for current billing period",
            "compliance_violation": "Generated content failed brand compliance checks",
            "storage_error": "File system or cloud storage service failure",
            "network_error": "Network connectivity issues or DNS resolution problems",
            "timeout": "Request timeout - slow API response or network latency",
            "invalid_request": "Invalid API request parameters or malformed data",
        }

        error_patterns = []
        for error_type, count in most_common:
            percentage = (count / len(errors)) * 100
            root_cause = root_cause_map.get(
                error_type, f"Unknown error pattern: {error_type}"
            )
            error_patterns.append(
                {
                    "error_type": error_type,
                    "count": count,
                    "percentage": round(percentage, 1),
                    "root_cause": root_cause,
                }
            )

        timeline = None
        if len(errors) > 1:
            first_error = min(errors, key=lambda e: e.occurred_at)
            last_error = max(errors, key=lambda e: e.occurred_at)
            duration = last_error.occurred_at - first_error.occurred_at
            timeline = {
                "first_error": first_error.occurred_at.isoformat(),
                "last_error": last_error.occurred_at.isoformat(),
                "duration": str(duration),
                "total_errors": len(errors),
            }

        return {
            "analysis": f"Analyzed {len(errors)} errors from the last 60 minutes",
            "error_patterns": error_patterns,
            "timeline": timeline,
            "recommendations": [
                "Check API quotas and rate limits",
                "Verify network connectivity",
                "Review recent configuration changes",
                "Monitor external service status",
            ],
        }

    except Exception as e:
        logger.error(f"Error analyzing root cause: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error performing root cause analysis: {str(e)}"
        )
