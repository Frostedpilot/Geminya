"""MCP (Model Context Protocol) service package for Geminya bot.

This package provides a clean, modular interface for working with MCP servers,
including client management, tool execution, and server lifecycle management.
"""

from .client import MCPClient
from .manager import MCPClientManager
from .exceptions import MCPError, MCPConnectionError, MCPToolError, MCPServerError
from .types import ToolCall, ToolResult, ServerConfig, MCPResponse
from .registry import MCPServerRegistry
from .health import MCPHealthMonitor, HealthStatus, SystemHealth, HealthCheck

__all__ = [
    "MCPClient",
    "MCPClientManager",
    "MCPError",
    "MCPConnectionError",
    "MCPToolError",
    "MCPServerError",
    "ToolCall",
    "ToolResult",
    "ServerConfig",
    "MCPResponse",
    "MCPServerRegistry",
    "MCPHealthMonitor",
    "HealthStatus",
    "SystemHealth",
    "HealthCheck",
]
