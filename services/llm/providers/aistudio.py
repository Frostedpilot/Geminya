"""Google (AI Studio) provider implementation using LiteLLM."""

import logging
from typing import Dict, Any, List, Optional, Union

from litellm import acompletion, aimage_generation

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


class AIStudioProvider(LLMProvider):
    def __init__(self, config: ProviderConfig, logger: logging.Logger):
        super().__init__("aistudio", config, logger)
        self.client: Optional[Any] = None

    async def initialize(self):
        try:
            if not self._get_api_key():
                raise ProviderError("aistudio", "API key not provided")

            self._set_initialized(True)
            self.logger.info("AI Studio provider initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize AI Studio provider: {e}")
            raise ProviderError("aistudio", "Initialization failed") from e

    async def cleanup(self):
        try:
            self.client = None
            self._set_initialized(False)
            self.logger.info("AI Studio provider cleaned up successfully.")
        except Exception as e:
            self.logger.error(f"Failed to cleanup AI Studio provider: {e}")
            raise ProviderError("aistudio", "Cleanup failed") from e

    def get_models(self):
        model_infos = self.config.model_infos
        return {
            display_name: model_info
            for display_name, model_info in model_infos.items()
            if model_info.provider == "aistudio"
        }

    def get_model_info(self, model_id: str) -> ModelInfo:
        models = self.get_models()
        # First check if model_id is a display name (key in models dict)
        if model_id in models:
            return models[model_id]
        # Then check if model_id matches any model's actual ID
        for model_info in models.values():
            if model_info.id == model_id:
                return model_info
        # If not found, raise error
        raise ModelNotFoundError(model_id, "aistudio")

    def supports_model(self, model_id: str) -> bool:
        """Check if AI Studio supports the given model."""
        # Get model info from config
        model_infos = self.config.model_infos

        # Check if model_id is in display name keys (direct match)
        if model_id in model_infos:
            return model_infos[model_id].provider == "aistudio"

        # Check if model_id matches any ModelInfo.id values for this provider
        for model_info in model_infos.values():
            if model_info.provider == "aistudio" and model_info.id == model_id:
                return True

        # Check for short format (e.g., "gemini-2.5-flash-lite")
        # by checking if "aistudio/" + model_id matches any ModelInfo.id
        prefixed_model_id = f"aistudio/{model_id}"
        for model_info in model_infos.values():
            if model_info.provider == "aistudio" and model_info.id == prefixed_model_id:
                return True

        return False

    def convert_mcp_tools(self, mcp_tools: List[Tool]) -> List[Dict[str, Any]]:
        tools = []
        for tool in mcp_tools:
            try:
                tool_dict = self._build_tool_dict(tool)
                tools.append(tool_dict)
                self.logger.debug(
                    f"Converted tool {tool.name} to OpenAI format: {tool_dict}"
                )
            except Exception as e:
                self.logger.error(f"Failed to convert tool {tool.name}: {e}")
                continue
        return tools

    def _build_tool_dict(self, tool: Tool) -> Dict[str, Any]:
        """Build a single tool dictionary in OpenAI format."""
        name = tool.name
        description = tool.description or "No description"
        schema = tool.inputSchema or {}

        params = {"type": "object", "properties": {}, "required": []}
        if "properties" in schema:
            cleaned_props = self._convert_properties(schema["properties"])
            params["properties"] = cleaned_props

        if "required" in schema and isinstance(schema["required"], list):
            valid_required = [
                field for field in schema["required"] if field in params["properties"]
            ]
            if valid_required:
                params["required"] = valid_required

        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": params,
            },
        }

    def _convert_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Convert properties to JSON schema format, handling simple types only."""
        return {
            name: self._convert_single_property(prop_def)
            for name, prop_def in properties.items()
            if isinstance(prop_def, dict)
        }

    def _convert_single_property(self, prop_def: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a single property definition."""
        prop_type = self._sanitize_type(str(prop_def.get("type", "string")))
        result = {"type": prop_type}

        if "description" in prop_def:
            result["description"] = prop_def["description"]
        if "enum" in prop_def:
            result["enum"] = prop_def["enum"]

        if prop_type == "array" and "items" in prop_def:
            result["items"] = self._convert_array_items(prop_def["items"])
        elif prop_type == "object" and "properties" in prop_def:
            result["properties"] = self._convert_nested_object_properties(
                prop_def["properties"]
            )

        return result

    def _convert_array_items(self, items_def: Any) -> Dict[str, Any]:
        """Convert array item type definition."""
        if not isinstance(items_def, dict) or "type" not in items_def:
            return {"type": "string"}

        result = {"type": self._sanitize_type(str(items_def["type"]))}
        if "description" in items_def:
            result["description"] = items_def["description"]
        return result

    def _convert_nested_object_properties(
        self, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert nested object properties (scalar types only)."""
        scalar_types = ["string", "number", "integer", "boolean"]
        result = {}

        for name, prop_def in properties.items():
            if not isinstance(prop_def, dict) or "type" not in prop_def:
                continue
            prop_type = self._sanitize_type(str(prop_def["type"]))
            if prop_type in scalar_types:
                result[name] = {"type": prop_type}
                if "description" in prop_def:
                    result[name]["description"] = prop_def["description"]

        return result

    def _sanitize_type(self, type_value: str) -> str:
        """Convert MCP type to a JSON schema-compatible type."""
        if isinstance(type_value, list):
            for type_name in type_value:
                if type_name != "null":
                    return self._sanitize_single_type(type_name)
            return "string"

        return self._sanitize_single_type(type_value)

    def _sanitize_single_type(self, type_str: str) -> str:
        """Convert a single type string to JSON schema format."""
        type_mapping = {
            "string": "string",
            "number": "number",
            "integer": "integer",
            "boolean": "boolean",
            "array": "array",
            "object": "object",
        }
        return type_mapping.get(type_str, "string")

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        if not self.is_initialized():
            raise ProviderError("aistudio", "Provider not initialized")
        if not self.supports_model(request.model):
            raise ModelNotFoundError(request.model, "aistudio")

        try:
            api_request = self._build_api_request(request)
            self.logger.debug(
                f"Calling AI Studio via LiteLLM with model: {request.model}"
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
            raise ProviderError("aistudio", "Empty response from API")

        choice = response.choices[0]
        message = choice.message
        content = getattr(message, "content", "") or ""
        tool_calls = self._extract_tool_calls(message)

        if not content and not tool_calls:
            raise ProviderError("aistudio", "No response from API")

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
            "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
            "completion_tokens": getattr(response.usage, "completion_tokens", None),
            "total_tokens": getattr(response.usage, "total_tokens", None),
        }

    def _handle_generation_error(self, error: Exception) -> None:
        """Handle and re-raise generation errors with appropriate type."""
        if RetriableError.is_retriable_error(error):
            raise RetriableError(
                "aistudio",
                str(error),
                RetriableError.extract_status_code(error),
                error,
            )
        if "rate limit" in str(error).lower() or "quota" in str(error).lower():
            raise QuotaExceededError("aistudio", str(error))
        raise ProviderError("aistudio", str(error)) from error

    async def generate_image(self, request: ImageRequest) -> ImageResponse:
        model_info = self.get_model_info(request.model)

        if not model_info.image_gen:
            return ImageResponse(
                error=f"Model {request.model} does not support image generation",
                image_url=None,
                model_used=None,
                user_id=request.user_id,
            )

        try:
            resolved_model_id = self._resolve_model_id(request.model)
            response = await aimage_generation(
                model=resolved_model_id,
                prompt=request.prompt,
                api_key=self._get_api_key(),
            )

            image_url = None
            if response and getattr(response, "data", None):
                image_data = response.data[0]
                image_url = getattr(image_data, "url", None)
                if not image_url and getattr(image_data, "b64_json", None):
                    image_url = f"data:image/png;base64,{image_data.b64_json}"

            if not image_url:
                return ImageResponse(
                    error="No image returned from API",
                    image_url=None,
                    model_used=request.model,
                    user_id=request.user_id,
                )

            return ImageResponse(
                error=None,
                image_url=image_url,
                model_used=request.model,
                user_id=request.user_id,
                image_base64=(
                    image_url[len("data:image/png;base64,") :].encode("utf-8")
                    if image_url.startswith("data:image/png;base64,")
                    else None
                ),
            )

        except Exception as e:
            raise ProviderError("aistudio", str(e)) from e

    def _resolve_model_id(self, model_id: str) -> str:
        if model_id.startswith("aistudio/"):
            return f"gemini/{model_id[len('aistudio/') :]}"
        return f"gemini/{model_id}"

    def _get_api_key(self) -> Optional[str]:
        return self.config.api_key
