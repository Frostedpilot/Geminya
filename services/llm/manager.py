"""LLM Manager - Provider-focused service for managing multiple LLM providers."""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional, Type, TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    from config import Config

from services.state_manager import StateManager

from .provider import LLMProvider
from .types import LLMRequest, LLMResponse, ModelInfo, ImageRequest, ImageResponse
from .exceptions import (
    LLMError,
    ModelNotFoundError,
    ConfigurationError,
    ProviderError,
    RetriableError,
)
from .providers import OpenRouterProvider
from .providers.aistudio import AIStudioProvider


class LLMManager:
    """Manager for multiple LLM providers with unified API."""

    def __init__(
        self,
        config: Config,
        state_manager: StateManager,
        logger: logging.Logger,
    ):
        self.config = config
        self.state_manager = state_manager
        self.logger = logger

        self.providers: Dict[str, LLMProvider] = {}
        self.default_provider: Optional[str] = None
        self._initialized = False

        self.provider_mapping: Dict[str, Type[LLMProvider]] = {
            "openrouter": OpenRouterProvider,
            "aistudio": AIStudioProvider,
        }

    async def initialize(self) -> None:
        """Initialize the LLM Manager and all providers."""
        try:
            self.logger.info("Initializing LLM Manager...")

            await self._initialize_providers()

            # Set default provider
            self.default_provider = "openrouter"

            self._initialized = True
            self.logger.info("LLM Manager initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize LLM Manager: {e}")
            raise ConfigurationError(f"LLM Manager initialization failed: {str(e)}")

    async def cleanup(self) -> None:
        """Cleanup the LLM Manager and all providers."""
        self.logger.info("Cleaning up LLM Manager...")

        try:
            # Cleanup all providers
            for provider_name, provider in self.providers.items():
                try:
                    await provider.cleanup()
                    self.logger.debug(f"Provider {provider_name} cleaned up")
                except Exception as e:
                    self.logger.error(
                        f"Error cleaning up provider {provider_name}: {e}"
                    )

            self.providers.clear()
            self.default_provider = None
            self._initialized = False

            self.logger.info("LLM Manager cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during LLM Manager cleanup: {e}")

    async def _generate_with_provider(self, request: LLMRequest) -> LLMResponse:
        """Generate response using the appropriate provider."""
        if not self._initialized:
            raise LLMError("LLM Manager not initialized")

        # Extract provider from model name (e.g., "openrouter/model-name")
        provider_name = self._extract_provider_name(request.model)

        self.logger.debug(f"Using provider {provider_name} for model {request.model}")

        if provider_name not in self.providers:
            if self.default_provider and self.default_provider in self.providers:
                provider_name = self.default_provider
            else:
                raise ModelNotFoundError(f"No provider found for model {request.model}")

        provider = self.providers[provider_name]

        try:
            self.logger.debug(
                f"Generating with provider {provider_name} for model {request.model}"
            )
            response = await provider.generate_response(request)
            return response

        except RetriableError as e:
            self.logger.warning(
                f"Retriable error from provider {provider_name} for model {request.model}: {e}"
            )

            # Try fallback model
            fallback_response = await self._try_fallback_model(request)
            if fallback_response:
                return fallback_response

            # Re-raise original error if fallback failed
            raise e

        except Exception as e:
            self.logger.error(f"Error generating with provider {provider_name}: {e}")
            raise ProviderError(provider_name, f"Provider failed: {str(e)}", e)

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
            # Determine provider for fallback model
            fallback_provider_name = self._extract_provider_name(fallback_model)
            if fallback_provider_name not in self.providers:
                fallback_provider_name = self.default_provider

            if (
                not fallback_provider_name
                or fallback_provider_name not in self.providers
            ):
                self.logger.error("No fallback provider available")
                return None

            fallback_provider = self.providers[fallback_provider_name]
            self.logger.debug(
                f"Retrying with fallback provider {fallback_provider_name} for model {fallback_model}"
            )
            return await fallback_provider.generate_response(fallback_request)

        except Exception as fallback_error:
            self.logger.error(f"Fallback model also failed: {fallback_error}")
            return None

    def _extract_provider_name(self, model: str) -> str:
        """Extract provider name from model string."""
        if "/" in model:
            return model.split("/")[0]
        return self.default_provider or "openrouter"

    async def get_available_models(self) -> List[ModelInfo]:
        """Get all available models from all providers."""
        models = []
        for provider in self.providers.values():
            try:
                provider_models = await provider.get_available_models()
                models.extend(provider_models)
            except Exception as e:
                self.logger.warning(f"Failed to get models from provider: {e}")

        return models

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about all providers."""
        return {
            name: {
                "initialized": provider.is_initialized(),
                "models_count": (
                    len(provider.models) if hasattr(provider, "models") else 0
                ),
            }
            for name, provider in self.providers.items()
        }

    def get_model_info(self, model: str) -> ModelInfo:
        """Get information about a specific model."""
        for provider in self.providers.values():
            try:
                model_info = provider.get_model_info(model)
                if model_info:
                    return model_info
            except Exception as e:
                self.logger.warning(f"Failed to get model info from provider: {e}")
        raise ModelNotFoundError(f"Model {model} not found")

    async def _initialize_providers(self) -> None:
        """Initialize all configured LLM providers."""
        self.logger.info("Initializing LLM providers...")

        try:
            for provider_name in self.config.available_providers:
                self.logger.info(f"Initializing provider: {provider_name}")
                provider_class = self.provider_mapping.get(provider_name)

                if provider_class:
                    provider = provider_class(
                        self.config.llm_providers[provider_name], self.logger
                    )
                    await provider.initialize()
                    self.providers[provider_name] = provider
                    self.logger.info(
                        f"Provider {provider_name} initialized successfully"
                    )
                else:
                    self.logger.warning(f"No provider class found for {provider_name}")

        except Exception as e:
            self.logger.error(f"Failed to initialize LLM providers: {e}")
            raise ConfigurationError(f"LLM providers initialization failed: {str(e)}")

    async def generate_image(self, request: ImageRequest) -> ImageResponse:
        """Generate an image using the specified model."""
        provider_name = self._extract_provider_name(request.model)
        if provider_name not in self.providers:
            self.logger.error(f"Provider not found: {provider_name}")
            return ImageResponse.error("Provider not found")

        provider = self.providers[provider_name]
        return await provider.generate_image(request)
