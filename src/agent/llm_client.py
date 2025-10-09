"""
LLM client for generating human-readable alerts with MCP tool support.

Provider/model are configured via environment:
- AGENT_LLM_PROVIDER: "openai" | "google"
- AGENT_LLM_MODEL: optional explicit model override
- AGENT_LLM_MODEL_OPENAI / AGENT_LLM_MODEL_GOOGLE: provider defaults
- MCP_SERVER_URL: URL for MCP server with campaign data tools
"""

import json
from typing import Any, Dict, List

import httpx
from google import genai
from openai import AsyncOpenAI

from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a Creative Operations Assistant monitoring an automated ad campaign generation pipeline.

Your role:
- Analyze campaign delays or issues using available tools
- Draft clear, actionable email alerts for stakeholders
- Reference specific campaign details gathered from tools
- Provide estimated time to resolution based on error patterns
- Suggest concrete next steps for stakeholders
- Use professional, solution-oriented tone

Available Tools:
- get_campaign_details: Get campaign metadata, status, timeline
- get_product_variants: Query variant counts and aspect ratios
- get_recent_errors: Retrieve filtered error logs
- get_alert_history: Check previous alerts to prevent spam
- analyze_root_cause: Perform error pattern analysis

Email Structure:
1. Subject: Brief, specific issue description with campaign name
2. Greeting: Address recipient by role
3. Issue Summary: 2-3 bullet points with key facts
4. Technical Details: Code block with error logs (if applicable)
5. Next Steps: Numbered action items with ETAs
6. Closing: Reassurance + contact information

Process:
1. Use get_campaign_details to understand the campaign
2. Use get_product_variants to check variant status
3. Use get_recent_errors and analyze_root_cause for technical context
4. Use get_alert_history to avoid duplicate notifications
5. Draft a professional email with gathered information

Tone Guidelines:
- Professional but conversational
- Focus on solutions, not blame
- Use bullet points for clarity
- Include specific timestamps and metrics
- Avoid technical jargon unless necessary
- Don't generate overly technical explanations
- Include concrete next steps with ETAs
"""


async def generate_alert_email(
    campaign_id: str, issue_type: str, context: Dict[str, Any]
) -> str:
    """
    Generate stakeholder email using MCP tools for dynamic context gathering.

    Args:
        campaign_id: Campaign identifier
        issue_type: Type of issue detected
        context: Initial context from monitoring

    Returns:
        Formatted email content
    """
    # Resolve provider and model
    provider = (getattr(settings, "AGENT_LLM_PROVIDER", "openai") or "openai").lower()
    model = _resolve_agent_model(provider)

    # Create initial prompt with issue context
    user_prompt = f"""
Campaign Issue Detected:

Campaign ID: {campaign_id}
Issue Type: {issue_type.replace('_', ' ').title()}
Initial Context: {json.dumps(context, indent=2)}

Please investigate this campaign issue and draft a professional email alert for the Creative Lead.

Use the available tools to gather comprehensive information about:
1. Campaign details and timeline
2. Product variant status
3. Recent errors and root cause
4. Alert history to avoid duplicates

