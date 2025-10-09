"""
Pydantic models for agent context and alerts.
"""
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel


class ProductStatus(BaseModel):
    """Product status for alert context"""

    product_id: str
    product_name: Optional[str] = None
    variant_count: int
    ratios_generated: List[str]
    ratios_missing: List[str]


class ErrorLog(BaseModel):
    """Error log entry for alert context"""

    timestamp: str
    type: str
    message: str


class CampaignContext(BaseModel):
    """Campaign information for alert context"""

    campaign_id: str
    campaign_name: str
    created_at: str
    elapsed_time: str
    target_market: str
    target_audience: Optional[str] = None
    campaign_message: Optional[str] = None
    products: List[ProductStatus]


class AlertContext(BaseModel):
    """Complete context for LLM alert generation"""

    issue_type: Literal["insufficient_variants", "repeated_failures", "sla_breach"]
    campaign: CampaignContext
    errors: List[ErrorLog]
    root_cause: str
    context: Dict

