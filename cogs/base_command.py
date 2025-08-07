"""Base classes for commands with dependency injection."""

import logging
from discord.ext import commands

from services.container import ServiceContainer


class BaseCommand(commands.Cog):
    """Base class for all command cogs with service dependencies."""

    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        self.bot = bot
        self.services = services
        self.config = services.config
        self.state_manager = services.state_manager
        self.llm_manager = services.llm_manager
        self.logger = services.get_logger(self.__class__.__name__)

        self.logger.debug(f"Initialized {self.__class__.__name__}")

    async def cog_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        """Handle command errors for this cog."""
        self.logger.error(f"Command error in {ctx.command}: {error}")

        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                f"{ctx.author.mention} You don't have permission to use this command, nya! (´･ω･`)"
            )
        elif isinstance(error, commands.NotOwner):
            await ctx.send(
                f"{ctx.author.mention} Only my owner can use this command, nya! (｡•́︿•̀｡)"
            )
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"{ctx.author.mention} This command is on cooldown, please wait {error.retry_after:.1f} seconds, nya!"
            )
        else:
            await ctx.send("Something went wrong, nya! Please try again later. (´･ω･`)")

            # Log to error logger for serious issues
            self.services.get_error_logger().error(
                f"Unhandled command error in {ctx.command}: {error}", exc_info=True
            )
