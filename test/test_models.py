"""Tests for Pydantic models and validation"""

import pytest
from pydantic import ValidationError

from src.models.brief import ASPECT_RATIOS, CampaignBrief, Product


def test_campaign_brief_valid():
    """Test valid campaign brief creation"""
    valid_brief = {
        "campaign_id": "test-001",
        "products": [
            {"id": "p1", "name": "Product 1", "description": "Test product 1"},
            {"id": "p2", "name": "Product 2", "description": "Test product 2"},
        ],
        "target_market": "US",
        "target_audience": "Test audience",
        "campaign_message": "Test message",
        "locale": "en",
    }

    brief = CampaignBrief(**valid_brief)

    assert brief.campaign_id == "test-001"
    assert len(brief.products) == 2
    assert brief.target_market == "US"
    assert brief.locale == "en"


def test_campaign_brief_requires_one_or_more_products():
    """Test that at least 1 product is required"""
    invalid_brief = {
        "campaign_id": "test-001",
        "products": [],
        "target_market": "US",
        "target_audience": "Test",
        "campaign_message": "Test",
    }

    with pytest.raises(ValidationError) as exc_info:
        CampaignBrief(**invalid_brief)

    assert "products" in str(exc_info.value).lower()
    assert (
        "at least 1" in str(exc_info.value).lower()
        or "too_short" in str(exc_info.value).lower()
    )


def test_campaign_message_max_length():
    """Test campaign message length validation"""
    long_message = "x" * 101

    invalid_brief = {
        "campaign_id": "test-001",
        "products": [
            {"id": "p1", "name": "Product 1"},
            {"id": "p2", "name": "Product 2"},
        ],
        "target_market": "US",
        "target_audience": "Test",
        "campaign_message": long_message,
    }

    with pytest.raises(ValidationError):
        CampaignBrief(**invalid_brief)


def test_aspect_ratios_defined():
    """Test that standard aspect ratios are defined"""
    assert len(ASPECT_RATIOS) == 3

    ratio_names = [r.name for r in ASPECT_RATIOS]
    assert "1x1" in ratio_names
    assert "9x16" in ratio_names
    assert "16x9" in ratio_names


def test_product_optional_fields():
    """Test that product description and hero_image_url are optional"""
    product = Product(id="p1", name="Test Product")

    assert product.id == "p1"
    assert product.name == "Test Product"
    assert product.description is None
    assert product.hero_image_url is None
