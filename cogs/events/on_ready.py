import asyncio
from itertools import cycle
import discord
from discord.ext import commands


class OnReady(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.bot.user} aka {self.bot.user.name} has connected to Discord!")
        invite_link = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=discord.Permissions(),
            scopes=("bot", "applications.commands"),
        )
        print(f"Invite link: {invite_link}")


async def setup(bot):
    await bot.add_cog(OnReady(bot))
