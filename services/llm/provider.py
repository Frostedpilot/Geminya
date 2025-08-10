"""Abstract base provider interface for LLM services."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
import logging

from mcp.types import Tool
from .types import LLMRequest, LLMResponse, ModelInfo, ProviderConfig
from .exceptions import LLMError


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(
        self,
        name: str,
        config: Union[ProviderConfig, Dict[str, Any]],
        logger: logging.Logger,
    ):
        self.name = name
        self.config = config
        self.logger = logger
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider (setup clients, validate config, etc.)."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup provider resources."""
        pass

    @abstractmethod
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate a response using the provider's models."""
        pass

    @abstractmethod
    def get_models(self) -> Dict[str, ModelInfo]:
        """Get available models from this provider."""
        pass

    @abstractmethod
    def get_model_info(self, model_id: str) -> ModelInfo:
        """Get detailed information about a specific model."""
        pass

    @abstractmethod
    def supports_model(self, model_id: str) -> bool:
        """Check if this provider supports the given model."""
        pass

    @abstractmethod
    def convert_mcp_tools(self, mcp_tools: List[Tool]) -> List[Dict[str, Any]]:
        """Convert MCP Tool objects to provider-specific format."""
        pass

    def is_initialized(self) -> bool:
        """Check if the provider is initialized."""
        return self._initialized

    def _set_initialized(self, value: bool = True) -> None:
        """Set the initialization status."""
        self._initialized = value
