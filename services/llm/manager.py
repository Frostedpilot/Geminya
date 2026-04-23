"""LLM Manager - Unified LLM interface using LiteLLM."""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    from config import Config

from services.state_manager import StateManager

from .types import LLMRequest, LLMResponse, ModelInfo, ImageRequest, ImageResponse
from .exceptions import (
    LLMError,
    ModelNotFoundError,
    ConfigurationError,
    ProviderError,
    RetriableError,
)

# Import litellm for unified LLM interface
import litellm
from litellm import acompletion, aimage_generation


class LLMManager:
    """Manager for LLM operations using LiteLLM as a unified interface."""

    def __init__(
        self,
        config: Config,
        state_manager: StateManager,
        logger: logging.Logger,
    ):
        self.config = config
        self.state_manager = state_manager
        self.logger = logger

        self._initialized = False
        
        # Store API keys for different providers
        self.api_keys: Dict[str, str] = {}
        
        # Configure litellm settings
        litellm.set_verbose = False
        litellm.drop_params = True

    async def initialize(self) -> None:
        """Initialize the LLM Manager and configure API keys."""
        try:
            self.logger.info("Initializing LLM Manager with LiteLLM...")

            # Extract and store API keys from config
            await self._setup_api_keys()

            self._initialized = True
            self.logger.info("LLM Manager initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize LLM Manager: {e}")
            raise ConfigurationError(f"LLM Manager initialization failed: {str(e)}")

    async def _setup_api_keys(self) -> None:
        """Setup API keys for different providers from config."""
        # Setup OpenRouter API key
        if "openrouter" in self.config.llm_providers:
            openrouter_config = self.config.llm_providers["openrouter"]
            api_key = openrouter_config.api_key if hasattr(openrouter_config, 'api_key') else openrouter_config.get("api_key")
            if api_key:
                self.api_keys["openrouter"] = api_key
                self.logger.info("OpenRouter API key configured")

        # Setup Google AI Studio API key
        if "aistudio" in self.config.llm_providers:
            aistudio_config = self.config.llm_providers["aistudio"]
            api_key = aistudio_config.api_key if hasattr(aistudio_config, 'api_key') else aistudio_config.get("api_key")
            if api_key:
                self.api_keys["aistudio"] = api_key
                litellm.google_ai_studio_api_key = api_key
                self.logger.info("Google AI Studio API key configured")

    async def cleanup(self) -> None:
        """Cleanup the LLM Manager."""
        self.logger.info("Cleaning up LLM Manager...")

        try:
            self.api_keys.clear()
            self._initialized = False

            self.logger.info("LLM Manager cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during LLM Manager cleanup: {e}")

    async def _generate_with_provider(self, request: LLMRequest) -> LLMResponse:
        """Generate response using LiteLLM's unified interface."""
        if not self._initialized:
            raise LLMError("LLM Manager not initialized")

        # Resolve the model name to litellm format
        litellm_model = self._resolve_model_for_litellm(request.model)

        self.logger.debug(f"Using LiteLLM model: {litellm_model}")

        try:
            # Prepare the request for litellm
            completion_kwargs = {
                "model": litellm_model,
                "messages": request.messages,
                "temperature": request.temperature,
            }

            # Add optional parameters
            if request.max_tokens:
                completion_kwargs["max_tokens"] = request.max_tokens

            # Add tools if provided (convert to litellm format)
            if request.tools and len(request.tools) > 0:
                tools = self._convert_tools_for_litellm(request.tools)
                completion_kwargs["tools"] = tools

            # Add API key based on provider
            provider_name = self._extract_provider_name(request.model)
            if provider_name == "openrouter" and "openrouter" in self.api_keys:
                completion_kwargs["api_key"] = self.api_keys["openrouter"]
                # Set base URL for OpenRouter
                litellm.api_base = "https://openrouter.ai/api/v1"
            elif provider_name == "aistudio":
                # Google AI Studio uses the globally set key
                pass

            # Make the API call using litellm
            self.logger.debug(
                f"Making LiteLLM API request for model {request.model}"
            )
            
            response = await acompletion(**completion_kwargs)

            if not response.choices or not response.choices[0].message:
                raise ProviderError("litellm", "Empty response from API")

            choice = response.choices[0]
            message = choice.message

            # Extract content
            content = message.content or ""

            # Extract tool calls if present
            tool_calls = None
            if hasattr(message, 'tool_calls') and message.tool_calls:
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
                raise ProviderError("litellm", "Empty response from API")

            # Extract usage information
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            self.logger.info(f"Generated LiteLLM response ({len(content)} chars)")

            return LLMResponse(
                content=content,
                model_used=request.model,
                provider_used=provider_name,
                tool_calls=tool_calls,
                usage=usage,
                metadata={
                    "finish_reason": choice.finish_reason,
                    "response_id": getattr(response, 'id', None),
                },
            )

        except RetriableError as e:
            self.logger.warning(
                f"Retriable error from LiteLLM for model {request.model}: {e}"
            )

            # Try fallback model
            fallback_response = await self._try_fallback_model(request)
            if fallback_response:
                return fallback_response

            # Re-raise original error if fallback failed
            raise e

        except Exception as e:
            # Check if this is a retriable error
            if RetriableError.is_retriable_error(e):
                status_code = RetriableError.extract_status_code(e)
                raise RetriableError("litellm", str(e), status_code, e)

            self.logger.error(f"Error generating LiteLLM response: {e}")
            raise ProviderError("litellm", f"Generation failed: {str(e)}", e) from e

    async def _try_fallback_model(
        self, original_request: LLMRequest
    ) -> Optional[LLMResponse]:
        """Try to generate response using fallback model."""

        use_tool = (
            original_request.tools is not None and len(original_request.tools) > 0
        )

        if use_tool:
            fallback_model = self.config.fall_back_tool_model
        else:
            fallback_model = self.config.fall_back_model
            
        if not fallback_model or fallback_model == original_request.model:
            self.logger.warning("No fallback model configured or same as current model")
            return None

        self.logger.info(f"Retrying with fallback model: {fallback_model}")

        # Create fallback request
        fallback_request = LLMRequest(
            messages=original_request.messages,
            model=fallback_model,
            max_tokens=original_request.max_tokens,
            temperature=original_request.temperature,
            tools=original_request.tools,
        )

        try:
            return await self._generate_with_provider(fallback_request)

        except Exception as fallback_error:
            self.logger.error(f"Fallback model also failed: {fallback_error}")
            return None

    def _extract_provider_name(self, model: str) -> str:
        """Extract provider name from model string."""
        if "/" in model:
            return model.split("/")[0]
        return "openrouter"  # Default provider

    def _resolve_model_for_litellm(self, model: str) -> str:
        """Resolve model name to litellm format.
        
        LiteLLM expects model names in format: 'provider/model_id'
        For example: 'openrouter/deepseek/deepseek-chat-v3-0324:free'
                     'gemini/gemini-2.5-flash-lite'
        """
        # Get model info from config to resolve the actual model ID
        model_infos = self._get_all_model_infos()
        
        # Check if model_id is a display name (key in models dict)
        if model in model_infos:
            model_info = model_infos[model]
            # Return in litellm format: provider/model_id
            return f"{model_info.provider}/{model_info.id}"
        
        # Check if model already has provider prefix
        if "/" in model:
            parts = model.split("/", 1)
            provider = parts[0]
            model_id = parts[1] if len(parts) > 1 else model
            
            # Check if this matches any known model
            for info in model_infos.values():
                if info.provider == provider and (info.id == model_id or info.id.endswith(model_id)):
                    return f"{provider}/{info.id}"
            
            # Return as-is if no match found
            return model
        
        # Default: assume openrouter provider
        return f"openrouter/{model}"

    def _get_all_model_infos(self) -> Dict[str, ModelInfo]:
        """Get all model infos from config."""
        all_models = {}
        for provider_name, provider_config in self.config.llm_providers.items():
            model_infos = (
                provider_config.model_infos 
                if hasattr(provider_config, 'model_infos') 
                else provider_config.get("model_infos", {})
            )
            all_models.update(model_infos)
        return all_models

    def _convert_tools_for_litellm(self, tools: List[Any]) -> List[Dict[str, Any]]:
        """Convert MCP Tool objects to litellm/OpenAI format."""
        from mcp.types import Tool
        
        converted_tools = []
        
        for tool in tools:
            try:
                if isinstance(tool, Tool):
                    # Extract properties and required fields safely
                    properties = {}
                    required = []

                    name = tool.name
                    description = tool.description or "No description"
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
                    converted_tools.append(tool_dict)
                elif isinstance(tool, dict):
                    # Already in dict format, use as-is
                    converted_tools.append(tool)
                    
            except Exception as e:
                self.logger.error(f"Error converting tool: {e}", exc_info=True)
                continue

        self.logger.debug(f"Converted {len(converted_tools)} tools for LiteLLM")
        return converted_tools

    async def get_available_models(self) -> List[ModelInfo]:
        """Get all available models from config."""
        return list(self._get_all_model_infos().values())

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about configured providers."""
        return {
            name: {
                "initialized": self._initialized,
                "api_key_configured": name in self.api_keys,
            }
            for name in self.config.llm_providers.keys()
        }

    def get_model_info(self, model: str) -> ModelInfo:
        """Get information about a specific model."""
        model_infos = self._get_all_model_infos()
        
        # Check direct match
        if model in model_infos:
            return model_infos[model]
        
        # Check by model ID
        for model_info in model_infos.values():
            if model_info.id == model:
                return model_info
        
        raise ModelNotFoundError(f"Model {model} not found")

    async def generate_image(self, request: ImageRequest) -> ImageResponse:
        """Generate an image using LiteLLM's unified interface."""
        if not self._initialized:
            return ImageResponse(
                error="LLM Manager not initialized",
                image_url=None,
                model_used=None,
                user_id=request.user_id,
            )

        # Resolve the model name to litellm format
        litellm_model = self._resolve_model_for_litellm(request.model)
        provider_name = self._extract_provider_name(request.model)

        try:
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

            # Prepare the request for litellm image generation
            image_kwargs = {
                "model": litellm_model,
                "prompt": request.prompt,
            }

            # Add API key based on provider
            if provider_name == "openrouter" and "openrouter" in self.api_keys:
                image_kwargs["api_key"] = self.api_keys["openrouter"]

            # Make the API call using litellm
            response = await aimage_generation(**image_kwargs)

            # Extract image URL from response
            image_url = None
            if hasattr(response, 'data') and response.data and len(response.data) > 0:
                image_data = response.data[0]
                if hasattr(image_data, 'url'):
                    image_url = image_data.url
                elif isinstance(image_data, dict) and 'url' in image_data:
                    image_url = image_data['url']

            if not image_url:
                return ImageResponse(
                    error="No image URL in response",
                    image_url=None,
                    model_used=request.model,
                    user_id=request.user_id,
                )

            # Extract base64 if it's a data URL
            image_base64 = None
            if image_url.startswith("data:image"):
                image_base64 = image_url.split(",", 1)[1].encode("utf-8") if "," in image_url else None

            return ImageResponse(
                error=None,
                image_url=image_url,
                model_used=request.model,
                user_id=request.user_id,
                image_base64=image_base64,
            )

        except Exception as e:
            self.logger.error(f"Error generating image: {e}")
            return ImageResponse(
                error=f"Image generation failed: {str(e)}",
                image_url=None,
                model_used=request.model,
                user_id=request.user_id,
            )
