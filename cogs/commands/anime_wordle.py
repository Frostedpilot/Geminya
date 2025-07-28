import discord
import aiohttp
import random
import asyncio
from discord.ext import commands
from discord import app_commands
from typing import Dict, List, Optional, Any, Union
import json

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


class AnimeData:
    """Data structure for anime information."""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.title = self._extract_title(data.get('title', {}))
        self.synonyms = data.get('synonyms', [])
        self.start_date = data.get('startDate', {})
        self.year = self._extract_year(self.start_date)
        self.score = data.get('averageScore', 0) or 0
        self.episodes = data.get('episodes', 0) or 0
        self.genres = [genre for genre in data.get('genres', [])]
        self.studios = self._extract_studios(data.get('studios', {}).get('nodes', []))
        self.source = data.get('source', 'UNKNOWN')
        self.format = data.get('format', 'UNKNOWN')
    
    def _extract_title(self, title_data: Dict) -> str:
        """Extract the best available title."""
        if isinstance(title_data, dict):
            return (title_data.get('english') or 
                   title_data.get('romaji') or 
                   title_data.get('native') or 
                   'Unknown')
        return str(title_data) if title_data else 'Unknown'
    
    def _extract_year(self, start_date: Dict) -> int:
        """Extract year from start date."""
        if isinstance(start_date, dict):
            return start_date.get('year', 0) or 0
        return 0
    
    def _extract_studios(self, studios_data: List) -> List[str]:
        """Extract studio names."""
        if not studios_data:
            return ['Unknown']
        return [studio.get('name', 'Unknown') for studio in studios_data if studio.get('name')]
    
    def get_all_titles(self) -> List[str]:
        """Get all possible titles including synonyms for matching, filtered for English/Latin characters only."""
        titles = [self.title]
        if self.synonyms:
            titles.extend(self.synonyms)
        
        # Filter titles to only include those with English/Latin characters and numbers
        filtered_titles = []
        for title in titles:
            if title and title.strip():
                # Check if title contains only Latin alphabet, numbers, spaces, and common punctuation
                if self._is_latin_title(title.strip()):
                    filtered_titles.append(title.strip())
        
        return filtered_titles
    
    def _is_latin_title(self, title: str) -> bool:
        """Check if title contains only Latin characters, numbers, and common punctuation."""
        import re
        # Allow Latin letters (a-z, A-Z), numbers (0-9), spaces, and extended punctuation
        # This includes accented characters like é, ñ, ü, etc. and many special characters used in anime titles
        # Added: ♥ ★ ☆ × ÷ ♦ ♠ ♣ ♪ ♫ ° † ‡ • … — – ' ' " " ¡ ¿ § ¤ ® © ™ ± ² ³ ¼ ½ ¾
        latin_pattern = re.compile(r'^[a-zA-Z0-9\s\-_\'\"\.!?\(\)\[\]:&+,;♥★☆×÷♦♠♣♪♫°†‡•…—–''""¡¿§¤®©™±²³¼½¾~@#$%^*={}|\\/<>]*$')
        return bool(latin_pattern.match(title))


