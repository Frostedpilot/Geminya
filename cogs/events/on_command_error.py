from discord.ext import commands

from cogs.base_event import BaseEventHandler
from services.container import ServiceContainer


class OnError(BaseEventHandler):
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        """Handle command errors globally."""

        # Log the error
        self.logger.error(f"Command error in {ctx.command}: {error}")

        # Handle specific error types
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
                f"{ctx.author.mention} This command is on cooldown, please wait "
                f"{error.retry_after:.1f} seconds, nya!"
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"{ctx.author.mention} You're missing a required argument: `{error.param}`, nya!"
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"{ctx.author.mention} Invalid argument provided, nya! Please check the command usage."
            )
        elif isinstance(error, commands.CommandNotFound):
            # Ignore command not found errors (they're handled by Discord's slash command system)
            pass
        else:
            # For unknown errors, send a generic message and log to error logger
            await ctx.send("Something went wrong, nya! Please try again later. (´･ω･`)")
            self.services.get_error_logger().error(
                f"Unhandled command error in {ctx.command}: {error}", exc_info=True
            )


async def setup(bot: commands.Bot):
    # Get services from bot instance
    if hasattr(bot, "services"):
        await bot.add_cog(OnError(bot, bot.services))
    else:
        # Fallback for old architecture during transition
        class LegacyOnError(commands.Cog):
            def __init__(self, bot):
                self.bot = bot

            @commands.Cog.listener()
            async def on_command_error(self, ctx, error):
                if isinstance(error, commands.MissingPermissions):
                    await ctx.send(
                        f"{ctx.author.mention} You do not have permission to use this command."
                    )
                elif isinstance(error, commands.NotOwner):
                    await ctx.send(
                        f"{ctx.author.mention} Only the owner of the bot can use this command."
                    )

        await bot.add_cog(LegacyOnError(bot))
