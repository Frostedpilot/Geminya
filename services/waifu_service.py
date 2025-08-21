"""Waifu service for managing gacha mechanics and character data."""

import random
import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from services.database import DatabaseService


class WaifuService:
    """Service for managing waifu gacha system."""

    # Gacha rates (percentages)
    GACHA_RATES = {
        5: 0.6,  # 5-star: 0.6%
        4: 2.0,  # 4-star: 2.0%
        3: 25.0,  # 3-star: 25.0%
        2: 35.0,  # 2-star: 35.0%
        1: 37.4,  # 1-star: 37.4%
    }

    # Pity system
    PITY_4_STAR = 10  # Guaranteed 4-star every 10 pulls
    PITY_5_STAR = 90  # Guaranteed 5-star every 90 pulls

    # Elements for diversity
    ELEMENTS = ["Fire", "Water", "Earth", "Air", "Light", "Dark"]

    # Cost per summon
    SUMMON_COST = 10
    MULTI_SUMMON_COST = 90  # Cost for x10 summons (10% discount)

    def __init__(self, database: DatabaseService):
        self.db = database
        self.jikan_base_url = "https://api.jikan.moe/v4"
        self.rate_limit_delay = 0.2  # Increased delay to be more polite to Jikan API
        self.logger = logging.getLogger(__name__)
        self._character_cache = {}
        self._last_request_time = 0

    async def initialize(self):
        """Initialize the waifu service."""
        await self.db.initialize()
        self.logger.info("Waifu service initialized")

    async def close(self):
        """Close the waifu service and its database connection."""
        await self.db.close()
        self.logger.info("Waifu service closed")

    async def _query_jikan(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make a REST API call to Jikan API with polite rate limiting."""
        try:
            # Ensure proper spacing between requests to be polite
            import time

            current_time = time.time()
            time_since_last = current_time - self._last_request_time

            if time_since_last < self.rate_limit_delay:
                wait_time = self.rate_limit_delay - time_since_last
                self.logger.debug(
                    f"Rate limiting: waiting {wait_time:.2f}s before Jikan API request"
                )
                await asyncio.sleep(wait_time)

            self._last_request_time = time.time()
            url = f"{self.jikan_base_url}{endpoint}"

            self.logger.debug(f"Making Jikan API request to: {endpoint}")

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params or {},
                    timeout=aiohttp.ClientTimeout(total=30),  # Increased timeout
                    headers={"User-Agent": "Geminya-WaifuBot/1.0"},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.logger.debug(f"Successfully fetched data from {endpoint}")
                        return data
                    elif response.status == 429:  # Rate limited
                        self.logger.warning("Jikan API rate limit hit, waiting longer")
                        await asyncio.sleep(5.0)  # Wait longer on rate limit
                        return None
                    elif response.status == 404:
                        self.logger.info(f"Resource not found at {endpoint}")
                        return None
                    else:
                        self.logger.warning(
                            f"Jikan API returned status {response.status} for {endpoint}"
                        )
                        return None

        except asyncio.TimeoutError:
            self.logger.error(f"Timeout querying Jikan API endpoint: {endpoint}")
            return None
        except aiohttp.ClientError as e:
            self.logger.error(f"Client error querying Jikan API: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error querying Jikan API: {e}")
            return None

    async def populate_initial_waifus(self):
        """Populate database with initial waifus from MAL completed anime."""
        try:
            self.logger.info("Starting polite population of waifu database...")

            # Smaller initial set to be more polite to the API
            popular_series = [
                {"mal_id": 16498, "title": "Attack on Titan"},
                {"mal_id": 11061, "title": "Hunter x Hunter (2011)"},
                {"mal_id": 9253, "title": "Steins;Gate"},
                {"mal_id": 38000, "title": "Demon Slayer"},
                {"mal_id": 40748, "title": "Jujutsu Kaisen"},
            ]

            for i, series_info in enumerate(popular_series):
                self.logger.info(
                    f"Processing series {i+1}/{len(popular_series)}: {series_info['title']}"
                )

                success = await self._populate_characters_from_anime(
                    series_info["mal_id"], series_info["title"]
                )

                if not success:
                    self.logger.warning(
                        f"Failed to populate {series_info['title']}, continuing..."
                    )

                # Extra polite delay between series
                if i < len(popular_series) - 1:  # Don't sleep after the last one
                    self.logger.debug(
                        "Waiting before next series to be polite to Jikan API..."
                    )
                    await asyncio.sleep(2.0)

        except Exception as e:
            self.logger.error(f"Error populating initial waifus: {e}")

    async def _populate_characters_from_anime(
        self, mal_id: int, series_title: str
    ) -> bool:
        """Populate characters from a specific anime. Returns True if successful."""
        try:
            self.logger.debug(f"Fetching anime details for {series_title}")

            # Get anime details
            anime_data = await self._query_jikan(f"/anime/{mal_id}")

            if not anime_data or not anime_data.get("data"):
                self.logger.warning(
                    f"No anime data found for {series_title} (ID: {mal_id})"
                )
                return False

            self.logger.debug(f"Fetching characters for {series_title}")

            # Get characters with a small delay
            await asyncio.sleep(0.5)  # Small delay between anime and character requests
            characters_data = await self._query_jikan(f"/anime/{mal_id}/characters")

            if not characters_data or not characters_data.get("data"):
                self.logger.warning(f"No character data found for {series_title}")
                return False

            added_count = 0
            # Limit to top 8 characters to be more reasonable
            for char_data in characters_data["data"][:8]:
                character = char_data.get("character", {})
                if not character:
                    continue

                role = char_data.get("role", "Supporting")

                # Determine rarity based on role and popularity
                rarity = self._determine_character_rarity(
                    role, character.get("favorites", 0), character.get("name", "")
                )

                # Create character profile
                waifu_data = {
                    "name": character.get("name", "Unknown"),
                    "series": series_title,
                    "genre": ", ".join(
                        [
                            g["name"]
                            for g in anime_data.get("data", {}).get("genres", [])[:3]
                        ]
                    ),
                    "element": random.choice(self.ELEMENTS),
                    "rarity": rarity,
                    "image_url": character.get("images", {})
                    .get("jpg", {})
                    .get("image_url"),
                    "mal_id": character.get("mal_id"),
                    "personality_profile": await self._generate_personality_profile(
                        character, role, series_title
                    ),
                    "base_stats": self._generate_base_stats(rarity),
                    "birthday": None,  # Could be parsed from character.about if available
                    "favorite_gifts": self._generate_favorite_gifts(rarity),
                    "special_dialogue": self._generate_special_dialogue(
                        character.get("name", "Unknown")
                    ),
                }

                # Check if character already exists
                existing = await self.db.search_waifus(character.get("name", ""))
                if not any(
                    w["name"] == waifu_data["name"]
                    and w["series"] == waifu_data["series"]
                    for w in existing
                ):
                    await self.db.add_waifu(waifu_data)
                    self.logger.info(f"Added {waifu_data['name']} from {series_title}")
                    added_count += 1

            self.logger.info(
                f"Successfully added {added_count} characters from {series_title}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error populating characters from {series_title}: {e}")
            return False

    def _determine_character_rarity(
        self, role: str, favorites: int, character_name: str = ""
    ) -> int:
        """Determine character rarity based on role and popularity. Base waifus are 1-3 stars only."""
        # Famous characters get higher base rarity (but still max 3 stars)
        famous_3_star = [
            "mikasa",
            "eren",
            "armin",
            "gon",
            "killua",
            "kurapika",
            "leorio",
            "light",
            "l",
            "kurisu",
            "okabe",
            "saitama",
            "genos",
            "tanjiro",
            "nezuko",
            "zenitsu",
            "inosuke",
            "gojo",
            "yuji",
            "megumi",
            "nobara",
            "howl",
            "sophie",
            "san",
            "ashitaka",
        ]

        famous_2_star = [
            "sasha",
            "erwin",
            "historia",
            "annie",
            "reiner",
            "hisoka",
            "ryuk",
            "misa",
            "calcifer",
            "markl",
        ]

        # Check if character name contains any famous names
        char_name = character_name.lower()
        if any(famous.lower() in char_name for famous in famous_3_star):
            return 3
        elif any(famous.lower() in char_name for famous in famous_2_star):
            return 2

        # Base rarity distribution (1-3 stars only)
        if role == "Main" and favorites > 5000:
            return 3
        elif role == "Main" and favorites > 1000:
            return 3
        elif role == "Main":
            return 2
        elif role == "Supporting" and favorites > 2000:
            return 3
        elif role == "Supporting" and favorites > 500:
            return 2
        else:
            return 1

    async def _generate_personality_profile(
        self, character: Dict, role: str, series: str
    ) -> str:
        """Generate a personality profile for the character."""
        # This could be enhanced with AI generation later
        base_profiles = [
            "A cheerful and optimistic character who brings light to any situation.",
            "A mysterious and elegant character with hidden depths.",
            "A brave and determined character who never gives up.",
            "A gentle and caring character who puts others first.",
            "A witty and intelligent character with a sharp tongue.",
            "A energetic and passionate character who lives life to the fullest.",
            "A calm and composed character who thinks before acting.",
            "A playful and mischievous character who loves to tease.",
        ]

        profile = random.choice(base_profiles)
        return f"{profile} From the world of {series}, this {role.lower()} character has captured many hearts."

    def _generate_base_stats(self, rarity: int) -> Dict[str, int]:
        """Generate base stats based on rarity."""
        base_value = 10 + (rarity * 5)
        variation = rarity * 2

        return {
            "strength": base_value + random.randint(-variation, variation),
            "intelligence": base_value + random.randint(-variation, variation),
            "charm": base_value + random.randint(-variation, variation),
            "creativity": base_value + random.randint(-variation, variation),
            "empathy": base_value + random.randint(-variation, variation),
        }

    def _generate_favorite_gifts(self, rarity: int) -> List[str]:
        """Generate favorite gifts based on rarity."""
        gift_pools = {
            1: ["flowers", "snacks", "books"],
            2: ["jewelry", "plushies", "music box"],
            3: ["rare books", "art supplies", "handmade items"],
            4: ["luxury items", "rare artifacts", "custom accessories"],
            5: ["legendary items", "divine artifacts", "soulbound treasures"],
        }

        gifts = gift_pools.get(rarity, gift_pools[1])
        return random.sample(gifts, min(len(gifts), 2))

    def _generate_special_dialogue(self, name: str) -> Dict[str, List[str]]:
        """Generate special dialogue options."""
        return {
            "greeting": [
                f"Hello! I'm {name}, nice to meet you!",
                f"Oh, it's you! {name} here, ready for an adventure?",
                f"Welcome to my world! I'm {name}, your new companion.",
            ],
            "bond_up": [
                "I feel like we're getting closer!",
                "Thank you for spending time with me!",
                "Our bond grows stronger each day!",
            ],
            "gift_received": [
                "A gift? For me? Thank you so much!",
                "You're so thoughtful! I love it!",
                "This is perfect! How did you know?",
            ],
        }

    async def perform_summon(
        self, discord_id: str, summon_type: str = "standard"
    ) -> Dict[str, Any]:
        """Perform a waifu summon."""
        user = await self.db.get_or_create_user(discord_id)

        # Check if user has enough crystals
        if user["sakura_crystals"] < self.SUMMON_COST:
            return {
                "success": False,
                "message": f"Not enough Sakura Crystals! You need {self.SUMMON_COST} but have {user['sakura_crystals']}.",
            }

        # Determine rarity with pity system
        rarity = await self._determine_summon_rarity(user)

        # Get available waifus of that rarity
        available_waifus = await self.db.get_waifus_by_rarity(rarity, 50)

        if not available_waifus:
            return {
                "success": False,
                "message": f"No waifus available for rarity {rarity}. Please contact an administrator.",
            }

        # Select random waifu
        selected_waifu = random.choice(available_waifus)

        # Add to user's collection
        await self.db.add_waifu_to_user(discord_id, selected_waifu["id"])

        # Update user's crystals and pity counter
        await self.db.update_user_crystals(discord_id, -self.SUMMON_COST)

        if rarity >= 4:
            await self.db.update_pity_counter(discord_id, reset=True)
        else:
            await self.db.update_pity_counter(discord_id)

        # Check if this is a new waifu or constellation
        user_collection = await self.db.get_user_collection(discord_id)
        waifu_count = sum(
            1 for w in user_collection if w["waifu_id"] == selected_waifu["id"]
        )

        is_new = waifu_count == 1
        constellation_level = waifu_count - 1

        return {
            "success": True,
            "waifu": selected_waifu,
            "is_new": is_new,
            "constellation_level": constellation_level,
            "crystals_remaining": user["sakura_crystals"] - self.SUMMON_COST,
            "rarity": rarity,
        }

    async def perform_multi_summon(
        self, discord_id: str, count: int = 10
    ) -> Dict[str, Any]:
        """Perform multiple waifu summons with discount."""
        user = await self.db.get_or_create_user(discord_id)

        # Calculate cost (with discount for x10 pulls)
        if count == 10:
            total_cost = self.MULTI_SUMMON_COST  # 10% discount for x10 pulls
        else:
            total_cost = self.SUMMON_COST * count

        # Check if user has enough crystals
        if user["sakura_crystals"] < total_cost:
            return {
                "success": False,
                "message": f"Not enough Sakura Crystals! You need {total_cost} but have {user['sakura_crystals']}.",
            }

        # Perform individual summons
        results = []
        rarity_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        new_waifus = []
        constellation_upgrades = []

        for i in range(count):
            # Get fresh user data for each summon (for pity system)
            current_user = await self.db.get_or_create_user(discord_id)

            # Determine rarity with pity system
            rarity = await self._determine_summon_rarity(current_user)

            # Get available waifus of that rarity
            available_waifus = await self.db.get_waifus_by_rarity(rarity, 50)

            if not available_waifus:
                # Skip this summon if no waifus available
                continue

            # Select random waifu
            selected_waifu = random.choice(available_waifus)

            # Add to user's collection
            await self.db.add_waifu_to_user(discord_id, selected_waifu["id"])

            # Update crystals and pity counter
            cost = self.SUMMON_COST
            if count == 10 and i == 9:  # Last summon in x10 pull gets the discount
                cost = 0  # Already accounted for in total_cost calculation

            await self.db.update_user_crystals(discord_id, -cost)

            if rarity >= 4:
                await self.db.update_pity_counter(discord_id, reset=True)
            else:
                await self.db.update_pity_counter(discord_id)

            # Check if this is a new waifu or constellation
            user_collection = await self.db.get_user_collection(discord_id)
            waifu_count = sum(
                1 for w in user_collection if w["waifu_id"] == selected_waifu["id"]
            )

            is_new = waifu_count == 1
            constellation_level = waifu_count - 1

            # Track results
            rarity_counts[rarity] += 1

            if is_new:
                new_waifus.append(selected_waifu)
            else:
                constellation_upgrades.append(
                    {
                        "waifu": selected_waifu,
                        "constellation_level": constellation_level,
                    }
                )

            results.append(
                {
                    "waifu": selected_waifu,
                    "rarity": rarity,
                    "is_new": is_new,
                    "constellation_level": constellation_level,
                }
            )

        # Get final user state
        final_user = await self.db.get_or_create_user(discord_id)

        return {
            "success": True,
            "results": results,
            "count": len(results),
            "total_cost": total_cost,
            "crystals_remaining": final_user["sakura_crystals"],
            "rarity_counts": rarity_counts,
            "new_waifus": new_waifus,
            "constellation_upgrades": constellation_upgrades,
            "discount_applied": count == 10,
        }

    async def _determine_summon_rarity(self, user: Dict[str, Any]) -> int:
        """Determine summon rarity using gacha rates and pity system."""
        pity_count = user["pity_counter"]

        # Pity system check
        if pity_count >= self.PITY_5_STAR:
            return 5
        elif pity_count >= self.PITY_4_STAR:
            return 4

        # Normal rates with pity soft increase
        rates = self.GACHA_RATES.copy()

        # Soft pity - increase 5-star rate after 75 pulls
        if pity_count >= 75:
            increase = (pity_count - 74) * 0.6
            rates[5] = min(rates[5] + increase, 100)

        # Generate random number and determine rarity
        roll = random.random() * 100
        
        # Build proper cumulative ranges from lowest to highest rarity
        cumulative = 0
        for rarity in sorted(rates.keys()):  # Process 1, 2, 3, 4, 5
            cumulative += rates[rarity]
            if roll <= cumulative:
                return rarity

        return 1  # Fallback

    async def get_user_stats(self, discord_id: str) -> Dict[str, Any]:
        """Get user's academy stats."""
        user = await self.db.get_or_create_user(discord_id)
        collection = await self.db.get_user_collection(discord_id)

        # Calculate collection stats
        total_waifus = len(collection)
        unique_waifus = len(set(w["waifu_id"] for w in collection))
        rarity_counts = {}

        for waifu in collection:
            rarity = waifu["rarity"]
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1

        return {
            "user": user,
            "total_waifus": total_waifus,
            "unique_waifus": unique_waifus,
            "rarity_distribution": rarity_counts,
            "collection_power": sum(w["rarity"] * w["bond_level"] for w in collection),
        }
