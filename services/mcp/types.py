"""Type definitions for MCP components."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class ServerStatus(Enum):
    """Enumeration of possible server states."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class ServerConfig:
    """Configuration for an MCP server."""

    name: str
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None
    blacklist: Optional[List[str]] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5

    def __post_init__(self):
        if self.blacklist is None:
            self.blacklist = []


@dataclass
class ToolCall:
    """Represents a tool call request."""

    id: str
    name: str
    arguments: Dict[str, Any]
    server_name: Optional[str] = None

    @classmethod
    def from_openai_tool_call(
        cls, tool_call, server_name: Optional[str] = None
    ) -> "ToolCall":
        """Create ToolCall from OpenAI tool call format."""
        return cls(
            id=getattr(tool_call, "id", f"tool_{id(tool_call)}"),
            name=tool_call.function.name,
            arguments=(
                tool_call.function.arguments
                if isinstance(tool_call.function.arguments, dict)
                else {}
            ),
            server_name=server_name,
        )


@dataclass
class ToolResult:
    """Represents the result of a tool execution."""

    tool_call_id: str
    name: str
    content: str
    success: bool = True
    error: Optional[str] = None
    execution_time: Optional[float] = None
    server_name: Optional[str] = None

    def to_message_dict(self) -> Dict[str, Any]:
        """Convert to OpenAI message format."""
        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "name": self.name,
            "content": self.content,
        }


@dataclass
class ServerInfo:
    """Information about an MCP server."""

    name: str
    status: ServerStatus
    tool_count: int
    blacklisted_tools: List[str]
    last_error: Optional[str] = None
    connection_time: Optional[float] = None
    uptime: Optional[float] = None


@dataclass
class MCPResponse:
    """Response from MCP processing."""

    content: str
    tool_calls_made: int
    iterations: int
    execution_time: float
    servers_used: List[str]
    success: bool = True
    error: Optional[str] = None
