import logging
import asyncio

import discord
from discord.ext import commands

from cogs.base_event import BaseEventHandler
from services.container import ServiceContainer


class OnVoiceStateUpdate(BaseEventHandler):
    """Handle voice state updates to detect bot disconnections."""

    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """Handle voice state updates."""
        # Only handle the bot's own voice state changes
        if member.id != self.bot.user.id:
            return

        # Check if the bot was disconnected from a voice channel
        if before.channel and not after.channel:
            guild_id = before.channel.guild.id
            self.logger.info(
                f"Bot was disconnected from voice channel in guild {guild_id}, waiting to see if it reconnects..."
            )

            # Wait a moment to see if it's a transient disconnect (e.g. discord.py retrying)
            await asyncio.sleep(2)
            
            # Re-check current voice state
            guild = self.bot.get_guild(guild_id)
            if guild:
                me = guild.get_member(self.bot.user.id)
                if me and me.voice and me.voice.channel:
                    self.logger.info(f"Bot reconnected to {me.voice.channel.name} automatically, skipping cleanup")
                    return

            # Still disconnected, handle forced disconnect
            try:
                music_service = self.services.music_service
                if music_service:
                    await music_service.handle_forced_disconnect(guild_id)
            except Exception as e:
                self.logger.error(f"Error handling voice disconnect: {e}")


async def setup(bot: commands.Bot):
    """Setup the cog."""
    await bot.add_cog(OnVoiceStateUpdate(bot, bot.services))
