"""OpenRouter provider implementation."""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI

from mcp.types import Tool
from ..provider import LLMProvider
from ..types import LLMRequest, LLMResponse, ModelInfo, ToolCall
from ..exceptions import ProviderError, ModelNotFoundError, QuotaExceededError


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider using OpenAI-compatible API."""

    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        super().__init__("openrouter", config, logger)
        self.client: Optional[AsyncOpenAI] = None
        self.available_models: Dict[str, ModelInfo] = {}

    async def initialize(self) -> None:
        """Initialize the OpenRouter provider."""
        try:
            api_key = self.config.get("api_key")
            if not api_key:
                raise ProviderError("openrouter", "API key not provided")

            base_url = self.config.get("base_url", "https://openrouter.ai/api/v1")

            self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)

            # Load available models from config
            self._load_models()

            self._set_initialized(True)
            self.logger.info("OpenRouter provider initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize OpenRouter provider: {e}")
            raise ProviderError("openrouter", f"Initialization failed: {str(e)}", e)

    async def cleanup(self) -> None:
        """Cleanup OpenRouter provider resources."""
        if self.client:
            await self.client.close()
            self.client = None

        self._set_initialized(False)
        self.logger.info("OpenRouter provider cleanup completed")

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate a response using OpenRouter."""
        if not self.is_initialized() or not self.client:
            raise ProviderError("openrouter", "Provider not initialized")

        if not self.supports_model(request.model):
            raise ModelNotFoundError(request.model, "openrouter")

        try:
            # Prepare the request
            api_request = {
                "model": request.model,
                "messages": request.messages,
                "temperature": request.temperature,
            }

            # Add optional parameters
            if request.max_tokens:
                api_request["max_tokens"] = request.max_tokens

            # Add tools if provided
            if request.tools:
                api_request["tools"] = request.tools

            # Add provider-specific parameters
            api_request.update(request.provider_specific)

            self.logger.debug(
                f"Making OpenRouter API request for model {request.model}"
            )

            # Make the API call
            response = await self.client.chat.completions.create(**api_request)

            if not response.choices or not response.choices[0].message:
                raise ProviderError("openrouter", "Empty response from API")

            choice = response.choices[0]
            message = choice.message

            # Extract content
            content = message.content or ""

            # Extract tool calls if present
            tool_calls = None
            if message.tool_calls:
                tool_calls = []
                for tool_call in message.tool_calls:
                    tool_calls.append(
                        {
                            "id": tool_call.id,
                            "type": tool_call.type,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                    )

            # Extract usage information
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            self.logger.info(f"Generated OpenRouter response ({len(content)} chars)")

            return LLMResponse(
                content=content,
                model_used=request.model,
                provider_used=self.name,
                tool_calls=tool_calls,
                usage=usage,
                metadata={
                    "finish_reason": choice.finish_reason,
                    "response_id": response.id,
                },
            )

        except Exception as e:
            if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                raise QuotaExceededError("openrouter", str(e))

            self.logger.error(f"Error generating OpenRouter response: {e}")
            raise ProviderError("openrouter", f"Generation failed: {str(e)}", e)

    def get_models(self) -> Dict[str, ModelInfo]:
        """Get available models from OpenRouter."""
        return self.available_models.copy()

    def supports_model(self, model_id: str) -> bool:
        """Check if OpenRouter supports the given model."""
        return model_id in self.available_models

    def convert_mcp_tools(self, mcp_tools: List[Tool]) -> List[Dict[str, Any]]:
        """Convert MCP Tool objects to OpenAI format for OpenRouter."""
        tools = []

        for tool in mcp_tools:
            try:
                # Extract properties and required fields safely
                properties = {}
                required = []

                if hasattr(tool, "inputSchema") and tool.inputSchema:
                    if "properties" in tool.inputSchema:
                        properties = tool.inputSchema["properties"]
                    if "required" in tool.inputSchema:
                        required_field = tool.inputSchema["required"]
                        # Handle both list and string cases
                        if isinstance(required_field, list):
                            required = required_field
                        elif isinstance(required_field, str):
                            required = [required_field]
                        else:
                            required = []

                converted_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": required,
                        },
                    },
                }
                tools.append(converted_tool)

            except Exception:
                # Fallback to basic tool format
                return {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": getattr(tool, "description", ""),
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                    },
                }

        self.logger.debug(f"Converted {len(tools)} MCP tools to OpenAI format")
        return tools

    def _load_models(self) -> None:
        """Load available models from configuration."""
        models_config = self.config.get("models", {})

        for display_name, model_id in models_config.items():
            self.available_models[model_id] = ModelInfo(
                id=model_id,
                name=display_name,
                provider=self.name,
                context_length=self._get_context_length(model_id),
                supports_tools=True,  # OpenRouter generally supports tools
                description=f"OpenRouter model: {display_name}",
            )

        self.logger.info(f"Loaded {len(self.available_models)} models for OpenRouter")

    def _get_context_length(self, model_id: str) -> int:
        """Get context length for a model (approximate)."""
        # Common context lengths - this could be enhanced with actual API data
        if "gpt-4" in model_id.lower():
            return 128000
        elif "gpt-3.5" in model_id.lower():
            return 16385
        elif "claude" in model_id.lower():
            return 200000
        elif "gemini" in model_id.lower():
            return 128000
        else:
            return 4096  # Conservative default
