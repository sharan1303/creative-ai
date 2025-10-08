"""
Alert delivery system for email and Slack notifications.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx

from src.agent.models import AlertContext
from src.db.database import Campaign, get_db
from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def deliver_alert(email_content: str, campaign: Campaign, context: AlertContext):
    """
    Deliver alert via multiple channels.

    Args:
        email_content: Generated email body
        campaign: Campaign record
        context: Alert context
    """
    db = get_db()

    # Determine recipient
    recipient = _get_stakeholder_email(campaign.target_market)

    # 1. Send email (if configured)
    if hasattr(settings, "SMTP_HOST") and settings.SMTP_HOST:
        try:
            await _send_email(
                to=recipient,
                subject=f"⚠️ Asset Generation Delay – {campaign.name or campaign.id}",
                body=email_content,
                priority="medium",
            )
            logger.info(f"Email sent to {recipient}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
    else:
        logger.warning("SMTP not configured, skipping email delivery")
        logger.info(f"Would send email to: {recipient}")
        logger.debug(f"Email content:\n{email_content}")

    # 2. Post to Slack (optional)
    slack_url = getattr(settings, "SLACK_WEBHOOK_URL", None)
    if slack_url:
        try:
            await _post_to_slack(
                webhook_url=slack_url,
                channel="#creative-ops",
                message=f"🚨 Campaign alert generated for {campaign.name or campaign.id}",
                attachment=email_content[:500],  # Truncate for preview
            )
            logger.info("Slack notification sent")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")

    # 3. Log to audit trail
    db.create_alert(
        campaign_id=campaign.id,
        issue_type=context.issue_type,
        email_content=email_content,
        recipient=recipient,
    )

    # 4. Update campaign status
    if campaign.status != "alerted":
        db.update_campaign_status(campaign.id, "alerted")


def _get_stakeholder_email(market: Optional[str]) -> str:
    """
    Get stakeholder email based on market.

    Args:
        market: Target market identifier

    Returns:
        Stakeholder email address
    """
    # In production, this would look up from a database or config
    # For demo, use default or configured email
    default_email = getattr(settings, "STAKEHOLDER_EMAIL", "creative-lead@company.com")

    # Market-specific overrides could be added here
    market_emails = {
        "EU": "eu-creative-lead@company.com",
        "US": "us-creative-lead@company.com",
        "APAC": "apac-creative-lead@company.com",
    }

    return market_emails.get(market, default_email)


async def _send_email(to: str, subject: str, body: str, priority: str = "normal"):
    """
    Send email via SMTP.

    Args:
        to: Recipient email
        subject: Email subject
        body: Email body (text or HTML)
        priority: Email priority (low, normal, high)
    """
    smtp_host = settings.SMTP_HOST
    smtp_port = getattr(settings, "SMTP_PORT", 587)
    smtp_user = getattr(settings, "SMTP_USER", None)
    smtp_password = getattr(settings, "SMTP_PASSWORD", None)
    from_email = getattr(settings, "SMTP_FROM", "noreply@company.com")

    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to
    msg["X-Priority"] = {"low": "5", "normal": "3", "high": "1"}.get(priority, "3")

    # Add body
    part = MIMEText(body, "plain")
    msg.attach(part)

    # Send email
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        server.send_message(msg)

    logger.debug(f"Email sent to {to} via {smtp_host}:{smtp_port}")


async def _post_to_slack(
    webhook_url: str, channel: str, message: str, attachment: Optional[str] = None
):
    """
    Post notification to Slack via webhook.

    Args:
        webhook_url: Slack webhook URL
        channel: Target channel
        message: Main message text
        attachment: Optional attachment text
    """
    payload = {
        "channel": channel,
        "username": "Creative Automation Agent",
        "text": message,
        "icon_emoji": ":robot_face:",
    }

    if attachment:
        payload["attachments"] = [{"text": attachment, "color": "warning"}]

    async with httpx.AsyncClient() as client:
        response = await client.post(webhook_url, json=payload, timeout=10.0)
        response.raise_for_status()

    logger.debug(f"Slack notification posted to {channel}")
