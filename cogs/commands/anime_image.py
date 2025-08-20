import discord
import aiohttp
import random
import asyncio
import time
from discord.ext import commands
from discord import app_commands
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


@dataclass
class AnimeImageData:
    """Data structure for anime image information."""
    id: str
    original_url: str
    x332_url: str
    x166_url: str


@dataclass
class AnimeData:
    """Data structure for anime information from Shikimori GraphQL."""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.mal_id = data.get('malId')
        self.name = data.get('name', 'Unknown')
        self.english = data.get('english', '')
        self.russian = data.get('russian', '')
        self.synonyms = data.get('synonyms', [])
        self.score = data.get('score', 0.0) or 0.0
        self.episodes = data.get('episodes', 0) or 0
        self.kind = data.get('kind', 'Unknown')
        self.status = data.get('status', 'Unknown')
        self.year = self._extract_year(data.get('airedOn', {}))
        self.genres = self._extract_genres(data.get('genres', []))
        self.studios = self._extract_studios(data.get('studios', []))
        self.poster_url = self._extract_poster(data.get('poster', {}))
        self.screenshots = self._extract_screenshots(data.get('screenshots', []))
        self.franchise = data.get('franchise', '')
        
    def _extract_year(self, aired_on: Dict) -> int:
        """Extract year from airedOn data."""
        if aired_on and aired_on.get('year'):
            return aired_on['year']
        return 0
    
    def _extract_genres(self, genres_data: List) -> List[str]:
        """Extract genre names from Shikimori data."""
        if not genres_data:
            return ['Unknown']
        return [genre.get('name', 'Unknown') for genre in genres_data if genre.get('name')]
    
    def _extract_studios(self, studios_data: List) -> List[str]:
        """Extract studio names from Shikimori data."""
        if not studios_data:
            return ['Unknown']
        return [studio.get('name', 'Unknown') for studio in studios_data if studio.get('name')]
    
    def _extract_poster(self, poster_data: Dict) -> Optional[str]:
        """Extract poster URL from Shikimori data."""
        if not poster_data:
            return None
        return poster_data.get('originalUrl') or poster_data.get('mainUrl')
    
    def _extract_screenshots(self, screenshots_data: List) -> List[AnimeImageData]:
        """Extract screenshot data from Shikimori data."""
        screenshots = []
        for screenshot in screenshots_data:
            screenshots.append(AnimeImageData(
                id=screenshot.get('id', ''),
                original_url=screenshot.get('originalUrl', ''),
                x332_url=screenshot.get('x332Url', ''),
                x166_url=screenshot.get('x166Url', '')
            ))
        return screenshots
    
    def get_all_titles(self) -> List[str]:
        """Get all possible titles including synonyms for matching."""
        titles = [self.name]
        
        if self.english and self.english.strip():
            titles.append(self.english)
        if self.russian and self.russian.strip():
            titles.append(self.russian)
        
        # Add synonyms
        for synonym in self.synonyms:
            if synonym and synonym.strip():
                titles.append(synonym)
        
        return [title.strip() for title in titles if title.strip()]
    
    def has_images(self) -> bool:
        """Check if anime has any screenshots/images."""
        return len(self.screenshots) > 0


