"""
LLM client for generating human-readable alerts using OpenAI Responses API.
"""

from openai import AsyncOpenAI

from src.agent.models import AlertContext
from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a Creative Operations Assistant monitoring an automated ad campaign generation pipeline.

Your role:
- Analyze campaign delays or issues from structured data
- Draft clear, actionable email alerts for stakeholders
- Reference specific campaign details (name, product, timeline)
- Provide estimated time to resolution based on error type
- Suggest concrete next steps for stakeholders
- Use professional, solution-oriented tone

Email Structure:
1. Subject: Brief, specific issue description with campaign name
2. Greeting: Address recipient by role
3. Issue Summary: 2-3 bullet points with key facts
4. Technical Details: Code block with error logs (if applicable)
5. Next Steps: Numbered action items with ETAs
6. Closing: Reassurance + contact information

Tone Guidelines:
- Professional but conversational
- Focus on solutions, not blame
- Use bullet points for clarity
- Include specific timestamps and metrics
- Avoid technical jargon unless necessary

Do NOT:
- Generate overly technical explanations
- Include speculation or assumptions
- Provide generic "contact support" messages
- Use excessive apologies
"""


async def generate_alert_email(context: AlertContext) -> str:
    """
    Generate stakeholder email from structured alert context.

    Args:
        context: AlertContext with campaign and error information

    Returns:
        Formatted email content
    """
    # If no API key configured or provider set to mock, use fallback
    if not settings.OPENAI_API_KEY or getattr(settings, "GENAI_PROVIDER", "") == "mock":
        logger.warning(
            "OPENAI_API_KEY not set or mock provider selected; using mock email content"
        )
        return _generate_mock_email(context)

    # Format context as natural language prompt
    user_prompt = _format_context_prompt(context)

    # Call OpenAI Responses API with graceful fallback on error
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        response = await client.responses.create(
            model=getattr(settings, "AGENT_LLM_MODEL", "gpt-5-mini"),
            input=[
                {
                    "role": "developer",
                    "content": [
                        {"type": "input_text", "text": SYSTEM_PROMPT},
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": user_prompt},
                    ],
                },
            ],
            reasoning={"effort": "medium"},
            text={"verbosity": "medium"},
            max_output_tokens=800,
        )

        # Prefer unified text accessor if available
        email_content = getattr(response, "output_text", None)
        if not email_content:
            # Fallback to choices/message format if SDK version lacks output_text
            try:
                email_content = response.choices[0].message.content
            except Exception:
                # Last-resort string conversion
                email_content = str(response)

        logger.info(
            f"Generated alert email: {len(email_content)} chars, "
            f"tokens={getattr(getattr(response, 'usage', None), 'total_tokens', 'n/a')}"
        )

        return email_content

    except Exception as e:
        logger.warning(
            f"Responses API failed ({e}); returning mock email content instead"
        )
        return _generate_mock_email(context)


def _format_context_prompt(context: AlertContext) -> str:
    """Convert structured context to natural language prompt"""

    campaign = context.campaign

    # Format product status
    products_text = "\n".join(
        [
            f"- {p.product_name or p.product_id}: {p.variant_count}/3 variants "
            f"(generated: {', '.join(p.ratios_generated or ['none'])}, "
            f"missing: {', '.join(p.ratios_missing or ['none'])})"
            for p in campaign.products
        ]
    )

    # Format errors
    if context.errors:
        errors_text = "\n".join(
            [f"- [{e.timestamp}] {e.type}: {e.message}" for e in context.errors]
        )
    else:
        errors_text = "- No recent errors logged"

    prompt = f"""
Campaign Issue Detected:

Campaign: {campaign.campaign_name} (ID: {campaign.campaign_id})
Market: {campaign.target_market}
Audience: {campaign.target_audience or 'Not specified'}
Issue Type: {context.issue_type.replace('_', ' ').title()}
Elapsed Time: {campaign.elapsed_time}

Products Status:
{products_text}

Recent Errors:
{errors_text}

Root Cause Analysis:
{context.root_cause}

Additional Context:
{context.context}

Please draft a professional email alert for the Creative Lead explaining this delay and providing clear next steps.
Include:
- Brief subject line
- Polite greeting
- 2-3 bullet point summary
- Technical details (if relevant)
- Numbered next steps with ETAs
- Reassuring closing
"""

    return prompt


def _generate_mock_email(context: AlertContext) -> str:
    """Generate a simple deterministic email without calling external APIs.

    Used when OPENAI_API_KEY is not configured or mock provider is selected.
    """
    campaign = context.campaign
    lines = [
        f"Subject: {context.issue_type.replace('_', ' ').title()} – {campaign.campaign_name}",
        "",
        "Hi Creative Lead,",
        "",
        f"We detected an issue for campaign '{campaign.campaign_name}' (ID: {campaign.campaign_id}).",
        f"- Market: {campaign.target_market}",
        f"- Elapsed: {campaign.elapsed_time}",
    ]

    if context.issue_type == "insufficient_variants":
        lines.append("- Not all required variants are generated yet.")
    elif context.issue_type == "repeated_failures":
        lines.append(f"- {len(context.errors)} recent errors observed.")

    if context.errors:
        lines.append("")
        lines.append("Recent errors:")
        for e in context.errors:
            lines.append(f"- [{e.timestamp}] {e.type}: {e.message}")

    lines.extend(
        [
            "",
            "Next steps:",
            "1) The automation will continue generation attempts.",
            "2) If this persists for 30 minutes, we will escalate.",
            "",
            "Best regards,",
            "Creative Automation Agent",
        ]
    )

    return "\n".join(lines)
