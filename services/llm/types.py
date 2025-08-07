"""Data types and models for the LLM service."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class LLMRequest:
    """Request object for LLM generation."""

    messages: List[Dict[str, str]]
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    provider_specific: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Response object from LLM generation."""

    content: str
    model_used: str
    provider_used: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    usage: Optional[Dict[str, int]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelInfo:
    """Information about an available model."""

    id: str
    name: str
    provider: str
    context_length: int
    supports_tools: bool = False
    cost_per_million_tokens: Optional[Dict[str, float]] = None
    description: Optional[str] = None


@dataclass
class ToolCall:
    """Represents a tool call request from the model."""

    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    """Represents the result of a tool call."""

    tool_call_id: str
    content: str
    error: Optional[str] = None