class AnimeImageCog(BaseCommand):
    """Fetch random anime images from Shikimori."""
    
    def __init__(self, bot, services: ServiceContainer):
        super().__init__(bot, services)
        self.shikimori_base_url = "https://shikimori.one/api/graphql"
        
        # Rate limiting for Shikimori API (5 RPS, 90 RPM)
        self._last_request_time = 0
        self._request_count = 0
        self._request_timestamps = []
        
        # Cache for autocomplete results
        self.autocomplete_cache: Dict[str, Tuple[List[Tuple[str, str]], float]] = {}
        self.autocomplete_cache_timeout = 300  # 5 minutes cache timeout
    
    async def _rate_limit_check(self):
        """Ensure we don't exceed Shikimori rate limits."""
        current_time = time.time()
        
        # Clean old timestamps (older than 1 minute)
        self._request_timestamps = [
            timestamp for timestamp in self._request_timestamps 
            if current_time - timestamp < 60
        ]
        
        # Check RPM limit (90 requests per minute)
        if len(self._request_timestamps) >= 90:
            sleep_time = 60 - (current_time - self._request_timestamps[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Check RPS limit (5 requests per second)
        if current_time - self._last_request_time < 0.2:  # 1/5 second
            await asyncio.sleep(0.2 - (current_time - self._last_request_time))
        
        self._last_request_time = time.time()
        self._request_timestamps.append(self._last_request_time)
    
    async def _query_shikimori_autocomplete(self, query: str, variables: Optional[Dict] = None) -> Optional[Dict]:
        """Execute a GraphQL query against Shikimori API with lighter rate limiting for autocomplete."""
        # Light rate limiting for autocomplete - allow one request per 0.2 seconds
        current_time = time.time()
        if current_time - self._last_request_time < 0.2:
            await asyncio.sleep(0.2 - (current_time - self._last_request_time))
        
        self._last_request_time = time.time()
        
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Geminya Discord Bot"  # Required by Shikimori
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=2)  # Very short timeout for autocomplete
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.shikimori_base_url,
                    json=payload,
                    headers=headers,
                    timeout=timeout
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'errors' in data:
                            self.logger.warning(f"Shikimori GraphQL errors in autocomplete: {data['errors']}")
                            return None
                        return data.get('data')
                    else:
                        self.logger.warning(f"Shikimori API returned status {response.status} in autocomplete")
                        return None
        except Exception as e:
            self.logger.warning(f"Error querying Shikimori API for autocomplete: {e}")
            return None
    
    async def _query_shikimori(self, query: str, variables: Optional[Dict] = None) -> Optional[Dict]:
        """Execute a GraphQL query against Shikimori API."""
        await self._rate_limit_check()
        
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Geminya Discord Bot"  # Required by Shikimori
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.shikimori_base_url,
                    json=payload,
                    headers=headers,
                    timeout=timeout
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'errors' in data:
                            self.logger.error(f"Shikimori GraphQL errors: {data['errors']}")
                            return None
                        return data.get('data')
                    else:
                        self.logger.warning(f"Shikimori API returned status {response.status}")
                        return None
        except Exception as e:
            self.logger.error(f"Error querying Shikimori API: {e}")
            return None
    
    async def _search_anime_by_name(self, anime_name: str) -> Optional[AnimeData]:
        """Search for a specific anime by name."""
        query = """
        query SearchAnimeByName($search: String!, $limit: PositiveInt!) {
          animes(search: $search, limit: $limit) {
            id
            malId
            name
            english
            russian
            synonyms
            score
            episodes
            kind
            status
            airedOn { year }
            genres { name }
            studios { name }
            franchise
            poster { originalUrl mainUrl }
            screenshots {
              id
              originalUrl
              x332Url
              x166Url
            }
          }
        }
        """
        
        variables = {
            "search": anime_name.strip(),
            "limit": 1
        }
        
        data = await self._query_shikimori(query, variables)
        if data and data.get('animes') and len(data['animes']) > 0:
            anime = AnimeData(data['animes'][0])
            if anime.has_images():
                return anime
        
        return None
    
    async def _search_anime_autocomplete(self, search_term: str, limit: int = 25) -> List[Tuple[str, str]]:
        """Search for anime names for autocomplete. Returns list of (display_name, value) tuples."""
        if not search_term or len(search_term.strip()) < 2:
            return []
        
        # Create cache key
        search_key = f"anime_{search_term.lower().strip()}"
        
        # Check cache first
        current_time = time.time()
        if search_key in self.autocomplete_cache:
            cached_data, timestamp = self.autocomplete_cache[search_key]
            if current_time - timestamp < self.autocomplete_cache_timeout:
                # Return cached results
                return cached_data[:limit]
        
        query = """
        query SearchAnimeAutocomplete($search: String!, $limit: PositiveInt!) {
          animes(search: $search, limit: $limit) {
            name
            english
            russian
            synonyms
            airedOn { year }
            screenshots {
              id
            }
          }
        }
        """
        
        variables = {
            "search": search_term.strip(),
            "limit": limit
        }
        
        try:
            data = await self._query_shikimori_autocomplete(query, variables)
            if not data or not data.get('animes'):
                return []
            
            results = []
            for anime_data in data['animes']:
                # Only include anime that have screenshots/images
                if not anime_data.get('screenshots'):
                    continue
                
                name = anime_data.get('name', '')
                english = anime_data.get('english', '')
                russian = anime_data.get('russian', '')
                synonyms = anime_data.get('synonyms', [])
                year = anime_data.get('airedOn', {}).get('year', '')
                
                # Primary name (usually Japanese romanized)
                if name:
                    display_name = f"{name}"
                    if year:
                        display_name += f" ({year})"
                    results.append((display_name, name))
                
                # English name if different and available
                if english and english != name and len(results) < limit:
                    display_name = f"{english}"
                    if year:
                        display_name += f" ({year})"
                    results.append((display_name, english))
                
                # Russian name if different and available
                if russian and russian != name and russian != english and len(results) < limit:
                    display_name = f"{russian}"
                    if year:
                        display_name += f" ({year})"
                    results.append((display_name, russian))
                
                # Add synonyms (alternative titles)
                if synonyms and len(results) < limit:
                    for synonym in synonyms:
                        if synonym and synonym.strip() and len(results) < limit:
                            # Check if synonym is different from existing titles
                            if synonym not in [name, english, russian]:
                                display_name = f"{synonym}"
                                if year:
                                    display_name += f" ({year})"
                                results.append((display_name, synonym))
                
                # Stop if we have enough results
                if len(results) >= limit:
                    break
            
            # Cache the results
            self.autocomplete_cache[search_key] = (results, current_time)
            
            # Clean old cache entries (keep cache size reasonable)
            if len(self.autocomplete_cache) > 50:
                # Remove oldest entries
                old_keys = sorted(self.autocomplete_cache.keys(), 
                                key=lambda k: self.autocomplete_cache[k][1])[:25]
                for key in old_keys:
                    del self.autocomplete_cache[key]
            
            return results[:limit]
            
        except Exception as e:
            self.logger.error(f"Error in anime autocomplete search: {e}")
            return []
    
    async def anime_name_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete function for anime names."""
        if not current or len(current.strip()) < 2:
            return []
        
        try:
            # Use asyncio.wait_for to ensure we don't exceed Discord's autocomplete timeout
            results = await asyncio.wait_for(
                self._search_anime_autocomplete(current, limit=25),
                timeout=2.0  # 2 second max timeout
            )
            
            # Convert to app_commands.Choice objects
            choices = []
            for display_name, value in results:
                # Ensure display name fits Discord's limit (100 characters)
                if len(display_name) > 100:
                    display_name = display_name[:97] + "..."
                
                # Ensure value fits Discord's limit (100 characters)  
                if len(value) > 100:
                    value = value[:100]
                
                choices.append(app_commands.Choice(name=display_name, value=value))
            
            return choices[:25]  # Discord limit is 25 choices
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Anime autocomplete timeout for query: '{current}'")
            return []
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.logger.warning(f"Network error in anime autocomplete: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error in anime name autocomplete: {e}")
            return []
    
    @app_commands.command(name="animeimage", description="Get a random image from a specified anime!")
    @app_commands.describe(
        anime_name="The name of the anime to get an image from"
    )
    @app_commands.autocomplete(anime_name=anime_name_autocomplete)
    async def animeimage(
        self, 
        interaction: discord.Interaction, 
        anime_name: str
    ):
        """Main command handler for fetching random anime images."""
        try:
            # Validate input
            if not anime_name or not anime_name.strip():
                embed = discord.Embed(
                    title="❌ Missing Anime Name",
                    description="Please provide an anime name!\nExample: `/animeimage Attack on Titan`",
                    color=0xff6b6b
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Send initial "searching" message
            embed = discord.Embed(
                title="🔍 Searching for Anime...",
                description=f"Looking for images from **{anime_name.strip()}**...",
                color=0x3498db
            )
            await interaction.response.send_message(embed=embed)
            
            # Search for the anime
            anime = await self._search_anime_by_name(anime_name.strip())
            
            if not anime:
                embed = discord.Embed(
                    title="❌ Anime Not Found",
                    description=f"Sorry! I couldn't find any anime matching **'{anime_name.strip()}'** or it doesn't have any images.\n\n"
                               f"Please try:\n"
                               f"• Using the autocomplete feature\n"
                               f"• Checking the spelling\n"
                               f"• Using alternative titles (English/Japanese)",
                    color=0xff6b6b
                )
                await interaction.edit_original_response(embed=embed)
                return
            
            if not anime.screenshots:
                embed = discord.Embed(
                    title="❌ No Images Available",
                    description=f"**{anime.name}** was found but doesn't have any screenshots/images available.",
                    color=0xff6b6b
                )
                await interaction.edit_original_response(embed=embed)
                return
            
            # Select a random image
            random_image = random.choice(anime.screenshots)
            
            # Create result embed
            embed = discord.Embed(
                title=f"📸 Random Image from {anime.name}",
                color=0x00ff9f
            )
            
            # Add anime information
            description_parts = []
            
            if anime.english and anime.english != anime.name:
                description_parts.append(f"**English:** {anime.english}")
            
            if anime.year:
                description_parts.append(f"**Year:** {anime.year}")
            
            if anime.episodes:
                description_parts.append(f"**Episodes:** {anime.episodes}")
            
            if anime.score > 0:
                description_parts.append(f"**Score:** {anime.score}/10")
            
            if anime.genres and anime.genres[0] != 'Unknown':
                genres_display = ', '.join(anime.genres[:3])
                if len(anime.genres) > 3:
                    genres_display += f" (+{len(anime.genres) - 3} more)"
                description_parts.append(f"**Genres:** {genres_display}")
            
            if anime.studios and anime.studios[0] != 'Unknown':
                studios_display = ', '.join(anime.studios[:2])
                if len(anime.studios) > 2:
                    studios_display += f" (+{len(anime.studios) - 2} more)"
                description_parts.append(f"**Studio:** {studios_display}")
            
            if description_parts:
                embed.description = '\n'.join(description_parts)
            
            # Set the random image
            image_url = random_image.x332_url or random_image.original_url
            embed.set_image(url=image_url)
            
            # Add thumbnail if poster is available
            if anime.poster_url:
                embed.set_thumbnail(url=anime.poster_url)
            
            # Add footer with image info
            embed.set_footer(
                text=f"🎲 Random image from {len(anime.screenshots)} available screenshots • ID: {random_image.id}"
            )
            
            await interaction.edit_original_response(embed=embed)
            self.logger.info(f"Displayed random image for anime: {anime.name} (User: {interaction.user})")
            
        except Exception as e:
            self.logger.error(f"Error in animeimage command: {e}")
            error_embed = discord.Embed(
                title="❌ Command Error",
                description="An unexpected error occurred. Please try again.",
                color=0xff0000
            )
            
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)


async def setup(bot):
    """Setup function to add the cog to the bot."""
    services = getattr(bot, 'services', None)
    if services is None:
        raise RuntimeError("Services container not found. Make sure bot is properly initialized.")
    
    await bot.add_cog(AnimeImageCog(bot, services))
