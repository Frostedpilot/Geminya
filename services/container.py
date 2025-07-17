"""Service container for dependency injection in Geminya bot."""

import logging
from typing import Optional

from config import Config
from utils.logging import setup_logging
from services.state_manager import StateManager
from services.ai_service import AIService
from services.error_handler import ErrorHandler


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
        self.ai_service = AIService(
            config, self.state_manager, self.logger_manager.get_ai_logger()
        )

        self.logger.info("Service container created")

    async def initialize_all(self) -> None:
        """Initialize all services."""
        self.logger.info("Initializing all services...")

        try:
            await self.state_manager.initialize()
            await self.ai_service.initialize()

            self.logger.info("All services initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            await self.cleanup_all()
            raise

    async def cleanup_all(self) -> None:
        """Cleanup all services."""
        self.logger.info("Cleaning up all services...")

        try:
            if hasattr(self, "ai_service"):
                await self.ai_service.cleanup()
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
