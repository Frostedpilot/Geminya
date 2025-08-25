"""Spotify music commands using librespot integration.

This cog provides Discord commands for Spotify music playback using
librespot-python for direct streaming without external device dependencies.
"""

import asyncio
import logging
from typing import Optional, List
from datetime import datetime

import discord
from discord.ext import commands
from discord import app_commands

from cogs.base_command import BaseCommand
from services.container import ServiceContainer
from services.spotify_service import (
    SpotifyService,
    SpotifyTrack,
    SpotifyPlaylist,
    SpotifyQuality,
)
from services.music_service import MusicService, QueueItem, QueueMode


class SpotifyView(discord.ui.View):
    """View for Spotify search results with selection buttons."""

    def __init__(self, tracks: List[SpotifyTrack], timeout: int = 60):
        super().__init__(timeout=timeout)
        self.tracks = tracks
        self.selected_track: Optional[SpotifyTrack] = None

        # Add selection buttons (max 10 tracks)
        for i, track in enumerate(tracks[:10]):
            button = discord.ui.Button(
                label=f"{i+1}",
                style=discord.ButtonStyle.primary,
                custom_id=f"track_{i}",
            )
            button.callback = self.make_callback(i)
            self.add_item(button)

        # Add cancel button
        cancel_button = discord.ui.Button(
            label="Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel"
        )
        cancel_button.callback = self.cancel_callback
        self.add_item(cancel_button)

    def make_callback(self, index: int):
        """Create callback for track selection button."""

        async def callback(interaction: discord.Interaction):
            self.selected_track = self.tracks[index]
            await interaction.response.edit_message(
                content=f"✅ Selected: **{self.selected_track.display_name}**",
                view=None,
            )
            self.stop()

        return callback

    async def cancel_callback(self, interaction: discord.Interaction):
        """Handle cancel button."""
        await interaction.response.edit_message(
            content="❌ Selection cancelled.", view=None
        )
        self.stop()


