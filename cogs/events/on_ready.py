import discord
from discord.ext import commands

from cogs.base_event import BaseEventHandler
from services.container import ServiceContainer


class OnReady(BaseEventHandler):
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready and connected to Discord."""
        user = self.bot.user
        if not user:
            self.logger.error("Bot user is None in on_ready")
            return

        self.logger.info(f"{user} ({user.name}) has connected to Discord!")

        # Generate invite link
        invite_link = discord.utils.oauth_url(
            user.id,
            permissions=discord.Permissions(),
            scopes=("bot", "applications.commands"),
        )
        self.logger.info(f"Invite link: {invite_link}")

        # Initialize state for all connected guilds and channels
        self._initialize_guilds()
        self._initialize_channels()

        # Log final status
        guild_count = len(self.bot.guilds)
        channel_count = len(
            [
                c
                for c in self.bot.get_all_channels()
                if isinstance(c, discord.TextChannel)
            ]
        )

        self.logger.info(
            f"Bot is ready! Connected to {guild_count} guilds with {channel_count} text channels"
        )

        # Update bot status
        activity = discord.Game(name="with yarn balls | /help")
        await self.bot.change_presence(activity=activity)

    def _initialize_guilds(self) -> None:
        """Initialize state for all connected guilds."""
        for guild in self.bot.guilds:
            server_id = str(guild.id)
            self.state_manager.initialize_server(server_id)
            self.logger.info(f"Initialized server: {guild.name} ({server_id})")

    def _initialize_channels(self) -> None:
        """Initialize history tracking for all text channels."""
        channel_count = 0
        for channel in self.bot.get_all_channels():
            if isinstance(channel, discord.TextChannel):
                self.state_manager.initialize_channel(channel.id)
                channel_count += 1

        self.logger.info(f"Initialized history tracking for {channel_count} channels")


async def setup(bot: commands.Bot):
    # Get services from bot instance
    await bot.add_cog(OnReady(bot, bot.services))
