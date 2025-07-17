"""State management service for the Geminya bot.

This module handles all bot state including conversation history,
model preferences, lore book data, and server-specific settings.
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Any, Set
import discord
from pathlib import Path

from config import Config


class StateManager:
    """Manages all bot state including history, models, and lore book."""

    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger

        # State storage
        self.models: Dict[str, str] = {}  # server_id -> model_id
        self.histories: Dict[int, List[Dict[str, Any]]] = defaultdict(
            list
        )  # channel_id -> messages
        self.lore_book: Optional[Dict[str, Any]] = None

        # Cache for performance
        self._channel_cache: Set[int] = set()

    async def initialize(self) -> None:
        """Initialize the state manager and load initial data."""
        self.logger.info("Initializing state manager...")

        # Load lore book
        await self._load_lore_book()

        self.logger.info("State manager initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup resources and save state if needed."""
        self.logger.info("Cleaning up state manager...")

        # Clear large objects
        self.histories.clear()
        self.models.clear()
        self.lore_book = None
        self._channel_cache.clear()

        self.logger.info("State manager cleanup completed")

    def initialize_server(self, server_id: str) -> None:
        """Initialize state for a new server.

        Args:
            server_id: Discord server (guild) ID as string
        """
        if server_id not in self.models:
            self.models[server_id] = self.config.default_model
            self.logger.info(
                f"Initialized server {server_id} with default model: {self.config.default_model}"
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

    def get_lore_book(self) -> Optional[Dict[str, Any]]:
        """Get the current lore book data.

        Returns:
            Optional[Dict[str, Any]]: Lore book data or None if not loaded
        """
        return self.lore_book

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
            "lore_book_loaded": self.lore_book is not None,
            "memory_channels": len(self._channel_cache),
        }

        if self.lore_book:
            stats["lore_book_entries"] = len(self.lore_book.get("trigger_words", {}))
            stats["lore_book_triggers"] = len(
                self.lore_book.get("quick_trigger_list", set())
            )

        return stats

    async def _load_lore_book(self) -> None:
        """Load the lore book from the language file."""
        try:
            from utils.config_load import load_language_file

            lang_data = load_language_file()
            lore_book_data = lang_data.get("lorebook", {})

            if not lore_book_data:
                self.logger.warning(
                    "Lore book data is missing or empty in language file"
                )
                self.lore_book = None
                return

            # Process lore book data
            trigger_words = {}
            example_responses = {}

            for key, value in lore_book_data.items():
                words = value.get("keywords", [])
                for word in words:
                    if word not in trigger_words:
                        trigger_words[word] = []
                    trigger_words[word].append(key)

                example_responses[
                    key
                ] = f"""
        {{user}}: {value.get("example_user", "")}
        Geminya: {value.get("example", "")}
        """

            self.lore_book = {
                "trigger_words": trigger_words,
                "example_responses": example_responses,
                "quick_trigger_list": set(trigger_words.keys()),
            }

            self.logger.info(
                f"Loaded lore book with {len(trigger_words)} trigger words and {len(example_responses)} examples"
            )

        except Exception as e:
            self.logger.error(f"Failed to load lore book: {e}")
            self.lore_book = None
