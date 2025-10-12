"""
FastAPI-MCP server for Creative Automation Agent.

Uses fastapi-mcp to automatically convert FastAPI endpoints to MCP tools.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP

from src.mcp.endpoints import router
from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Creative Automation MCP Server",
    description="Model Context Protocol server for campaign data access using fastapi-mcp",
    version="1.0.0",
)

origins_raw = getattr(settings, "MCP_CORS_ALLOW_ORIGINS", "*")
origins_list = (
    [o.strip() for o in origins_raw.split(",") if o.strip()]
    if isinstance(origins_raw, str)
    else ["*"]
)

# If wildcard is present, disable credentials to avoid ValueError
contains_wildcard = any(o == "*" for o in origins_list)
cors_allow_credentials = not contains_wildcard
cors_allow_origins = ["*"] if contains_wildcard else origins_list

if contains_wildcard:
    logger.info(
        "CORS configured with wildcard origins; disabling credentials for safety"
    )
else:
    logger.info(f"CORS allowed origins: {cors_allow_origins}; credentials enabled")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mcp-server"}


mcp = FastApiMCP(app)
mcp.mount_http()

logger.info("MCP server initialized with fastapi-mcp")
logger.info(
    "Available MCP tools: get_campaign_details, get_product_variants, get_recent_errors, get_alert_history, analyze_root_cause"
)

if __name__ == "__main__":
    import uvicorn

    from src.utils.config import settings

    host = getattr(settings, "MCP_SERVER_HOST", "0.0.0.0")
    port = getattr(settings, "MCP_SERVER_PORT", 8001)

    logger.info(f"Starting MCP server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
