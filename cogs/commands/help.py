import discord
from discord.ext import commands

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


class HelpCog(BaseCommand):
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

    @commands.hybrid_command(
        name="help", description="Display available commands and bot information."
    )
    async def help(self, ctx: commands.Context):
        """Display help information for available commands."""
        embed = discord.Embed(
            title="Geminya Commands",
            description="Here are my available commands, nya! (＾◡＾)",
            color=0x03A64B,
        )

        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        # Get all commands
        command_tree = self.bot.commands
        for command in command_tree:
            if command.hidden:
                continue
            command_description = command.description or "Not implemented yet, nyaa!"
            embed.add_field(
                name=f"/{command.name}", value=command_description, inline=False
            )

        # Add footer with bot info
        embed.set_footer(
            text=f"Running Geminya v1.0 | {len(command_tree)} commands available"
        )

        await ctx.send(embed=embed)
        self.logger.info(f"Help command used by {ctx.author} in {ctx.guild}")


async def setup(bot: commands.Bot):
    # Get services from bot instance
    await bot.add_cog(HelpCog(bot, bot.services))
