"""Service container for dependency injection in Geminya bot."""

from __future__ import annotations
import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from config import Config

from utils.logging import setup_logging
from services.state_manager import StateManager
from services.llm import LLMManager
from services.ai_service import AIService
from services.error_handler import ErrorHandler
from services.mcp import MCPClientManager
from services.database import DatabaseService
from services.waifu_service import WaifuService
from services.command_queue import CommandQueueService


class ServiceContainer:
    """Container for managing all bot services and dependencies."""

    def __init__(self, config: Config):
        self.config = config

        # Initialize logging first
        self.logger_manager = setup_logging(config)
        self.logger = self.logger_manager.get_logger("services")

        # Initialize error handler
        self.error_handler = ErrorHandler(
            config, self.logger_manager.get_error_logger()
        )

        # Initialize services
        self.state_manager = StateManager(
            config, self.logger_manager.get_logger("state")
        )

        self.llm_manager = LLMManager(
            config,
            self.state_manager,
            self.logger_manager.get_ai_logger(),
        )

        self.mcp_client = MCPClientManager(
            config,
            self.state_manager,
            self.llm_manager,
            self.logger_manager.get_mcp_logger(),
        )

        # Create AI Service as the main orchestrator
        self.ai_service = AIService(
            config,
            self.state_manager,
            self.llm_manager,
            self.mcp_client,
            self.logger_manager.get_ai_logger(),
        )

        # Initialize Waifu Academy services
        self.database = DatabaseService(config)
        self.waifu_service = WaifuService(self.database)
        self.command_queue = CommandQueueService()

        self.logger.info("Service container created")

    async def initialize_all(self) -> None:
        """Initialize all services."""
        self.logger.info("Initializing all services...")

        try:
            await self.state_manager.initialize()
            await self.llm_manager.initialize()

            # Initialize Waifu Academy services
            await self.waifu_service.initialize()

            # MCP servers will connect automatically when needed
            self.logger.info(
                "MCP client manager ready (servers will connect on demand)"
            )

            self.logger.info("All services initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            await self.cleanup_all()
            raise

    async def cleanup_all(self) -> None:
        """Cleanup all services."""
        self.logger.info("Cleaning up all services...")

        try:
            if hasattr(self, "command_queue"):
                await self.command_queue.shutdown()
            if hasattr(self, "waifu_service"):
                await self.waifu_service.close()
            if hasattr(self, "llm_manager"):
                await self.llm_manager.cleanup()
            if hasattr(self, "mcp_client"):
                await self.mcp_client.disconnect_all()
            if hasattr(self, "state_manager"):
                await self.state_manager.cleanup()

            self.logger.info("All services cleaned up successfully")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger for a specific module.

        Args:
            name: Logger name

        Returns:
            logging.Logger: Logger instance
        """
        return self.logger_manager.get_logger(name)

    def get_message_logger(self) -> logging.Logger:
        """Get the message processing logger."""
        return self.logger_manager.get_message_logger()

    def get_error_logger(self) -> logging.Logger:
        """Get the error logger."""
        return self.logger_manager.get_error_logger()

    def get_ai_service(self) -> AIService:
        """Get the AI service."""
        return self.ai_service

    def get_waifu_service(self) -> WaifuService:
        """Get the waifu service."""
        return self.waifu_service

    def get_command_queue(self) -> CommandQueueService:
        """Get the command queue service."""
        return self.command_queue
