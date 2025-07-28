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
        
        # Title comparison
        comparison['title'] = '✅' if guess.title.lower() == self.target.title.lower() else '❌'
        
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
        
        # Genres comparison
        guess_genres = set(guess.genres)
        target_genres = set(self.target.genres)
        if guess_genres == target_genres:
            comparison['genres'] = '✅'
        elif guess_genres & target_genres:  # Some overlap
            comparison['genres'] = '🟡'
        else:
            comparison['genres'] = '❌'
        
        # Studio comparison
        guess_studios = set(guess.studios)
        target_studios = set(self.target.studios)
        if guess_studios & target_studios:  # Any studio match
            comparison['studio'] = '✅'
        else:
            comparison['studio'] = '❌'
        
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
        """Get a random popular anime for the game."""
        query = """
        query ($page: Int) {
            Page(page: $page, perPage: 1) {
                media(type: ANIME, sort: POPULARITY_DESC, isAdult: false, episodes_greater: 0) {
                    id
                    title {
                        english
                        romaji
                        native
                    }
                    startDate {
                        year
                    }
                    averageScore
                    episodes
                    genres
                    studios {
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
        
        # Get a random page from the top 500 anime
        random_page = random.randint(1, 500)
        variables = {'page': random_page}
        
        data = await self._query_anilist(query, variables)
        if data and data.get('Page', {}).get('media'):
            anime_data = data['Page']['media'][0]
            return AnimeData(anime_data)
        
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
                startDate {
                    year
                }
                averageScore
                episodes
                genres
                studios {
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
            f"**Genres:** {', '.join(guess.genres[:3])} {comparison['genres']}\n"
            f"**Studio:** {', '.join(guess.studios[:2])} {comparison['studio']}\n"
            f"**Source:** {guess.source} {comparison['source']}\n"
            f"**Format:** {guess.format} {comparison['format']}"
        )
        
        embed.add_field(
            name="📊 Comparison",
            value=comparison_text,
            inline=False
        )
        
        # Add legend
        legend = (
            "**Legend:**\n"
            "✅ = Correct\n"
            "⬆️ = Target is higher\n"
            "⬇️ = Target is lower\n"
            "🟡 = Partial match (genres)\n"
            "❌ = Incorrect"
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
                    "🟡 Partial match (genres)\n"
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
