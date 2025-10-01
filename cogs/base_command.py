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
        self.ai_service = services.ai_service
        self.logger = services.get_logger(self.__class__.__name__)

        self.logger.debug(f"Initialized {self.__class__.__name__}")

    async def queue_command(self, ctx: commands.Context, command_impl, *args, **kwargs):
        """
        Queue a command for sequential execution per user, blocking banned users.
        """
        from utils.ban_utils import is_user_banned
        user_id = ctx.author.id
        if is_user_banned(user_id):
            await ctx.send(f"Sorry {ctx.author.mention}, you are banned from using this bot.")
            self.logger.warning(f"Blocked banned user {user_id} from using command: {ctx.command}")
            return
        command_queue = self.services.get_command_queue()
        return await command_queue.enqueue_command(
            str(user_id), 
            command_impl, 
            ctx,
            *args, 
            **kwargs
        )

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