class AnimeWordle:
    """Game state for anime Wordle."""
    
    def __init__(self, target_anime: AnimeData):
        self.target = target_anime
        self.guesses: List[AnimeData] = []
        self.max_guesses = 6
        self.is_complete = False
        self.is_won = False
    
    def add_guess(self, guess: AnimeData) -> bool:
        """Add a guess and check if game is complete."""
        self.guesses.append(guess)
        
        if guess.id == self.target.id:
            self.is_complete = True
            self.is_won = True
            return True
        
        if len(self.guesses) >= self.max_guesses:
            self.is_complete = True
            self.is_won = False
        
        return False
    
    def get_comparison(self, guess: AnimeData) -> Dict[str, str]:
        """Compare guess with target and return result indicators."""
        comparison = {}
        
        # Title comparison - check main title and synonyms
        guess_titles = [title.lower().strip() for title in guess.get_all_titles()]
        target_titles = [title.lower().strip() for title in self.target.get_all_titles()]
        
        title_match = any(guess_title in target_titles for guess_title in guess_titles)
        comparison['title'] = '✅' if title_match else '❌'
        
        # Year comparison
        if guess.year == self.target.year:
            comparison['year'] = '✅'
        elif guess.year < self.target.year:
            comparison['year'] = '⬆️'
        else:
            comparison['year'] = '⬇️'
        
        # Score comparison
        if guess.score == self.target.score:
            comparison['score'] = '✅'
        elif guess.score < self.target.score:
            comparison['score'] = '⬆️'
        else:
            comparison['score'] = '⬇️'
        
        # Episodes comparison
        if guess.episodes == self.target.episodes:
            comparison['episodes'] = '✅'
        elif guess.episodes < self.target.episodes:
            comparison['episodes'] = '⬆️'
        else:
            comparison['episodes'] = '⬇️'
        
        # Genres comparison - show individual matches
        guess_genres = set(guess.genres)
        target_genres = set(self.target.genres)
        if guess_genres == target_genres:
            comparison['genres'] = '✅'
        else:
            # Show individual genre matches
            genre_matches = []
            for genre in guess.genres:
                if genre in target_genres:
                    genre_matches.append(f"{genre} ✅")
                else:
                    genre_matches.append(f"{genre} ❌")
            comparison['genres'] = ', '.join(genre_matches) if genre_matches else '❌'
        
        # Studio comparison - show individual matches
        guess_studios = set(guess.studios)
        target_studios = set(self.target.studios)
        if guess_studios == target_studios:
            comparison['studio'] = '✅'
        else:
            # Show individual studio matches
            studio_matches = []
            for studio in guess.studios:
                if studio in target_studios:
                    studio_matches.append(f"{studio} ✅")
                else:
                    studio_matches.append(f"{studio} ❌")
            comparison['studio'] = ', '.join(studio_matches) if studio_matches else '❌'
        
        # Source comparison
        comparison['source'] = '✅' if guess.source == self.target.source else '❌'
        
        # Format comparison
        comparison['format'] = '✅' if guess.format == self.target.format else '❌'
        
        return comparison


