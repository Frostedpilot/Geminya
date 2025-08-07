"""LLM Manager - Main service for managing multiple LLM providers."""

import logging
from typing import Dict, Any, List, Optional
import asyncio

from config import Config
from services.state_manager import StateManager
from services.mcp import MCPClientManager

from .provider import LLMProvider
from .types import LLMRequest, LLMResponse, ModelInfo
from .exceptions import LLMError, ModelNotFoundError, ConfigurationError, ProviderError
from .providers import OpenRouterProvider


class LLMManager:
    """Manager for multiple LLM providers with unified API."""

    def __init__(
        self,
        config: Config,
        state_manager: StateManager,
        mcp_client: MCPClientManager,
        logger: logging.Logger,
    ):
        self.config = config
        self.state_manager = state_manager
        self.mcp_client = mcp_client
        self.logger = logger

        self.providers: Dict[str, LLMProvider] = {}
        self.default_provider: Optional[str] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the LLM Manager and all providers."""
        try:
            self.logger.info("Initializing LLM Manager...")

            # Initialize OpenRouter provider (for now, only this one)
            await self._initialize_openrouter_provider()

            # Set default provider
            self.default_provider = "openrouter"

            self._initialized = True
            self.logger.info("LLM Manager initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize LLM Manager: {e}")
            await self.cleanup()
            raise

    async def cleanup(self) -> None:
        """Cleanup all providers and resources."""
        self.logger.info("Cleaning up LLM Manager...")

        for provider_name, provider in self.providers.items():
            try:
                await provider.cleanup()
                self.logger.debug(f"Cleaned up provider: {provider_name}")
            except Exception as e:
                self.logger.error(f"Error cleaning up provider {provider_name}: {e}")

        self.providers.clear()
        self.default_provider = None
        self._initialized = False

        self.logger.info("LLM Manager cleanup completed")

    async def get_response(self, message, server_id: str) -> str:
        """Generate an AI response for a Discord message (main interface)."""
        if not self._initialized:
            self.logger.error("LLM Manager not initialized")
            return "Nya! I'm not ready yet, please try again in a moment."

        try:
            # Ensure server is initialized
            self.state_manager.initialize_server(server_id)

            # Get model and history
            model = self.state_manager.get_model(server_id)
            history = self.state_manager.get_history(message.channel.id)

            # Get persona-specific lore book
            persona_name = self.state_manager.persona.get(
                server_id, self.config.default_persona
            )
            lore_books = self.state_manager.get_lore_books()
            lore_book = lore_books.get(persona_name) if lore_books else None

            # Determine if we should use MCP
            use_mcp = self.state_manager.use_mcp

            if use_mcp:
                return await self._get_mcp_response(
                    message, server_id, model, history, lore_book
                )
            else:
                return await self._get_standard_response(
                    message, server_id, model, history, lore_book
                )

        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return "Nya! Something went wrong, please try again later."

    async def get_check_response(self, prompt: str, message) -> str:
        """Get a check response using the check model."""
        if not self._initialized:
            self.logger.error("LLM Manager not initialized for check response")
            return "no"

        server_id = str(message.guild.id) if message.guild else "default"
        self.state_manager.initialize_server(server_id)

        max_retries = 5

        for attempt in range(max_retries):
            try:
                # Get the check model
                check_model = getattr(
                    self.config, "check_model", "deepseek/deepseek-chat"
                )

                # Get personality prompt
                personality_prompt = self._get_personality_prompt(message)

                # Create request
                request = LLMRequest(
                    messages=[
                        {"role": "system", "content": personality_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    model=check_model,
                    temperature=0.1,  # Lower temperature for more consistent responses
                )

                # Generate response
                response = await self._generate_with_provider(request)
                result = response.content.strip().lower()

                self.logger.debug(f"Check response: {result}")
                return result

            except Exception as e:
                self.logger.warning(
                    f"Check response error (attempt {attempt + 1}): {e}"
                )
                await asyncio.sleep(2**attempt)

        self.logger.error("Failed to get check response after all retries")
        return "no"

    def get_available_models(self) -> Dict[str, ModelInfo]:
        """Get all available models from all providers."""
        all_models = {}

        for provider in self.providers.values():
            if provider.is_initialized():
                provider_models = provider.get_models()
                all_models.update(provider_models)

        return all_models

    async def _initialize_openrouter_provider(self) -> None:
        """Initialize the OpenRouter provider."""
        try:
            # Create provider config
            provider_config = {
                "api_key": self.config.openrouter_api_key,
                "base_url": "https://openrouter.ai/api/v1",
                "models": self.config.available_models,  # From existing config
            }

            # Create and initialize provider
            provider = OpenRouterProvider(
                provider_config, self.logger.getChild("openrouter")
            )
            await provider.initialize()

            self.providers["openrouter"] = provider
            self.logger.info("OpenRouter provider initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize OpenRouter provider: {e}")
            raise ConfigurationError(f"OpenRouter initialization failed: {str(e)}")

    async def _get_mcp_response(
        self, message, server_id: str, model: str, history, lore_book
    ) -> str:
        """Generate response using MCP tools."""
        try:
            # Build prompt without tools (MCP handles tools separately)
            prompt = self._build_prompt(message, history, lore_book)

            self.logger.debug(
                f"Generating MCP response for {message.author} using model {model}"
            )

            # Use MCP client to process the query
            response = await self.mcp_client.process_query(prompt, server_id)

            if not response or not response.success:
                self.logger.warning(
                    f"MCP client returned error: {response.error if response else 'Empty response'}"
                )
                return "Nya! Something went wrong, please try again later."

            self.logger.info(
                f"Generated MCP response for {message.author.name} "
                f"({len(response.content)} chars, {response.tool_calls_made} tool calls, "
                f"{response.iterations} iterations, {response.execution_time:.2f}s)"
            )

            return response.content.strip()

        except Exception as e:
            self.logger.error(f"Error generating MCP response: {e}")
            return "Nya! Something went wrong, please try again later."

    async def _get_standard_response(
        self, message, server_id: str, model: str, history, lore_book
    ) -> str:
        """Generate standard response without MCP tools."""
        try:
            # Build prompt
            prompt = self._build_prompt(message, history, lore_book)

            self.logger.debug(
                f"Generating standard response for {message.author} using model {model}"
            )

            # Create request
            request = LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                temperature=getattr(self.config, "temperature", 0.7),
            )

            # Generate response
            response = await self._generate_with_provider(request)

            self.logger.info(
                f"Generated response for {message.author.name} ({len(response.content)} chars)"
            )

            return response.content.strip()

        except Exception as e:
            self.logger.error(f"Error generating standard response: {e}")
            return "Nya! Something went wrong, please try again later."

    async def _generate_with_provider(self, request: LLMRequest) -> LLMResponse:
        """Generate response using appropriate provider."""
        # Find provider that supports the model
        provider = self._get_provider_for_model(request.model)

        if not provider:
            raise ModelNotFoundError(request.model)

        return await provider.generate_response(request)

    def _get_provider_for_model(self, model: str) -> Optional[LLMProvider]:
        """Get the provider that supports the given model."""
        for provider in self.providers.values():
            if provider.is_initialized() and provider.supports_model(model):
                return provider

        return None

    def _build_prompt(self, message, history, lore_book) -> str:
        """Build the complete prompt for AI generation (extracted from original AIService)."""
        author = message.author
        author_name = author.name
        if author.nick:
            author_name = f"{author.nick} ({author.name})"

        # Get personality prompt
        personality_prompt = self._get_personality_prompt(message)

        # Build history section
        history_prompt = ""
        if history:
            for entry in history:
                nick_part = f" (aka {entry['nick']})" if entry["nick"] else ""
                line = f"From: {entry['name']}{nick_part}\n{entry['content']}\n\n"
                history_prompt += line
        history_prompt = history_prompt.strip()

        # Build lore book section
        lore_prompt = ""
        if lore_book:
            for category_name, category_data in lore_book.items():
                if isinstance(category_data, dict) and "keywords" in category_data:
                    keywords = category_data.get("keywords", [])

                    if any(keyword in message.content.lower() for keyword in keywords):
                        example = category_data.get("example", "")
                        if example:
                            lore_prompt += f"\n\n{example}"
                            self.logger.debug(
                                f"Added lore example from category: {category_name}"
                            )
                            break

        # Collect all participants
        authors = {author_name}
        if history:
            for entry in history:
                authors.add(entry["name"])

        # Get persona name
        server_id = str(message.guild.id) if message.guild else "default"
        persona_name = self.state_manager.persona.get(
            server_id, self.config.default_persona
        )

        # Build final prompt
        final_prompt = f"""