Then draft a clear, actionable email explaining the delay and providing next steps.
"""

    # Route to provider-specific implementation
    try:
        if provider == "openai":
            # Require key
            if not (settings.OPENAI_API_KEY or "").strip():
                raise ValueError("OPENAI_API_KEY not set for OpenAI provider")
            return await _generate_with_openai_mcp(user_prompt=user_prompt, model=model)

        if provider == "google":
            if not (getattr(settings, "GOOGLE_AI_API_KEY", None) or "").strip():
                raise ValueError("GOOGLE_AI_API_KEY not set for Google provider")
            return await _generate_with_google_mcp(user_prompt=user_prompt, model=model)

        logger.warning(f"Unknown AGENT_LLM_PROVIDER '{provider}'")
        raise ValueError(f"Unknown AGENT_LLM_PROVIDER '{provider}'")
    except Exception as e:
        logger.warning(f"LLM generation failed: {e}", exc_info=True)
        # Fallback to basic alert
        return _generate_fallback_alert(campaign_id, issue_type, context)


async def _get_mcp_tools() -> List[Dict[str, Any]]:
    """Get tool definitions by parsing FastAPI OpenAPI schema (transport-agnostic)."""
    try:
        mcp_server_url = getattr(settings, "MCP_SERVER_URL", "http://localhost:8001")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{mcp_server_url}/openapi.json")
            response.raise_for_status()

            openapi = response.json()
            components = openapi.get("components", {}).get("schemas", {})

            def resolve_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
                ref = schema.get("$ref")
                if ref and ref.startswith("#/components/schemas/"):
                    name = ref.split("/")[-1]
                    return components.get(name, {"type": "object"})
                return schema

            tools: List[Dict[str, Any]] = []
            for path, methods in openapi.get("paths", {}).items():
                if not path.startswith("/mcp/tools/"):
                    continue
                post_op = methods.get("post")
                if not post_op:
                    continue
                # Prefer stable tool names based on path segment to avoid
                # auto-generated operationId suffixes
                op_id = path.split("/")[-1]
                description = post_op.get("description") or ""
                req = (
                    post_op.get("requestBody", {})
                    .get("content", {})
                    .get("application/json", {})
                )
                schema = resolve_schema(req.get("schema", {"type": "object"}))
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": op_id,
                            "description": description,
                            "parameters": schema,
                        },
                    }
                )
            if tools:
                return tools
            logger.warning("No MCP tool operations discovered in OpenAPI")
            return _get_fallback_tools()

    except Exception as e:
        logger.error(f"Failed to parse MCP tools from OpenAPI: {e}")
        return _get_fallback_tools()


async def _get_mcp_tools_for_gemini() -> List[Dict[str, Any]]:
    """Get tool definitions for Gemini by parsing FastAPI OpenAPI schema."""
    try:
        mcp_server_url = getattr(settings, "MCP_SERVER_URL", "http://localhost:8001")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{mcp_server_url}/openapi.json")
            response.raise_for_status()

            openapi = response.json()
            components = openapi.get("components", {}).get("schemas", {})

            def resolve_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
                ref = schema.get("$ref")
                if ref and ref.startswith("#/components/schemas/"):
                    name = ref.split("/")[-1]
                    return components.get(name, {"type": "object"})
                return schema

            functions: List[Dict[str, Any]] = []
            for path, methods in openapi.get("paths", {}).items():
                if not path.startswith("/mcp/tools/"):
                    continue
                post_op = methods.get("post")
                if not post_op:
                    continue
                # Prefer stable tool names based on path segment
                op_id = path.split("/")[-1]
                description = post_op.get("description") or ""
                req = (
                    post_op.get("requestBody", {})
                    .get("content", {})
                    .get("application/json", {})
                )
                schema = resolve_schema(req.get("schema", {"type": "object"}))
                functions.append(
                    {
                        "name": op_id,
                        "description": description,
                        "parameters": schema,
                    }
                )
            if functions:
                return [{"function_declarations": functions}]
            logger.warning("No MCP tool operations discovered in OpenAPI for Gemini")
            # Fallback to static tools
            fallback = _get_fallback_tools()
            return [
                {
                    "function_declarations": [t["function"] for t in fallback],
                }
            ]

    except Exception as e:
        logger.error(f"Failed to parse MCP tools for Gemini from OpenAPI: {e}")
        fallback = _get_fallback_tools()
        return [
            {
                "function_declarations": [t["function"] for t in fallback],
            }
        ]


async def _execute_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Execute tool by calling the FastAPI endpoint directly.

    Using direct HTTP avoids transport differences (SSE vs HTTP) and JSON-RPC.
    """
    return await _execute_direct_endpoint(tool_name, arguments)