class SpotifyMusicCog(BaseCommand):
    """Discord cog for Spotify music commands."""

    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)
        self.spotify = services.get_spotify_service()
        self.music = services.get_music_service()

        if not self.spotify or not self.music:
            self.logger.error(
                "Spotify services not available - music commands disabled"
            )
            return

        # Set up event callbacks
        self.music.set_callbacks(
            on_track_start=self._on_track_start,
            on_track_end=self._on_track_end,
            on_queue_empty=self._on_queue_empty,
        )

        self.logger.info("Spotify music cog initialized")

    def cog_check(self, ctx: commands.Context) -> bool:
        """Check if Spotify services are available."""
        return self.spotify is not None and self.music is not None

    @app_commands.command(
        name="spotify_join", description="Join your voice channel for Spotify playback"
    )
    async def join(self, interaction: discord.Interaction):
        """Join the user's voice channel."""
        if not interaction.user.voice:
            await interaction.response.send_message(
                "❌ You need to be in a voice channel!", ephemeral=True
            )
            return

        channel = interaction.user.voice.channel
        success = await self.music.join_voice_channel(channel)

        if success:
            await interaction.response.send_message(f"🎵 Joined **{channel.name}**!")
        else:
            await interaction.response.send_message(
                f"❌ Failed to join **{channel.name}**!", ephemeral=True
            )

    @app_commands.command(
        name="spotify_leave",
        description="Leave the voice channel and stop Spotify playback",
    )
    async def leave(self, interaction: discord.Interaction):
        """Leave the voice channel."""
        guild_id = interaction.guild_id
        success = await self.music.leave_voice_channel(guild_id)

        if success:
            await interaction.response.send_message("👋 Left the voice channel!")
        else:
            await interaction.response.send_message(
                "❌ Not connected to a voice channel!", ephemeral=True
            )

    @app_commands.command(
        name="spotify_search", description="Search for music on Spotify"
    )
    async def search(self, interaction: discord.Interaction, query: str):
        """Search for tracks on Spotify."""
        await interaction.response.defer()

        tracks = await self.spotify.search_tracks(query, limit=10)

        if not tracks:
            await interaction.followup.send(f"❌ No tracks found for: **{query}**")
            return

        # Create embed with search results
        embed = discord.Embed(
            title=f"🔍 Spotify Search Results",
            description=f"Found {len(tracks)} tracks for: **{query}**",
            color=0x1DB954,  # Spotify green
        )

        for i, track in enumerate(tracks):
            embed.add_field(
                name=f"{i+1}. {track.name}",
                value=f"**Artist:** {track.artist}\n**Album:** {track.album}\n**Duration:** {track.duration_formatted}",
                inline=False,
            )

        # Create view for selection
        view = SpotifyView(tracks)
        await interaction.followup.send(embed=embed, view=view)

        # Wait for selection
        await view.wait()

        if view.selected_track:
            # Add to queue and play
            if not interaction.user.voice:
                await interaction.followup.send(
                    "❌ You need to be in a voice channel to play music!",
                    ephemeral=True,
                )
                return

            # Auto-join if not connected
            guild_id = interaction.guild_id
            if guild_id not in self.music._voice_clients:
                await self.music.join_voice_channel(interaction.user.voice.channel)

            # Add to queue
            self.music.add_to_queue(guild_id, view.selected_track, interaction.user)

            # Start playing if nothing is playing
            if not self.music.is_playing(guild_id):
                await self.music.play_next(guild_id)

    @app_commands.command(
        name="spotify_play", description="Search and play a track from Spotify"
    )
    async def play(self, interaction: discord.Interaction, query: str):
        """Search and play the first result."""
        if not interaction.user.voice:
            await interaction.response.send_message(
                "❌ You need to be in a voice channel!", ephemeral=True
            )
            return

        await interaction.response.defer()

        tracks = await self.spotify.search_tracks(query, limit=1)

        if not tracks:
            await interaction.followup.send(f"❌ No tracks found for: **{query}**")
            return

        track = tracks[0]
        guild_id = interaction.guild_id

        # Auto-join if not connected
        if guild_id not in self.music._voice_clients:
            await self.music.join_voice_channel(interaction.user.voice.channel)

        # Add to queue
        self.music.add_to_queue(guild_id, track, interaction.user)

        # Start playing if nothing is playing
        if not self.music.is_playing(guild_id):
            await self.music.play_next(guild_id)
            await interaction.followup.send(f"🎵 Now playing: **{track.display_name}**")
        else:
            queue_position = len(self.music.get_queue(guild_id))
            await interaction.followup.send(
                f"➕ Added to queue (#{queue_position}): **{track.display_name}**"
            )

    @app_commands.command(
        name="spotify_playlist", description="Search and queue a Spotify playlist"
    )
    async def playlist(self, interaction: discord.Interaction, query: str):
        """Search and queue a playlist."""
        if not interaction.user.voice:
            await interaction.response.send_message(
                "❌ You need to be in a voice channel!", ephemeral=True
            )
            return

        await interaction.response.defer()

        playlists = await self.spotify.search_playlists(query, limit=1)

        if not playlists:
            await interaction.followup.send(f"❌ No playlists found for: **{query}**")
            return

        playlist = playlists[0]
        tracks = await self.spotify.get_playlist_tracks(playlist.id)

        if not tracks:
            await interaction.followup.send(
                f"❌ Playlist **{playlist.name}** has no playable tracks!"
            )
            return

        guild_id = interaction.guild_id

        # Auto-join if not connected
        if guild_id not in self.music._voice_clients:
            await self.music.join_voice_channel(interaction.user.voice.channel)

        # Add tracks to queue
        self.music.add_playlist_to_queue(guild_id, tracks, interaction.user)

        # Start playing if nothing is playing
        if not self.music.is_playing(guild_id):
            await self.music.play_next(guild_id)

        await interaction.followup.send(
            f"➕ Added **{len(tracks)}** tracks from playlist: **{playlist.name}**"
        )

    @app_commands.command(
        name="spotify_queue", description="Show the current Spotify queue"
    )
    async def queue(self, interaction: discord.Interaction):
        """Show the current music queue."""
        guild_id = interaction.guild_id
        current = self.music.get_current_track(guild_id)
        queue = self.music.get_queue(guild_id)

        embed = discord.Embed(title="🎵 Music Queue", color=0x1DB954)

        if current:
            embed.add_field(
                name="🎶 Now Playing",
                value=f"**{current.track.display_name}**\nRequested by: {current.requested_by.mention}",
                inline=False,
            )

        if queue:
            queue_text = ""
            for i, item in enumerate(queue[:10]):  # Show max 10 items
                queue_text += f"{i+1}. **{item.track.display_name}**\n"

            if len(queue) > 10:
                queue_text += f"\n... and {len(queue) - 10} more tracks"

            embed.add_field(
                name=f"📋 Queue ({len(queue)} tracks)", value=queue_text, inline=False
            )
        else:
            embed.add_field(name="📋 Queue", value="No tracks in queue", inline=False)

        # Add queue info
        mode = self.music.get_queue_mode(guild_id)
        volume = self.music.get_volume(guild_id)

        embed.add_field(
            name="⚙️ Settings",
            value=f"Mode: **{mode.value.title()}**\nVolume: **{volume:.0%}**",
            inline=True,
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="spotify_skip", description="Skip the current Spotify track"
    )
    async def skip(self, interaction: discord.Interaction):
        """Skip the current track."""
        guild_id = interaction.guild_id
        current = self.music.get_current_track(guild_id)

        if not current:
            await interaction.response.send_message(
                "❌ Nothing is currently playing!", ephemeral=True
            )
            return

        success = await self.music.skip(guild_id)

        if success:
            await interaction.response.send_message(
                f"⏭️ Skipped: **{current.track.display_name}**"
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to skip track!", ephemeral=True
            )

    @app_commands.command(
        name="spotify_skip_to", description="Skip to a specific track in the queue"
    )
    @app_commands.describe(position="The position in the queue to skip to (1-based)")
    async def skip_to(self, interaction: discord.Interaction, position: int):
        """Skip to a specific track in the queue."""
        guild_id = interaction.guild_id

        # Validate position
        if position < 1:
            await interaction.response.send_message(
                "❌ Position must be 1 or greater!", ephemeral=True
            )
            return

        # Get current queue to validate position and show what we're skipping to
        queue = self.music.get_queue(guild_id)
        if not queue:
            await interaction.response.send_message(
                "❌ No tracks in queue!", ephemeral=True
            )
            return

        if position > len(queue):
            await interaction.response.send_message(
                f"❌ Queue only has {len(queue)} track(s)!", ephemeral=True
            )
            return

        # Get the track we're skipping to
        target_track = queue[position - 1]

        success = await self.music.skip_to(guild_id, position)
        if success:
            await interaction.response.send_message(
                f"⏭️ Skipped to position {position}: **{target_track.track.display_name}**"
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to skip to track!", ephemeral=True
            )

    @app_commands.command(name="spotify_pause", description="Pause Spotify playback")
    async def pause(self, interaction: discord.Interaction):
        """Pause current playback."""
        guild_id = interaction.guild_id

        if self.music.is_paused(guild_id):
            await interaction.response.send_message(
                "❌ Playback is already paused!", ephemeral=True
            )
            return

        success = await self.music.pause(guild_id)

        if success:
            await interaction.response.send_message("⏸️ Paused playback")
        else:
            await interaction.response.send_message(
                "❌ Nothing is currently playing!", ephemeral=True
            )

    @app_commands.command(name="spotify_resume", description="Resume Spotify playback")
    async def resume(self, interaction: discord.Interaction):
        """Resume paused playback."""
        guild_id = interaction.guild_id

        if not self.music.is_paused(guild_id):
            await interaction.response.send_message(
                "❌ Playback is not paused!", ephemeral=True
            )
            return

        success = await self.music.resume(guild_id)

        if success:
            await interaction.response.send_message("▶️ Resumed playback")
        else:
            await interaction.response.send_message(
                "❌ Failed to resume playback!", ephemeral=True
            )

    @app_commands.command(
        name="spotify_stop", description="Stop Spotify playback and clear queue"
    )
    async def stop(self, interaction: discord.Interaction):
        """Stop playback and clear the queue."""
        guild_id = interaction.guild_id
        success = await self.music.stop(guild_id)

        if success:
            await interaction.response.send_message(
                "⏹️ Stopped playback and cleared queue"
            )
        else:
            await interaction.response.send_message(
                "❌ Nothing is currently playing!", ephemeral=True
            )

    @app_commands.command(
        name="spotify_volume", description="Set Spotify playback volume (0-100)"
    )
    async def volume(
        self, interaction: discord.Interaction, level: app_commands.Range[int, 0, 100]
    ):
        """Set the playback volume."""
        guild_id = interaction.guild_id
        volume = level / 100.0

        self.music.set_volume(guild_id, volume)
        await interaction.response.send_message(f"🔊 Volume set to **{level}%**")

    @app_commands.command(
        name="spotify_now", description="Show currently playing Spotify track"
    )
    async def now_playing(self, interaction: discord.Interaction):
        """Show the currently playing track."""
        guild_id = interaction.guild_id
        current = self.music.get_current_track(guild_id)

        if not current:
            await interaction.response.send_message(
                "❌ Nothing is currently playing!", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{current.track.display_name}**",
            color=0x1DB954,
        )

        embed.add_field(name="Album", value=current.track.album, inline=True)
        embed.add_field(
            name="Duration", value=current.track.duration_formatted, inline=True
        )
        embed.add_field(
            name="Requested by", value=current.requested_by.mention, inline=True
        )

        if current.track.external_url:
            embed.add_field(
                name="Spotify Link",
                value=f"[Open in Spotify]({current.track.external_url})",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    async def _on_track_start(self, guild_id: int, item: QueueItem):
        """Handle track start event."""
        self.logger.info(
            f"Track started in guild {guild_id}: {item.track.display_name}"
        )

    async def _on_track_end(self, guild_id: int, item: QueueItem):
        """Handle track end event."""
        self.logger.info(f"Track ended in guild {guild_id}: {item.track.display_name}")

    async def _on_queue_empty(self, guild_id: int):
        """Handle queue empty event."""
        self.logger.info(f"Queue empty in guild {guild_id}")


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    services = getattr(bot, "services", None)
    if services and services.get_spotify_service() and services.get_music_service():
        await bot.add_cog(SpotifyMusicCog(bot, services))
    else:
        logging.getLogger(__name__).warning(
            "Spotify services not available - music cog not loaded"
        )
