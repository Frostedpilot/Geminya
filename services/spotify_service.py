"""Spotify service using librespot-python for direct streaming.

This service provides Spotify integration using librespot-python to create
a virtual Spotify Connect device that can stream music directly without
requiring external Spotify applications.

WARNING: This uses unofficial librespot library which may violate Spotify's ToS.
Use at your own risk. Requires Spotify Premium account.
"""

import asyncio
import logging
import io
import threading
import subprocess
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from librespot.core import Session
from librespot.metadata import TrackId
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality
import discord


class SpotifyQuality(Enum):
    """Audio quality options for Spotify streaming."""

    NORMAL = AudioQuality.NORMAL
    HIGH = AudioQuality.HIGH
    VERY_HIGH = AudioQuality.VERY_HIGH


@dataclass
class SpotifyTrack:
    """Represents a Spotify track with metadata."""

    id: str
    name: str
    artist: str
    album: str
    duration_ms: int
    uri: str
    external_url: str
    preview_url: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Human-readable track representation."""
        return f"{self.artist} - {self.name}"

    @property
    def duration_formatted(self) -> str:
        """Duration in MM:SS format."""
        minutes = self.duration_ms // 60000
        seconds = (self.duration_ms % 60000) // 1000
        return f"{minutes}:{seconds:02d}"


@dataclass
class SpotifyPlaylist:
    """Represents a Spotify playlist with metadata."""

    id: str
    name: str
    description: str
    tracks_total: int
    external_url: str
    owner: str


class LibrespotAudioSource(discord.AudioSource):
    """Discord audio source that streams from librespot via FFmpeg."""

    def __init__(self, track_stream, track: SpotifyTrack):
        self.track_stream = track_stream
        self.track = track
        self._ffmpeg_process = None
        self._audio_thread = None
        self._is_running = False
        self._read_buffer = bytearray()  # Buffer for smoother reading
        self.CHUNK_SIZE = 3840  # 20ms of audio at 48kHz/16-bit/stereo

        # Start FFmpeg process to convert librespot stream to PCM
        self._start_ffmpeg()

    def _start_ffmpeg(self):
        """Start FFmpeg process to convert audio."""
        try:
            # Check if FFmpeg is available
            try:
                subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                logging.error(
                    "FFmpeg not found. Please install FFmpeg for Spotify audio streaming."
                )
                logging.error(
                    "Windows: Download from https://ffmpeg.org/ or use 'winget install ffmpeg'"
                )
                raise RuntimeError("FFmpeg is required but not found")

            # FFmpeg command optimized for low latency
            # Discord expects: 48kHz, 16-bit, 2 channels (stereo), little-endian PCM
            self._ffmpeg_process = subprocess.Popen(
                [
                    "ffmpeg",
                    "-i",
                    "pipe:0",  # Input from stdin
                    "-f",
                    "s16le",  # Output format: 16-bit little-endian PCM
                    "-ar",
                    "48000",  # Sample rate: 48kHz
                    "-ac",
                    "2",  # Audio channels: stereo
                    "-buffer_size",
                    "32768",  # Reduce buffer size for lower latency
                    "-fflags",
                    "+genpts",  # Generate presentation timestamps
                    "-avoid_negative_ts",
                    "make_zero",  # Avoid negative timestamps
                    "-loglevel",
                    "error",  # Suppress FFmpeg logs
                    "pipe:1",  # Output to stdout
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Start thread to feed data from librespot to FFmpeg
            self._is_running = True
            self._audio_thread = threading.Thread(target=self._feed_ffmpeg, daemon=True)
            self._audio_thread.start()

        except Exception as e:
            logging.error(f"Failed to start FFmpeg: {e}")
            self._ffmpeg_process = None
            raise

    def _feed_ffmpeg(self):
        """Feed audio data from librespot stream to FFmpeg."""
        buffer_size = 8192  # Read in chunks for better performance
        try:
            while self._is_running and self._ffmpeg_process:
                # Check if FFmpeg process is still alive
                if self._ffmpeg_process.poll() is not None:
                    # FFmpeg has terminated
                    break

                # Read data in larger chunks for better performance
                try:
                    # Read chunk_size bytes at once instead of byte-by-byte
                    chunk_data = self.track_stream.input_stream.stream().read(
                        buffer_size
                    )
                    if not chunk_data or chunk_data == -1:  # End of stream or no data
                        break

                    # Ensure we have bytes, not int
                    if isinstance(chunk_data, int):
                        if chunk_data == -1:
                            break
                        chunk_data = bytes([chunk_data])
                    elif not isinstance(chunk_data, (bytes, bytearray)):
                        # Convert to bytes if it's something else
                        chunk_data = bytes(chunk_data)

                except Exception:
                    # Error reading from stream
                    break

                if self._ffmpeg_process and self._ffmpeg_process.stdin:
                    try:
                        self._ffmpeg_process.stdin.write(chunk_data)
                        self._ffmpeg_process.stdin.flush()
                    except OSError:
                        # FFmpeg process was terminated, stop feeding
                        break

        except Exception as e:
            # Only log if it's not a broken pipe (which is expected when stopping)
            if "Broken pipe" not in str(e):
                logging.error(f"Error feeding FFmpeg: {e}")
        finally:
            # Close FFmpeg stdin when done
            if self._ffmpeg_process and self._ffmpeg_process.stdin:
                try:
                    self._ffmpeg_process.stdin.close()
                except Exception:
                    pass

    def read(self) -> bytes:
        """Read audio data for Discord."""
        if not self._ffmpeg_process or not self._ffmpeg_process.stdout:
            return b""

        try:
            # Use the defined chunk size (20ms of 48kHz 16-bit stereo)
            target_size = self.CHUNK_SIZE

            # If buffer has enough data, use it first
            if len(self._read_buffer) >= target_size:
                result = bytes(self._read_buffer[:target_size])
                self._read_buffer = self._read_buffer[target_size:]
                return result

            # Read more data to fill buffer
            try:
                new_data = self._ffmpeg_process.stdout.read(
                    target_size * 2
                )  # Read double to buffer
                if new_data:
                    self._read_buffer.extend(new_data)
            except Exception:
                pass

            # Now extract what we need
            if len(self._read_buffer) >= target_size:
                result = bytes(self._read_buffer[:target_size])
                self._read_buffer = self._read_buffer[target_size:]
                return result
            elif len(self._read_buffer) > 0:
                # Use what we have and pad with silence
                result = bytes(self._read_buffer) + b"\x00" * (
                    target_size - len(self._read_buffer)
                )
                self._read_buffer.clear()
                return result
            else:
                # No data available
                return b""

        except Exception as e:
            logging.error(f"Error reading from FFmpeg: {e}")
            return b""

    def cleanup(self):
        """Clean up the audio source and FFmpeg process."""
        self._is_running = False

        try:
            # Wait for audio thread to finish
            if self._audio_thread and self._audio_thread.is_alive():
                self._audio_thread.join(timeout=1.0)

            # Terminate FFmpeg process
            if self._ffmpeg_process:
                try:
                    self._ffmpeg_process.terminate()
                    self._ffmpeg_process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self._ffmpeg_process.kill()
                except Exception:
                    pass
                finally:
                    self._ffmpeg_process = None

            # Close librespot stream
            if hasattr(self.track_stream, "close"):
                self.track_stream.close()

        except Exception as e:
            logging.error(f"Error cleaning up audio source: {e}")


class SpotifyService:
    """Service for Spotify integration using librespot."""

    def __init__(
        self, username: str, password: str, client_id: str, client_secret: str
    ):
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret

        self.logger = logging.getLogger(__name__)
        self._session: Optional[Session] = None
        self._spotipy: Optional[spotipy.Spotify] = None
        self._quality = SpotifyQuality.HIGH

        # Playback state
        self._current_track: Optional[SpotifyTrack] = None
        self._is_playing = False
        self._volume = 0.5

        # Event callbacks
        self._on_track_start: Optional[Callable[[SpotifyTrack], None]] = None
        self._on_track_end: Optional[Callable[[SpotifyTrack], None]] = None

    async def initialize(self) -> bool:
        """Initialize the Spotify service."""
        try:
            # Initialize spotipy for search/metadata
            auth_manager = SpotifyClientCredentials(
                client_id=self.client_id, client_secret=self.client_secret
            )
            self._spotipy = spotipy.Spotify(auth_manager=auth_manager)

            # Initialize librespot session
            await self._create_session()

            self.logger.info("Spotify service initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Spotify service: {e}")
            return False

    async def _create_session(self):
        """Create librespot session in a thread to avoid blocking."""

        def create_session():
            try:
                # Use OAuth authentication instead of username/password
                # This works without requiring explicit credentials
                self._session = Session.Builder().oauth(None).create()
                self.logger.info("Librespot session created successfully using OAuth")
            except Exception as e:
                self.logger.error(f"Failed to create librespot session: {e}")
                raise

        # Run in thread to avoid blocking async loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, create_session)

    async def search_tracks(self, query: str, limit: int = 10) -> List[SpotifyTrack]:
        """Search for tracks on Spotify."""
        try:
            results = self._spotipy.search(q=query, type="track", limit=limit)
            tracks = []

            for item in results["tracks"]["items"]:
                track = SpotifyTrack(
                    id=item["id"],
                    name=item["name"],
                    artist=", ".join([artist["name"] for artist in item["artists"]]),
                    album=item["album"]["name"],
                    duration_ms=item["duration_ms"],
                    uri=item["uri"],
                    external_url=item["external_urls"]["spotify"],
                    preview_url=item.get("preview_url"),
                )
                tracks.append(track)

            return tracks

        except Exception as e:
            self.logger.error(f"Error searching tracks: {e}")
            return []

    async def search_playlists(
        self, query: str, limit: int = 10
    ) -> List[SpotifyPlaylist]:
        """Search for playlists on Spotify."""
        try:
            results = self._spotipy.search(q=query, type="playlist", limit=limit)
            playlists = []

            for item in results["playlists"]["items"]:
                playlist = SpotifyPlaylist(
                    id=item["id"],
                    name=item["name"],
                    description=item.get("description", ""),
                    tracks_total=item["tracks"]["total"],
                    external_url=item["external_urls"]["spotify"],
                    owner=item["owner"]["display_name"],
                )
                playlists.append(playlist)

            return playlists

        except Exception as e:
            self.logger.error(f"Error searching playlists: {e}")
            return []

    async def get_playlist_tracks(self, playlist_id: str) -> List[SpotifyTrack]:
        """Get tracks from a playlist."""
        try:
            results = self._spotipy.playlist_tracks(playlist_id)
            tracks = []

            for item in results["items"]:
                if item["track"] and item["track"]["type"] == "track":
                    track_data = item["track"]
                    track = SpotifyTrack(
                        id=track_data["id"],
                        name=track_data["name"],
                        artist=", ".join(
                            [artist["name"] for artist in track_data["artists"]]
                        ),
                        album=track_data["album"]["name"],
                        duration_ms=track_data["duration_ms"],
                        uri=track_data["uri"],
                        external_url=track_data["external_urls"]["spotify"],
                        preview_url=track_data.get("preview_url"),
                    )
                    tracks.append(track)

            return tracks

        except Exception as e:
            self.logger.error(f"Error getting playlist tracks: {e}")
            return []

    async def create_audio_source(
        self, track: SpotifyTrack
    ) -> Optional[LibrespotAudioSource]:
        """Create an audio source for Discord from a Spotify track."""
        if not self._session:
            self.logger.error("Librespot session not initialized")
            return None

        try:

            def get_stream():
                track_id = TrackId.from_uri(track.uri)
                quality = VorbisOnlyAudioQuality(self._quality.value)
                return self._session.content_feeder().load(
                    track_id, quality, False, None
                )

            # Run in thread to avoid blocking
            loop = asyncio.get_event_loop()
            track_stream = await loop.run_in_executor(None, get_stream)

            # Update current track
            self._current_track = track
            self._is_playing = True

            # Trigger callback
            if self._on_track_start:
                self._on_track_start(track)

            return LibrespotAudioSource(track_stream, track)

        except Exception as e:
            self.logger.error(
                f"Error creating audio source for {track.display_name}: {e}"
            )
            return None

    def set_quality(self, quality: SpotifyQuality):
        """Set audio quality."""
        self._quality = quality
        self.logger.info(f"Audio quality set to {quality.name}")

    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)."""
        self._volume = max(0.0, min(1.0, volume))
        self.logger.info(f"Volume set to {self._volume:.1%}")

    def set_callbacks(
        self,
        on_track_start: Callable[[SpotifyTrack], None] = None,
        on_track_end: Callable[[SpotifyTrack], None] = None,
    ):
        """Set event callbacks."""
        self._on_track_start = on_track_start
        self._on_track_end = on_track_end

    @property
    def current_track(self) -> Optional[SpotifyTrack]:
        """Get the currently playing track."""
        return self._current_track

    @property
    def is_playing(self) -> bool:
        """Check if currently playing."""
        return self._is_playing

    @property
    def quality(self) -> SpotifyQuality:
        """Get current audio quality."""
        return self._quality

    @property
    def volume(self) -> float:
        """Get current volume."""
        return self._volume

    def stop(self):
        """Stop current playback."""
        self._is_playing = False
        if self._current_track and self._on_track_end:
            self._on_track_end(self._current_track)
        self._current_track = None

    async def close(self):
        """Close the Spotify service."""
        self.stop()
        if self._session:
            # librespot session cleanup if needed
            pass
        self.logger.info("Spotify service closed")
