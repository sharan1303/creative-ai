"""
Pydantic models for MCP server requests and responses.
"""
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class MCPRequest(BaseModel):
    """Base MCP request model"""
    
    jsonrpc: str = "2.0"
    id: Union[str, int]
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """Base MCP response model"""
    
    jsonrpc: str = "2.0"
    id: Union[str, int]
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPError(BaseModel):
    """MCP error details"""
    
    code: int
    message: str
    data: Optional[Any] = None


class ToolDefinition(BaseModel):
    """MCP tool definition"""
    
    name: str
    description: str
    inputSchema: Dict[str, Any]


class ToolResult(BaseModel):
    """MCP tool execution result"""
    
    content: List[Dict[str, Any]]
    isError: bool = False


class CampaignDetails(BaseModel):
    """Campaign details response"""
    
    campaign_id: str
    campaign_name: str
    status: str
    created_at: str
    elapsed_time: str
    target_market: str
    target_audience: Optional[str] = None
    campaign_message: Optional[str] = None
    product_ids: List[str]


class ProductVariants(BaseModel):
    """Product variants response"""
    
    product_id: str
    product_name: Optional[str] = None
    variant_count: int
    ratios_generated: List[str]
    ratios_missing: List[str]
    variants: List[Dict[str, Any]]


class ErrorLogEntry(BaseModel):
    """Error log entry"""
    
    timestamp: str
    error_type: str
    error_message: str
    campaign_id: str
    product_id: Optional[str] = None


class AlertHistoryEntry(BaseModel):
    """Alert history entry"""
    
    alert_id: str
    campaign_id: str
    issue_type: str
    created_at: str
    recipient: str
    resolved: bool = False
