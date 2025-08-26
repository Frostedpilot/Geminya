"""Google (AI Studio) provider implementation."""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from google.genai import Client
from google.genai import types as genai_types

from mcp.types import Tool
from ..provider import LLMProvider
from ..types import LLMRequest, LLMResponse, ModelInfo, ToolCall, ProviderConfig
from ..exceptions import (
    ProviderError,
    ModelNotFoundError,
    QuotaExceededError,
    RetriableError,
)


class AIStudioProvider(LLMProvider):
    def __init__(self, config: ProviderConfig, logger: logging.Logger):
        super().__init__(config, logger)
        self.client: Optional[Client] = None

    def initialize(self):
        try:
            # Get the api key from the config
            aistudio_api_key = self.config.aistudio_api_key
            self.client = Client(api_key=aistudio_api_key)
            self._set_initialized()
            self.logger.info("AI Studio client initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize AI Studio client: {e}")
            raise ProviderError("Initialization failed") from e

    def cleanup(self):
        try:
            if self.client:
                self.client = None
                self.logger.info("AI Studio client cleaned up successfully.")
                self._set_initialized(False)
        except Exception as e:
            self.logger.error(f"Failed to cleanup AI Studio client: {e}")
            raise ProviderError("Cleanup failed") from e

    def get_models(self):
        model_infos = self.config.model_infos
        return {
            display_name: model_info
            for display_name, model_info in model_infos.items()
            if model_info.provider == "aistudio"
        }

    def get_model_info(self, model_id: str) -> ModelInfo:
        models = self.get_models()
        model_ids = [model_info.id for model_info in models.values()]
        if model_id in models:
            return models[model_id]
        elif model_id in model_ids:
            return models[model_ids.index(model_id)]
        else:
            raise ModelNotFoundError(model_id, "aistudio")

    def supports_model(self, model_id: str) -> bool:
        return model_id in self.get_models()

    def convert_mcp_tools(self, mcp_tools):
        # Don't know how to properly implement this yet, since format for AI Studio tools is too different and strongly typed.
        raise NotImplementedError("Tool conversion not implemented for AI Studio")

    def generate_response(self, request: LLMRequest) -> LLMResponse:
        if not self.initialize():
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
            messages = [
                genai_types.Content(
                    role="user" if m["role"] == "user" else "model",
                    parts=[genai_types.Part.from_text(c) for c in m["content"]],
                )
                for m in contents
            ]

            # Get the config
            additional_config = request.provider_specific or {}
            config = self._get_gen_config(request.temperature, additional_config)

            # Now call the API
            response = self.client.models.generate_content(
                model=resolved_model_id, contents=messages, config=config
            )

            # Parse the result
            if not response or not response.text:
                raise ProviderError("aistudio", "No response from API")

            response_text = response.text

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
