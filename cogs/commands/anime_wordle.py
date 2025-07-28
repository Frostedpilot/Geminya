import discord
import aiohttp
import random
import asyncio
from discord.ext import commands
from discord import app_commands
from typing import Dict, List, Optional, Any

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
        self.cover_image = self._extract_cover_image(data.get('coverImage', {}))
    
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
    
    def _extract_cover_image(self, cover_data: Dict) -> Optional[str]:
        """Extract cover image URL."""
        if not cover_data:
            return None
        return cover_data.get('large') or cover_data.get('medium')
    
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
        # Check if title contains only allowed characters (Latin alphabet, numbers, punctuation)
        # We exclude non-Latin scripts like Japanese, Chinese, Korean, Arabic, etc.
        try:
            # Allow ASCII letters, numbers, extended Latin characters, and common punctuation
            title.encode('ascii', errors='ignore').decode('ascii')
            # Also allow common extended characters used in anime titles
            forbidden_patterns = [
                r'[\u3040-\u309F]',  # Hiragana
                r'[\u30A0-\u30FF]',  # Katakana  
                r'[\u4E00-\u9FAF]',  # CJK Unified Ideographs
                r'[\u0400-\u04FF]',  # Cyrillic
                r'[\u0590-\u05FF]',  # Hebrew
                r'[\u0600-\u06FF]',  # Arabic
            ]
            
            for pattern in forbidden_patterns:
                if re.search(pattern, title):
                    return False
            
            return True
        except UnicodeError:
            return False


class AnimeWordle:
    """Game state for anime Wordle."""
    
    def __init__(self, target_anime: AnimeData, difficulty: str = "normal"):
        self.target = target_anime
        self.guesses: List[AnimeData] = []
        self.max_guesses = 21
        self.is_complete = False
        self.is_won = False
        self.hint_penalty = 0  # Track additional guess penalty from hints
        self.difficulty = difficulty  # Track game difficulty
    
    def add_guess(self, guess: AnimeData) -> bool:
        """Add a guess and check if game is complete."""
        self.guesses.append(guess)
        
        if guess.id == self.target.id:
            self.is_complete = True
            self.is_won = True
            return True
        
        # Check if total guesses (including hint penalty) exceed max
        total_guesses = len(self.guesses) + self.hint_penalty
        if total_guesses >= self.max_guesses:
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
        comparison['title'] = f"{guess.title} {'✅' if title_match else '❌'}"
        
        # Year comparison
        if guess.year == self.target.year:
            comparison['year'] = f"{guess.year} ✅"
        elif guess.year < self.target.year:
            comparison['year'] = f"{guess.year} ⬆️"
        else:
            comparison['year'] = f"{guess.year} ⬇️"
        
        # Score comparison
        if guess.score == self.target.score:
            comparison['score'] = f"{guess.score}/100 ✅"
        elif guess.score < self.target.score:
            comparison['score'] = f"{guess.score}/100 ⬆️"
        else:
            comparison['score'] = f"{guess.score}/100 ⬇️"
        
        # Episodes comparison
        if guess.episodes == self.target.episodes:
            comparison['episodes'] = f"{guess.episodes} ✅"
        elif guess.episodes < self.target.episodes:
            comparison['episodes'] = f"{guess.episodes} ⬆️"
        else:
            comparison['episodes'] = f"{guess.episodes} ⬇️"
        
        # Genres comparison - show individual matches
        guess_genres = set(guess.genres)
        target_genres = set(self.target.genres)
        if guess_genres == target_genres:
            comparison['genres'] = f"{', '.join(sorted(guess.genres))} ✅"
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
            comparison['studio'] = f"{', '.join(sorted(guess.studios))} ✅"
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
        comparison['source'] = f"{guess.source} {'✅' if guess.source == self.target.source else '❌'}"
        
        # Format comparison
        comparison['format'] = f"{guess.format} {'✅' if guess.format == self.target.format else '❌'}"
        
        return comparison