async def _execute_direct_endpoint(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Execute tool by calling FastAPI endpoint directly"""
    try:
        mcp_server_url = getattr(settings, "MCP_SERVER_URL", "http://localhost:8001")

        async with httpx.AsyncClient(timeout=30.0) as client:
            endpoint_url = f"{mcp_server_url}/mcp/tools/{tool_name}"
            response = await client.post(endpoint_url, json=arguments)
            response.raise_for_status()

            result = response.json()

            # Format result as readable text
            if isinstance(result, list):
                if not result:
                    return f"No data returned from {tool_name}"
                # Format list results
                if tool_name == "get_product_variants":
                    return _format_product_variants(result)
                elif tool_name == "get_recent_errors":
                    return _format_error_logs(result)
                elif tool_name == "get_alert_history":
                    return _format_alert_history(result)
                else:
                    return json.dumps(result, indent=2)
            elif isinstance(result, dict):
                if tool_name == "get_campaign_details":
                    return _format_campaign_details(result)
                elif tool_name == "analyze_root_cause":
                    return _format_root_cause_analysis(result)
                else:
                    return json.dumps(result, indent=2)
            else:
                return str(result)

    except Exception as e:
        logger.error(f"Direct endpoint call failed for {tool_name}: {e}")
        return f"Error executing {tool_name}: {str(e)}"


def _get_fallback_tools() -> List[Dict[str, Any]]:
    """Fallback tool definitions if MCP server is unavailable"""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_campaign_details",
                "description": "Get campaign metadata, status, timeline, and product list",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "Campaign identifier",
                        }
                    },
                    "required": ["campaign_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_product_variants",
                "description": "Get variant counts and aspect ratios for campaign products",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "Campaign identifier",
                        },
                        "product_id": {
                            "type": "string",
                            "description": "Optional specific product ID",
                        },
                    },
                    "required": ["campaign_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_recent_errors",
                "description": "Get recent error logs with filtering options",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "Campaign identifier",
                        },
                        "minutes": {
                            "type": "integer",
                            "description": "Look back window in minutes",
                            "default": 30,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum errors to return",
                            "default": 10,
                        },
                    },
                    "required": ["campaign_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_alert_history",
                "description": "Get previous alerts to prevent duplicate notifications",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "Campaign identifier",
                        },
                        "hours": {
                            "type": "integer",
                            "description": "Look back window in hours",
                            "default": 24,
                        },
                    },
                    "required": ["campaign_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_root_cause",
                "description": "Perform error pattern analysis to identify root causes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "Campaign identifier",
                        }
                    },
                    "required": ["campaign_id"],
                },
            },
        },
    ]


def _format_campaign_details(data: dict) -> str:
    """Format campaign details for LLM consumption"""
    return f"""Campaign Details:
- Name: {data.get('campaign_name', 'N/A')}
- Status: {data.get('status', 'N/A')}
- Created: {data.get('created_at', 'N/A')}
- Elapsed Time: {data.get('elapsed_time', 'N/A')}
- Target Market: {data.get('target_market', 'N/A')}
- Target Audience: {data.get('target_audience', 'N/A')}
- Campaign Message: {data.get('campaign_message', 'N/A')}
- Products: {', '.join(data.get('product_ids', []))}"""


def _format_product_variants(data: list) -> str:
    """Format product variants for LLM consumption"""
    if not data:
        return "No product variants found"

    lines = ["Product Variants:"]
    for product in data:
        name = product.get("product_name") or product.get("product_id", "Unknown")
        count = product.get("variant_count", 0)
        generated = ", ".join(product.get("ratios_generated", []))
        missing = ", ".join(product.get("ratios_missing", []))
        lines.append(
            f"- {name}: {count}/3 variants (generated: {generated or 'none'}, missing: {missing or 'none'})"
        )

    return "\n".join(lines)


def _format_error_logs(data: list) -> str:
    """Format error logs for LLM consumption"""
    if not data:
        return "No recent errors found"

    lines = [f"Recent Errors ({len(data)} found):"]
    for error in data:
        timestamp = error.get("timestamp", "N/A")
        error_type = error.get("error_type", "N/A")
        message = error.get("error_message", "N/A")
        lines.append(f"- [{timestamp}] {error_type}: {message}")

    return "\n".join(lines)


def _format_alert_history(data: list) -> str:
    """Format alert history for LLM consumption"""
    if not data:
        return "No recent alerts found"

    lines = [f"Alert History ({len(data)} found):"]
    for alert in data:
        created = alert.get("created_at", "N/A")
        issue_type = alert.get("issue_type", "N/A")
        recipient = alert.get("recipient", "N/A")
        lines.append(f"- [{created}] {issue_type} -> {recipient}")

    return "\n".join(lines)


def _format_root_cause_analysis(data: dict) -> str:
    """Format root cause analysis for LLM consumption"""
    lines = [data.get("analysis", "No analysis available")]

    patterns = data.get("error_patterns", [])
    if patterns:
        lines.append("\nError Patterns:")
        for pattern in patterns:
            error_type = pattern.get("error_type", "N/A")
            count = pattern.get("count", 0)
            percentage = pattern.get("percentage", 0)
            root_cause = pattern.get("root_cause", "N/A")
            lines.append(
                f"- {error_type}: {count} occurrences ({percentage}%) - {root_cause}"
            )

    timeline = data.get("timeline")
    if timeline:
        lines.append(
            f"\nTimeline: {timeline.get('total_errors', 0)} errors over {timeline.get('duration', 'unknown duration')}"
        )

    return "\n".join(lines)


def _generate_fallback_alert(
    campaign_id: str, issue_type: str, context: Dict[str, Any]
) -> str:
    """Generate basic fallback alert when MCP tools fail"""
    return f"""Subject: ⚠️ Campaign Alert - {campaign_id}

Dear Creative Lead,

We've detected an issue with campaign {campaign_id}:

Issue Type: {issue_type.replace('_', ' ').title()}
Context: {json.dumps(context, indent=2)}

Our automated monitoring system encountered an error while gathering detailed information. Please manually review this campaign in the dashboard.

Next Steps:
1. Check campaign status in the admin panel
2. Review recent error logs
3. Contact the technical team if issues persist

Best regards,
Creative Automation System
"""


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
        return getattr(settings, "AGENT_LLM_MODEL_GOOGLE", "gemini-2.0-flash-exp")
    # default to OpenAI
    return getattr(settings, "AGENT_LLM_MODEL_OPENAI", "gpt-4o-mini")


async def _generate_with_openai_mcp(*, user_prompt: str, model: str) -> str:
    """Generate alert using OpenAI Response API with MCP tool calling."""
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    # Get available MCP tools
    tools = await _get_mcp_tools()

    # Use Response API with tools
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
        tools=tools,
        reasoning={"effort": "medium"},
        text={"verbosity": "medium"},
        max_output_tokens=1500,
    )

    # Handle tool calls if present
    if hasattr(response, "tool_calls") and response.tool_calls:
        # Execute tool calls and continue conversation
        tool_results = []
        for tool_call in response.tool_calls:
            result = await _execute_mcp_tool(
                tool_call.function.name, json.loads(tool_call.function.arguments)
            )
            tool_results.append(result)

        # Continue with tool results
        follow_up_input = [
            {
                "role": "developer",
                "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
            },
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "input_text",
                        "text": "I'll gather the campaign information using the available tools.",
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Tool results: {json.dumps(tool_results, indent=2)}\n\nNow please draft the email alert based on this information.",
                    }
                ],
            },
        ]

        response = await client.responses.create(
            model=model,
            input=follow_up_input,
            reasoning={"effort": "medium"},
            text={"verbosity": "medium"},
            max_output_tokens=1500,
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


async def _generate_with_google_mcp(*, user_prompt: str, model: str) -> str:
    """Generate alert using Google Gemini with MCP function calling."""
    api_key = (getattr(settings, "GOOGLE_AI_API_KEY", "") or "").strip()
    if not api_key:
        raise ValueError("GOOGLE_AI_API_KEY is required for Google provider")

    # Get available tools from MCP server
    tools_schema = await _get_mcp_tools_for_gemini()

    client = genai.Client(api_key=api_key)
    aclient = client.aio

    try:
        # Initial request with tool declarations and AFC enabled
        response = await aclient.models.generate_content(
            model=model,
            contents=f"{SYSTEM_PROMPT}\n\n{user_prompt}",
            config={
                "tools": tools_schema,
                "tool_config": {"function_calling_config": {"mode": "AUTO"}},
            },
        )

        # Collect function call results (if any)
        tool_results: List[Dict[str, Any]] = []
        if getattr(response, "candidates", None):
            candidate = response.candidates[0]
            if getattr(candidate, "content", None) and getattr(
                candidate.content, "parts", None
            ):
                for part in candidate.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        func_name = part.function_call.name
                        func_args = dict(part.function_call.args)
                        result_text = await _execute_mcp_tool(func_name, func_args)
                        tool_results.append({"name": func_name, "result": result_text})

        # If we have tool results, make a follow-up call to draft the email
        if tool_results:
            follow_up = (
                f"{SYSTEM_PROMPT}\n\n{user_prompt}\n\n"
                f"Tool results: {json.dumps(tool_results, indent=2)}\n\n"
                "Now draft the email alert based on this information."
            )
            response2 = await aclient.models.generate_content(
                model=model,
                contents=follow_up,
            )
            text = getattr(response2, "text", None) or str(response2)
        else:
            # No function call; use first response text
            text = getattr(response, "text", None) or str(response)

        if not isinstance(text, str) or not text.strip():
            raise ValueError("Gemini SDK returned empty text")

        logger.info(f"Generated alert email (google/{model}): {len(text)} chars")
        return text

    finally:
        await aclient.aclose()