class AnimeWordleCog(BaseCommand):
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)
        self.games: Dict[int, AnimeWordle] = {}  # channel_id -> game
        self.anilist_url = "https://graphql.anilist.co"
    
    async def _query_anilist(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make a GraphQL query to AniList API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.anilist_url,
                    json={'query': query, 'variables': variables or {}},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('data')
                    else:
                        self.logger.warning(f"AniList API returned status {response.status}")
                        return None
        except Exception as e:
            self.logger.error(f"Error querying AniList API: {e}")
            return None
    
    async def _get_random_anime(self) -> Optional[AnimeData]:
        """Get a random anime for the game using weighted selection based on score ranges."""
        try:
            # Get score weights from config
            anime_config = getattr(self.services.config, 'anime_wordle', {})
            score_weights = anime_config.get('score_weights', {
                '90-100': 5, '80-89': 10, '70-79': 8, '60-69': 6,
                '50-59': 3, '40-49': 2, '30-39': 1, '0-29': 1
            })
            max_pages = anime_config.get('max_search_pages', 200)
            
            # Create weighted list of score ranges
            weighted_ranges = []
            for score_range, weight in score_weights.items():
                min_score, max_score = map(int, score_range.split('-'))
                weighted_ranges.extend([(min_score, max_score)] * weight)
            
            # Randomly select a score range based on weights
            selected_range = random.choice(weighted_ranges)
            min_score, max_score = selected_range
            
            # Query anime within the selected score range
            query = """
            query ($page: Int, $minScore: Int, $maxScore: Int) {
                Page(page: $page, perPage: 50) {
                    media(type: ANIME, sort: POPULARITY_DESC, isAdult: false, episodes_greater: 0, averageScore_greater: $minScore, averageScore_lesser: $maxScore) {
                        id
                        title {
                            english
                            romaji
                            native
                        }
                        synonyms
                        startDate {
                            year
                        }
                        averageScore
                        episodes
                        genres  
                        studios(isMain: true) {
                            nodes {
                                name
                            }
                        }
                        source
                        format
                    }
                }
            }
            """
            
            # Try to get anime from random pages within the score range
            max_attempts = 10
            for attempt in range(max_attempts):
                random_page = random.randint(1, max_pages)
                variables = {
                    'page': random_page,
                    'minScore': min_score,
                    'maxScore': max_score
                }
                
                data = await self._query_anilist(query, variables)
                if data and data.get('Page', {}).get('media'):
                    anime_list = data['Page']['media']
                    if anime_list:
                        # Randomly select one anime from the page
                        selected_anime = random.choice(anime_list)
                        return AnimeData(selected_anime)
                
                # If no results, try a broader range or different page
                if attempt > 5:
                    # Fallback to a broader score range
                    min_score = max(0, min_score - 10)
                    max_score = min(100, max_score + 10)
            
            # Final fallback - get any popular anime
            fallback_query = """
            query ($page: Int) {
                Page(page: $page, perPage: 1) {
                    media(type: ANIME, sort: POPULARITY_DESC, isAdult: false, episodes_greater: 0) {
                        id
                        title {
                            english
                            romaji
                            native
                        }
                        synonyms
                        startDate {
                            year
                        }
                        averageScore
                        episodes
                        genres  
                        studios(isMain: true) {
                            nodes {
                                name
                            }
                        }
                        source
                        format
                    }
                }
            }
            """
            
            random_page = random.randint(1, 500)
            data = await self._query_anilist(fallback_query, {'page': random_page})
            if data and data.get('Page', {}).get('media'):
                return AnimeData(data['Page']['media'][0])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in weighted anime selection: {e}")
            return None
    
    async def _search_anime(self, search_term: str) -> Optional[AnimeData]:
        """Search for an anime by name."""
        query = """
        query ($search: String) {
            Media(search: $search, type: ANIME, isAdult: false) {
                id
                title {
                    english
                    romaji
                    native
                }
                synonyms
                startDate {
                    year
                }
                averageScore
                episodes
                genres
                studios(isMain: true) {
                    nodes {
                        name
                    }
                }
                source
                format
            }
        }
        """
        
        variables = {'search': search_term}
        data = await self._query_anilist(query, variables)
        
        if data and data.get('Media'):
            return AnimeData(data['Media'])
        
        return None
    
    async def _search_multiple_anime(self, search_term: str, limit: int = 25) -> List[Dict[str, str]]:
        """Search for multiple anime and return choices with all titles/synonyms."""
        if not search_term or len(search_term.strip()) < 2:
            return []
        
        query = """
        query ($search: String, $perPage: Int) {
            Page(page: 1, perPage: $perPage) {
                media(search: $search, type: ANIME, isAdult: false) {
                    id
                    title {
                        english
                        romaji
                        native
                    }
                    synonyms
                    startDate {
                        year
                    }
                }
            }
        }
        """
        
        variables = {'search': search_term.strip(), 'perPage': limit}
        data = await self._query_anilist(query, variables)
        
        choices = []
        if data and data.get('Page', {}).get('media'):
            for anime in data['Page']['media']:
                anime_data = AnimeData(anime)
                
                # Get all possible titles for this anime (already filtered for Latin characters)
                all_titles = anime_data.get_all_titles()
                
                # Filter titles that contain the search term (case-insensitive)
                search_lower = search_term.lower().strip()
                matching_titles = [
                    title for title in all_titles 
                    if search_lower in title.lower()
                ]
                
                # If no direct matches in filtered titles, skip this anime
                # (don't include non-Latin titles even as fallback)
                if not matching_titles:
                    continue
                
                # Add each matching title as a choice
                for title in matching_titles[:3]:  # Limit to 3 titles per anime to avoid clutter
                    if len(choices) < 25:  # Discord limit
                        # Create display name with year for clarity
                        display_name = f"{title}"
                        if anime_data.year:
                            display_name += f" ({anime_data.year})"
                        
                        # Truncate if too long (Discord choice name limit is 100 chars)
                        if len(display_name) > 100:
                            display_name = display_name[:97] + "..."
                        
                        choices.append({
                            'name': display_name,
                            'value': title
                        })
        
        return choices
    
    async def anime_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete function for anime names."""
        try:
            choices_data = await self._search_multiple_anime(current, limit=20)
            return [
                app_commands.Choice(name=choice['name'], value=choice['value'])
                for choice in choices_data
            ]
        except Exception as e:
            self.logger.error(f"Error in anime autocomplete: {e}")
            return []
    
    def _create_guess_embed(self, game: AnimeWordle, guess: AnimeData, comparison: Dict[str, str]) -> discord.Embed:
        """Create an embed showing the guess results."""
        embed = discord.Embed(
            title=f"Anime Wordle - Guess {len(game.guesses)}/{game.max_guesses}",
            color=0x02A9FF
        )
        
        # Add guess information
        embed.add_field(
            name="🎯 Your Guess",
            value=f"**{guess.title}**",
            inline=False
        )
        
        # Create comparison table
        comparison_text = (
            f"**Title:** {comparison['title']}\n"
            f"**Year:** {guess.year} {comparison['year']}\n"
            f"**Score:** {guess.score}/100 {comparison['score']}\n"
            f"**Episodes:** {guess.episodes} {comparison['episodes']}\n"
            f"**Source:** {guess.source} {comparison['source']}\n"
            f"**Format:** {guess.format} {comparison['format']}"
        )
        
        embed.add_field(
            name="📊 Comparison",
            value=comparison_text,
            inline=False
        )
        
        # Add genres comparison separately to handle longer text
        embed.add_field(
            name="🎭 Genres",
            value=comparison['genres'],
            inline=False
        )
        
        # Add studio comparison separately to handle longer text
        embed.add_field(
            name="🏢 Studio",
            value=comparison['studio'],
            inline=False
        )
        
        # Add legend
        legend = (
            "**Legend:**\n"
            "✅ = Correct/Match\n"
            "⬆️ = Target is higher\n"
            "⬇️ = Target is lower\n"
            "❌ = Incorrect/No match"
        )
        embed.add_field(name="ℹ️ Legend", value=legend, inline=False)
        
        return embed
    
    def _create_game_over_embed(self, game: AnimeWordle) -> discord.Embed:
        """Create an embed for game completion."""
        if game.is_won:
            embed = discord.Embed(
                title="🎉 Congratulations!",
                description=f"You guessed it in {len(game.guesses)} tries!",
                color=0x00FF00
            )
        else:
            embed = discord.Embed(
                title="💀 Game Over!",
                description="Better luck next time!",
                color=0xFF0000
            )
        
        # Show the target anime
        target_info = (
            f"**Title:** {game.target.title}\n"
            f"**Year:** {game.target.year}\n"
            f"**Score:** {game.target.score}/100\n"
            f"**Episodes:** {game.target.episodes}\n"
            f"**Genres:** {', '.join(game.target.genres)}\n"
            f"**Studio:** {', '.join(game.target.studios)}\n"
            f"**Source:** {game.target.source}\n"
            f"**Format:** {game.target.format}"
        )
        
        embed.add_field(
            name="🎯 The Answer",
            value=target_info,
            inline=False
        )
        
        return embed
    
    @app_commands.command(
        name="animewordle",
        description="Play Anime Wordle! Guess the anime based on its properties."
    )
    @app_commands.describe(
        action="Choose an action",
        guess="Anime name to guess (only for 'guess' action)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Start New Game", value="start"),
        app_commands.Choice(name="Make a Guess", value="guess"),
        app_commands.Choice(name="Get Hint", value="hint"),
        app_commands.Choice(name="Give Up", value="giveup")
    ])
    @app_commands.autocomplete(guess=anime_autocomplete)
    async def animewordle(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        guess: Optional[str] = None
    ):
        """Main anime wordle command."""
        if not interaction.channel:
            await interaction.response.send_message(
                "❌ This command can only be used in a channel!",
                ephemeral=True
            )
            return
            
        channel_id = interaction.channel.id
        
        if action.value == "start":
            await self._start_game(interaction, channel_id)
        elif action.value == "guess":
            await self._make_guess(interaction, channel_id, guess or "")
        elif action.value == "hint":
            await self._give_hint(interaction, channel_id)
        elif action.value == "giveup":
            await self._give_up(interaction, channel_id)
    
    async def _start_game(self, interaction: discord.Interaction, channel_id: int):
        """Start a new anime wordle game."""
        await interaction.response.defer(thinking=True)
        
        try:
            target_anime = await self._get_random_anime()
            if not target_anime:
                await interaction.followup.send(
                    "❌ Failed to fetch anime data. Please try again later!",
                    ephemeral=True
                )
                return
            
            self.games[channel_id] = AnimeWordle(target_anime)
            
            embed = discord.Embed(
                title="🎮 Anime Wordle Started!",
                description=(
                    "Guess the anime! You have 6 tries.\n"
                    "Use `/animewordle guess <anime_name>` to make a guess.\n\n"
                    "**Properties to match:**\n"
                    "• Title, Year, Score, Episodes\n"
                    "• Genres, Studio, Source, Format"
                ),
                color=0x02A9FF
            )
            
            embed.add_field(
                name="ℹ️ How to Play",
                value=(
                    "**Arrows indicate:**\n"
                    "⬆️ Target value is higher\n"
                    "⬇️ Target value is lower\n"
                    "✅ Exact match\n"
                    "❌ No match"
                ),
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            self.logger.info(f"Started anime wordle game in channel {channel_id} with target: {target_anime.title}")
            
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            self.logger.error(f"Error starting anime wordle game: {e}")
            await interaction.followup.send(
                "❌ An error occurred while starting the game. Please try again!",
                ephemeral=True
            )
    
    async def _make_guess(self, interaction: discord.Interaction, channel_id: int, guess: str):
        """Make a guess in the anime wordle game."""
        if channel_id not in self.games:
            await interaction.response.send_message(
                "❌ No active game in this channel! Use `/animewordle start` to begin.",
                ephemeral=True
            )
            return
        
        if not guess:
            await interaction.response.send_message(
                "❌ Please provide an anime name to guess!",
                ephemeral=True
            )
            return
        
        game = self.games[channel_id]
        
        if game.is_complete:
            await interaction.response.send_message(
                "❌ This game is already completed! Start a new game with `/animewordle start`.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(thinking=True)
        
        try:
            anime_data = await self._search_anime(guess)
            if not anime_data:
                await interaction.followup.send(
                    f"❌ Couldn't find anime: '{guess}'. Please check the spelling and try again!",
                    ephemeral=True
                )
                return
            
            game.add_guess(anime_data)
            comparison = game.get_comparison(anime_data)
            
            # Send guess result
            guess_embed = self._create_guess_embed(game, anime_data, comparison)
            await interaction.followup.send(embed=guess_embed)
            
            # Check if game is complete
            if game.is_complete:
                game_over_embed = self._create_game_over_embed(game)
                await interaction.followup.send(embed=game_over_embed)
                
                # Clean up the game
                del self.games[channel_id]
                
                self.logger.info(f"Anime wordle game completed in channel {channel_id}. Won: {game.is_won}")
            
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            self.logger.error(f"Error making guess in anime wordle: {e}")
            await interaction.followup.send(
                "❌ An error occurred while processing your guess. Please try again!",
                ephemeral=True
            )
    
    async def _give_hint(self, interaction: discord.Interaction, channel_id: int):
        """Give a hint for the current game."""
        if channel_id not in self.games:
            await interaction.response.send_message(
                "❌ No active game in this channel! Use `/animewordle start` to begin.",
                ephemeral=True
            )
            return
        
        game = self.games[channel_id]
        
        if game.is_complete:
            await interaction.response.send_message(
                "❌ This game is already completed!",
                ephemeral=True
            )
            return
        
        # Provide a random hint
        hints = [
            f"🎭 One of the genres is: {random.choice(game.target.genres)}",
            f"🏢 The studio is: {game.target.studios[0] if game.target.studios else 'Unknown'}",
            f"📅 It's from the {game.target.year}s" if game.target.year else "📅 Year is unknown",
            f"📺 Format: {game.target.format}",
            f"📚 Source: {game.target.source}",
            f"⭐ Score range: {(game.target.score // 10) * 10}-{(game.target.score // 10) * 10 + 9}" if game.target.score else "⭐ Score is unknown"
        ]
        
        hint = random.choice(hints)
        
        embed = discord.Embed(
            title="💡 Hint",
            description=hint,
            color=0xFFD700
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _give_up(self, interaction: discord.Interaction, channel_id: int):
        """Give up the current game."""
        if channel_id not in self.games:
            await interaction.response.send_message(
                "❌ No active game in this channel!",
                ephemeral=True
            )
            return
        
        game = self.games[channel_id]
        
        if game.is_complete:
            await interaction.response.send_message(
                "❌ This game is already completed!",
                ephemeral=True
            )
            return
        
        # End the game
        game.is_complete = True
        game.is_won = False
        
        game_over_embed = self._create_game_over_embed(game)
        await interaction.response.send_message(embed=game_over_embed)
        
        # Clean up
        del self.games[channel_id]
        
        self.logger.info(f"User gave up anime wordle game in channel {channel_id}")


async def setup(bot: commands.Bot):
    """Setup function for cog loading."""
    # Get services from bot instance
    services = getattr(bot, 'services', None)
    if services:
        await bot.add_cog(AnimeWordleCog(bot, services))
    else:
        # Fallback if services not available
        raise RuntimeError("Bot services not available")
