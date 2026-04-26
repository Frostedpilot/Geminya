"""OpenRouter provider implementation using LiteLLM."""

import logging
from typing import Dict, Any, List, Optional, Union

from litellm import acompletion

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
        self.client: Optional[Any] = None

    async def initialize(self) -> None:
        """Initialize the OpenRouter provider."""
        try:
            api_key = self._get_api_key()
            if not api_key:
                raise ProviderError("openrouter", "API key not provided")

            self._set_initialized(True)
            self.logger.info("OpenRouter provider initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize OpenRouter provider: {e}")
            raise ProviderError(
                "openrouter", f"Initialization failed: {str(e)}", e
            ) from e

    async def cleanup(self) -> None:
        """Cleanup OpenRouter provider resources."""
        self.client = None
        self._set_initialized(False)
        self.logger.info("OpenRouter provider cleanup completed")

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate a response using OpenRouter."""
        if not self.is_initialized():
            raise ProviderError("openrouter", "Provider not initialized")
        if not self.supports_model(request.model):
            raise ModelNotFoundError(request.model, "openrouter")

        try:
            api_request = self._build_api_request(request)
            self.logger.debug(
                f"Making OpenRouter API request for model {request.model}"
            )
            response = await acompletion(**api_request)
            return self._process_completion_response(response, request)
        except Exception as e:
            return self._handle_generation_error(e)

    def _build_api_request(self, request: LLMRequest) -> Dict[str, Any]:
        """Build the API request dictionary for LiteLLM."""
        resolved_model_id = self._resolve_model_id(request.model)
        api_request = {
            "model": resolved_model_id,
            "messages": request.messages,
            "temperature": request.temperature,
            "api_key": self._get_api_key(),
        }
        if request.max_tokens:
            api_request["max_tokens"] = request.max_tokens
        if request.tools:
            api_request["tools"] = (
                self.convert_mcp_tools(request.tools)
                if isinstance(request.tools[0], Tool)
                else request.tools
            )
        api_request.update(request.provider_specific)
        return api_request

    def _process_completion_response(
        self, response: Any, request: LLMRequest
    ) -> LLMResponse:
        """Extract and structure the completion response."""
        if not response.choices or not response.choices[0].message:
            raise ProviderError("openrouter", "Empty response from API")

        choice = response.choices[0]
        message = choice.message
        content = message.content or ""
        tool_calls = self._extract_tool_calls(message)

        if not content and not tool_calls:
            raise ProviderError("openrouter", "Empty response from API")

        self.logger.info(f"Generated OpenRouter response ({len(content)} chars)")
        return LLMResponse(
            content=content,
            model_used=request.model,
            provider_used=self.name,
            tool_calls=tool_calls,
            usage=self._extract_usage(response),
            metadata={
                "finish_reason": getattr(choice, "finish_reason", None),
                "response_id": getattr(response, "id", None),
            },
        )

    def _extract_tool_calls(self, message: Any) -> Optional[List[Dict[str, Any]]]:
        """Extract tool calls from message if present."""
        if not getattr(message, "tool_calls", None):
            return None
        return [
            {
                "id": tool_call.id,
                "type": tool_call.type,
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            }
            for tool_call in message.tool_calls
        ]

    def _extract_usage(self, response: Any) -> Optional[Dict[str, int]]:
        """Extract usage information from response."""
        if not getattr(response, "usage", None):
            return None
        return {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    def _handle_generation_error(self, error: Exception) -> None:
        """Handle and re-raise generation errors with appropriate type."""
        if RetriableError.is_retriable_error(error):
            raise RetriableError(
                "openrouter",
                str(error),
                RetriableError.extract_status_code(error),
                error,
            )
        if "rate limit" in str(error).lower() or "quota" in str(error).lower():
            raise QuotaExceededError("openrouter", str(error))
        self.logger.error(f"Error generating OpenRouter response: {error}")
        raise ProviderError(
            "openrouter", f"Generation failed: {str(error)}", error
        ) from error

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
            "messages": [
                {"role": "user", "content": message_content},
            ],
            "temperature": 1,
            "modalities": ["text", "image"],
            "api_key": self._get_api_key(),
        }
        response = await acompletion(**request_params)

        if response and response.choices:
            message = response.choices[0].message
            image_url = None
            if message.images and len(message.images) > 0:
                image_dict = message.images[0]
                if isinstance(image_dict, dict):
                    image_url = image_dict.get("image_url", {}).get("url")
                else:
                    image_url = getattr(image_dict, "url", None)

            return ImageResponse(
                error=None,
                image_url=image_url,
                model_used=model_name,
                user_id=request.user_id,
                image_base64=(
                    image_url[len("data:image/png;base64,") :].encode("utf-8")
                    if image_url and image_url.startswith("data:image/png;base64,")
                    else None
                ),
            )

        return ImageResponse(
            error="No image returned from API",
            image_url=None,
            model_used=model_name,
            user_id=request.user_id,
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
            return model_infos[model_id].id

        # Check if it's already a full model ID for this provider
        for model_info in model_infos.values():
            if model_info.provider == "openrouter" and model_info.id == model_id:
                return model_id

        # Check for short format and see if we have a matching full ID
        prefixed_model_id = f"openrouter/{model_id}"
        for model_info in model_infos.values():
            if (
                model_info.provider == "openrouter"
                and model_info.id == prefixed_model_id
            ):
                return prefixed_model_id

        if model_id.startswith("openrouter/"):
            return model_id

        return prefixed_model_id

    def _get_api_key(self) -> Optional[str]:
        if isinstance(self.config, ProviderConfig):
            return self.config.api_key
        return self.config.get("api_key")

    def convert_mcp_tools(self, mcp_tools: List[Tool]) -> List[Dict[str, Any]]:
        """Convert MCP Tool objects to OpenAI format for OpenRouter."""
        tools = []

        for tool in mcp_tools:
            try:
                # Extract properties and required fields safely
                properties = {}
                required = []

                name = tool.name
                description = tool.description
                if tool.inputSchema and "properties" in tool.inputSchema:
                    properties = tool.inputSchema["properties"]
                    required = tool.inputSchema.get("required", [])

                tool_dict = {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": required,
                        },
                    },
                }

                self.logger.debug(
                    f"Converted tool {tool.name} to OpenAI format: {tool_dict}"
                )

                if not self._verify_tool_dict(tool_dict):
                    self.logger.warning(f"Invalid tool format for tool {tool.name}")
                    self.logger.warning(f"Tool dict: {tool_dict}")

                tools.append(tool_dict)

            except Exception:
                self.logger.error(f"Error converting tool {tool.name}", exc_info=True)
                continue

        self.logger.debug(f"Converted {len(tools)} MCP tools to OpenAI format")
        return tools

    def _verify_tool_dict(self, tool_dict: Dict[str, Any]) -> bool:
        """Verify tool dictionary structure (simplified validation)."""
        try:
            params = tool_dict["function"]["parameters"]
            properties = params.get("properties", {})
            required_fields = params.get("required", [])

            # Check that all required fields exist in properties
            for field in required_fields:
                if field not in properties:
                    self.logger.warning(
                        f"Required field '{field}' missing from properties"
                    )
                    return False

            # Basic type validation for properties
            valid_types = {"string", "integer", "boolean", "array", "object", "number"}
            for prop_name, prop_info in properties.items():
                if isinstance(prop_info, dict):
                    prop_type = prop_info.get("type", "").lower()
                    if prop_type and prop_type not in valid_types:
                        self.logger.warning(
                            f"Invalid type '{prop_type}' for property '{prop_name}'"
                        )

            return True
        except KeyError as e:
            self.logger.error(f"Tool dict missing required structure: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error validating tool dict: {e}")
            return False
