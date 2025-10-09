"""
Agentic monitoring system for creative automation pipeline.

This module provides AI-driven monitoring and alerting for campaign
generation, detecting issues and communicating with stakeholders.
"""

from src.agent.context import build_alert_context
from src.agent.llm_client import generate_alert_email
from src.agent.monitor import CampaignMonitorAgent

__all__ = [
    "CampaignMonitorAgent",
    "build_alert_context",
    "generate_alert_email",
]

