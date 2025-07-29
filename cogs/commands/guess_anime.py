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
class ScreenshotData:
    """Data structure for anime screenshot information."""
    id: str
    original_url: str
    x332_url: str
    x166_url: str


@dataclass
class ShikimoriAnimeData:
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
    
    def _extract_screenshots(self, screenshots_data: List) -> List[ScreenshotData]:
        """Extract screenshot data from Shikimori data."""
        screenshots = []
        for screenshot in screenshots_data:
            screenshots.append(ScreenshotData(
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
    
    def has_sufficient_screenshots(self, min_count: int = 4) -> bool:
        """Check if anime has enough screenshots for the game."""
        return len(self.screenshots) >= min_count


class GuessAnimeGame:
    """Game state for visual anime guessing game."""
    
    def __init__(self, target_anime: ShikimoriAnimeData, difficulty: str = "normal"):
        self.target = target_anime
        self.guesses: List[str] = []  # Store guess anime names/titles
        self.max_guesses = 4  # Exactly 4 tries, one for each screenshot
        self.is_complete = False
        self.is_won = False
        self.difficulty = difficulty
        self.start_time = time.time()
        
        # Screenshot progression system
        self.max_screenshots = 4
        self.current_screenshot_index = 0  # Which screenshot to show next
        self.revealed_screenshots: List[ScreenshotData] = []
        
        # Select 4 random screenshots for this game
        self.game_screenshots = self._select_game_screenshots()
        
        # Reveal first screenshot immediately
        if self.game_screenshots:
            self.reveal_next_screenshot()
    
    def _select_game_screenshots(self) -> List[ScreenshotData]:
        """Select 4 random screenshots from the target anime."""
        available_screenshots = self.target.screenshots.copy()
        
        if len(available_screenshots) < self.max_screenshots:
            # If not enough screenshots, use what we have
            return available_screenshots
        
        # Randomly select 4 screenshots
        return random.sample(available_screenshots, self.max_screenshots)
    
    def reveal_next_screenshot(self) -> bool:
        """Reveal the next screenshot. Returns True if screenshot was revealed."""
        if self.current_screenshot_index >= len(self.game_screenshots):
            return False
        
        next_screenshot = self.game_screenshots[self.current_screenshot_index]
        self.revealed_screenshots.append(next_screenshot)
        self.current_screenshot_index += 1
        return True
    
    def add_guess(self, guess_name: str) -> bool:
        """Add a guess and check if game is complete."""
        self.guesses.append(guess_name)
        
        # Check if guess matches any of the target anime titles
        guess_lower = guess_name.lower().strip()
        target_titles = [title.lower().strip() for title in self.target.get_all_titles()]
        
        # Check for exact match or close match
        if any(guess_lower == target_title for target_title in target_titles):
            self.is_complete = True
            self.is_won = True
            return True
        
        # Check for partial matches (for common alternative names)
        for target_title in target_titles:
            if len(guess_lower) > 3 and guess_lower in target_title:
                self.is_complete = True
                self.is_won = True
                return True
            if len(target_title) > 3 and target_title in guess_lower:
                self.is_complete = True
                self.is_won = True
                return True
        
        # Wrong guess - reveal next screenshot if available and not at max guesses
        if not self.is_won and len(self.guesses) < self.max_guesses:
            self.reveal_next_screenshot()
        
        # Check if max guesses reached (game over)
        if len(self.guesses) >= self.max_guesses:
            self.is_complete = True
            self.is_won = False
        
        return False
    
    def get_current_screenshot(self) -> Optional[ScreenshotData]:
        """Get the most recently revealed screenshot."""
        if not self.revealed_screenshots:
            return None
        return self.revealed_screenshots[-1]
    
    def get_screenshot_progress(self) -> str:
        """Get a string showing screenshot progress (e.g., "2/4")."""
        return f"{len(self.revealed_screenshots)}/{self.max_screenshots}"
    
    def get_attempts_remaining(self) -> int:
        """Get number of attempts remaining."""
        return max(0, self.max_guesses - len(self.guesses))
    
    def get_game_duration(self) -> int:
        """Get game duration in seconds."""
        return int(time.time() - self.start_time)
    
    def can_reveal_more_screenshots(self) -> bool:
        """Check if there are more screenshots to reveal."""
        return self.current_screenshot_index < len(self.game_screenshots)


class GuessAnimeCog(BaseCommand):
    """Visual anime guessing game using Shikimori screenshots."""
    
    def __init__(self, bot, services: ServiceContainer):
        super().__init__(bot, services)
        self.games: Dict[int, GuessAnimeGame] = {}  # channel_id -> game
        self.shikimori_base_url = "https://shikimori.one/api/graphql"
        
        # Rate limiting for Shikimori API (5 RPS, 90 RPM)
        self._last_request_time = 0
        self._request_count = 0
        self._request_timestamps = []
    
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
    
    def cleanup_game(self, channel_id: int):
        """Remove completed game from memory."""
        if channel_id in self.games:
            del self.games[channel_id]
    
    def _get_difficulty_filters(self, difficulty: str) -> Dict[str, Any]:
        """Get Shikimori query filters based on difficulty level."""
        if difficulty == "easy":
            return {"score": 8, "censored": True}
        elif difficulty == "normal":
            return {"score": 7, "censored": True}
        elif difficulty == "hard":
            return {"score": 6, "censored": True}
        elif difficulty == "expert":
            return {"score": 5, "censored": True}
        else:
            return {"score": 7, "censored": True}  # Default to normal
    
    async def _fetch_random_anime(self, difficulty: str) -> Optional[ShikimoriAnimeData]:
        """Fetch a random anime from Shikimori with sufficient screenshots."""
        filters = self._get_difficulty_filters(difficulty)
        
        # GraphQL query to get anime with screenshots
        query = """
        query GetAnimeWithScreenshots($limit: PositiveInt!, $score: Int, $censored: Boolean) {
          animes(limit: $limit, score: $score, censored: $censored, order: random) {
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
        
        # Try multiple times to find anime with enough screenshots
        for attempt in range(5):
            variables = {
                "limit": 20,  # Get multiple anime to choose from
                "score": filters["score"],
                "censored": filters["censored"]
            }
            
            data = await self._query_shikimori(query, variables)
            if not data or not data.get('animes'):
                continue
            
            # Filter anime with sufficient screenshots
            suitable_anime = []
            for anime_data in data['animes']:
                anime = ShikimoriAnimeData(anime_data)
                if anime.has_sufficient_screenshots(4):
                    suitable_anime.append(anime)
            
            if suitable_anime:
                return random.choice(suitable_anime)
        
        return None
    
    async def _search_anime(self, search_term: str) -> Optional[ShikimoriAnimeData]:
        """Search for anime by name on Shikimori."""
        query = """
        query SearchAnime($search: String!, $limit: PositiveInt!) {
          animes(search: $search, limit: $limit) {
            id
            malId
            name
            english
            russian
            synonyms
          }
        }
        """
        
        variables = {
            "search": search_term,
            "limit": 1
        }
        
        data = await self._query_shikimori(query, variables)
        if data and data.get('animes') and len(data['animes']) > 0:
            return ShikimoriAnimeData(data['animes'][0])
        
        return None
    
    @app_commands.command(name="guessanime", description="Start a visual anime guessing game!")
    @app_commands.describe(
        action="Choose an action: start, guess, giveup",
        difficulty="Game difficulty (only for start): easy, normal, hard, expert",
        anime_name="Your anime guess (only for guess action)"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="start", value="start"),
            app_commands.Choice(name="guess", value="guess"),
            app_commands.Choice(name="giveup", value="giveup")
        ],
        difficulty=[
            app_commands.Choice(name="easy", value="easy"),
            app_commands.Choice(name="normal", value="normal"),
            app_commands.Choice(name="hard", value="hard"),
            app_commands.Choice(name="expert", value="expert")
        ]
    )
    async def guessanime(
        self, 
        interaction: discord.Interaction, 
        action: str,
        difficulty: Optional[str] = "normal",
        anime_name: Optional[str] = None
    ):
        """Main command handler for visual anime guessing game."""
        try:
            if action == "start":
                await self._handle_start(interaction, difficulty or "normal")
            elif action == "guess":
                await self._handle_guess(interaction, anime_name)
            elif action == "giveup":
                await self._handle_giveup(interaction)
            else:
                await interaction.response.send_message("Invalid action. Please choose: start, guess, or giveup.", ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error in guessanime command: {e}")
            error_embed = discord.Embed(
                title="❌ Command Error",
                description="An unexpected error occurred. Please try again.",
                color=0xff0000
            )
            
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
    
    async def _handle_start(self, interaction: discord.Interaction, difficulty: str):
        """Handle starting a new game."""
        if not interaction.channel_id:
            await interaction.response.send_message("Error: Could not determine channel ID.")
            return
            
        channel_id = interaction.channel_id
        
        # Check if game already exists in this channel
        if channel_id in self.games:
            embed = discord.Embed(
                title="🎮 Game Already Active!",
                description="There's already a Guess the Anime game running in this channel.\nUse `/guessanime giveup` to end it or continue playing!",
                color=0xff6b6b
            )
            await interaction.response.send_message(embed=embed)
            return
        
        # Send initial "searching" message
        embed = discord.Embed(
            title="🔍 Searching for Anime...",
            description=f"Finding a {difficulty} difficulty anime with screenshots...",
            color=0x3498db
        )
        await interaction.response.send_message(embed=embed)
        
        try:
            # Fetch random anime from Shikimori
            target_anime = await self._fetch_random_anime(difficulty)
            
            if not target_anime:
                embed = discord.Embed(
                    title="❌ No Anime Found",
                    description="Sorry! Couldn't find a suitable anime for this difficulty. Please try again.",
                    color=0xff6b6b
                )
                await interaction.edit_original_response(embed=embed)
                return
            
            # Create new game
            game = GuessAnimeGame(target_anime, difficulty)
            self.games[channel_id] = game
            
            # Get first screenshot
            first_screenshot = game.get_current_screenshot()
            if not first_screenshot:
                embed = discord.Embed(
                    title="❌ Screenshot Error",
                    description="Error loading screenshots for this anime. Please try again.",
                    color=0xff6b6b
                )
                await interaction.edit_original_response(embed=embed)
                self.cleanup_game(channel_id)
                return
            
            # Create game start embed
            embed = discord.Embed(
                title="🎌 Guess the Anime!",
                description=f"**Difficulty:** {difficulty.title()}\n"
                          f"**Screenshots:** {game.get_screenshot_progress()}\n"
                          f"**Attempts Remaining:** {game.get_attempts_remaining()}\n\n"
                          f"Look at the screenshot and guess the anime!\n"
                          f"Use `/guessanime guess <anime_name>` to make a guess.",
                color=0x00ff9f
            )
            
            # Add screenshot
            embed.set_image(url=first_screenshot.x332_url or first_screenshot.original_url)
            embed.set_footer(text="🎮 Good luck!")
            
            await interaction.edit_original_response(embed=embed)
            self.logger.info(f"Started guess anime game in channel {channel_id}, target: {target_anime.name}")
            
        except Exception as e:
            self.logger.error(f"Error starting guess anime game: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while starting the game. Please try again.",
                color=0xff6b6b
            )
            await interaction.edit_original_response(embed=embed)
    
    async def _handle_guess(self, interaction: discord.Interaction, anime_name: Optional[str]):
        """Handle making a guess."""
        if not interaction.channel_id:
            await interaction.response.send_message("Error: Could not determine channel ID.")
            return
            
        channel_id = interaction.channel_id
        
        # Check if game exists
        if channel_id not in self.games:
            embed = discord.Embed(
                title="❌ No Active Game",
                description="There's no active game in this channel.\nUse `/guessanime start` to begin a new game!",
                color=0xff6b6b
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if anime name provided
        if not anime_name or not anime_name.strip():
            embed = discord.Embed(
                title="❌ Missing Anime Name",
                description="Please provide an anime name to guess!\nExample: `/guessanime guess Attack on Titan`",
                color=0xff6b6b
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        game = self.games[channel_id]
        
        # Check if game is already complete
        if game.is_complete:
            embed = discord.Embed(
                title="🎮 Game Already Complete",
                description="This game has already ended.\nUse `/guessanime start` to begin a new game!",
                color=0xff6b6b
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Make the guess
        anime_name_clean = anime_name.strip()
        is_correct = game.add_guess(anime_name_clean)
        
        if is_correct:
            # Correct guess - game won!
            embed = discord.Embed(
                title="🎉 Correct! You Win!",
                description=f"**{anime_name_clean}** is correct!\n\n"
                          f"**Anime:** {game.target.name}\n"
                          f"**English:** {game.target.english or 'N/A'}\n"
                          f"**Year:** {game.target.year or 'Unknown'}\n"
                          f"**Episodes:** {game.target.episodes}\n"
                          f"**Score:** {game.target.score}/10\n"
                          f"**Genres:** {', '.join(game.target.genres[:3])}\n"
                          f"**Studio:** {', '.join(game.target.studios[:2])}\n\n"
                          f"🎯 **Guessed in {len(game.guesses)}/{game.max_guesses} attempts**\n"
                          f"⏱️ **Time:** {game.get_game_duration()}s",
                color=0x00ff00
            )
            
            # Add poster if available
            if game.target.poster_url:
                embed.set_thumbnail(url=game.target.poster_url)
            
            await interaction.response.send_message(embed=embed)
            self.cleanup_game(channel_id)
            
        elif game.is_complete:
            # Game over - all attempts used
            embed = discord.Embed(
                title="💀 Game Over!",
                description=f"Sorry! You've used all {game.max_guesses} attempts.\n\n"
                          f"**The answer was:** {game.target.name}\n"
                          f"**English:** {game.target.english or 'N/A'}\n"
                          f"**Year:** {game.target.year or 'Unknown'}\n"
                          f"**Episodes:** {game.target.episodes}\n"
                          f"**Score:** {game.target.score}/10\n"
                          f"**Genres:** {', '.join(game.target.genres[:3])}\n"
                          f"**Studio:** {', '.join(game.target.studios[:2])}\n\n"
                          f"Better luck next time!",
                color=0xff0000
            )
            
            # Add poster if available
            if game.target.poster_url:
                embed.set_thumbnail(url=game.target.poster_url)
            
            # Show all screenshots
            if len(game.game_screenshots) > 0:
                embed.set_image(url=game.game_screenshots[-1].x332_url or game.game_screenshots[-1].original_url)
            
            await interaction.response.send_message(embed=embed)
            self.cleanup_game(channel_id)
            
        else:
            # Wrong guess - continue game
            current_screenshot = game.get_current_screenshot()
            
            embed = discord.Embed(
                title="❌ Wrong Guess",
                description=f"**'{anime_name_clean}'** is not correct.\n\n"
                          f"**Screenshots:** {game.get_screenshot_progress()}\n"
                          f"**Attempts Remaining:** {game.get_attempts_remaining()}\n\n"
                          f"A new screenshot has been revealed!" if game.can_reveal_more_screenshots() or len(game.revealed_screenshots) > 1 else "Keep trying!",
                color=0xff9500
            )
            
            # Show current screenshot
            if current_screenshot:
                embed.set_image(url=current_screenshot.x332_url or current_screenshot.original_url)
            
            embed.set_footer(text="🎮 Keep trying!")
            
            await interaction.response.send_message(embed=embed)
    
    async def _handle_giveup(self, interaction: discord.Interaction):
        """Handle giving up the current game."""
        if not interaction.channel_id:
            await interaction.response.send_message("Error: Could not determine channel ID.")
            return
            
        channel_id = interaction.channel_id
        
        # Check if game exists
        if channel_id not in self.games:
            embed = discord.Embed(
                title="❌ No Active Game",
                description="There's no active game in this channel.\nUse `/guessanime start` to begin a new game!",
                color=0xff6b6b
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        game = self.games[channel_id]
        
        # Check if game is already complete
        if game.is_complete:
            embed = discord.Embed(
                title="🎮 Game Already Complete",
                description="This game has already ended.",
                color=0xff6b6b
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Show the answer
        embed = discord.Embed(
            title="🏳️ Game Ended - Answer Revealed",
            description=f"You gave up after {len(game.guesses)} guess(es).\n\n"
                      f"**The answer was:** {game.target.name}\n"
                      f"**English:** {game.target.english or 'N/A'}\n"
                      f"**Year:** {game.target.year or 'Unknown'}\n"
                      f"**Episodes:** {game.target.episodes}\n"
                      f"**Score:** {game.target.score}/10\n"
                      f"**Genres:** {', '.join(game.target.genres[:3])}\n"
                      f"**Studio:** {', '.join(game.target.studios[:2])}\n\n"
                      f"⏱️ **Game Duration:** {game.get_game_duration()}s",
            color=0xffaa00
        )
        
        # Add poster if available
        if game.target.poster_url:
            embed.set_thumbnail(url=game.target.poster_url)
        
        # Show all remaining screenshots
        if len(game.game_screenshots) > 0:
            # Show the last screenshot or current one
            last_screenshot = game.game_screenshots[-1]
            embed.set_image(url=last_screenshot.x332_url or last_screenshot.original_url)
        
        # Add field showing previous guesses if any
        if game.guesses:
            guesses_text = ", ".join(game.guesses)
            if len(guesses_text) > 1024:  # Discord field limit
                guesses_text = guesses_text[:1021] + "..."
            embed.add_field(name="Your Guesses", value=guesses_text, inline=False)
        
        await interaction.response.send_message(embed=embed)
        self.cleanup_game(channel_id)


async def setup(bot):
    """Setup function to add the cog to the bot."""
    services = getattr(bot, 'services', None)
    if services is None:
        raise RuntimeError("Services container not found. Make sure bot is properly initialized.")
    
    await bot.add_cog(GuessAnimeCog(bot, services))
