"""State management service for the Geminya bot.

This module handles all bot state including conversation history,
model preferences, lore book data, and server-specific settings.
"""

from __future__ import annotations
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Any, Set, TYPE_CHECKING
import discord
from pathlib import Path

if TYPE_CHECKING:
    from config import Config


class StateManager:
    """Manages all bot state including history, models, and lore book."""

    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger

        # State storage
        self.models: Dict[str, str] = {}  # server_id -> model_id
        self.tool_models: Dict[str, str] = {}  # server_id -> tool model_id
        self.histories: Dict[int, List[Dict[str, Any]]] = defaultdict(
            list
        )  # channel_id -> messages

        self.lore_books: Optional[Dict[str, Any]] = {}  # persona -> lore book data

        self.persona: Dict[str, str] = {}  # server_id -> persona name

        # Cache for performance
        self._channel_cache: Set[int] = set()

        # MCP related state
        self.use_mcp: bool = True

    async def initialize(self) -> None:
        """Initialize the state manager and load initial data."""
        self.logger.info("Initializing state manager...")

        # Load lore books
        self._load_lore_books()

        # Load persona list
        self._load_persona_list()

        self.logger.info("State manager initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup resources and save state if needed."""
        self.logger.info("Cleaning up state manager...")

        # Clear large objects
        self.histories.clear()
        self.models.clear()
        self.tool_models.clear()
        self.lore_books = None
        self._channel_cache.clear()

        self.logger.info("State manager cleanup completed")

    def initialize_server(self, server_id: str) -> None:
        """Initialize state for a new server.

        Args:
            server_id: Discord server (guild) ID as string
        """
        if server_id not in self.models:
            self.models[server_id] = self.config.default_model
            self.persona[server_id] = self.config.default_persona
            self.logger.info(
                f"Initialized server {server_id} with default model: {self.config.default_model}"
            )

        if server_id not in self.tool_models:
            self.tool_models[server_id] = self.config.default_tool_model
            self.logger.info(
                f"Initialized server {server_id} with default tool model: {self.config.default_tool_model}"
            )

    def initialize_channel(self, channel_id: int) -> None:
        """Initialize history for a new channel.

        Args:
            channel_id: Discord channel ID
        """
        if channel_id not in self._channel_cache:
            self.histories[channel_id] = []
            self._channel_cache.add(channel_id)
            self.logger.debug(f"Initialized history for channel {channel_id}")

    def get_model(self, server_id: str) -> str:
        """Get the current AI model for a server.

        Args:
            server_id: Discord server ID as string

        Returns:
            str: Model identifier
        """
        return self.models.get(server_id, self.config.default_model)

    def get_tool_model(self, server_id: str) -> str:
        """Get the current tool model for a server.

        Args:
            server_id: Discord server ID as string

        Returns:
            str: Tool model identifier
        """
        return self.tool_models.get(server_id, self.config.default_tool_model)

    def set_model(self, server_id: str, model_id: str) -> None:
        """Set the AI model for a server.

        Args:
            server_id: Discord server ID as string
            model_id: Model identifier to set
        """
        old_model = self.models.get(server_id, "none")
        self.models[server_id] = model_id
        self.logger.info(
            f"Changed model for server {server_id}: {old_model} -> {model_id}"
        )

    def set_tool_model(self, server_id: str, model_id: str) -> None:
        """Set the tool model for a server.

        Args:
            server_id: Discord server ID as string
            model_id: Tool model identifier to set
        """
        old_model = self.tool_models.get(server_id, "none")
        self.tool_models[server_id] = model_id
        self.logger.info(
            f"Changed tool model for server {server_id}: {old_model} -> {model_id}"
        )

    def set_persona(self, server_id: str, persona_name: str) -> None:
        """Set the persona for a server.

        Args:
            server_id: Discord server ID as string
            persona_name: Name of the persona to set
        """
        old_persona = self.persona.get(server_id, "none")
        self.persona[server_id] = persona_name
        self.logger.info(
            f"Changed persona for server {server_id}: {old_persona} -> {persona_name}"
        )

    def get_persona(self, server_id: str) -> str:
        """Get the current persona for a server.

        Args:
            server_id: Discord server ID as string

        Returns:
            str: Persona name
        """
        return self.persona.get(server_id, self.config.default_persona)

    def get_history(self, channel_id: int) -> List[Dict[str, Any]]:
        """Get conversation history for a channel.

        Args:
            channel_id: Discord channel ID

        Returns:
            List[Dict[str, Any]]: List of message entries
        """
        self.initialize_channel(channel_id)
        return self.histories[channel_id]

    def add_message(
        self,
        channel_id: int,
        author_id: int,
        author_name: str,
        nick: Optional[str],
        content: str,
    ) -> None:
        """Add a message to the conversation history.

        Args:
            channel_id: Discord channel ID
            author_id: Discord user ID of the message author
            author_name: Username of the author
            nick: Nickname of the author (if any)
            content: Message content
        """
        self.initialize_channel(channel_id)

        history = self.histories[channel_id]

        # Check if we can combine with the last message (same author)
        if history and history[-1]["author"] == author_id:
            # Combine messages from the same author
            history[-1]["content"] += f"\n{content}"
        else:
            # Add new message entry
            message_entry = {
                "author": author_id,
                "name": author_name,
                "nick": nick,
                "content": content,
            }
            history.append(message_entry)

        # Trim history if it exceeds maximum length
        if len(history) > self.config.max_history_length:
            removed = history.pop(0)
            self.logger.debug(
                f"Trimmed history for channel {channel_id}, removed message from {removed['name']}"
            )

    def get_lore_books(self) -> Optional[Dict[str, Any]]:
        """Get the current lore book data.

        Returns:
            Optional[Dict[str, Any]]: Lore book data or None if not loaded
        """
        return self.lore_books

    def clear_channel_history(self, channel_id: int) -> None:
        """Clear conversation history for a specific channel.

        Args:
            channel_id: Discord channel ID
        """
        if channel_id in self.histories:
            count = len(self.histories[channel_id])
            self.histories[channel_id].clear()
            self.logger.info(
                f"Cleared {count} messages from channel {channel_id} history"
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the current state.

        Returns:
            Dict[str, Any]: State statistics
        """
        total_messages = sum(len(hist) for hist in self.histories.values())

        stats = {
            "servers_configured": len(self.models),
            "channels_tracked": len(self.histories),
            "total_messages_stored": total_messages,
            "lore_books_loaded": self.lore_books is not None,
            "memory_channels": len(self._channel_cache),
        }

        if self.lore_books:
            # Count categories across all personas
            total_categories = sum(
                len(
                    [
                        k
                        for k, v in book.items()
                        if isinstance(v, dict) and "keywords" in v
                    ]
                )
                for book in self.lore_books.values()
            )
            # Count total keywords across all personas
            total_keywords = sum(
                sum(
                    len(v.get("keywords", []))
                    for v in book.values()
                    if isinstance(v, dict)
                )
                for book in self.lore_books.values()
            )
            stats["lore_book_categories"] = total_categories
            stats["lore_book_keywords"] = total_keywords

        return stats

    def _load_persona_list(self) -> None:
        """Load the list of available personas from the language file."""
        try:
            from utils.config_load import load_language_file

            lang_data = load_language_file()
            self.config.personas = lang_data.get("characters", {})
            if not self.config.personas:
                self.logger.warning("No personas found in language file")
        except Exception as e:
            self.logger.error(f"Failed to load personas: {e}")
            self.config.personas = {}

    def _load_lore_books(self) -> None:
        """Load the lore books from the language file."""
        try:
            from utils.config_load import load_language_file

            lang_data = load_language_file()
            characters = lang_data.get("characters", {})

            if not characters:
                self.logger.warning("No characters found in language file")
                self.lore_books = {}
                return

            for name, char in characters.items():
                lore_book_data = char.get("lorebook", {})

                if not lore_book_data:
                    self.logger.warning(
                        f"Lore book data is missing or empty for character '{name}'"
                    )
                    self.lore_books[name] = {}
                    continue

                # Store lore book data directly (new structure)
                self.lore_books[name] = lore_book_data

                # Count categories for logging
                categories = len(
                    [
                        k
                        for k, v in lore_book_data.items()
                        if isinstance(v, dict) and "keywords" in v
                    ]
                )
                total_keywords = sum(
                    len(v.get("keywords", []))
                    for v in lore_book_data.values()
                    if isinstance(v, dict)
                )

                self.logger.info(
                    f"Loaded lore book with {categories} categories and {total_keywords} total keywords for character '{name}'"
                )

        except Exception as e:
            self.logger.error(f"Failed to load lore books: {e}")
            self.lore_books = {}
