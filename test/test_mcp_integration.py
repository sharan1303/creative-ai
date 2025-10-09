#!/usr/bin/env python3
"""
Test script for MCP integration with LLM client.
"""
import asyncio
import os
import sys

from src.utils.config import settings

# Add src to path
sys.path.insert(0, 'src')

from src.agent.llm_client import generate_alert_email
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def test_mcp_integration():
    """Test the MCP integration with a mock alert scenario."""
    
    # Test scenario: insufficient variants
    campaign_id = "winter-warmth-uk-2025"
    issue_type = "insufficient_variants"
    context = {
        "product_id": "prod_thermal_socks_002",
        "variant_count": 2,
        "required_count": 3,
        "elapsed_time": "1 day, 1:41:54"
    }
    
    logger.info("Testing MCP integration...")
    logger.info(f"Campaign: {campaign_id}")
    logger.info(f"Issue: {issue_type}")
    logger.info(f"Context: {context}")
    
    try:
        # This should use MCP tools to gather campaign data
        email_content = await generate_alert_email(
            campaign_id=campaign_id,
            issue_type=issue_type,
            context=context
        )
        
        logger.info("✅ MCP integration test successful!")
        logger.info("Generated email content:")
        print("=" * 80)
        print(email_content)
        print("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ MCP integration test failed: {e}")
        logger.exception("Full error details:")
        return False


if __name__ == "__main__":
    # Set environment variables for testing
    os.environ.setdefault("AGENT_LLM_PROVIDER", "google")
    os.environ.setdefault("MCP_SERVER_URL", "http://localhost:8001")
    
    # Check if OpenAI API key is set
    if not (getattr(settings, "GOOGLE_AI_API_KEY", None) or "").strip():
       raise ValueError("GOOGLE_AI_API_KEY not set for Google provider")
    
    success = asyncio.run(test_mcp_integration())
    sys.exit(0 if success else 1)