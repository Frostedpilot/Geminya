"""Base classes for event handlers with dependency injection."""

import logging
from discord.ext import commands

from services.container import ServiceContainer


class BaseEventHandler(commands.Cog):
    """Base class for all event handler cogs with service dependencies."""

    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        self.bot = bot
        self.services = services
        self.config = services.config
        self.state_manager = services.state_manager
        self.ai_service = services.ai_service
        self.logger = services.get_logger(self.__class__.__name__)

        self.logger.debug(f"Initialized {self.__class__.__name__}")

    async def cog_load(self) -> None:
        """Called when the cog is loaded."""
        self.logger.info(f"Event handler {self.__class__.__name__} loaded")

    async def cog_unload(self) -> None:
        """Called when the cog is unloaded."""
        self.logger.info(f"Event handler {self.__class__.__name__} unloaded")
