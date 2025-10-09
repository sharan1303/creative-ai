"""
FastAPI-MCP server for Creative Automation Agent.

Uses fastapi-mcp to automatically convert FastAPI endpoints to MCP tools.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP

from src.mcp.endpoints import router
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Creative Automation MCP Server",
    description="Model Context Protocol server for campaign data access using fastapi-mcp",
    version="1.0.0",
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include MCP endpoints
app.include_router(router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mcp-server"}


# Initialize FastAPI-MCP
mcp = FastApiMCP(app)

# Mount the MCP server using HTTP transport so clients can POST to /mcp
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
