import asyncio
from itertools import cycle
import discord
from discord.ext import commands


class OnReady(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        discord.client._log.info(
            f"{self.bot.user} aka {self.bot.user.name} has connected to Discord!"
        )
        invite_link = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=discord.Permissions(),
            scopes=("bot", "applications.commands"),
        )
        discord.client._log.info(f"Invite link: {invite_link}")

        self.bot.history = {}
        for channel in self.bot.get_all_channels():
            if isinstance(channel, discord.TextChannel):
                self.bot.history[channel.id] = []
                discord.client._log.info(
                    f"Initialized history for channel {channel.name} ({channel.id})"
                )


async def setup(bot):
    await bot.add_cog(OnReady(bot))
