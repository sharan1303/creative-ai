"""Campaign brief schema definitions"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Product(BaseModel):
    """Product information for campaign

    Each product represents an item to generate creative assets for.
    """

    id: str = Field(..., description="Unique product identifier")
    name: str = Field(..., description="Product display name")
    description: Optional[str] = Field(
        None, description="Product description for prompt engineering"
    )
    hero_image_url: Optional[str] = Field(
        None, description="Existing hero image URL (for asset reuse)"
    )


class CampaignBrief(BaseModel):
    """Campaign brief input schema

    This represents the input contract for the automation pipeline.
    Validates that all required fields are present and meet business rules.
    """

    campaign_id: str = Field(..., description="Unique campaign identifier")
    products: List[Product] = Field(
        ..., min_length=1, description="At least 1 product required"
    )
    target_market: str = Field(
        ..., description="Target region/market (e.g., 'EU', 'US-West')"
    )
    target_audience: str = Field(..., description="Audience persona for targeting")
    campaign_message: str = Field(
        ..., max_length=100, description="Text overlay for creative"
    )
    brand_colors: Optional[List[str]] = Field(
        None, description="Hex color codes for brand compliance"
    )
    locale: str = Field("en", description="Language code (e.g., 'en', 'fr', 'es')")

    @field_validator("products")
    @classmethod
    def validate_product_count(cls, v: List[Product]) -> List[Product]:
        """Ensure at least 1 product is provided"""
        if len(v) < 1:
            raise ValueError("At least 1 product required per campaign brief")
        return v

    @field_validator("campaign_message")
    @classmethod
    def validate_message_length(cls, v: str) -> str:
        """Ensure campaign message is reasonable length for overlay"""
        if len(v) > 100:
            raise ValueError("Campaign message must be 100 characters or less")
        return v


class AspectRatio(BaseModel):
    """Aspect ratio specification for social media platforms

    Defines target dimensions for different social media formats.
    """

    name: str  # "1x1", "9x16", "16x9"
    width: int
    height: int
    platform: str  # Description of primary platform


# Standard aspect ratios for social media campaigns
ASPECT_RATIOS = [
    AspectRatio(name="1x1", width=1024, height=1024, platform="Instagram Feed"),
    AspectRatio(name="9x16", width=1080, height=1920, platform="Stories/Reels"),
    AspectRatio(name="16x9", width=1920, height=1080, platform="YouTube/Facebook"),
]
