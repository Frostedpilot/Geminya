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


class AIService:
    """Service for handling AI operations and API communication."""

    def __init__(
        self, config: Config, state_manager: StateManager, logger: logging.Logger
    ):
        self.config = config
        self.state_manager = state_manager
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
        if not self.client:
            self.logger.error("AI client not initialized")
            return "Nya! I'm not ready yet, please try again in a moment."

        try:
            # Get model and history
            model = self.state_manager.get_model(server_id)
            history = self.state_manager.get_history(message.channel.id)
            lore_book = self.state_manager.get_lore_book()

            # Build prompt
            prompt = self._build_prompt(message, history, lore_book)

            self.logger.debug(
                f"Generating response for {message.author} using model {model}"
            )

            # Make API call
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt},
                ],
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

    async def get_check_response(self, prompt: str) -> str:
        """Get a check response using the check model.

        Args:
            prompt: Prompt text for the check

        Returns:
            str: Check response (usually "yes" or "no")
        """
        if not self.client:
            self.logger.error("AI client not initialized for check response")
            return "no"

        max_retries = 5

        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.config.check_model,
                    messages=[
                        {"role": "system", "content": self._get_personality_prompt()},
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

        # Get personality prompt
        personality_prompt = self._get_personality_prompt()

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
            word_list = set(message.content.lower().split())
            overlap = word_list.intersection(lore_book.get("quick_trigger_list", set()))

            if overlap:
                lore_list = set()
                for word in overlap:
                    if word in lore_book.get("trigger_words", {}):
                        lore_list.update(lore_book["trigger_words"][word])

                for lore in lore_list:
                    if lore in lore_book.get("example_responses", {}):
                        example = lore_book["example_responses"][lore]
                        lore_prompt += f"\n\n{example}"

        # Collect all participants
        authors = {author_name}
        if history:
            for entry in history:
                authors.add(entry["name"])

        # Build final prompt
        final_prompt = f"""
Write Geminya's next reply in a fictional chat between participants and {author_name}.
{personality_prompt}
{lore_prompt}
[Start a new group chat. Group members: Geminya, {', '.join(authors)}]
{history_prompt}
[Write the next reply only as Geminya. Only use information related to {author_name}'s message and only answer {author_name} directly.]
"""

        return final_prompt.strip()

    def _get_personality_prompt(self) -> str:
        """Get the personality system prompt.

        Returns:
            str: Personality prompt text
        """
        try:
            from utils.config_load import load_language_file

            lang_data = load_language_file()
            personality = lang_data.get("personality", {})
            return personality.get(
                "Geminya_Exp", "You are Geminya, a helpful AI assistant."
            )

        except Exception as e:
            self.logger.error(f"Failed to load personality prompt: {e}")
            return "You are Geminya, a helpful AI assistant."
