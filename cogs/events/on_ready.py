from itertools import cycle
from utils.config_load import lore_book_load
import discord
from discord.ext import commands

from constants import DEFAULT_MODEL


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

        self.bot.model = {}

        for guild in self.bot.guilds:
            server_id = str(guild.id)
            self.bot.model[server_id] = DEFAULT_MODEL
            discord.client._log.info(
                f"Set default model for server {guild.name} ({server_id}) to {DEFAULT_MODEL}"
            )

        lore_book_load(self.bot)
        if self.bot.lore_book:
            discord.client._log.info(
                "Lore book loaded successfully with trigger words and example responses."
            )
        else:
            discord.client._log.warning("Lore book is empty or not loaded correctly.")
            self.bot.lore_book = None

        discord.client._log.info("Bot is ready to receive messages!")


async def setup(bot):
    await bot.add_cog(OnReady(bot))
