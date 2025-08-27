"""Google (AI Studio) provider implementation."""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from google.genai import Client
from google.genai import types as genai_types

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
        self.client: Optional[Client] = None

    async def initialize(self):
        try:
            # Get the api key from the config
            aistudio_api_key = self.config.api_key
            self.client = Client(api_key=aistudio_api_key)
            self._set_initialized(True)
            self.logger.info("AI Studio client initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize AI Studio client: {e}")
            raise ProviderError("aistudio", "Initialization failed") from e

    async def cleanup(self):
        try:
            if self.client:
                self.client = None
                self.logger.info("AI Studio client cleaned up successfully.")
                self._set_initialized(False)
        except Exception as e:
            self.logger.error(f"Failed to cleanup AI Studio client: {e}")
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

    def convert_mcp_tools(self, mcp_tools):
        # Don't know how to properly implement this yet, since format for AI Studio tools is too different and strongly typed.
        raise NotImplementedError("Tool conversion not implemented for AI Studio")

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        if not self.is_initialized() or not self.client:
            raise ProviderError("aistudio", "Provider not initialized")

        if not self.supports_model(request.model):
            raise ModelNotFoundError(request.model, "aistudio")

        tools = request.tools
        if tools:
            raise NotImplementedError("Tool use not implemented for AI Studio")

        try:
            model_id = request.model
            resolved_model_id = self._resolve_model_id(model_id)

            contents = request.messages

            # Build the messages object for aistudio
            messages = []
            for m in contents:
                role = "user" if m["role"] == "user" else "model"
                # Handle content - it could be a string or a list
                content = m["content"]
                if isinstance(content, str):
                    parts = [genai_types.Part.from_text(text=content)]
                elif isinstance(content, list):
                    parts = [genai_types.Part.from_text("\n".join(content))]
                else:
                    parts = [genai_types.Part.from_text(text=str(content))]

                messages.append(genai_types.Content(role=role, parts=parts))

            # Get the config
            additional_config = request.provider_specific or {}
            config = self._get_gen_config(request.temperature, additional_config)

            # Now call the API
            self.logger.debug(f"Calling AI Studio API with model: {resolved_model_id}")

            response = self.client.models.generate_content(
                model=resolved_model_id, contents=messages, config=config
            )

            # Parse the result
            if not response or not response.text:
                raise ProviderError("aistudio", "No response from API")

            response_text = response.text

            self.logger.debug(
                f"Generated AI Studio response: {len(response_text)} characters"
            )

            # NOTE: Additional tool call parsing if we ever implement one

            llmresponse = LLMResponse(
                content=response_text,
                model_used=request.model,
                provider_used="aistudio",
                tool_calls=[],  # No tool calls implemented yet
                usage=None,
                metadata={
                    "finish_reason": "stop",
                    "response_id": response.response_id,
                },
            )

            return llmresponse

        except Exception as e:
            raise ProviderError("aistudio", str(e)) from e

    async def generate_image(self, request: ImageRequest) -> ImageResponse:
        return ImageResponse()

    def _resolve_model_id(self, model_id: str) -> str:
        if not model_id.startswith("aistudio/"):
            raise ProviderError("aistudio", f"Invalid model ID format: {model_id}")
        return model_id[len("aistudio/") :]

    def _get_gen_config(
        self, temperature: float, provider_specific_config: dict
    ) -> genai_types.GenerateContentConfig:
        tmp = {
            "temperature": temperature,
            "safety_settings": [
                genai_types.SafetySetting(
                    category=genai_types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=genai_types.HarmBlockThreshold.OFF,
                ),
                genai_types.SafetySetting(
                    category=genai_types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
                    threshold=genai_types.HarmBlockThreshold.OFF,
                ),
                genai_types.SafetySetting(
                    category=genai_types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=genai_types.HarmBlockThreshold.OFF,
                ),
                genai_types.SafetySetting(
                    category=genai_types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=genai_types.HarmBlockThreshold.OFF,
                ),
                genai_types.SafetySetting(
                    category=genai_types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=genai_types.HarmBlockThreshold.OFF,
                ),
            ],
            **provider_specific_config,
        }

        cfg = genai_types.GenerateContentConfig(**tmp)
        return cfg