Write {persona_name}'s next reply in a fictional chat between participants and {author_name}.
{personality_prompt}
{lore_prompt}
[Start a new group chat. Group members: {persona_name}, {', '.join(authors)}]
{history_prompt}
[Write the next reply only as {persona_name}. Only use information related to {author_name}'s message and only answer {author_name} directly. Do not start with "From {persona_name}:" or similar.]
[You have access to tools, so leverage them as much as possible. You can use more than one tool at a time, and you can iteratively call them up to {self.config.max_tool_iterations} times with consecutive messages before giving answer, so plan accordingly. For tasks you deemed as hard, start with the sequential-thinking tool.]
""".replace(
            "{{user}}", author_name
        )

        return final_prompt.strip()

    def _get_personality_prompt(self, message) -> str:
        """Get the personality system prompt (extracted from original AIService)."""
        try:
            from utils.config_load import load_language_file

            # Get server ID and ensure it's initialized
            server_id = str(message.guild.id) if message.guild else "default"
            self.state_manager.initialize_server(server_id)

            # Get persona name for this server
            persona_name = self.state_manager.persona.get(
                server_id, self.config.default_persona
            )

            # Load language data
            lang_data = load_language_file()
            characters = lang_data.get("characters", {})
            character = characters.get(persona_name, {})

            self.logger.debug(f"Using persona '{persona_name}' for server {server_id}")

            personality = character.get(
                "personality", "You are Geminya, a helpful AI assistant."
            )

            self.logger.debug(f"Personality prompt length: {len(personality)} chars")
            return personality

        except Exception as e:
            self.logger.error(f"Failed to load personality prompt: {e}")
            return "You are Geminya, a helpful AI assistant."
