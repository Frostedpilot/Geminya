"""Music service for Discord voice integration with Spotify.

This service manages the music queue, voice connections, and integrates
with the Spotify service to provide music playback functionality.
"""

import asyncio
import logging
import random
from typing import Optional, List, Dict, Deque, Callable, Any
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

import discord
from discord.ext import commands

from .spotify_service import SpotifyService, SpotifyTrack, LibrespotAudioSource


class QueueMode(Enum):
    """Queue playback modes."""

    NORMAL = "normal"
    LOOP_TRACK = "loop_track"
    LOOP_QUEUE = "loop_queue"
    SHUFFLE = "shuffle"


@dataclass
class QueueItem:
    """Represents an item in the music queue."""

    track: SpotifyTrack
    requested_by: discord.Member
    added_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())


class MusicService:
    """Service for managing music playback in Discord voice channels."""

    def __init__(self, spotify_service: SpotifyService):
        self.spotify = spotify_service
        self.logger = logging.getLogger(__name__)

        # Voice connection management
        self._voice_clients: Dict[int, discord.VoiceClient] = (
            {}
        )  # guild_id -> voice_client

        # Queue management per guild
        self._queues: Dict[int, Deque[QueueItem]] = {}  # guild_id -> queue
        self._current_tracks: Dict[int, Optional[QueueItem]] = (
            {}
        )  # guild_id -> current_item
        self._queue_modes: Dict[int, QueueMode] = {}  # guild_id -> mode
        self._volumes: Dict[int, float] = {}  # guild_id -> volume

        # Enhanced queue management for queue loop mode
        self._queue_snapshots: Dict[int, List[QueueItem]] = {}  # guild_id -> snapshot
        self._snapshot_positions: Dict[int, int] = (
            {}
        )  # guild_id -> position in snapshot
        self._is_shuffled: Dict[int, bool] = {}  # guild_id -> shuffle state
        self._snapshot_shuffled: Dict[int, bool] = (
            {}
        )  # guild_id -> snapshot shuffle state

        # Playback state
        self._is_playing: Dict[int, bool] = {}  # guild_id -> is_playing
        self._is_paused: Dict[int, bool] = {}  # guild_id -> is_paused

        # Event callbacks
        self._on_track_start: Optional[Callable[[int, QueueItem], Any]] = None
        self._on_track_end: Optional[Callable[[int, QueueItem], Any]] = None
        self._on_queue_empty: Optional[Callable[[int], Any]] = None

        # Store the main event loop for thread-safe callbacks
        try:
            self._main_loop = asyncio.get_running_loop()
        except RuntimeError:
            self._main_loop = None

        # Auto-disconnect settings
        self._auto_disconnect_delay = 300  # 5 minutes
        self._disconnect_timers: Dict[int, asyncio.Task] = {}

    async def initialize(self) -> bool:
        """Initialize the music service."""
        try:
            # Set up Spotify callbacks
            self.spotify.set_callbacks(
                on_track_start=self._on_spotify_track_start,
                on_track_end=self._on_spotify_track_end,
            )

            self.logger.info("Music service initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize music service: {e}")
            return False

    def _get_guild_queue(self, guild_id: int) -> Deque[QueueItem]:
        """Get or create queue for guild."""
        if guild_id not in self._queues:
            self._queues[guild_id] = deque()
            self._queue_modes[guild_id] = QueueMode.NORMAL
            self._volumes[guild_id] = 0.5
            self._is_playing[guild_id] = False
            self._is_paused[guild_id] = False
            self._current_tracks[guild_id] = None
            # Initialize new fields
            self._queue_snapshots[guild_id] = []
            self._snapshot_positions[guild_id] = 0
            self._is_shuffled[guild_id] = False
            self._snapshot_shuffled[guild_id] = False
        return self._queues[guild_id]

    async def join_voice_channel(self, channel: discord.VoiceChannel) -> bool:
        """Join a voice channel."""
        guild_id = channel.guild.id

        try:
            # Disconnect from current channel if connected
            if guild_id in self._voice_clients:
                await self.leave_voice_channel(guild_id)

            # Connect to new channel
            voice_client = await channel.connect()
            self._voice_clients[guild_id] = voice_client

            # Cancel any pending disconnect
            if guild_id in self._disconnect_timers:
                self._disconnect_timers[guild_id].cancel()
                del self._disconnect_timers[guild_id]

            self.logger.info(
                f"Joined voice channel {channel.name} in {channel.guild.name}"
            )

            # Auto-resume if there's a queue or current track waiting
            await self._try_resume_playback_after_reconnect(guild_id)

            return True

        except Exception as e:
            self.logger.error(f"Failed to join voice channel {channel.name}: {e}")
            return False

    async def leave_voice_channel(self, guild_id: int) -> bool:
        """Leave voice channel."""
        try:
            if guild_id in self._voice_clients:
                voice_client = self._voice_clients[guild_id]

                # Stop current playback without clearing queue
                self.stop_playback_only(guild_id)

                await voice_client.disconnect()
                del self._voice_clients[guild_id]

                # Cancel disconnect timer
                if guild_id in self._disconnect_timers:
                    self._disconnect_timers[guild_id].cancel()
                    del self._disconnect_timers[guild_id]

                self.logger.info(f"Left voice channel in guild {guild_id}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to leave voice channel in guild {guild_id}: {e}")
            return False

    async def handle_forced_disconnect(self, guild_id: int):
        """Handle forced disconnect from voice channel (preserves queue)."""
        try:
            if guild_id in self._voice_clients:
                # Remove the voice client reference since we're already disconnected
                del self._voice_clients[guild_id]

                # Stop current playback gracefully without clearing queue
                # We can't use stop_playback_only since there's no voice client anymore
                self._is_playing[guild_id] = False
                self._is_paused[guild_id] = False
                # Note: We intentionally keep current_tracks and queues intact

                # Cancel disconnect timer if it exists
                if guild_id in self._disconnect_timers:
                    self._disconnect_timers[guild_id].cancel()
                    del self._disconnect_timers[guild_id]

                self.logger.info(
                    f"Handled forced disconnect in guild {guild_id} - queue preserved"
                )
                return True

            return False

        except Exception as e:
            self.logger.error(
                f"Failed to handle forced disconnect in guild {guild_id}: {e}"
            )
            return False

    def add_to_queue(
        self,
        guild_id: int,
        track: SpotifyTrack,
        requested_by: discord.Member,
        add_to_start: bool = False,
    ):
        """Add track to queue."""
        mode = self._queue_modes[guild_id]

        if mode == QueueMode.LOOP_QUEUE:
            # In queue loop mode, add to the snapshot queue instead of regular queue
            snapshot = self._queue_snapshots.get(guild_id, [])
            item = QueueItem(track=track, requested_by=requested_by)

            if add_to_start:
                # Add to the beginning of snapshot (right after current position)
                current_pos = self._snapshot_positions[guild_id]
                snapshot.insert(current_pos, item)
            else:
                # Add to the end of snapshot
                snapshot.append(item)

            self._queue_snapshots[guild_id] = snapshot
        else:
            # Normal mode - use regular queue
            queue = self._get_guild_queue(guild_id)
            item = QueueItem(track=track, requested_by=requested_by)

            if add_to_start:
                queue.appendleft(item)
            else:
                queue.append(item)

            # Reset shuffle state for normal mode when adding new tracks
            if mode != QueueMode.LOOP_QUEUE:
                self._is_shuffled[guild_id] = False

        self.logger.info(
            f"Added {track.display_name} to {'start' if add_to_start else 'end'} of queue in guild {guild_id}"
        )

    def add_playlist_to_queue(
        self,
        guild_id: int,
        tracks: List[SpotifyTrack],
        requested_by: discord.Member,
        add_to_start: bool = False,
    ):
        """Add multiple tracks to queue, filtering out unavailable ones."""
        mode = self._queue_modes[guild_id]

        # Filter out unavailable tracks
        playable_tracks = []
        skipped_count = 0

        for track in tracks:
            if hasattr(track, "is_playable") and not track.is_playable:
                skipped_count += 1
                self.logger.debug(f"Skipping unavailable track: {track.display_name}")
                continue
            playable_tracks.append(track)

        # Add playable tracks to queue
        if mode == QueueMode.LOOP_QUEUE:
            # In queue loop mode, add to the snapshot queue
            snapshot = self._queue_snapshots.get(guild_id, [])
            current_pos = self._snapshot_positions[guild_id]

            for i, track in enumerate(playable_tracks):
                item = QueueItem(track=track, requested_by=requested_by)
                if add_to_start:
                    # Insert in reverse order to maintain playlist order when adding to start
                    snapshot.insert(current_pos + i, item)
                else:
                    snapshot.append(item)

            self._queue_snapshots[guild_id] = snapshot
        else:
            # Normal mode - use regular queue
            queue = self._get_guild_queue(guild_id)

            for track in playable_tracks:
                item = QueueItem(track=track, requested_by=requested_by)
                if add_to_start:
                    # Insert in reverse order to maintain playlist order when adding to start
                    queue.appendleft(item)
                else:
                    queue.append(item)

            # Reset shuffle state for normal mode when adding new tracks
            if mode != QueueMode.LOOP_QUEUE and playable_tracks:
                self._is_shuffled[guild_id] = False

        if skipped_count > 0:
            self.logger.info(
                f"Added {len(playable_tracks)} tracks to {'start' if add_to_start else 'end'} of queue in guild {guild_id} (skipped {skipped_count} unavailable)"
            )
        else:
            self.logger.info(
                f"Added {len(playable_tracks)} tracks to {'start' if add_to_start else 'end'} of queue in guild {guild_id}"
            )

        return len(playable_tracks), skipped_count

    async def play_next(self, guild_id: int) -> bool:
        """Play the next track in queue."""
        if guild_id not in self._voice_clients:
            self.logger.warning(f"No voice client for guild {guild_id}")
            return False

        voice_client = self._voice_clients[guild_id]
        queue = self._get_guild_queue(guild_id)

        # Check if already playing
        if voice_client.is_playing():
            voice_client.stop()

        # Try to get next playable track (may need to skip unavailable ones)
        max_attempts = 5  # Prevent infinite loop if all tracks are unavailable
        attempts = 0

        while attempts < max_attempts:
            # Get next track based on queue mode
            next_item = self._get_next_track(guild_id)
            if not next_item:
                # Queue is empty
                self._is_playing[guild_id] = False
                self._current_tracks[guild_id] = None

                if self._on_queue_empty:
                    if asyncio.iscoroutinefunction(self._on_queue_empty):
                        task = asyncio.create_task(self._on_queue_empty(guild_id))
                        # Store task reference to prevent garbage collection
                        if not hasattr(self, "_background_tasks"):
                            self._background_tasks = set()
                        self._background_tasks.add(task)
                        task.add_done_callback(self._background_tasks.discard)
                    else:
                        self._on_queue_empty(guild_id)

                # Start auto-disconnect timer
                await self._start_auto_disconnect_timer(guild_id)
                return False

            # Check if track is marked as unplayable
            if (
                hasattr(next_item.track, "is_playable")
                and not next_item.track.is_playable
            ):
                self.logger.warning(
                    f"Skipping unavailable track: {next_item.track.display_name}"
                )
                attempts += 1
                continue

            try:
                # Create audio source
                audio_source = await self.spotify.create_audio_source(next_item.track)
                if not audio_source:
                    self.logger.warning(
                        f"Failed to create audio source for {next_item.track.display_name}, skipping..."
                    )
                    attempts += 1
                    continue

                # Apply volume
                volume = self._volumes[guild_id]
                audio_source = discord.PCMVolumeTransformer(audio_source, volume=volume)

                # Create a thread-safe callback for when the track finishes
                def track_finished_callback(error, track_item=next_item):
                    if error:
                        self.logger.error(f"Player error: {error}")

                    # Schedule the async callback safely using the stored main loop
                    if self._main_loop and not self._main_loop.is_closed():
                        try:
                            asyncio.run_coroutine_threadsafe(
                                self._on_track_finished(guild_id, track_item, error),
                                self._main_loop,
                            )
                        except Exception as e:
                            self.logger.error(
                                f"Error scheduling track finished callback: {e}"
                            )
                    else:
                        self.logger.warning("No main event loop available for callback")

                # Play track
                voice_client.play(audio_source, after=track_finished_callback)

                # Update state
                self._current_tracks[guild_id] = next_item
                self._is_playing[guild_id] = True
                self._is_paused[guild_id] = False

                # Trigger callback (make it async-safe)
                if self._on_track_start:
                    if asyncio.iscoroutinefunction(self._on_track_start):
                        task = asyncio.create_task(
                            self._on_track_start(guild_id, next_item)
                        )
                        # Store task reference to prevent garbage collection
                        if not hasattr(self, "_background_tasks"):
                            self._background_tasks = set()
                        self._background_tasks.add(task)
                        task.add_done_callback(self._background_tasks.discard)
                    else:
                        self._on_track_start(guild_id, next_item)

                self.logger.info(
                    f"Started playing {next_item.track.display_name} in guild {guild_id}"
                )
                return True

            except Exception as e:
                self.logger.warning(
                    f"Error playing track {next_item.track.display_name}: {e}, attempting next track..."
                )
                attempts += 1
                continue

        # If we get here, we couldn't find any playable tracks
        self.logger.error(
            f"Could not find any playable tracks in queue for guild {guild_id}"
        )
        self._is_playing[guild_id] = False
        self._current_tracks[guild_id] = None

        if self._on_queue_empty:
            if asyncio.iscoroutinefunction(self._on_queue_empty):
                task = asyncio.create_task(self._on_queue_empty(guild_id))
                if not hasattr(self, "_background_tasks"):
                    self._background_tasks = set()
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
            else:
                self._on_queue_empty(guild_id)

        await self._start_auto_disconnect_timer(guild_id)
        return False

    def _get_next_track(self, guild_id: int) -> Optional[QueueItem]:
        """Get next track based on queue mode."""
        mode = self._queue_modes[guild_id]
        current = self._current_tracks[guild_id]

        # Loop current track
        if mode == QueueMode.LOOP_TRACK and current:
            return current

        # Queue loop mode - use snapshot queue
        elif mode == QueueMode.LOOP_QUEUE:
            snapshot = self._queue_snapshots.get(guild_id, [])
            if not snapshot:
                return None

            position = self._snapshot_positions[guild_id]

            if position >= len(snapshot):
                # Reset to beginning of snapshot
                position = 0
                self._snapshot_positions[guild_id] = 0

            next_item = snapshot[position]
            self._snapshot_positions[guild_id] = position + 1
            return next_item

        # Normal mode and shuffle mode - use regular queue
        else:
            queue = self._get_guild_queue(guild_id)

            if not queue:
                return None

            # Shuffle mode
            if mode == QueueMode.SHUFFLE:
                if not self._is_shuffled[guild_id]:
                    # Convert deque to list, shuffle, and convert back
                    queue_list = list(queue)
                    random.shuffle(queue_list)
                    queue.clear()
                    queue.extend(queue_list)
                    self._is_shuffled[guild_id] = True

            return queue.popleft()

    async def _on_track_finished(self, guild_id: int, item: QueueItem, error):
        """Handle track finishing."""
        if error:
            self.logger.error(f"Player error: {error}")

        # Trigger callback (make it async-safe)
        if self._on_track_end:
            if asyncio.iscoroutinefunction(self._on_track_end):
                task = asyncio.create_task(self._on_track_end(guild_id, item))
                # Store task reference to prevent garbage collection
                if not hasattr(self, "_background_tasks"):
                    self._background_tasks = set()
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
            else:
                self._on_track_end(guild_id, item)

        # Play next track
        await self.play_next(guild_id)

    async def pause(self, guild_id: int) -> bool:
        """Pause playback."""
        if guild_id in self._voice_clients:
            voice_client = self._voice_clients[guild_id]
            if voice_client.is_playing():
                voice_client.pause()
                self._is_paused[guild_id] = True
                return True
        return False

    async def resume(self, guild_id: int) -> bool:
        """Resume playback."""
        if guild_id in self._voice_clients:
            voice_client = self._voice_clients[guild_id]
            if voice_client.is_paused():
                voice_client.resume()
                self._is_paused[guild_id] = False
                return True
        return False

    def stop_playback_only(self, guild_id: int) -> bool:
        """Stop current playback without clearing queue or current track."""
        if guild_id in self._voice_clients:
            voice_client = self._voice_clients[guild_id]
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()

            # Update playback state only
            self._is_playing[guild_id] = False
            self._is_paused[guild_id] = False
            # Note: We keep _current_tracks and _queues intact

            return True
        return False

    async def stop(self, guild_id: int) -> bool:
        """Stop playback and clear queue."""
        if guild_id in self._voice_clients:
            voice_client = self._voice_clients[guild_id]
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()

            # Clear state
            self._is_playing[guild_id] = False
            self._is_paused[guild_id] = False
            self._current_tracks[guild_id] = None

            # Clear queue
            if guild_id in self._queues:
                self._queues[guild_id].clear()

            return True
        return False

    async def skip(self, guild_id: int) -> bool:
        """Skip current track."""
        if guild_id in self._voice_clients:
            voice_client = self._voice_clients[guild_id]
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()  # This will trigger _on_track_finished
                return True
        return False

    async def skip_to(self, guild_id: int, position: int) -> bool:
        """Skip to a specific position in the queue (1-indexed)."""
        mode = self._queue_modes[guild_id]

        # Convert to 0-indexed
        index = position - 1

        if mode == QueueMode.LOOP_QUEUE:
            # In loop queue mode, work with snapshot
            snapshot = self._queue_snapshots.get(guild_id, [])
            current_pos = self._snapshot_positions.get(guild_id, 0)

            # Get remaining tracks from current position
            remaining_tracks = snapshot[current_pos:] if snapshot else []

            if index < 0 or index >= len(remaining_tracks):
                return False

            # Update snapshot position to skip to the target
            new_position = current_pos + index
            self._snapshot_positions[guild_id] = new_position

        else:
            # Normal mode - work with regular queue
            queue = self._get_guild_queue(guild_id)

            if index < 0 or index >= len(queue):
                return False

            # Remove tracks before the target position
            for _ in range(index):
                if queue:
                    queue.popleft()

        # Stop current track to trigger playing the new target track
        if guild_id in self._voice_clients:
            voice_client = self._voice_clients[guild_id]
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()  # This will trigger _on_track_finished
                return True

        return False

    def set_volume(self, guild_id: int, volume: float):
        """Set volume for guild."""
        volume = max(0.0, min(1.0, volume))
        self._volumes[guild_id] = volume

        # Update current playing source if applicable
        if guild_id in self._voice_clients:
            voice_client = self._voice_clients[guild_id]
            if hasattr(voice_client.source, "volume"):
                voice_client.source.volume = volume

    def set_queue_mode(self, guild_id: int, mode: QueueMode):
        """Set queue mode for guild."""
        self._get_guild_queue(guild_id)  # Ensure guild is initialized
        old_mode = self._queue_modes[guild_id]
        self._queue_modes[guild_id] = mode

        # Handle mode transitions
        if mode == QueueMode.LOOP_QUEUE and old_mode != QueueMode.LOOP_QUEUE:
            # Create snapshot of current queue + current track
            self._create_queue_snapshot(guild_id)
        elif mode != QueueMode.LOOP_QUEUE and old_mode == QueueMode.LOOP_QUEUE:
            # Copy snapshot queue back to normal queue when leaving loop queue mode
            snapshot = self._queue_snapshots.get(guild_id, [])
            current_pos = self._snapshot_positions.get(guild_id, 0)

            # Get the remaining tracks from current position onwards, then wrap around
            if snapshot:
                remaining_tracks = snapshot[current_pos:] + snapshot[:current_pos]
                # Clear normal queue and add snapshot tracks
                queue = self._get_guild_queue(guild_id)
                queue.clear()
                queue.extend(remaining_tracks)

            # Clear snapshot data
            self._queue_snapshots[guild_id] = []
            self._snapshot_positions[guild_id] = 0

        # Reset shuffle state when changing modes
        if mode != QueueMode.SHUFFLE:
            self._is_shuffled[guild_id] = False
        if mode != QueueMode.LOOP_QUEUE:
            self._snapshot_shuffled[guild_id] = False

    def _create_queue_snapshot(self, guild_id: int):
        """Create a snapshot of the current queue state for loop queue mode."""
        queue = self._get_guild_queue(guild_id)
        current = self._current_tracks[guild_id]

        # Create snapshot: current track (if any) + remaining queue
        snapshot = []
        if current:
            snapshot.append(current)
        snapshot.extend(list(queue))

        self._queue_snapshots[guild_id] = snapshot
        self._snapshot_positions[guild_id] = 0

        # If shuffle was enabled before, maintain it in the snapshot
        if self._is_shuffled[guild_id]:
            random.shuffle(self._queue_snapshots[guild_id])
            self._snapshot_shuffled[guild_id] = True

    def shuffle_queue(self, guild_id: int):
        """Shuffle the current queue or snapshot queue depending on mode."""
        mode = self._queue_modes[guild_id]

        if mode == QueueMode.LOOP_QUEUE:
            # Shuffle the snapshot queue
            if self._queue_snapshots[guild_id]:
                random.shuffle(self._queue_snapshots[guild_id])
                self._snapshot_positions[guild_id] = 0  # Reset position
                self._snapshot_shuffled[guild_id] = True
        else:
            # Shuffle the regular queue
            queue = self._get_guild_queue(guild_id)
            if queue:
                queue_list = list(queue)
                random.shuffle(queue_list)
                queue.clear()
                queue.extend(queue_list)
                self._is_shuffled[guild_id] = True

    def get_queue_snapshot(self, guild_id: int) -> List[QueueItem]:
        """Get the current queue snapshot for loop queue mode."""
        return self._queue_snapshots.get(guild_id, []).copy()

    def get_snapshot_position(self, guild_id: int) -> int:
        """Get the current position in the snapshot queue."""
        return self._snapshot_positions.get(guild_id, 0)

    def set_snapshot_position(self, guild_id: int, position: int):
        """Set the current position in the snapshot queue."""
        if guild_id in self._queue_snapshots:
            snapshot_len = len(self._queue_snapshots[guild_id])
            if snapshot_len > 0:
                # Ensure position is within bounds
                self._snapshot_positions[guild_id] = max(
                    0, min(position, snapshot_len - 1)
                )

    def is_queue_shuffled(self, guild_id: int) -> bool:
        """Check if the queue is currently shuffled."""
        mode = self._queue_modes[guild_id]
        if mode == QueueMode.LOOP_QUEUE:
            return self._snapshot_shuffled.get(guild_id, False)
        else:
            return self._is_shuffled.get(guild_id, False)

    def clear_queue(self, guild_id: int):
        """Clear the queue for guild based on current mode."""
        mode = self._queue_modes.get(guild_id, QueueMode.NORMAL)

        if mode == QueueMode.LOOP_QUEUE:
            # In loop queue mode, clear snapshot queue
            if guild_id in self._queue_snapshots:
                self._queue_snapshots[guild_id].clear()
                self._snapshot_positions[guild_id] = 0
                self._snapshot_shuffled[guild_id] = False

        # Always clear regular queue as well
        if guild_id in self._queues:
            self._queues[guild_id].clear()
            self._is_shuffled[guild_id] = False

    def get_queue(self, guild_id: int) -> List[QueueItem]:
        """Get current queue for guild based on active mode."""
        mode = self._queue_modes.get(guild_id, QueueMode.NORMAL)

        if mode == QueueMode.LOOP_QUEUE:
            # In loop queue mode, return the snapshot queue from current position
            snapshot = self._queue_snapshots.get(guild_id, [])
            position = self._snapshot_positions.get(guild_id, 0)
            if snapshot:
                # Return remaining tracks from current position
                return snapshot[position:]
            return []
        else:
            # Normal mode, shuffle mode - return regular queue
            queue = self._get_guild_queue(guild_id)
            return list(queue)

    def get_current_track(self, guild_id: int) -> Optional[QueueItem]:
        """Get currently playing track for guild."""
        return self._current_tracks.get(guild_id)

    def is_playing(self, guild_id: int) -> bool:
        """Check if music is playing in guild."""
        return self._is_playing.get(guild_id, False)

    def is_paused(self, guild_id: int) -> bool:
        """Check if music is paused in guild."""
        return self._is_paused.get(guild_id, False)

    def get_volume(self, guild_id: int) -> float:
        """Get volume for guild."""
        return self._volumes.get(guild_id, 0.5)

    def get_queue_mode(self, guild_id: int) -> QueueMode:
        """Get queue mode for guild."""
        return self._queue_modes.get(guild_id, QueueMode.NORMAL)

    def has_queued_music(self, guild_id: int) -> bool:
        """Check if there's any music queued or paused for this guild."""
        current_track = self._current_tracks.get(guild_id)
        queue = self._get_guild_queue(guild_id)
        return bool(current_track or queue)

    async def _start_auto_disconnect_timer(self, guild_id: int):
        """Start auto-disconnect timer when queue is empty."""
        if guild_id in self._disconnect_timers:
            self._disconnect_timers[guild_id].cancel()

        async def auto_disconnect():
            await asyncio.sleep(self._auto_disconnect_delay)
            await self.leave_voice_channel(guild_id)
            self.logger.info(
                f"Auto-disconnected from guild {guild_id} due to inactivity"
            )

        self._disconnect_timers[guild_id] = asyncio.create_task(auto_disconnect())

    def set_callbacks(
        self,
        on_track_start: Callable[[int, QueueItem], Any] = None,
        on_track_end: Callable[[int, QueueItem], Any] = None,
        on_queue_empty: Callable[[int], Any] = None,
    ):
        """Set event callbacks."""
        self._on_track_start = on_track_start
        self._on_track_end = on_track_end
        self._on_queue_empty = on_queue_empty

    def _on_spotify_track_start(self, track: SpotifyTrack):
        """Handle Spotify track start."""
        # This is called by SpotifyService
        pass

    def _on_spotify_track_end(self, track: SpotifyTrack):
        """Handle Spotify track end."""
        # This is called by SpotifyService
        pass

    async def _try_resume_playback_after_reconnect(self, guild_id: int):
        """Try to resume playback after reconnecting to voice channel."""
        try:
            # Check if there's a current track or queue waiting
            current_track = self._current_tracks.get(guild_id)
            queue = self._get_guild_queue(guild_id)
            mode = self._queue_modes.get(guild_id, QueueMode.NORMAL)

            if (
                current_track
                or queue
                or (
                    mode == QueueMode.LOOP_QUEUE and self._queue_snapshots.get(guild_id)
                )
            ):
                self.logger.info(
                    f"Resuming playback after reconnect in guild {guild_id}"
                )

                # In loop queue mode, if we have a current track that was from the snapshot,
                # we need to ensure the snapshot position is consistent
                if mode == QueueMode.LOOP_QUEUE and current_track and not queue:
                    snapshot = self._queue_snapshots.get(guild_id, [])
                    position = self._snapshot_positions.get(guild_id, 0)

                    # If the current track matches the track at the current snapshot position,
                    # we're in sync. Otherwise, we might need to adjust.
                    if (
                        position < len(snapshot)
                        and snapshot[position].track.display_name
                        == current_track.track.display_name
                    ):
                        # We're in sync, current track will be replayed from snapshot
                        pass
                    else:
                        # Try to find the current track in the snapshot to sync position
                        for i, item in enumerate(snapshot):
                            if (
                                item.track.display_name
                                == current_track.track.display_name
                            ):
                                self._snapshot_positions[guild_id] = i
                                break

                # Start playing the current track or next in queue
                await self.play_next(guild_id)

        except Exception as e:
            self.logger.error(f"Error resuming playback after reconnect: {e}")

    async def close(self):
        """Close the music service."""
        # Disconnect from all voice channels
        for guild_id in list(self._voice_clients.keys()):
            await self.leave_voice_channel(guild_id)

        # Cancel all timers
        for timer in self._disconnect_timers.values():
            timer.cancel()
        self._disconnect_timers.clear()

        self.logger.info("Music service closed")
