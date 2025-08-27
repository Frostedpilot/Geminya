"""OpenRouter provider implementation."""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from openai import AsyncOpenAI

from mcp.types import Tool
from ..provider import LLMProvider
from ..types import (
    LLMRequest,
    LLMResponse,
    ModelInfo,
    ToolCall,
    ProviderConfig,
    ImageRequest,
    ImageResponse,
)
from ..exceptions import (
    ProviderError,
    ModelNotFoundError,
    QuotaExceededError,
    RetriableError,
)


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider using OpenAI-compatible API."""

    def __init__(
        self, config: Union[ProviderConfig, Dict[str, Any]], logger: logging.Logger
    ):
        super().__init__("openrouter", config, logger)
        self.client: Optional[AsyncOpenAI] = None

    async def initialize(self) -> None:
        """Initialize the OpenRouter provider."""
        try:
            # Get API key from config (handle both ProviderConfig and dict)
            if isinstance(self.config, ProviderConfig):
                api_key = self.config.api_key
                base_url = self.config.base_url
            else:
                api_key = self.config.get("api_key")
                base_url = self.config.get("base_url", "https://openrouter.ai/api/v1")

            if not api_key:
                raise ProviderError("openrouter", "API key not provided")

            self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)

            self._set_initialized(True)
            self.logger.info("OpenRouter provider initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize OpenRouter provider: {e}")
            raise ProviderError(
                "openrouter", f"Initialization failed: {str(e)}", e
            ) from e

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
            # Resolve the model ID to the full OpenRouter format
            resolved_model_id = self._resolve_model_id(request.model)

            # Prepare the request
            api_request = {
                "model": resolved_model_id,
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

            # Check if response is truly empty (no content AND no tool calls)
            if not content and not tool_calls:
                raise ProviderError("openrouter", "Empty response from API")

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
            # Check if this is a retriable error that should trigger fallback
            if RetriableError.is_retriable_error(e):
                status_code = RetriableError.extract_status_code(e)
                raise RetriableError("openrouter", str(e), status_code, e)

            # Keep the old QuotaExceededError for backward compatibility
            if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                raise QuotaExceededError("openrouter", str(e))

            self.logger.error(f"Error generating OpenRouter response: {e}")
            raise ProviderError("openrouter", f"Generation failed: {str(e)}", e) from e

    async def generate_image(self, request: ImageRequest) -> ImageResponse:
        """Generate an image using the provider's models."""
        model_name = request.model
        model_info = self.get_model_info(model_name)

        # Verify that the model can generate_image
        if not model_info.image_gen:
            return ImageResponse(
                error=f"Model {model_name} does not support image generation",
                image_url=None,
                model_used=None,
                user_id=request.user_id,
            )

        resolved_model_id = self._resolve_model_id(model_name)

        # Prepare message content based on whether we have an input image
        if request.input_image_url:
            # Use multimodal format with image input
            message_content = [
                {"type": "text", "text": request.prompt},
                {"type": "image_url", "image_url": {"url": request.input_image_url}},
            ]
        else:
            # Text-only prompt
            message_content = request.prompt

        # Now make the request
        request_params = {
            "model": resolved_model_id,
            "messages": [{"role": "user", "content": message_content}],
            "temperature": 1,
            "modalities": ["text", "image"],
        }
        response = await self.client.chat.completions.create(**request_params)

        if response and response.choices:
            message = response.choices[0].message
            image_url = None
            if message.images and len(message.images) > 0:
                image_dict = message.images[0]
                image_url = image_dict.get("image_url").get("url")

            return ImageResponse(
                error=None,
                image_url=image_url,
                model_used=model_name,
                user_id=request.user_id,
                image_base64=image_url[len("data:image/png;base64,") :].encode("utf-8"),
            )

    def get_models(self) -> Dict[str, ModelInfo]:
        """Get available models from OpenRouter."""
        # Get model info from config and filter for this provider
        model_infos = (
            self.config.model_infos
            if isinstance(self.config, ProviderConfig)
            else self.config.get("model_infos", {})
        )

        # Return only models for this provider
        return {
            display_name: model_info
            for display_name, model_info in model_infos.items()
            if model_info.provider == "openrouter"
        }

    def get_model_info(self, model_id: str) -> ModelInfo:
        """Get detailed information about a specific model."""
        # Get model info from config
        model_infos = (
            self.config.model_infos
            if isinstance(self.config, ProviderConfig)
            else self.config.get("model_infos", {})
        )

        # Check if model_id is in display name keys (direct match)
        if model_id in model_infos and model_infos[model_id].provider == "openrouter":
            return model_infos[model_id]

        # Check if model_id matches any ModelInfo.id values for this provider
        for model_info in model_infos.values():
            if model_info.provider == "openrouter" and model_info.id == model_id:
                return model_info

        # Check for short format (e.g., "deepseek/deepseek-chat-v3-0324:free")
        # by checking if "openrouter/" + model_id matches any ModelInfo.id
        prefixed_model_id = f"openrouter/{model_id}"
        for model_info in model_infos.values():
            if (
                model_info.provider == "openrouter"
                and model_info.id == prefixed_model_id
            ):
                return model_info

        raise ModelNotFoundError(model_id, "openrouter")

    def supports_model(self, model_id: str) -> bool:
        """Check if OpenRouter supports the given model."""
        # Get model info from config
        model_infos = (
            self.config.model_infos
            if isinstance(self.config, ProviderConfig)
            else self.config.get("model_infos", {})
        )

        # Check if model_id is in display name keys (direct match)
        if model_id in model_infos:
            return model_infos[model_id].provider == "openrouter"

        # Check if model_id matches any ModelInfo.id values for this provider
        for model_info in model_infos.values():
            if model_info.provider == "openrouter" and model_info.id == model_id:
                return True

        # Check for short format (e.g., "deepseek/deepseek-chat-v3-0324:free")
        # by checking if "openrouter/" + model_id matches any ModelInfo.id
        prefixed_model_id = f"openrouter/{model_id}"
        for model_info in model_infos.values():
            if (
                model_info.provider == "openrouter"
                and model_info.id == prefixed_model_id
            ):
                return True

        return False

    def _resolve_model_id(self, model_id: str) -> str:
        """Resolve model ID to the format expected by OpenRouter API."""
        # Get model info from config
        model_infos = (
            self.config.model_infos
            if isinstance(self.config, ProviderConfig)
            else self.config.get("model_infos", {})
        )

        # Check if it's a display name key
        if model_id in model_infos and model_infos[model_id].provider == "openrouter":
            api_model_id = model_infos[model_id].id
            # Strip the provider prefix for the API call
            if api_model_id.startswith("openrouter/"):
                return api_model_id[len("openrouter/") :]
            return api_model_id

        # Check if it's already a full model ID for this provider
        for model_info in model_infos.values():
            if model_info.provider == "openrouter" and model_info.id == model_id:
                # Strip the provider prefix for the API call
                if model_id.startswith("openrouter/"):
                    return model_id[len("openrouter/") :]
                return model_id

        # Check for short format and see if we have a matching full ID
        prefixed_model_id = f"openrouter/{model_id}"
        for model_info in model_infos.values():
            if (
                model_info.provider == "openrouter"
                and model_info.id == prefixed_model_id
            ):
                # Return the model ID without the openrouter prefix
                return model_id

        # Return as-is but strip openrouter prefix if present
        if model_id.startswith("openrouter/"):
            return model_id[len("openrouter/") :]
        return model_id

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
                fallback_tool = {
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
                tools.append(fallback_tool)

        self.logger.debug(f"Converted {len(tools)} MCP tools to OpenAI format")
        return tools
