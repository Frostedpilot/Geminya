#!/usr/bin/env python3
"""Script to populate waifu database from MAL user's watching/reading list with female characters only."""

import asyncio
import aiohttp
import json
import sys
import os
import re
from typing import List, Dict, Any, Set, Optional
import logging

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.mal_api import MALAPIService
from services.database import DatabaseService
from services.waifu_service import WaifuService
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


class MALWaifuPopulator:
    """Service to populate waifu database from MAL user lists."""

    def __init__(self, config: Config):
        self.config = config
        self.mal_service = None
        self.db_service = None
        self.waifu_service = None

        # Female detection keywords (Japanese and English)
        self.female_indicators = {
            "female",
            "girl",
            "woman",
            "lady",
            "princess",
            "queen",
            "goddess",
            "witch",
            "maiden",
            "daughter",
            "sister",
            "mother",
            "grandmother",
            "aunt",
            "niece",
            "wife",
            "girlfriend",
            "女",
            "女性",
            "女の子",
            "少女",
            "姫",
            "女王",
            "魔女",
            "乙女",
            "ojou",
            "chan",
            "san",
        }

        # Male detection keywords to exclude
        self.male_indicators = {
            "male",
            "man",
            "boy",
            "guy",
            "king",
            "prince",
            "lord",
            "master",
            "father",
            "brother",
            "son",
            "grandfather",
            "uncle",
            "nephew",
            "husband",
            "boyfriend",
            "男",
            "男性",
            "男の子",
            "少年",
            "王",
            "王子",
            "父",
            "兄",
            "kun",
            "sama",
        }

        # Pronoun indicators for gender detection
        self.female_pronouns = {"she", "her", "hers", "herself"}
        self.male_pronouns = {"he", "him", "his", "himself"}

    async def __aenter__(self):
        """Async context manager entry."""
        self.mal_service = MALAPIService(
            self.config.mal_client_id, self.config.mal_client_secret
        )
        await self.mal_service.__aenter__()

        self.db_service = DatabaseService(self.config)
        await self.db_service.initialize()

        self.waifu_service = WaifuService(self.db_service)
        await self.waifu_service.initialize()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.waifu_service:
            await self.waifu_service.close()
        if self.db_service:
            await self.db_service.close()
        if self.mal_service:
            await self.mal_service.__aexit__(exc_type, exc_val, exc_tb)

    def setup_oauth_flow(self, redirect_uri: str = "http://localhost:8080/callback"):
        """Setup OAuth flow for MAL authentication."""
        auth_url, code_verifier = self.mal_service.generate_auth_url(redirect_uri)

        print(f"🔐 MAL OAuth Setup Required")
        print(f"1. Open this URL in your browser:")
        print(f"   {auth_url}")
        print(f"2. Authorize the application")
        print(f"3. Copy the authorization code from the callback URL")
        print(f"4. Enter the code below:")

        auth_code = input("Enter authorization code: ").strip()
        return auth_code, code_verifier, redirect_uri

    async def authenticate_mal(self):
        """Complete MAL OAuth authentication."""
        try:
            auth_code, code_verifier, redirect_uri = self.setup_oauth_flow()

            logger.info("Exchanging authorization code for tokens...")
            tokens = await self.mal_service.exchange_code_for_tokens(
                auth_code, redirect_uri, code_verifier
            )

            logger.info("✅ MAL authentication successful!")
            return True

        except Exception as e:
            logger.error(f"❌ MAL authentication failed: {e}")
            return False

    def has_substantial_description(self, character: Dict[str, Any]) -> bool:
        """Check if character has a substantial description (important characters only)."""
        about = character.get("about", "")
        logger.info(
            f"Checking description for {character.get('name', 'Unknown')}: {about}"
        )
        if not about:
            return False

        # Remove common filler words for accurate word count
        filler_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        words = [word.lower().strip(".,!?;:()[]{}\"'") for word in about.split()]
        meaningful_words = [
            word for word in words if word not in filler_words and len(word) > 2
        ]

        # Character must have substantial description
        return len(about) > 30 and len(meaningful_words) > 5

    def determine_character_rarity(self, character: Dict[str, Any], is_most_popular: bool = False) -> int:
        """Determine character rarity based on popularity following guess_character config logic."""
        # Special rule: Most popular character in each anime/manga gets 5-star
        if is_most_popular:
            return 5
            
        favorites = character.get("favorites", 0)

        # Map popularity to difficulty ranges from config.yml
        # easy=5 star, normal=4 star, hard=3 star, expert=2 star, crazy and insanity=1 star

        if favorites >= 0 and favorites <= 250:
            return 1  # easy - 5 star
        elif favorites >= 251 and favorites <= 900:
            return 2  # normal - 4 star
        elif favorites >= 901 and favorites <= 2000:
            return 3  # hard - 3 star
        elif favorites >= 2001 and favorites <= 4000:
            return 4  # expert - 2 star
        else:
            return 5  # crazy/insanity - 1 star

    def is_female_character(self, character: Dict[str, Any]) -> bool:
        """Determine if a character is female based on available information."""
        name = character.get("name", "").lower()
        about = character.get("about", "").lower() if character.get("about") else ""

        # Count pronouns in the about text for gender detection (using word boundaries)
        import re

        female_pronoun_count = 0
        male_pronoun_count = 0

        for pronoun in self.female_pronouns:
            # Use word boundaries to avoid substring matches
            pattern = r"\b" + re.escape(pronoun) + r"\b"
            female_pronoun_count += len(re.findall(pattern, about, re.IGNORECASE))

        for pronoun in self.male_pronouns:
            # Use word boundaries to avoid substring matches
            pattern = r"\b" + re.escape(pronoun) + r"\b"
            male_pronoun_count += len(re.findall(pattern, about, re.IGNORECASE))
        print(female_pronoun_count, male_pronoun_count)

        # Strong indicator: if there are significantly more female pronouns
        if female_pronoun_count > 0 and female_pronoun_count > male_pronoun_count:
            logger.debug(
                f"Female pronouns detected for {character.get('name', 'Unknown')}: {female_pronoun_count} vs {male_pronoun_count}"
            )
            return True

        # Strong indicator: if there are significantly more male pronouns, exclude
        if male_pronoun_count > 0 and male_pronoun_count > female_pronoun_count:
            logger.debug(
                f"Male pronouns detected for {character.get('name', 'Unknown')}: {male_pronoun_count} vs {female_pronoun_count}"
            )
            return False

        # Check for explicit male indicators first (more reliable to exclude)
        if any(indicator in about for indicator in self.male_indicators):
            logger.debug(
                f"Male indicators detected for {character.get('name', 'Unknown')}"
            )
            return False

        # Check for explicit female indicators
        if any(indicator in about for indicator in self.female_indicators):
            logger.debug(
                f"Female indicators detected for {character.get('name', 'Unknown')}"
            )
            return True

        # Check character name patterns (common female name endings in Japanese)
        female_name_patterns = [
            "ko",
            "mi",
            "ki",
            "ri",
            "na",
            "ka",
            "sa",
            "ra",
            "ya",
            "to",
            "chi",
        ]
        name_parts = name.split()

        if name_parts:
            first_name = name_parts[0] if "," not in name else name_parts[-1]
            if any(first_name.endswith(pattern) for pattern in female_name_patterns):
                logger.debug(
                    f"Female name pattern detected for {character.get('name', 'Unknown')}"
                )
                return True

        # For anime characters, default to including if uncertain since most characters
        # in waifu contexts tend to be female, and manual review can filter later
        logger.info(
            f"Gender uncertain for {character.get('name', 'Unknown')} - defaulting to female for anime character"
        )
        return True

    def extract_birthday(self, about: str) -> Optional[str]:
        """Extract birthday from character description."""
        if not about:
            return None

        # Pattern to match "Birthday: Month Day" or "Birthday: Month Day, Year"
        birthday_pattern = r"Birthday:\s*([A-Za-z]+)\s*(\d{1,2})(?:,?\s*(\d{4}))?"
        match = re.search(birthday_pattern, about, re.IGNORECASE)

        if match:
            month = match.group(1)
            day = match.group(2)
            year = match.group(3)

            # Format as YYYY-MM-DD or just MM-DD if no year
            month_map = {
                "january": "01",
                "february": "02",
                "march": "03",
                "april": "04",
                "may": "05",
                "june": "06",
                "july": "07",
                "august": "08",
                "september": "09",
                "october": "10",
                "november": "11",
                "december": "12",
                "jan": "01",
                "feb": "02",
                "mar": "03",
                "apr": "04",
                "jun": "06",
                "jul": "07",
                "aug": "08",
                "sep": "09",
                "oct": "10",
                "nov": "11",
                "dec": "12",
            }

            month_num = month_map.get(month.lower())
            if month_num:
                day_formatted = day.zfill(2)
                if year:
                    return f"{year}-{month_num}-{day_formatted}"
                else:
                    return f"{month_num}-{day_formatted}"

        return None

    def determine_element(self, character: Dict[str, Any]) -> str:
        """Determine character element based on traits and series."""
        about = character.get("about", "").lower()
        series = character.get("series", "").lower()
        name = character.get("name", "").lower()

        # Element keywords mapping
        element_keywords = {
            "fire": [
                "fire",
                "flame",
                "burn",
                "heat",
                "phoenix",
                "dragon",
                "volcano",
                "lava",
            ],
            "water": [
                "water",
                "ocean",
                "sea",
                "ice",
                "snow",
                "frost",
                "mermaid",
                "aqua",
            ],
            "earth": [
                "earth",
                "ground",
                "stone",
                "rock",
                "mountain",
                "nature",
                "plant",
                "forest",
            ],
            "air": ["wind", "air", "sky", "cloud", "feather", "bird", "angel", "wings"],
            "lightning": ["lightning", "thunder", "electric", "storm", "spark", "bolt"],
            "light": ["light", "holy", "divine", "angel", "pure", "white", "sacred"],
            "dark": ["dark", "shadow", "demon", "evil", "black", "night", "death"],
            "psychic": ["psychic", "mind", "telekinesis", "mental", "psi", "telepathy"],
        }

        text_to_check = f"{about} {series} {name}"

        for element, keywords in element_keywords.items():
            if any(keyword in text_to_check for keyword in keywords):
                return element.title()

        return "Neutral"

    def generate_base_stats(self, character: Dict[str, Any]) -> Dict[str, int]:
        """Generate base stats for character based on rarity and traits."""
        is_most_popular = character.get("is_most_popular_in_series", False)
        rarity = self.determine_character_rarity(character, is_most_popular)

        # Base stats scale with rarity
        base_multiplier = rarity * 20

        # Random variation based on character name hash for consistency
        import hashlib

        name_hash = int(
            hashlib.md5(character.get("name", "").encode()).hexdigest()[:8], 16
        )

        stats = {
            "strength": base_multiplier + (name_hash % 21) - 10,  # ±10 variation
            "intelligence": base_multiplier + ((name_hash >> 8) % 21) - 10,
            "agility": base_multiplier + ((name_hash >> 16) % 21) - 10,
            "luck": base_multiplier + ((name_hash >> 24) % 21) - 10,
        }

        # Ensure minimum values
        for stat in stats:
            stats[stat] = max(stats[stat], 10)

        return stats

    def generate_favorite_gifts(self, character: Dict[str, Any]) -> List[str]:
        """Generate favorite gifts based on character traits."""
        about = character.get("about", "").lower()
        name = character.get("name", "").lower()

        # Default gift categories
        all_gifts = {
            "sweet": ["Chocolate", "Cake", "Ice Cream", "Candy", "Cookies"],
            "flower": ["Roses", "Sakura Petals", "Sunflower", "Lily", "Tulips"],
            "book": ["Novel", "Manga", "Poetry Book", "Art Book", "Encyclopedia"],
            "accessory": ["Hair Ribbon", "Necklace", "Bracelet", "Ring", "Earrings"],
            "food": ["Bento", "Tea", "Coffee", "Fruit", "Pastry"],
            "toy": ["Plushie", "Figurine", "Music Box", "Puzzle", "Game"],
        }

        favorite_gifts = []

        # Determine preferences based on character description
        if any(word in about for word in ["sweet", "candy", "cake", "dessert"]):
            favorite_gifts.extend(all_gifts["sweet"][:2])
        if any(word in about for word in ["flower", "garden", "nature", "plant"]):
            favorite_gifts.extend(all_gifts["flower"][:2])
        if any(
            word in about for word in ["book", "read", "study", "smart", "intelligent"]
        ):
            favorite_gifts.extend(all_gifts["book"][:2])
        if any(word in about for word in ["cute", "pretty", "beautiful", "fashion"]):
            favorite_gifts.extend(all_gifts["accessory"][:2])

        # If no specific preferences found, add some defaults
        if not favorite_gifts:
            favorite_gifts = ["Chocolate", "Roses", "Hair Ribbon"]

        # Limit to 3-5 gifts
        return favorite_gifts[:5]

    async def get_character_details(self, character_id: int) -> Dict[str, Any]:
        """Get detailed character information from Jikan API."""
        try:
            await asyncio.sleep(1.5)  # Rate limiting

            url = f"https://api.jikan.moe/v4/characters/{character_id}"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        character = data.get("data", {})

                        res = {
                            "mal_id": character.get("mal_id"),
                            "name": character.get("name", "Unknown"),
                            "name_kanji": character.get("name_kanji", ""),
                            "nicknames": character.get("nicknames", []),
                            "about": character.get("about", ""),
                            "image_url": character.get("images", {})
                            .get("jpg", {})
                            .get("image_url", ""),
                            "favorites": character.get("favorites", 0),
                        }
                    else:
                        logger.warning(
                            f"Failed to get character details for {character_id}: {response.status}"
                        )
                        res = None

                if res:
                    logger.info(
                        f"Retrieved details for character {character_id}: {res['name']}"
                    )
                return res

        except Exception as e:
            logger.error(f"Error getting character details for {character_id}: {e}")
            return None

    async def get_anime_characters(self, anime_id: int) -> List[Dict[str, Any]]:
        """Get characters from an anime using Jikan API."""
        try:
            # await asyncio.sleep(1.5)  # Rate limiting

            url = f"https://api.jikan.moe/v4/anime/{anime_id}/characters"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        characters = []

                        for char_data in data.get("data", []):
                            character = char_data.get("character", {})
                            character_id = character.get("mal_id")

                            logger.info(
                                f"Processing character {character_id} from anime {anime_id}: {character.get('name', 'Unknown')}"
                            )

                            if character_id:
                                # Get detailed character information
                                character_details = await self.get_character_details(
                                    character_id
                                )

                                logger.info(
                                    f"Character details for {character_id}: {character_details is not None}"
                                )

                                if character_details:
                                    logger.info(
                                        f"Starting filters for {character_details.get('name', 'Unknown')}"
                                    )

                                    is_female = self.is_female_character(
                                        character_details
                                    )
                                    logger.info(
                                        f"Female check result for {character_details.get('name', 'Unknown')}: {is_female}"
                                    )

                                    has_description = self.has_substantial_description(
                                        character_details
                                    )
                                    logger.info(
                                        f"Description check result for {character_details.get('name', 'Unknown')}: {has_description}"
                                    )

                                    if is_female and has_description:
                                        logger.info(
                                            f"Character {character_id} passed all filters and will be included."
                                        )
                                        characters.append(character_details)
                                    else:
                                        logger.info(
                                            f"Character {character_id} failed filters - Female: {is_female}, Description: {has_description}"
                                        )
                                else:
                                    logger.warning(
                                        f"No character details retrieved for {character_id}"
                                    )

                        # Find the most popular character and mark them
                        if characters:
                            most_popular = max(characters, key=lambda x: x.get("favorites", 0))
                            most_popular["is_most_popular_in_series"] = True
                            logger.info(f"Most popular character in anime {anime_id}: {most_popular.get('name')} with {most_popular.get('favorites', 0)} favorites")

                        return characters
                    else:
                        logger.warning(
                            f"Failed to get characters for anime {anime_id}: {response.status}"
                        )
                        return []

        except Exception as e:
            logger.error(f"Error getting characters for anime {anime_id}: {e}")
            return []

    async def get_manga_characters(self, manga_id: int) -> List[Dict[str, Any]]:
        """Get characters from a manga using Jikan API."""
        try:
            await asyncio.sleep(1.5)  # Rate limiting

            url = f"https://api.jikan.moe/v4/manga/{manga_id}/characters"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        characters = []

                        for char_data in data.get("data", []):
                            character = char_data.get("character", {})
                            character_id = character.get("mal_id")

                            if character_id:
                                # Get detailed character information
                                character_details = await self.get_character_details(
                                    character_id
                                )

                                if character_details:
                                    # Only include female characters with substantial descriptions
                                    if self.is_female_character(
                                        character_details
                                    ) and self.has_substantial_description(
                                        character_details
                                    ):
                                        characters.append(character_details)

                        # Find the most popular character and mark them
                        if characters:
                            most_popular = max(characters, key=lambda x: x.get("favorites", 0))
                            most_popular["is_most_popular_in_series"] = True
                            logger.info(f"Most popular character in manga {manga_id}: {most_popular.get('name')} with {most_popular.get('favorites', 0)} favorites")

                        return characters
                    else:
                        logger.warning(
                            f"Failed to get characters for manga {manga_id}: {response.status}"
                        )
                        return []

        except Exception as e:
            logger.error(f"Error getting characters for manga {manga_id}: {e}")
            return []

    async def populate_from_mal_user(self):
        """Main function to populate database from MAL user's lists."""
        try:
            logger.info("🎌 Starting MAL user list population...")

            # Authenticate with MAL
            if not await self.authenticate_mal():
                return False

            # Get user's anime and manga lists
            logger.info("📺 Fetching user's anime list...")
            anime_list = await self.mal_service.get_user_anime_list()

            logger.info("📚 Fetching user's manga list...")
            manga_list = await self.mal_service.get_user_manga_list()

            logger.info(
                f"Found {len(anime_list)} anime and {len(manga_list)} manga in user's lists"
            )

            # Collect all female characters
            all_characters = []
            processed_char_ids = set()

            # Process anime
            for i, anime in enumerate(anime_list, 1):
                anime_id = anime["id"]
                title = anime["title"]

                logger.info(f"Processing anime {i}/{len(anime_list)}: {title}")
                characters = await self.get_anime_characters(anime_id)

                for char in characters:
                    char_id = char["mal_id"]
                    if char_id not in processed_char_ids:
                        char["series"] = title
                        char["series_type"] = "anime"
                        all_characters.append(char)
                        processed_char_ids.add(char_id)

                logger.info(f"  Found {len(characters)} important female characters")

            # Process manga
            for i, manga in enumerate(manga_list, 1):
                manga_id = manga["id"]
                title = manga["title"]

                logger.info(f"Processing manga {i}/{len(manga_list)}: {title}")
                characters = await self.get_manga_characters(manga_id)

                for char in characters:
                    char_id = char["mal_id"]
                    if char_id not in processed_char_ids:
                        char["series"] = title
                        char["series_type"] = "manga"
                        all_characters.append(char)
                        processed_char_ids.add(char_id)

                logger.info(f"  Found {len(characters)} important female characters")

            # Add characters to database
            logger.info(
                f"💾 Adding {len(all_characters)} female characters to database..."
            )

            for char in all_characters:
                try:
                    # Check if this character is the most popular in their series
                    is_most_popular = char.get("is_most_popular_in_series", False)
                    
                    # Determine rarity based on character popularity from config logic
                    rarity = self.determine_character_rarity(char, is_most_popular)
                    
                    if is_most_popular:
                        logger.info(f"⭐⭐⭐⭐⭐ {char.get('name')} from {char.get('series')} upgraded to 5-star (most popular in series)")

                    # Use the filtered about text as personality profile
                    personality_profile = char.get("about", "")
                    if len(personality_profile) > 1000:  # Truncate if too long
                        personality_profile = personality_profile[:1000] + "..."

                    # Extract birthday from character description
                    birthday = self.extract_birthday(char.get("about", ""))

                    # Determine element based on character traits
                    element = self.determine_element(char)

                    # Generate base stats
                    base_stats = self.generate_base_stats(char)

                    # Generate favorite gifts
                    favorite_gifts = self.generate_favorite_gifts(char)

                    await self.db_service.add_waifu(
                        {
                            "name": char["name"],
                            "series": char["series"],
                            "genre": char["series_type"].title(),
                            "element": element,
                            "rarity": rarity,
                            "image_url": char["image_url"],
                            "mal_id": char["mal_id"],
                            "personality_profile": (
                                personality_profile if personality_profile else None
                            ),
                            "base_stats": base_stats,  # Pass dict directly
                            "birthday": birthday,
                            "favorite_gifts": favorite_gifts,  # Pass list directly
                            "special_dialogue": {
                                "greeting": f"Hello! I'm {char['name']} from {char['series']}!",
                                "bond_1": "It's nice to meet you!",
                                "bond_3": "I'm getting to know you better.",
                                "bond_5": "We've become good friends!",
                                "bond_7": "I really trust you now.",
                                "bond_10": "You mean so much to me!",
                            },  # Pass dict directly
                        }
                    )

                except Exception as e:
                    logger.error(f"Error adding character {char['name']}: {e}")

            logger.info(
                f"✅ Successfully populated database with {len(all_characters)} female characters!"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Error during population: {e}")
            return False


async def main():
    """Main function."""
    try:
        config = Config.create()

        async with MALWaifuPopulator(config) as populator:
            success = await populator.populate_from_mal_user()

        return success

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
