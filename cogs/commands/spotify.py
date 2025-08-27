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
from services.spotify_cache import spotify_cache


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


class SpotifyPlaylistView(discord.ui.View):
    """View for Spotify playlist search results with selection buttons."""

    def __init__(
        self,
        playlists: List[SpotifyPlaylist],
        playlist_previews: dict,
        timeout: int = 60,
    ):
        super().__init__(timeout=timeout)
        self.playlists = playlists
        self.playlist_previews = (
            playlist_previews  # Dict of playlist_id -> List[SpotifyTrack]
        )
        self.selected_playlist: Optional[SpotifyPlaylist] = None

        # Add selection buttons (max 10 playlists)
        for i, playlist in enumerate(playlists[:10]):
            button = discord.ui.Button(
                label=f"{i+1}",
                style=discord.ButtonStyle.primary,
                custom_id=f"playlist_{i}",
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
        """Create callback for playlist selection button."""

        async def callback(interaction: discord.Interaction):
            self.selected_playlist = self.playlists[index]
            await interaction.response.edit_message(
                content=f"✅ Selected: **{self.selected_playlist.name}** by {self.selected_playlist.owner}",
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


class LazyLoadedSpotifyView(discord.ui.View):
    """Lazy-loaded paginated view for Spotify search results."""

    def __init__(
        self, search_type: str, query: str, spotify_service, timeout: int = 60
    ):
        super().__init__(timeout=timeout)
        self.search_type = search_type  # "tracks" or "playlists"
        self.query = query
        self.spotify_service = spotify_service
        self.current_page = 0
        self.items_per_page = 5 if search_type == "tracks" else 3
        self.max_items = 50 if search_type == "tracks" else 30
        self.max_pages = (self.max_items - 1) // self.items_per_page + 1
        self.selected_item = None

        # Cache for loaded pages
        self.page_cache = {}
        self.playlist_tracks_cache = {}  # For playlist track previews

        # Update buttons for current page
        self._update_buttons()

    def _get_cache_key(self, page: int) -> str:
        """Generate cache key for a specific page."""
        return f"{self.search_type}:{self.query}:page_{page}"

    async def _load_page_data(self, page: int) -> List:
        """Load data for a specific page with caching."""
        cache_key = self._get_cache_key(page)

        # Check cache first
        cached_data = spotify_cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        # Calculate offset for this page
        offset = page * self.items_per_page

        # Load data from Spotify API
        if self.search_type == "tracks":
            # For tracks, we can use offset parameter
            data = self.spotify_service.search_tracks(
                self.query, limit=self.items_per_page, offset=offset
            )
        else:
            # For playlists, we need to load more and slice
            # (Spotify playlist search doesn't support offset well)
            all_data = self.spotify_service.search_playlists(
                self.query, limit=min(30, offset + self.items_per_page)
            )
            data = all_data[offset : offset + self.items_per_page]

            # Load track previews for playlists
            for playlist in data:
                preview_key = f"playlist_tracks:{playlist.id}"
                if spotify_cache.get(preview_key) is None:
                    try:
                        tracks = self.spotify_service.get_playlist_tracks(playlist.id)
                        # Cache the full track list for playlist command use
                        spotify_cache.set(
                            preview_key, tracks, ttl=600
                        )  # 10 minutes for playlist data
                    except Exception as e:
                        logging.warning(
                            f"Failed to load playlist tracks for {playlist.id}: {e}"
                        )

        # Cache the page data
        spotify_cache.set(cache_key, data, ttl=300)  # 5 minutes for search results
        return data

    def _update_buttons(self):
        """Update buttons based on current page."""
        self.clear_items()

        # We don't know exact item count yet, so show navigation based on theoretical max
        start_idx = self.current_page * self.items_per_page

        # Add selection buttons placeholder (will be updated when data loads)
        for i in range(self.items_per_page):
            global_index = start_idx + i
            if global_index < self.max_items:
                button = discord.ui.Button(
                    label=f"{global_index + 1}",
                    style=discord.ButtonStyle.primary,
                    custom_id=f"select_{global_index}",
                    row=0 if i < 3 else 1,
                    disabled=True,  # Will be enabled when data loads
                )
                button.callback = self.make_select_callback(global_index)
                self.add_item(button)

        # Navigation buttons (row 2)
        if self.max_pages > 1:
            # Previous page button
            prev_button = discord.ui.Button(
                label="◀️ Previous",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page == 0,
                row=2,
            )
            prev_button.callback = self.previous_page
            self.add_item(prev_button)

            # Page indicator
            page_button = discord.ui.Button(
                label=f"Page {self.current_page + 1}/{self.max_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True,
                row=2,
            )
            self.add_item(page_button)

            # Next page button
            next_button = discord.ui.Button(
                label="Next ▶️",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page >= self.max_pages - 1,
                row=2,
            )
            next_button.callback = self.next_page
            self.add_item(next_button)

        # Cancel button (row 3)
        cancel_button = discord.ui.Button(
            label="❌ Cancel", style=discord.ButtonStyle.danger, row=3
        )
        cancel_button.callback = self.cancel_callback
        self.add_item(cancel_button)

    async def _enable_selection_buttons(self, page_data: List):
        """Enable selection buttons based on loaded data."""
        start_idx = self.current_page * self.items_per_page

        # Enable buttons for available items
        for item in self.children:
            if (
                hasattr(item, "custom_id")
                and item.custom_id
                and item.custom_id.startswith("select_")
            ):
                global_index = int(item.custom_id.split("_")[1])
                local_index = global_index - start_idx
                item.disabled = local_index >= len(page_data)

    def make_select_callback(self, index: int):
        """Create callback for item selection."""

        async def callback(interaction: discord.Interaction):
            # Load current page data to get the item
            page_data = await self._load_page_data(self.current_page)
            start_idx = self.current_page * self.items_per_page
            local_index = index - start_idx

            if local_index < len(page_data):
                self.selected_item = page_data[local_index]
                item_name = getattr(
                    self.selected_item, "display_name", None
                ) or getattr(self.selected_item, "name", "Unknown")
                await interaction.response.edit_message(
                    content=f"✅ Selected: **{item_name}**",
                    view=None,
                )
                self.stop()
            else:
                await interaction.response.defer()

        return callback

    async def previous_page(self, interaction: discord.Interaction):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_buttons()

            # Load and show new page
            embed = await self._create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    async def next_page(self, interaction: discord.Interaction):
        """Go to next page."""
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self._update_buttons()

            # Load and show new page
            embed = await self._create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    async def cancel_callback(self, interaction: discord.Interaction):
        """Handle cancel button."""
        await interaction.response.edit_message(
            content="❌ Selection cancelled.", view=None
        )
        self.stop()

    async def _create_embed(self):
        """Create embed for current page with lazy loading."""
        # Show loading message first
        embed = discord.Embed(
            title=f"🔍 Spotify {'Track' if self.search_type == 'tracks' else 'Playlist'} Search Results",
            description=f"Loading page {self.current_page + 1}...",
            color=0x1DB954,
        )

        try:
            # Load page data
            page_data = await self._load_page_data(self.current_page)

            if not page_data:
                embed.description = f"No {'tracks' if self.search_type == 'tracks' else 'playlists'} found on this page."
                return embed

            # Update embed with actual data
            embed.description = f"Found results for: `{self.query}`\nPage {self.current_page + 1} of {self.max_pages}"

            start_idx = self.current_page * self.items_per_page

            if self.search_type == "tracks":
                for i, track in enumerate(page_data):
                    global_num = start_idx + i + 1
                    embed.add_field(
                        name=f"{global_num}. {track.name}",
                        value=f"**Artist:** {track.artist}\n**Duration:** {track.duration_formatted}",
                        inline=True,
                    )
            else:
                for i, playlist in enumerate(page_data):
                    global_num = start_idx + i + 1

                    # Get cached playlist preview
                    preview_key = f"playlist_tracks:{playlist.id}"
                    preview_data = spotify_cache.get(preview_key)

                    if preview_data and isinstance(preview_data, list):
                        # preview_data is now the full track list
                        tracks = preview_data
                        preview_tracks = tracks[:3]  # Show first 3 tracks
                        total_tracks = len(tracks)

                        # Format track list
                        if preview_tracks:
                            track_list = "\n".join(
                                [f"• {track.display_name}" for track in preview_tracks]
                            )
                            if total_tracks > 3:
                                track_list += (
                                    f"\n... and {total_tracks - 3} more tracks"
                                )
                        else:
                            track_list = "No playable tracks found"
                    else:
                        track_list = "Loading track preview..."

                    embed.add_field(
                        name=f"{global_num}. {playlist.name}",
                        value=f"**By:** {playlist.owner}\n**Tracks:**\n{track_list}",
                        inline=False,
                    )

            # Enable selection buttons for loaded items
            await self._enable_selection_buttons(page_data)

        except Exception as e:
            embed.description = f"Error loading page: {e}"
            embed.color = 0xFF0000

        return embed


class PaginatedSpotifyView(discord.ui.View):
    """Paginated view for Spotify search results with navigation."""

    def __init__(self, items: List, items_per_page: int = 5, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.items = items
        self.items_per_page = items_per_page
        self.current_page = 0
        self.max_pages = (len(items) - 1) // items_per_page + 1
        self.selected_item = None

        # Update buttons for current page
        self._update_buttons()

    def _update_buttons(self):
        """Update buttons based on current page."""
        self.clear_items()

        # Get items for current page
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = self.items[start_idx:end_idx]

        # Add selection buttons for current page items
        for i, item in enumerate(page_items):
            global_index = start_idx + i
            button = discord.ui.Button(
                label=f"{global_index + 1}",
                style=discord.ButtonStyle.primary,
                custom_id=f"select_{global_index}",
                row=0 if i < 3 else 1,
            )
            button.callback = self.make_select_callback(global_index)
            self.add_item(button)

        # Navigation buttons (row 2)
        if self.max_pages > 1:
            # Previous page button
            prev_button = discord.ui.Button(
                label="◀️ Previous",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page == 0,
                row=2,
            )
            prev_button.callback = self.previous_page
            self.add_item(prev_button)

            # Page indicator
            page_button = discord.ui.Button(
                label=f"Page {self.current_page + 1}/{self.max_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True,
                row=2,
            )
            self.add_item(page_button)

            # Next page button
            next_button = discord.ui.Button(
                label="Next ▶️",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page >= self.max_pages - 1,
                row=2,
            )
            next_button.callback = self.next_page
            self.add_item(next_button)

        # Cancel button (row 3)
        cancel_button = discord.ui.Button(
            label="❌ Cancel", style=discord.ButtonStyle.danger, row=3
        )
        cancel_button.callback = self.cancel_callback
        self.add_item(cancel_button)

    def make_select_callback(self, index: int):
        """Create callback for item selection."""

        async def callback(interaction: discord.Interaction):
            self.selected_item = self.items[index]
            item_name = getattr(self.selected_item, "display_name", None) or getattr(
                self.selected_item, "name", "Unknown"
            )
            await interaction.response.edit_message(
                content=f"✅ Selected: **{item_name}**",
                view=None,
            )
            self.stop()

        return callback

    async def previous_page(self, interaction: discord.Interaction):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_buttons()

            # Update the embed for new page
            embed = await self._create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    async def next_page(self, interaction: discord.Interaction):
        """Go to next page."""
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self._update_buttons()

            # Update the embed for new page
            embed = await self._create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    async def cancel_callback(self, interaction: discord.Interaction):
        """Handle cancel button."""
        await interaction.response.edit_message(
            content="❌ Selection cancelled.", view=None
        )
        self.stop()

    async def _create_embed(self):
        """Create embed for current page - to be overridden by subclasses."""
        return discord.Embed(title="Spotify Results", description="Select an item")


class PaginatedTrackView(PaginatedSpotifyView):
    """Paginated view specifically for track search results."""

    def __init__(self, tracks: List[SpotifyTrack], query: str, timeout: int = 60):
        self.query = query
        super().__init__(tracks, items_per_page=5, timeout=timeout)

    async def _create_embed(self):
        """Create embed for track search results."""
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_tracks = self.items[start_idx:end_idx]

        embed = discord.Embed(
            title="🔍 Spotify Track Search Results",
            description=f"Found **{len(self.items)}** track(s) for: `{self.query}`\nPage {self.current_page + 1} of {self.max_pages}",
            color=0x1DB954,
            timestamp=datetime.now(),
        )

        for i, track in enumerate(page_tracks):
            global_num = start_idx + i + 1
            embed.add_field(
                name=f"{global_num}. {track.name}",
                value=f"**Artist:** {track.artist}\n**Duration:** {track.duration_formatted}",
                inline=True,
            )

        return embed


class PaginatedPlaylistView(PaginatedSpotifyView):
    """Paginated view specifically for playlist search results."""

    def __init__(
        self,
        playlists: List[SpotifyPlaylist],
        playlist_previews: dict,
        playlist_full_tracks: dict,
        query: str,
        timeout: int = 60,
    ):
        self.query = query
        self.playlist_previews = playlist_previews
        self.playlist_full_tracks = playlist_full_tracks
        super().__init__(
            playlists, items_per_page=3, timeout=timeout
        )  # Fewer per page due to track previews

    async def _create_embed(self):
        """Create embed for playlist search results."""
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_playlists = self.items[start_idx:end_idx]

        embed = discord.Embed(
            title="🔍 Spotify Playlist Search Results",
            description=f"Found **{len(self.items)}** playlist(s) for: `{self.query}`\nPage {self.current_page + 1} of {self.max_pages}",
            color=0x1DB954,
            timestamp=datetime.now(),
        )

        for i, playlist in enumerate(page_playlists):
            global_num = start_idx + i + 1
            preview_tracks = self.playlist_previews.get(playlist.id, [])

            # Format track list
            if preview_tracks:
                track_list = "\n".join(
                    [f"• {track.display_name}" for track in preview_tracks]
                )
                full_tracks = self.playlist_full_tracks.get(playlist.id, [])
                if len(full_tracks) > 3:
                    track_list += f"\n... and {len(full_tracks) - 3} more tracks"
            else:
                track_list = "No playable tracks found"

            embed.add_field(
                name=f"{global_num}. {playlist.name}",
                value=f"**By:** {playlist.owner}\n**Tracks:**\n{track_list}",
                inline=False,
            )

        return embed


class PaginatedQueueView(discord.ui.View):
    """Paginated view for the music queue."""

    def __init__(
        self,
        queue_items: List,
        current_track=None,
        guild_id: int = None,
        music_service=None,
        timeout: int = 60,
    ):
        super().__init__(timeout=timeout)
        self.queue_items = queue_items
        self.current_track = current_track
        self.guild_id = guild_id
        self.music_service = music_service
        self.items_per_page = 10
        self.current_page = 0
        self.max_pages = (
            (len(queue_items) - 1) // self.items_per_page + 1 if queue_items else 1
        )

        # Update buttons for current page
        self._update_buttons()

    def _update_buttons(self):
        """Update buttons based on current page."""
        self.clear_items()

        # Only add navigation if there are multiple pages
        if self.max_pages > 1:
            # Previous page button
            prev_button = discord.ui.Button(
                label="◀️ Previous",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page == 0,
                row=0,
            )
            prev_button.callback = self.previous_page
            self.add_item(prev_button)

            # Page indicator
            page_button = discord.ui.Button(
                label=f"Page {self.current_page + 1}/{self.max_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True,
                row=0,
            )
            self.add_item(page_button)

            # Next page button
            next_button = discord.ui.Button(
                label="Next ▶️",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page >= self.max_pages - 1,
                row=0,
            )
            next_button.callback = self.next_page
            self.add_item(next_button)

        # Add refresh button
        refresh_button = discord.ui.Button(
            label="🔄 Refresh", style=discord.ButtonStyle.primary, row=1
        )
        refresh_button.callback = self.refresh_queue
        self.add_item(refresh_button)

    async def previous_page(self, interaction: discord.Interaction):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_buttons()

            # Update the embed for new page
            embed = self._create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    async def next_page(self, interaction: discord.Interaction):
        """Go to next page."""
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self._update_buttons()

            # Update the embed for new page
            embed = self._create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    async def refresh_queue(self, interaction: discord.Interaction):
        """Refresh the queue data."""
        if self.music_service and self.guild_id:
            # Get updated queue data
            self.current_track = self.music_service.get_current_track(self.guild_id)

            # Get the appropriate queue based on mode
            mode = self.music_service.get_queue_mode(self.guild_id)
            if mode == QueueMode.LOOP_QUEUE:
                # For loop queue mode, show the snapshot queue with position offset
                snapshot = self.music_service.get_queue_snapshot(self.guild_id)
                snapshot_position = self.music_service.get_snapshot_position(
                    self.guild_id
                )

                # Show snapshot from current position, then loop back
                if snapshot:
                    self.queue_items = (
                        snapshot[snapshot_position:] + snapshot[:snapshot_position]
                    )
                else:
                    self.queue_items = []
            else:
                # Normal mode - just show regular queue
                self.queue_items = self.music_service.get_queue(self.guild_id)

            self.max_pages = (
                (len(self.queue_items) - 1) // self.items_per_page + 1
                if self.queue_items
                else 1
            )

            # Reset to first page if current page is now invalid
            if self.current_page >= self.max_pages:
                self.current_page = 0

            self._update_buttons()
            embed = self._create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    def _create_embed(self):
        """Create embed for current page."""
        embed = discord.Embed(title="🎵 Music Queue", color=0x1DB954)

        # Show currently playing track
        if self.current_track:
            embed.add_field(
                name="🎶 Now Playing",
                value=f"**{self.current_track.track.display_name}**\nRequested by: {self.current_track.requested_by.mention}",
                inline=False,
            )

        # Get mode info for queue display
        mode = None
        queue_title = "📋 Queue"
        if self.music_service and self.guild_id:
            mode = self.music_service.get_queue_mode(self.guild_id)
            if mode == QueueMode.LOOP_QUEUE:
                queue_title = "📋 Queue (Loop Mode)"

        # Show queue items for current page
        if self.queue_items:
            start_idx = self.current_page * self.items_per_page
            end_idx = start_idx + self.items_per_page
            page_items = self.queue_items[start_idx:end_idx]

            queue_text = ""
            for i, item in enumerate(page_items):
                global_index = start_idx + i + 1

                # Defensive check for item type
                if isinstance(item, str):
                    # Handle case where item is a string (shouldn't happen, but let's be safe)
                    queue_text += f"{global_index}. **{item}** ⚠️ *Invalid queue item*\n"
                    continue

                # Check if item has track attribute
                if not hasattr(item, "track"):
                    queue_text += (
                        f"{global_index}. **Unknown Track** ⚠️ *Invalid queue item*\n"
                    )
                    continue

                # Check if track is unavailable
                if hasattr(item.track, "is_playable") and not item.track.is_playable:
                    queue_text += f"{global_index}. ~~**{item.track.display_name}**~~ ⚠️ *Unavailable*\n"
                else:
                    queue_text += f"{global_index}. **{item.track.display_name}**\n"

            # Add pagination info if there are multiple pages
            page_info = ""
            if self.max_pages > 1:
                page_info = f" (Page {self.current_page + 1}/{self.max_pages})"

            embed.add_field(
                name=f"{queue_title} ({len(self.queue_items)} tracks){page_info}",
                value=queue_text,
                inline=False,
            )
        else:
            embed.add_field(name=queue_title, value="No tracks in queue", inline=False)

        # Add queue info if we have access to the music service
        if self.music_service and self.guild_id:
            mode = self.music_service.get_queue_mode(self.guild_id)
            volume = self.music_service.get_volume(self.guild_id)
            is_shuffled = self.music_service.is_queue_shuffled(self.guild_id)

            mode_display = f"**{mode.value.replace('_', ' ').title()}**"
            if is_shuffled:
                mode_display += " 🔀"

            settings_text = f"Mode: {mode_display}\nVolume: **{volume:.0%}**"

            # Add extra info for queue loop mode
            if mode == QueueMode.LOOP_QUEUE:
                snapshot = self.music_service.get_queue_snapshot(self.guild_id)
                position = self.music_service.get_snapshot_position(self.guild_id)

                settings_text += f"\nSnapshot: **{len(snapshot)}** tracks"
                if snapshot:
                    settings_text += (
                        f"\nSnapshot pos: **{position + 1}/{len(snapshot)}**"
                    )

            embed.add_field(
                name="⚙️ Settings",
                value=settings_text,
                inline=True,
            )

        return embed


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
        guild_id = interaction.guild_id

        # Check if there's a preserved queue before joining
        had_preserved_music = self.music.has_queued_music(guild_id)

        success = await self.music.join_voice_channel(channel)

        if success:
            message = f"🎵 Joined **{channel.name}**!"
            if had_preserved_music:
                message += "\n🎶 Resumed your preserved queue!"
            await interaction.response.send_message(message)
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

        # Check if there's a queue before leaving
        queue = self.music.get_queue(guild_id)
        current_track = self.music.get_current_track(guild_id)
        has_music = bool(queue or current_track)

        success = await self.music.leave_voice_channel(guild_id)

        if success:
            message = "👋 Left the voice channel!"
            if has_music:
                message += (
                    "\n💾 Your queue has been preserved and will resume when I rejoin!"
                )
            await interaction.response.send_message(message)
        else:
            await interaction.response.send_message(
                "❌ Not connected to a voice channel!", ephemeral=True
            )

    @app_commands.command(
        name="spotify_search", description="Search for music on Spotify"
    )
    async def search(self, interaction: discord.Interaction, query: str):
        """Search for tracks on Spotify with lazy loading."""
        await interaction.response.defer()

        # Create lazy loading view for track selection
        view = LazyLoadedSpotifyView("tracks", query, self.spotify)
        embed = await view._create_embed()
        await interaction.followup.send(embed=embed, view=view)

        # Wait for selection
        await view.wait()

        if view.selected_item:
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
            self.music.add_to_queue(guild_id, view.selected_item, interaction.user)

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

        tracks = self.spotify.search_tracks(query, limit=1)

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
        """Search and select a playlist with lazy loading."""
        if not interaction.user.voice:
            await interaction.response.send_message(
                "❌ You need to be in a voice channel!", ephemeral=True
            )
            return

        await interaction.response.defer()

        # Create lazy loading view for playlist selection
        view = LazyLoadedSpotifyView("playlists", query, self.spotify)
        embed = await view._create_embed()
        await interaction.followup.send(embed=embed, view=view)

        # Wait for user selection
        await view.wait()

        if view.selected_item is None:
            return

        # Get all tracks from selected playlist (from cache or load fresh)
        selected_playlist = view.selected_item
        cache_key = f"playlist_tracks:{selected_playlist.id}"
        cached_data = spotify_cache.get(cache_key)

        if cached_data and isinstance(cached_data, list):
            tracks = cached_data
            self.logger.info(f"Using cached playlist tracks: {len(tracks)} tracks")
        else:
            self.logger.info(
                f"Loading fresh playlist tracks for {selected_playlist.id}"
            )
            tracks = self.spotify.get_playlist_tracks(selected_playlist.id)
            # Cache the tracks for future use
            if tracks:
                spotify_cache.set(cache_key, tracks, ttl=600)  # 10 minutes

        if not tracks:
            await interaction.followup.send(
                f"❌ Playlist **{selected_playlist.name}** has no playable tracks!"
            )
            return

        guild_id = interaction.guild_id

        # Auto-join if not connected
        if guild_id not in self.music._voice_clients:
            await self.music.join_voice_channel(interaction.user.voice.channel)

        # Add tracks to queue
        added_count, skipped_count = self.music.add_playlist_to_queue(
            guild_id, tracks, interaction.user
        )

        # Start playing if nothing is playing
        if not self.music.is_playing(guild_id):
            await self.music.play_next(guild_id)

        # Create response message with skip info
        if skipped_count > 0:
            await interaction.followup.send(
                f"➕ Added **{added_count}** tracks from playlist: **{selected_playlist.name}**\n"
                f"⚠️ Skipped **{skipped_count}** unavailable tracks"
            )
        else:
            await interaction.followup.send(
                f"➕ Added **{added_count}** tracks from playlist: **{selected_playlist.name}**"
            )

    @app_commands.command(
        name="spotify_queue", description="Show the current Spotify queue"
    )
    async def queue(self, interaction: discord.Interaction):
        """Show the current music queue with pagination."""
        guild_id = interaction.guild_id
        current = self.music.get_current_track(guild_id)

        # Get the appropriate queue based on mode
        mode = self.music.get_queue_mode(guild_id)
        if mode == QueueMode.LOOP_QUEUE:
            # For loop queue mode, show the snapshot queue with position offset
            snapshot = self.music.get_queue_snapshot(guild_id)
            snapshot_position = self.music.get_snapshot_position(guild_id)

            # Show snapshot from current position, then loop back
            if snapshot:
                queue_items = (
                    snapshot[snapshot_position:] + snapshot[:snapshot_position]
                )
            else:
                queue_items = []
        else:
            # Normal mode - just show regular queue
            queue_items = self.music.get_queue(guild_id)

        # Create paginated view for the queue
        view = PaginatedQueueView(
            queue_items=queue_items,
            current_track=current,
            guild_id=guild_id,
            music_service=self.music,
        )

        embed = view._create_embed()
        await interaction.response.send_message(embed=embed, view=view)

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
        name="spotify_playback_mode",
        description="Set Spotify playback mode or manage queue shuffle",
    )
    @app_commands.describe(
        mode="Choose playback mode (optional - leave empty to see current status)",
        shuffle="Shuffle the current queue",
    )
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="Normal", value="normal"),
            app_commands.Choice(name="Song Loop", value="song_loop"),
            app_commands.Choice(name="Queue Loop", value="queue_loop"),
            app_commands.Choice(name="Shuffle Mode", value="shuffle"),
        ]
    )
    async def playback_mode(
        self,
        interaction: discord.Interaction,
        mode: app_commands.Choice[str] = None,
        shuffle: bool = False,
    ):
        """Set playback mode or shuffle the queue."""
        guild_id = interaction.guild_id

        # Handle shuffle action first
        if shuffle:
            current_mode = self.music.get_queue_mode(guild_id)
            queue = self.music.get_queue(guild_id)

            if not queue and current_mode != QueueMode.LOOP_QUEUE:
                await interaction.response.send_message(
                    "❌ No queue to shuffle!", ephemeral=True
                )
                return

            self.music.shuffle_queue(guild_id)

            if current_mode == QueueMode.LOOP_QUEUE:
                await interaction.response.send_message("🔀 Shuffled queue snapshot!")
            else:
                await interaction.response.send_message(
                    f"🔀 Shuffled queue with {len(queue)} tracks!"
                )
            return

        # If mode is provided, set it
        if mode:
            mode_map = {
                "normal": QueueMode.NORMAL,
                "song_loop": QueueMode.LOOP_TRACK,
                "queue_loop": QueueMode.LOOP_QUEUE,
                "shuffle": QueueMode.SHUFFLE,
            }

            new_mode = mode_map.get(mode.value)
            if not new_mode:
                await interaction.response.send_message(
                    "❌ Invalid mode selected!", ephemeral=True
                )
                return

            old_mode = self.music.get_queue_mode(guild_id)
            self.music.set_queue_mode(guild_id, new_mode)

            mode_display = {
                QueueMode.NORMAL: "Normal",
                QueueMode.LOOP_TRACK: "Song Loop",
                QueueMode.LOOP_QUEUE: "Queue Loop",
                QueueMode.SHUFFLE: "Shuffle",
            }

            response = f"🎵 Playback mode changed to **{mode_display[new_mode]}**"

            # Add special messages for mode transitions
            if new_mode == QueueMode.LOOP_QUEUE and old_mode != QueueMode.LOOP_QUEUE:
                response += "\n📸 Created queue snapshot for looping"
            elif new_mode == QueueMode.SHUFFLE:
                response += "\n🔀 Queue will be shuffled on next play"

            await interaction.response.send_message(response)
            return

        # No parameters provided, show current status
        current_mode = self.music.get_queue_mode(guild_id)
        is_shuffled = self.music.is_queue_shuffled(guild_id)

        mode_display = {
            QueueMode.NORMAL: "Normal",
            QueueMode.LOOP_TRACK: "Song Loop",
            QueueMode.LOOP_QUEUE: "Queue Loop",
            QueueMode.SHUFFLE: "Shuffle",
        }

        embed = discord.Embed(
            title="🎵 Current Playback Mode",
            description=f"**Mode:** {mode_display.get(current_mode, 'Unknown')}\n**Queue Shuffled:** {'Yes' if is_shuffled else 'No'}",
            color=0x1DB954,
        )

        # Add mode descriptions
        embed.add_field(
            name="Mode Descriptions",
            value=(
                "**Normal:** Play queue in order\n"
                "**Song Loop:** Repeat current song\n"
                "**Queue Loop:** Loop through queue snapshot\n"
                "**Shuffle:** Randomize queue order"
            ),
            inline=False,
        )

        embed.add_field(
            name="Usage",
            value=(
                "• Select a **mode** to change playback behavior\n"
                "• Enable **shuffle** to randomize the current queue\n"
                "• Use without parameters to see this status"
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

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

    @app_commands.command(
        name="spotify_status",
        description="Show detailed music service status (debug info)",
    )
    async def status(self, interaction: discord.Interaction):
        """Show detailed status of the music service."""
        guild_id = interaction.guild_id

        # Get music service status
        is_connected = guild_id in self.music._voice_clients
        is_playing = self.music.is_playing(guild_id)
        is_paused = self.music.is_paused(guild_id)
        has_queued_music = self.music.has_queued_music(guild_id)
        current_track = self.music.get_current_track(guild_id)
        queue = self.music.get_queue(guild_id)
        volume = self.music.get_volume(guild_id)
        queue_mode = self.music.get_queue_mode(guild_id)

        embed = discord.Embed(
            title="🎵 Music Service Status", color=discord.Color.blue()
        )

        # Connection status
        connection_status = "🟢 Connected" if is_connected else "🔴 Disconnected"
        embed.add_field(name="Voice Connection", value=connection_status, inline=True)

        # Playback status
        if is_playing:
            playback_status = "▶️ Playing"
        elif is_paused:
            playback_status = "⏸️ Paused"
        else:
            playback_status = "⏹️ Stopped"
        embed.add_field(name="Playback Status", value=playback_status, inline=True)

        # Music availability
        music_status = "🎶 Has Music" if has_queued_music else "💿 No Music"
        embed.add_field(name="Queue Status", value=music_status, inline=True)

        # Current track
        if current_track:
            embed.add_field(
                name="Current Track",
                value=f"**{current_track.track.display_name}**\nRequested by: {current_track.requested_by.display_name}",
                inline=False,
            )
        else:
            embed.add_field(name="Current Track", value="None", inline=False)

        # Queue info
        queue_info = f"{len(queue)} track(s) | Mode: {queue_mode.value} | Volume: {int(volume * 100)}%"
        embed.add_field(name="Queue Details", value=queue_info, inline=False)

        # Special note for preserved queues
        if not is_connected and has_queued_music:
            embed.add_field(
                name="📋 Note",
                value="Queue is preserved from previous session. Use `/spotify_join` to resume!",
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
