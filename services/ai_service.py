"""AI service layer for the Geminya bot.

This module handles all AI-related operations including response generation,
prompt building, and API communication with OpenRouter.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
import discord
from openai import AsyncOpenAI

from config import Config
from services.state_manager import StateManager
from services.mcp_client import MCPClientManager


class AIService:
    """Service for handling AI operations and API communication."""

    def __init__(
        self,
        config: Config,
        state_manager: StateManager,
        logger: logging.Logger,
        mcp_client: MCPClientManager,
    ):
        self.config = config
        self.state_manager = state_manager
        self.mcp_client = mcp_client
        self.logger = logger
        self.client: Optional[AsyncOpenAI] = None

    async def initialize(self) -> None:
        """Initialize the AI service and create API client."""
        try:
            self.client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.config.openrouter_api_key,
            )
            self.logger.info("AI service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize AI service: {e}")
            raise

    async def cleanup(self) -> None:
        """Cleanup AI service resources."""
        if self.client:
            await self.client.close()
            self.client = None
        self.logger.info("AI service cleanup completed")

    async def get_response(self, message: discord.Message, server_id: str) -> str:
        """Generate an AI response for a Discord message.

        Args:
            message: Discord message to respond to
            server_id: Server ID for model selection

        Returns:
            str: Generated response text
        """
        if self.state_manager.use_mcp:
            return await self._get_mcp_response(message, server_id)
        else:
            return await self._get_response(message, server_id)

    async def _get_mcp_response(self, message: discord.Message, server_id: str) -> str:
        """Generate an MCP AI response for a Discord message.

        Args:
            message: Discord message to respond to
            server_id: Server ID for model selection

        Returns:
            str: Generated response text
        """
        if not self.client:
            self.logger.error("AI client not initialized")
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

            # Build prompt
            prompt = self._build_prompt(message, history, lore_book)

            self.logger.debug(
                f"Generating response for {message.author} using model {model} and persona {persona_name} (With MCP)"
            )

            response = await self.mcp_client.process_query(prompt, server_id)

            if not response:
                self.logger.warning("Empty response from MCP client")
                return "Nya! Something went wrong, please try again later."

            self.logger.info(
                f"Generated MCP response for {message.author.name} ({len(response)} chars)"
            )

            return response.strip()

        except Exception as e:
            self.logger.error(f"Error generating MCP AI response: {e}")
            return "Nya! Something went wrong, please try again later."

    async def _get_response(self, message: discord.Message, server_id: str) -> str:
        """Generate an normal non-MCP AI response for a Discord message.

        Args:
            message: Discord message to respond to
            server_id: Server ID for model selection

        Returns:
            str: Generated response text
        """
        if not self.client:
            self.logger.error("AI client not initialized")
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

            # Build prompt
            prompt = self._build_prompt(message, history, lore_book)

            self.logger.debug(
                f"Generating response for {message.author} using model {model} and persona {persona_name}"
            )

            # Make API call
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=(
                    self.config.temperature
                    if hasattr(self.config, "temperature")
                    else 0.7
                ),
            )

            if len(response.choices) == 0 or not response.choices[0].message.content:
                self.logger.warning("Empty response from AI model")
                return "Nya! Something went wrong, please try again later."

            response_text = response.choices[0].message.content.strip()

            self.logger.info(
                f"Generated response for {message.author.name} ({len(response_text)} chars)"
            )

            return response_text

        except Exception as e:
            self.logger.error(f"Error generating AI response: {e}")
            return "Nya! Something went wrong, please try again later."

    async def get_check_response(self, prompt: str, message: discord.Message) -> str:
        """Get a check response using the check model.

        Args:
            prompt: Prompt text for the check
            message: Discord message to check

        Returns:
            str: Check response (usually "yes" or "no")
        """
        if not self.client:
            self.logger.error("AI client not initialized for check response")
            return "no"

        # Ensure server is initialized
        server_id = str(message.guild.id) if message.guild else "default"
        self.state_manager.initialize_server(server_id)

        max_retries = 5

        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.config.check_model,
                    messages=[
                        {
                            "role": "system",
                            "content": self._get_personality_prompt(message),
                        },
                        {"role": "user", "content": prompt},
                    ],
                )

                if (
                    len(response.choices) == 0
                    or not response.choices[0].message.content
                ):
                    self.logger.warning(f"Empty check response, attempt {attempt + 1}")
                    await asyncio.sleep(2**attempt)
                    continue

                result = response.choices[0].message.content.strip().lower()
                self.logger.debug(f"Check response: {result}")
                return result

            except Exception as e:
                self.logger.warning(
                    f"Check response error (attempt {attempt + 1}): {e}"
                )
                await asyncio.sleep(2**attempt)

        self.logger.error("Failed to get check response after all retries")
        return "no"

    def _get_mcp_prompt(self, history: List[Dict[str, Any]]) -> str:
        """Get the first part of the MCP prompt, which does not include lore and personality for correctness. (experimental)

        Args:
            history: Conversation history

        Returns:
            str: MCP prompt text
        """

        history_prompt = ""
        if history:
            for entry in history:
                nick_part = f" (aka {entry['nick']})" if entry["nick"] else ""
                line = f"From: {entry['name']}{nick_part}\n{entry['content']}\n\n"
                history_prompt += line

        return history_prompt

    def _build_prompt(
        self,
        message: discord.Message,
        history: List[Dict[str, Any]],
        lore_book: Optional[Dict[str, Any]],
    ) -> str:
        """Build the complete prompt for AI generation.

        Args:
            message: Discord message to respond to
            history: Conversation history
            lore_book: Lore book data for context

        Returns:
            str: Complete prompt text
        """
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
            # Check each lore book category
            for category_name, category_data in lore_book.items():
                if isinstance(category_data, dict) and "keywords" in category_data:
                    keywords = category_data.get("keywords", [])

                    # Check if any keywords match the message
                    if any(keyword in message.content.lower() for keyword in keywords):
                        example = category_data.get("example", "")
                        if example:
                            lore_prompt += f"\n\n{example}"
                            self.logger.debug(
                                f"Added lore example from category: {category_name}"
                            )
                            break  # Only use the first matching category to avoid overwhelming the prompt

        # Collect all participants
        authors = {author_name}
        if history:
            for entry in history:
                authors.add(entry["name"])

        # Collecr persona name
        persona_name = self.state_manager.persona.get(
            str(message.guild.id) if message.guild else "default",
            self.config.default_persona,
        )

        # Build final prompt
        final_prompt = f"""
Write {persona_name}'s next reply in a fictional chat between participants and {author_name}.
{personality_prompt}
{lore_prompt}
[Start a new group chat. Group members: {persona_name}, {', '.join(authors)}]
{history_prompt}
[Write the next reply only as {persona_name}. Only use information related to {author_name}'s message and only answer {author_name} directly. Do not start with "From {persona_name}:" or similar. You have access to tools, so leverage them as much as possible, you can use more than one tool each time you reply.]
""".replace(
            "{{user}}", author_name
        )

        return final_prompt.strip()

    def _get_personality_prompt(self, message: discord.Message) -> str:
        """Get the personality system prompt.

        Args:
            message: Discord message to get persona for

        Returns:
            str: Personality prompt text
        """
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
