"""Centralized logging configuration for Geminya bot."""

from __future__ import annotations
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, TYPE_CHECKING
import discord

if TYPE_CHECKING:
    from config import Config


class GeminyaLogger:
    """Centralized logger for the Geminya bot."""

    def __init__(self, config: Config):
        self.config = config
        self.loggers = {}
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging for the entire application."""
        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG if self.config.debug else logging.INFO)

        # Clear any existing handlers
        root_logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler for general logs
        file_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "geminya.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Configure Discord.py logging
        discord_logger = logging.getLogger("discord")
        discord_logger.setLevel(logging.INFO)

        # Create specific handler for message processing
        message_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "messages.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding="utf-8",
        )
        message_handler.setLevel(logging.DEBUG)
        message_handler.setFormatter(file_formatter)

        # Add message handler to message logger
        message_logger = logging.getLogger("geminya.messages")
        message_logger.addHandler(message_handler)
        message_logger.setLevel(logging.DEBUG)
        message_logger.propagate = True  # Also send to root logger

        # Create error handler for critical errors
        error_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "errors.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=10,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)

        error_logger = logging.getLogger("geminya.errors")
        error_logger.addHandler(error_handler)
        error_logger.setLevel(logging.ERROR)
        error_logger.propagate = True

        # Configure AI service logging
        ai_logger = logging.getLogger("geminya.ai")
        ai_logger.setLevel(logging.DEBUG if self.config.debug else logging.INFO)

        # Create MCP handler for MCP-specific logs
        mcp_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "mcp.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5,
            encoding="utf-8",
        )
        mcp_handler.setLevel(logging.DEBUG)
        mcp_handler.setFormatter(file_formatter)

        # Add MCP handler to MCP logger
        mcp_logger = logging.getLogger("geminya.mcp_client")
        mcp_logger.addHandler(mcp_handler)
        mcp_logger.setLevel(logging.DEBUG)
        mcp_logger.propagate = False  # Don't send to root logger to avoid duplication

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance for a specific module.

        Args:
            name: Logger name (usually __name__ from the calling module)

        Returns:
            logging.Logger: Configured logger instance
        """
        if name not in self.loggers:
            self.loggers[name] = logging.getLogger(f"geminya.{name}")
        return self.loggers[name]

    def get_message_logger(self) -> logging.Logger:
        """Get the specialized message processing logger.

        Returns:
            logging.Logger: Message processing logger
        """
        return logging.getLogger("geminya.messages")

    def get_error_logger(self) -> logging.Logger:
        """Get the specialized error logger.

        Returns:
            logging.Logger: Error logger
        """
        return logging.getLogger("geminya.errors")

    def get_ai_logger(self) -> logging.Logger:
        """Get the AI service logger.

        Returns:
            logging.Logger: AI service logger
        """
        return logging.getLogger("geminya.ai")

    def get_mcp_logger(self) -> logging.Logger:
        """Get the MCP client logger.

        Returns:
            logging.Logger: MCP client logger
        """
        return logging.getLogger("geminya.mcp_client")


def setup_logging(config: Config) -> GeminyaLogger:
    """Setup logging for the entire application.

    Args:
        config: Application configuration

    Returns:
        GeminyaLogger: Configured logger manager
    """
    return GeminyaLogger(config)