class AnimeWordleCog(BaseCommand):
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)
        self.games: Dict[int, AnimeWordle] = {}  # channel_id -> game
        self.anilist_url = "https://graphql.anilist.co"
        self.page_cache: Dict[str, int] = {}  # Cache for max page results
    
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
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.logger.error(f"Error querying AniList API: {e}")
            return None
    
    async def _find_max_page_binary_search(self, min_score: int, max_score: int, sort_method: str) -> int:
        """Find the maximum page number using binary search to locate the boundary between content and empty pages."""
        # Create cache key
        cache_key = f"{min_score}-{max_score}-{sort_method}"
        
        # Check if result is already cached
        if cache_key in self.page_cache:
            cached_result = self.page_cache[cache_key]
            self.logger.info(f"Using cached max page: {cached_result} for range {min_score}-{max_score}")
            return cached_result
        
        try:
            # Start with a reasonable upper bound for binary search
            left, right = 1, 1000
            max_page_found = 1
            
            # Binary search to find the last page with content
            while left <= right:
                mid = (left + right) // 2
                
                # Check if this page has content
                query = """
                query ($page: Int, $minScore: Int, $maxScore: Int, $sort: [MediaSort]) {
                    Page(page: $page, perPage: 50) {
                        media(type: ANIME, sort: $sort, episodes_greater: 0, averageScore_greater: $minScore, averageScore_lesser: $maxScore) {
                            id
                        }
                    }
                }
                """
                
                variables = {
                    'page': mid,
                    'minScore': min_score,
                    'maxScore': max_score,
                    'sort': [sort_method]
                }
                
                data = await self._query_anilist(query, variables)
                has_content = data and data.get('Page', {}).get('media') and len(data['Page']['media']) > 0
                
                if has_content:
                    max_page_found = mid
                    left = mid + 1  # Search for a higher page
                else:
                    right = mid - 1  # Search for a lower page
            
            # Cache the result
            self.page_cache[cache_key] = max_page_found
            self.logger.info(f"Binary search found and cached max page: {max_page_found} for range {min_score}-{max_score}")
            return max_page_found
            
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.logger.error(f"Error in binary search for max page: {e}")
            return 1  # Fallback to page 1

    def _get_difficulty_weights(self, difficulty: str) -> Dict[str, int]:
        """Get score weights based on difficulty level from config."""
        try:
            # Get config settings - now access anime_wordle directly as a dict
            anime_config = self.services.config.anime_wordle
            difficulty_weights = anime_config.get('difficulty_weights', {})
            
            # Get difficulty-specific weights from config
            if isinstance(difficulty_weights, dict) and difficulty in difficulty_weights:
                weights = difficulty_weights[difficulty]
                self.logger.info(f"Successfully loaded {difficulty} difficulty weights: {len(weights)} score ranges")
                return weights
            
            # Fallback to legacy score_weights if difficulty not found
            self.logger.warning(f"Difficulty '{difficulty}' not found in config, falling back to legacy weights")
            legacy_weights = anime_config.get('score_weights', {
                '80-100': 15, '60-79': 15, '50-59': 2, '40-49': 1, '0-39': 1
            })
            return legacy_weights
            
        except (AttributeError, KeyError, TypeError) as e:
            self.logger.error(f"Error reading difficulty weights from config: {e}")
            # Hard fallback to updated default normal weights to match your config style
            fallback_weights = {
                '80-100': 15, '60-79': 15, '50-59': 2, '40-49': 1, '0-39': 1
            }
            self.logger.info(f"Using hard fallback weights: {len(fallback_weights)} score ranges")
            return fallback_weights

    async def _get_random_anime(self, difficulty: str = "normal") -> Optional[AnimeData]:
        """Get a random anime for the game using weighted selection based on score ranges and difficulty."""
        try:
            # Get config settings - now access anime_wordle directly as a dict
            anime_config = self.services.config.anime_wordle
            
            # Use difficulty-specific weights instead of config weights
            score_weights = self._get_difficulty_weights(difficulty)
            sort_method = anime_config.get('sort_method', 'POPULARITY_DESC')
            
            # Create weighted list of score ranges
            weighted_ranges = []
            for score_range, weight in score_weights.items():
                min_score, max_score = map(int, score_range.split('-'))
                weighted_ranges.extend([(min_score, max_score)] * weight)
            
            # Randomly select a score range based on weights
            selected_range = random.choice(weighted_ranges)
            min_score, max_score = selected_range
            
            # Find the true maximum page using binary search
            max_pages = await self._find_max_page_binary_search(min_score, max_score, sort_method)
            if max_pages == 1:
                # If only 1 page found, try a broader range
                self.logger.warning(f"Only 1 page found in score range {min_score}-{max_score}, expanding range")
                min_score = max(0, min_score - 20)
                max_score = min(100, max_score + 20)
                max_pages = await self._find_max_page_binary_search(min_score, max_score, sort_method)
            
            self.logger.info(f"Selected score range: {min_score}-{max_score}, True max pages: {max_pages}")
            
            # Query anime within the selected score range with configurable sorting
            query = """
            query ($page: Int, $minScore: Int, $maxScore: Int, $sort: [MediaSort]) {
                Page(page: $page, perPage: 50) {
                    media(type: ANIME, sort: $sort, episodes_greater: 0, averageScore_greater: $minScore, averageScore_lesser: $maxScore) {
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
                        coverImage {
                            large
                            medium
                        }
                    }
                }
            }
            """
            
            # Try once with a random page within the true range
            random_page = random.randint(1, max_pages)
            variables = {
                'page': random_page,
                'minScore': min_score,
                'maxScore': max_score,
                'sort': [sort_method]
            }
            
            data = await self._query_anilist(query, variables)
            if data and data.get('Page', {}).get('media'):
                anime_list = data['Page']['media']
                if anime_list:
                    # Randomly select one anime from the page
                    selected_anime = random.choice(anime_list)
                    self.logger.info(f"Selected anime: {selected_anime.get('title', {}).get('english', 'Unknown')} (Score: {selected_anime.get('averageScore', 'N/A')})")
                    return AnimeData(selected_anime)
            
            # If no results on the selected page, fall back to page 1
            self.logger.warning(f"No anime found on page {random_page}, trying page 1")
            variables['page'] = 1
            data = await self._query_anilist(query, variables)
            if data and data.get('Page', {}).get('media'):
                anime_list = data['Page']['media']
                if anime_list:
                    selected_anime = random.choice(anime_list)
                    self.logger.info(f"Fallback selected anime: {selected_anime.get('title', {}).get('english', 'Unknown')} (Score: {selected_anime.get('averageScore', 'N/A')})")
                    return AnimeData(selected_anime)
            
            # Final fallback - get any popular anime with configurable sorting
            self.logger.warning("Falling back to general popular anime selection")
            fallback_query = """
            query ($page: Int, $sort: [MediaSort]) {
                Page(page: $page, perPage: 1) {
                    media(type: ANIME, sort: $sort, episodes_greater: 0) {
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
                        coverImage {
                            large
                            medium
                        }
                    }
                }
            }
            """
            
            random_page = random.randint(1, 100)  # Use smaller range for fallback
            data = await self._query_anilist(fallback_query, {
                'page': random_page,
                'sort': [sort_method]
            })
            if data and data.get('Page', {}).get('media'):
                return AnimeData(data['Page']['media'][0])
            
            return None
            
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.logger.error(f"Error in weighted anime selection: {e}")
            return None
    
    async def _search_anime(self, search_term: str) -> Optional[AnimeData]:
        """Search for an anime by name."""
        query = """
        query ($search: String) {
            Media(search: $search, type: ANIME) {
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
                coverImage {
                    large
                    medium
                }
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
                media(search: $search, type: ANIME) {
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
        # interaction parameter is required by Discord.py but not used
        del interaction  # Suppress unused argument warning
        try:
            choices_data = await self._search_multiple_anime(current, limit=20)
            return [
                app_commands.Choice(name=choice['name'], value=choice['value'])
                for choice in choices_data
            ]
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.logger.error(f"Error in anime autocomplete: {e}")
            return []
    
    def _create_guess_embed(self, game: AnimeWordle, guess: AnimeData, comparison: Dict[str, str]) -> discord.Embed:
        """Create an embed showing the guess results."""
        total_guesses = len(game.guesses) + game.hint_penalty
        
        # Get difficulty emoji
        difficulty_emojis = {
            "easy": "🟢",
            "normal": "🟡", 
            "hard": "🟠",
            "expert": "🔴"
        }
        difficulty_emoji = difficulty_emojis.get(game.difficulty, "🟡")
        
        embed = discord.Embed(
            title=f"Anime Wordle {difficulty_emoji} - Guess {total_guesses}/{game.max_guesses}",
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
            f"**Year:** {comparison['year']}\n"
            f"**Score:** {comparison['score']}\n"
            f"**Episodes:** {comparison['episodes']}\n"
            f"**Source:** {comparison['source']}\n"
            f"**Format:** {comparison['format']}"
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
        
        # # Add legend
        # legend = (
        #     "**Legend:**\n"
        #     "✅ = Correct/Match\n"
        #     "⬆️ = Target is higher\n"
        #     "⬇️ = Target is lower\n"
        #     "❌ = Incorrect/No match"
        # )
        # embed.add_field(name="ℹ️ Legend", value=legend, inline=False)
        
        return embed
    
    def _create_game_over_embed(self, game: AnimeWordle) -> discord.Embed:
        """Create an embed for game completion."""
        total_guesses = len(game.guesses) + game.hint_penalty
        
        # Get difficulty descriptions
        difficulty_descriptions = {
            "easy": "🟢 Easy",
            "normal": "🟡 Normal", 
            "hard": "🟠 Hard",
            "expert": "🔴 Expert"
        }
        difficulty_text = difficulty_descriptions.get(game.difficulty, "🟡 Normal")
        
        if game.is_won:
            embed = discord.Embed(
                title="🎉 Congratulations!",
                description=f"You guessed it in {total_guesses} tries!\n**Difficulty:** {difficulty_text}",
                color=0x00FF00
            )
        else:
            embed = discord.Embed(
                title="💀 Game Over!",
                description=f"Better luck next time!\n**Difficulty:** {difficulty_text}",
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
        guess="Anime name to guess (only for 'guess' action)",
        difficulty="Choose difficulty level (only for 'start' action)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Start New Game", value="start"),
        app_commands.Choice(name="Make a Guess", value="guess"),
        app_commands.Choice(name="Get Hint", value="hint"),
        app_commands.Choice(name="Game Status", value="status"),
        app_commands.Choice(name="Give Up", value="giveup")
    ])
    @app_commands.choices(difficulty=[
        app_commands.Choice(name="Easy - Popular & Well-known Anime", value="easy"),
        app_commands.Choice(name="Normal - Mixed Selection", value="normal"),
        app_commands.Choice(name="Hard - Obscure & Lesser-known", value="hard"),
        app_commands.Choice(name="Expert - Ultra Obscure & Hidden Gems", value="expert")
    ])
    @app_commands.autocomplete(guess=anime_autocomplete)
    async def animewordle(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        guess: Optional[str] = None,
        difficulty: Optional[app_commands.Choice[str]] = None
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
            difficulty_value = difficulty.value if difficulty else "normal"
            await self._start_game(interaction, channel_id, difficulty_value)
        elif action.value == "guess":
            await self._make_guess(interaction, channel_id, guess or "")
        elif action.value == "hint":
            await self._give_hint(interaction, channel_id)
        elif action.value == "status":
            await self._show_status(interaction, channel_id)
        elif action.value == "giveup":
            await self._give_up(interaction, channel_id)
    
    async def _start_game(self, interaction: discord.Interaction, channel_id: int, difficulty: str = "normal"):
        """Start a new anime wordle game with specified difficulty."""
        # Check if there's already an active game in this channel
        if channel_id in self.games:
            existing_game = self.games[channel_id]
            if not existing_game.is_complete:
                await interaction.response.send_message(
                    "❌ There's already an active game in this channel! Finish the current game or use `/animewordle giveup` to end it.",
                    ephemeral=True
                )
                return
            else:
                # Clean up completed game before starting new one
                del self.games[channel_id]
        
        await interaction.response.defer(thinking=True)
        
        try:
            target_anime = await self._get_random_anime(difficulty)
            if not target_anime:
                await interaction.followup.send(
                    "❌ Failed to fetch anime data. Please try again later!",
                    ephemeral=True
                )
                return
            
            self.games[channel_id] = AnimeWordle(target_anime, difficulty)
            
            # Get difficulty description
            difficulty_descriptions = {
                "easy": "🟢 **Easy** - Popular & Well-known Anime",
                "normal": "🟡 **Normal** - Mixed Selection", 
                "hard": "🟠 **Hard** - Obscure & Lesser-known",
                "expert": "🔴 **Expert** - Ultra Obscure & Hidden Gems"
            }
            
            embed = discord.Embed(
                title="🎮 Anime Wordle Started!",
                description=(
                    f"Guess the anime! You have 21 tries.\n"
                    f"**Difficulty:** {difficulty_descriptions.get(difficulty, '🟡 **Normal**')}\n\n"
                    f"Use `/animewordle guess <anime_name>` to make a guess.\n\n"
                    f"**Properties to match:**\n"
                    f"• Title, Year, Score, Episodes\n"
                    f"• Genres, Studio, Source, Format"
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
            
            # Add difficulty explanation
            difficulty_explanations = {
                "easy": "Focuses on mainstream, popular anime that most people have heard of.",
                "normal": "Balanced mix of popular and lesser-known anime.",
                "hard": "Emphasizes obscure, underrated, or niche anime series.",
                "expert": "Ultra challenging with the most obscure and unknown anime."
            }
            
            embed.add_field(
                name="🎯 Difficulty Info",
                value=f"{difficulty_explanations.get(difficulty, 'Balanced mix of popular and lesser-known anime.')}\n*Weights are configurable in config.yml*",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            self.logger.info(f"Started anime wordle game in channel {channel_id} with target: {target_anime.title} (Difficulty: {difficulty})")
            
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            self.logger.error(f"Error starting anime wordle game: {e}")
            await interaction.followup.send(
                "❌ An error occurred while starting the game. Please try again!",
                ephemeral=True
            )
    
    async def _make_guess(self, interaction: discord.Interaction, channel_id: int, guess: str):
        """Make a guess in the anime wordle game."""
        # Check if there's an active game
        if channel_id not in self.games:
            await interaction.response.send_message(
                "❌ No active game in this channel! Use `/animewordle start` to begin a new game.",
                ephemeral=True
            )
            return
        
        game = self.games[channel_id]
        
        # Check if game is already completed
        if game.is_complete:
            await interaction.response.send_message(
                "❌ This game is already completed! Start a new game with `/animewordle start`.",
                ephemeral=True
            )
            return
        
        # Validate guess input
        if not guess or not guess.strip():
            await interaction.response.send_message(
                "❌ Please provide an anime name to guess! Use the autocomplete feature to help find the correct title.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(thinking=True)
        
        try:
            anime_data = await self._search_anime(guess.strip())
            if not anime_data:
                await interaction.followup.send(
                    f"❌ Couldn't find anime: '{guess}'. Please check the spelling and try again, or use the autocomplete feature for suggestions!",
                    ephemeral=True
                )
                return
            
            # Check if this anime has already been guessed
            for previous_guess in game.guesses:
                if previous_guess.id == anime_data.id:
                    await interaction.followup.send(
                        f"❌ You've already guessed '{anime_data.title}'! Try a different anime.",
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
        """Display the anime poster image and add 10 guess penalty."""
        # Check if there's an active game
        if channel_id not in self.games:
            await interaction.response.send_message(
                "❌ No active game in this channel! Use `/animewordle start` to begin a new game.",
                ephemeral=False
            )
            return
        
        game = self.games[channel_id]
        
        # Check if game is already completed
        if game.is_complete:
            await interaction.response.send_message(
                "❌ This game is already completed! Start a new game with `/animewordle start`.",
                ephemeral=False
            )
            return
        
        # Check if adding 10 to total guesses would exceed max_guesses (21)
        total_guesses = len(game.guesses) + game.hint_penalty
        if total_guesses + 10 > game.max_guesses:
            await interaction.response.send_message(
                f"❌ Cannot use hint! Adding 10 guesses would exceed the maximum limit of {game.max_guesses} guesses. Current total: {total_guesses}/{game.max_guesses}",
                ephemeral=False
            )
            return
        
        # Check if there are any guesses made yet (optional: you might want hints only after some attempts)
        if len(game.guesses) == 0:
            await interaction.response.send_message(
                "💡 **Hint available!** But consider making at least one guess first to get a feel for the game. Using a hint adds +10 to your guess count!",
                ephemeral=False
            )
            return
        
        # Add 10 guess penalty
        game.hint_penalty += 10
        total_guesses = len(game.guesses) + game.hint_penalty
        
        embed = discord.Embed(
            title="� Poster Hint!",
            description=f"Here's the poster for the anime you're looking for!\n**Penalty**: +10 guesses (Total: {total_guesses}/{game.max_guesses})",
            color=0xFFD700
        )
        
        # Add poster image if available
        if game.target.cover_image:
            embed.set_image(url=game.target.cover_image)
        else:
            embed.add_field(
                name="⚠️ No Image Available",
                value="Poster image is not available for this anime.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=False)
    
    async def _give_up(self, interaction: discord.Interaction, channel_id: int):
        """Give up the current game."""
        # Check if there's an active game
        if channel_id not in self.games:
            await interaction.response.send_message(
                "❌ No active game in this channel! Use `/animewordle start` to begin a new game.",
                ephemeral=True
            )
            return
        
        game = self.games[channel_id]
        
        # Check if game is already completed
        if game.is_complete:
            await interaction.response.send_message(
                "❌ This game is already completed! The results were already shown.",
                ephemeral=True
            )
            return
        
        # Check if any guesses have been made
        if len(game.guesses) == 0:
            await interaction.response.send_message(
                "❓ Are you sure you want to give up without making any guesses? Try at least one guess first!",
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
        
        self.logger.info(f"User gave up anime wordle game in channel {channel_id} after {len(game.guesses)} guesses")
    
    async def _show_status(self, interaction: discord.Interaction, channel_id: int):
        """Show the current game status."""
        # Check if there's an active game
        if channel_id not in self.games:
            await interaction.response.send_message(
                "❌ No active game in this channel! Use `/animewordle start` to begin a new game.",
                ephemeral=True
            )
            return
        
        game = self.games[channel_id]
        
        # Check if game is already completed
        if game.is_complete:
            await interaction.response.send_message(
                "❌ This game is already completed! The results were already shown. Use `/animewordle start` to begin a new game.",
                ephemeral=True
            )
            return
        
        total_guesses = len(game.guesses) + game.hint_penalty
        remaining_guesses = game.max_guesses - total_guesses
        
        # Get difficulty description
        difficulty_descriptions = {
            "easy": "🟢 Easy - Popular & Well-known",
            "normal": "🟡 Normal - Mixed Selection", 
            "hard": "🟠 Hard - Obscure & Lesser-known",
            "expert": "🔴 Expert - Ultra Obscure & Hidden Gems"
        }
        
        embed = discord.Embed(
            title="📊 Game Status",
            color=0x02A9FF
        )
        
        embed.add_field(
            name="🎯 Progress",
            value=(
                f"**Difficulty:** {difficulty_descriptions.get(game.difficulty, '🟡 Normal')}\n"
                f"**Guesses Made:** {len(game.guesses)}\n"
                f"**Hint Penalty:** +{game.hint_penalty}\n"
                f"**Total Used:** {total_guesses}/{game.max_guesses}\n"
                f"**Remaining:** {remaining_guesses}"
            ),
            inline=False
        )
        
        if len(game.guesses) > 0:
            recent_guesses = game.guesses[-3:]  # Show last 3 guesses
            guess_list = []
            for i, guess in enumerate(recent_guesses):
                guess_number = len(game.guesses) - len(recent_guesses) + i + 1
                guess_list.append(f"{guess_number}. {guess.title}")
            
            embed.add_field(
                name="🕰️ Recent Guesses",
                value="\n".join(guess_list),
                inline=False
            )
        
        embed.add_field(
            name="ℹ️ Available Actions",
            value=(
                "• `/animewordle guess <anime>` - Make a guess\n"
                "• `/animewordle hint` - Get poster hint (+10 penalty)\n"
                "• `/animewordle giveup` - End the game"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Setup function for cog loading."""
    # Get services from bot instance
    services = getattr(bot, 'services', None)
    if services:
        await bot.add_cog(AnimeWordleCog(bot, services))
    else:
        # Fallback if services not available
        raise RuntimeError("Bot services not available")
