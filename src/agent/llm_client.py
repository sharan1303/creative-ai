"""
LLM client for generating human-readable alerts (OpenAI or Google Gemini).

Provider/model are configured via environment:
- AGENT_LLM_PROVIDER: "openai" | "google"
- AGENT_LLM_MODEL: optional explicit model override
- AGENT_LLM_MODEL_OPENAI / AGENT_LLM_MODEL_GOOGLE: provider defaults
"""

from google import genai
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
    # Resolve provider and model
    provider = (getattr(settings, "AGENT_LLM_PROVIDER", "openai") or "openai").lower()
    model = _resolve_agent_model(provider)

    # Format context as natural language prompt
    user_prompt = _format_context_prompt(context)

    # Route to provider-specific implementation
    try:
        if provider == "openai":
            # Require key
            if not (settings.OPENAI_API_KEY or "").strip():
                raise ValueError("OPENAI_API_KEY not set for OpenAI provider")
            return await _generate_with_openai(user_prompt=user_prompt, model=model)

        if provider == "google":
            if not (getattr(settings, "GOOGLE_AI_API_KEY", None) or "").strip():
                raise ValueError("GOOGLE_AI_API_KEY not set for Google provider")
            return await _generate_with_google(user_prompt=user_prompt, model=model)

        logger.warning(f"Unknown AGENT_LLM_PROVIDER '{provider}'")
        raise ValueError(f"Unknown AGENT_LLM_PROVIDER '{provider}'")
    except Exception as e:
        logger.warning(f"LLM generation failed: {e}", exc_info=True)
        raise


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


def _resolve_agent_model(provider: str) -> str:
    """Resolve the model to use for the agent based on provider and settings.

    Order:
    1) AGENT_LLM_MODEL if provided
    2) Provider-specific default
    """
    explicit = getattr(settings, "AGENT_LLM_MODEL", None)
    if explicit and explicit.strip():
        return explicit.strip()
    if provider == "google":
        return getattr(settings, "AGENT_LLM_MODEL_GOOGLE", "gemini-2.5-flash")
    # default to OpenAI
    return getattr(settings, "AGENT_LLM_MODEL_OPENAI", "gpt-5-nano")


async def _generate_with_openai(*, user_prompt: str, model: str) -> str:
    """Call OpenAI Responses API to generate the alert email text."""
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    response = await client.responses.create(
        model=model,
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

    email_content = getattr(response, "output_text", None)
    if not email_content:
        try:
            email_content = response.choices[0].message.content
        except Exception:
            email_content = str(response)

    logger.info(
        f"Generated alert email (openai/{model}): {len(email_content)} chars, "
        f"tokens={getattr(getattr(response, 'usage', None), 'total_tokens', 'n/a')}"
    )
    return email_content


async def _generate_with_google(*, user_prompt: str, model: str) -> str:
    """Generate alert text using the official google-genai SDK (async)."""
    api_key = (getattr(settings, "GOOGLE_AI_API_KEY", "") or "").strip()
    if not api_key:
        raise ValueError("GOOGLE_AI_API_KEY is required for Google provider")

    # Use async client from google-genai; ensure cleanup after request
    client = genai.Client(api_key=api_key)
    aclient = client.aio
    try:
        response = await aclient.models.generate_content(
            model=model,
            contents=f"{SYSTEM_PROMPT}\n\n{user_prompt}",
        )
    finally:
        await aclient.aclose()

    text = getattr(response, "text", None) or str(response)
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Gemini SDK returned empty text")

    logger.info(f"Generated alert email (google/{model}): {len(text)} chars")
    return text
