"""Custom exceptions for MCP operations."""

from typing import Optional


class MCPError(Exception):
    """Base exception for all MCP-related errors."""

    def __init__(self, message: str, server_name: Optional[str] = None):
        super().__init__(message)
        self.server_name = server_name


class MCPConnectionError(MCPError):
    """Raised when connection to MCP server fails."""

    pass


class MCPServerError(MCPError):
    """Raised when MCP server encounters an error."""

    pass


class MCPToolError(MCPError):
    """Raised when tool execution fails."""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        server_name: Optional[str] = None,
    ):
        super().__init__(message, server_name)
        self.tool_name = tool_name


class MCPConfigurationError(MCPError):
    """Raised when server configuration is invalid."""

    pass


class MCPTimeoutError(MCPError):
    """Raised when MCP operation times out."""

    pass
