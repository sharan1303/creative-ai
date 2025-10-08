"""Tests for agent monitoring system"""

from datetime import datetime

import pytest

from src.agent.context import _analyze_root_cause
from src.agent.llm_client import generate_alert_email
from src.agent.models import AlertContext, CampaignContext, ErrorLog, ProductStatus
from src.db.database import Database


class TestDatabase:
    """Test database operations"""

    @pytest.fixture
    def db(self, tmp_path):
        """Create temporary test database"""
        db_path = tmp_path / "test.db"
        db = Database(str(db_path))
        yield db
        db.close()

    def test_create_campaign(self, db):
        """Test campaign creation"""
        campaign = db.create_campaign(
            campaign_id="test-001",
            name="Test Campaign",
            product_ids=["prod_a", "prod_b"],
            target_market="EU",
            status="pending",
        )

        assert campaign.id == "test-001"
        assert campaign.name == "Test Campaign"
        assert len(campaign.product_ids) == 2
        assert campaign.status == "pending"

    def test_get_active_campaigns(self, db):
        """Test retrieving active campaigns"""
        # Create test campaigns
        db.create_campaign("test-001", "Campaign 1", ["prod_a"], status="processing")
        db.create_campaign("test-002", "Campaign 2", ["prod_b"], status="pending")
        db.create_campaign("test-003", "Campaign 3", ["prod_c"], status="completed")

        active = db.get_active_campaigns()

        assert len(active) == 2
        assert all(c.status in ["pending", "processing"] for c in active)

    def test_create_variant(self, db):
        """Test variant creation"""
        db.create_campaign("test-001", "Test", ["prod_a"])

        variant = db.create_variant(
            campaign_id="test-001",
            product_id="prod_a",
            product_name="Product A",
            aspect_ratio="1:1",
            file_path="/path/to/file.png",
            metadata={"size": "1024x1024"},
        )

        assert variant.campaign_id == "test-001"
        assert variant.product_id == "prod_a"
        assert variant.aspect_ratio == "1:1"

    def test_create_error(self, db):
        """Test error logging"""
        db.create_campaign("test-001", "Test", ["prod_a"])

        error = db.create_error(
            campaign_id="test-001",
            error_type="api_rate_limit",
            error_message="Rate limit exceeded",
            product_id="prod_a",
        )

        assert error.campaign_id == "test-001"
        assert error.error_type == "api_rate_limit"

    def test_get_recent_errors(self, db):
        """Test retrieving recent errors"""
        db.create_campaign("test-001", "Test", ["prod_a"])

        # Create multiple errors
        for i in range(5):
            db.create_error(
                campaign_id="test-001",
                error_type="api_failure",
                error_message=f"Error {i}",
            )

        errors = db.get_recent_errors("test-001", window_minutes=10, limit=3)

        assert len(errors) == 3
        assert all(e.campaign_id == "test-001" for e in errors)

    def test_create_alert(self, db):
        """Test alert creation"""
        db.create_campaign("test-001", "Test", ["prod_a"])

        alert = db.create_alert(
            campaign_id="test-001",
            issue_type="insufficient_variants",
            email_content="Test email content",
            recipient="test@example.com",
        )

        assert alert.campaign_id == "test-001"
        assert alert.issue_type == "insufficient_variants"
        assert alert.recipient == "test@example.com"

    def test_get_last_alert_time(self, db):
        """Test retrieving last alert time"""
        db.create_campaign("test-001", "Test", ["prod_a"])

        # No alerts yet
        assert db.get_last_alert_time("test-001") is None

        # Create alert
        db.create_alert(
            campaign_id="test-001",
            issue_type="insufficient_variants",
            email_content="Test",
            recipient="test@example.com",
        )

        last_time = db.get_last_alert_time("test-001", "insufficient_variants")
        assert last_time is not None
        assert isinstance(last_time, datetime)


class TestContextBuilder:
    """Test context builder functions"""

    def test_analyze_root_cause_empty(self):
        """Test root cause analysis with no errors"""
        result = _analyze_root_cause([])
        assert "Unknown" in result

    def test_analyze_root_cause_api_rate_limit(self):
        """Test root cause analysis for rate limits"""
        from src.db.database import Error

        errors = [
            Error(
                id=1,
                campaign_id="test",
                product_id=None,
                error_type="api_rate_limit",
                error_message="Rate limit exceeded",
                occurred_at=datetime.now(),
            )
        ] * 3

        result = _analyze_root_cause(errors)
        assert "rate limit" in result.lower()

    @pytest.mark.asyncio
    async def test_generate_alert_email_no_api_key_uses_fallback(self):
        """Integration-style unit test for email generation without mocking.

        With no OPENAI_API_KEY set, generate_alert_email should return a
        deterministic mock email body.
        """
        context = AlertContext(
            issue_type="insufficient_variants",
            campaign=CampaignContext(
                campaign_id="demo-001",
                campaign_name="Demo Campaign",
                created_at="2025-10-06T12:00:00",
                elapsed_time="0:15:00",
                target_market="EU",
                target_audience="Shoppers",
                campaign_message="Summer sale!",
                products=[
                    ProductStatus(
                        product_id="p1",
                        product_name="Product 1",
                        variant_count=1,
                        ratios_generated=["1:1"],
                        ratios_missing=["9:16", "16:9"],
                    )
                ],
            ),
            errors=[
                ErrorLog(
                    timestamp="2025-10-06T12:10:00",
                    type="api_rate_limit",
                    message="Rate limit exceeded",
                )
            ],
            root_cause="OpenAI API rate limit exceeded (quota exhausted)",
            context={"variant_count": 1, "required_count": 3},
        )

        email = await generate_alert_email(context)
        assert "Demo Campaign" in email
        assert (
            "insufficient variants".replace(" ", "")[:8]
            in email.replace(" ", "").lower()
        )


@pytest.mark.asyncio
class TestMonitorAgent:
    """Test monitoring agent logic"""

    async def test_campaign_check_logic(self):
        """Test campaign health check logic"""
        # This would test the agent's check logic
        # In a full implementation, we'd mock the database
        # and test SLA threshold checks
        pass


# Mark tests that require real API access
@pytest.mark.integration
@pytest.mark.asyncio
class TestLLMClient:
    """Integration tests for LLM client (requires API key)"""

    async def test_generate_alert_email(self):
        """Test email generation with real API"""
        # This would require OPENAI_API_KEY to be set
        # and would make a real API call
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
