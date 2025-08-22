#!/usr/bin/env python3
"""Script to upload character data from character_sql.csv to MySQL database."""

import asyncio
import csv
import json
import sys
import os
from typing import List, Dict, Any
import logging

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.database import DatabaseService
from services.waifu_service import WaifuService
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


class MySQLUploader:
    """Service to upload character data to MySQL database."""

    def __init__(self, config: Config):
        self.config = config
        self.db_service = None
        self.waifu_service = None
        self.input_file = "character_sql.csv"

    async def __aenter__(self):
        """Async context manager entry."""
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

    def load_characters(self) -> List[Dict[str, Any]]:
        """Load characters from character_sql.csv."""
        characters = []
        try:
            with open(self.input_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    characters.append(row)
            logger.info(f"Loaded {len(characters)} characters from {self.input_file}")
        except FileNotFoundError:
            logger.error(f"Input file {self.input_file} not found!")
            logger.error("Please run character_edit.py first to generate character_sql.csv")
            return []
        except Exception as e:
            logger.error(f"Error loading characters: {e}")
            return []
        
        return characters

    def load_anime_data(self) -> Dict[str, Dict[str, Any]]:
        """Load anime data from anime_mal.csv for series information."""
        anime_data = {}
        try:
            with open("anime_mal.csv", 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    mal_id = row.get("mal_id")
                    if mal_id:
                        anime_data[mal_id] = row
            logger.info(f"Loaded {len(anime_data)} anime records for series lookup")
        except FileNotFoundError:
            logger.warning("anime_mal.csv not found - series titles will use MAL IDs")
        except Exception as e:
            logger.warning(f"Error loading anime data: {e}")
        
        return anime_data

    def determine_character_rarity(self, character: Dict[str, Any], is_most_popular: bool = False) -> int:
        """Determine character rarity based on favorites."""
        favorites = int(character.get("favorites", 0))
        
        # Upgrade most popular character to 5-star
        if is_most_popular:
            return 5

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

    def determine_element(self, character: Dict[str, Any]) -> str:
        """Determine character element based on traits and series."""
        about = character.get("about", "").lower()
        series = character.get("series", "").lower()
        name = character.get("name", "").lower()

        # Magic-related
        if any(word in about for word in ["magic", "witch", "spell", "mage", "wizard", "sorcerer"]):
            return "magic"
        
        # Fire-related
        if any(word in about for word in ["fire", "flame", "burn", "hot", "heat", "dragon"]):
            return "fire"
        
        # Water-related
        if any(word in about for word in ["water", "sea", "ocean", "river", "ice", "snow", "cold"]):
            return "water"
        
        # Earth-related
        if any(word in about for word in ["earth", "stone", "rock", "mountain", "forest", "nature"]):
            return "earth"
        
        # Air-related
        if any(word in about for word in ["wind", "air", "sky", "cloud", "flying", "bird"]):
            return "air"
        
        # Light-related
        if any(word in about for word in ["light", "holy", "divine", "angel", "pure", "bright"]):
            return "light"
        
        # Dark-related
        if any(word in about for word in ["dark", "shadow", "demon", "evil", "death", "vampire"]):
            return "dark"

        # Default to neutral
        return "neutral"

    def generate_base_stats(self, character: Dict[str, Any]) -> Dict[str, int]:
        """Generate base stats for character."""
        favorites = int(character.get("favorites", 0))
        
        # Base stats influenced by popularity
        base = 50
        popularity_bonus = min(favorites // 100, 30)  # Max 30 bonus points
        
        return {
            "attack": base + popularity_bonus + (hash(character.get("name", "")) % 21 - 10),
            "defense": base + popularity_bonus + (hash(character.get("name", "")[::-1]) % 21 - 10),
            "speed": base + popularity_bonus + (hash(character.get("about", "")[:10]) % 21 - 10),
            "hp": base + popularity_bonus + (hash(character.get("mal_id", "0")) % 21 - 10)
        }

    def generate_favorite_gifts(self, character: Dict[str, Any]) -> List[str]:
        """Generate favorite gifts based on character traits."""
        about = character.get("about", "").lower()
        
        all_gifts = {
            "food": ["Chocolate", "Cake", "Ice Cream", "Cookies", "Candy"],
            "flower": ["Roses", "Sakura Petals", "Sunflower", "Lily", "Tulips"],
            "accessory": ["Hair Ribbon", "Necklace", "Earrings", "Bracelet", "Ring"],
            "book": ["Novel", "Manga", "Poetry Book", "Art Book", "Study Guide"],
            "toy": ["Plushie", "Figurine", "Music Box", "Puzzle", "Game"]
        }
        
        favorite_gifts = []
        
        # Analyze character description for preferences
        if any(word in about for word in ["food", "eat", "cook", "hungry", "sweet"]):
            favorite_gifts.extend(all_gifts["food"][:2])
        if any(word in about for word in ["flower", "garden", "nature", "beautiful"]):
            favorite_gifts.extend(all_gifts["flower"][:2])
        if any(word in about for word in ["book", "read", "study", "smart", "intelligent"]):
            favorite_gifts.extend(all_gifts["book"][:2])
        if any(word in about for word in ["cute", "pretty", "beautiful", "fashion"]):
            favorite_gifts.extend(all_gifts["accessory"][:2])

        # If no specific preferences found, add some defaults
        if not favorite_gifts:
            favorite_gifts = ["Chocolate", "Roses", "Hair Ribbon"]

        # Limit to 3-5 gifts
        return favorite_gifts[:5]

    def prepare_character_for_db(self, character: Dict[str, Any], anime_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare character data for database insertion."""
        series_mal_id = character.get("series_mal_id", "")
        series_title = "Unknown Series"
        
        # Look up series title from anime data
        if series_mal_id in anime_data:
            series_title = anime_data[series_mal_id].get("title", f"MAL ID {series_mal_id}")
        elif series_mal_id:
            series_title = f"MAL ID {series_mal_id}"

        # Generate character stats and attributes
        element = self.determine_element(character)
        rarity = self.determine_character_rarity(character)
        base_stats = self.generate_base_stats(character)
        favorite_gifts = self.generate_favorite_gifts(character)

        # Create birthday from character data if available
        birthday = character.get("birthday", "") or None

        return {
            "name": character.get("name", "Unknown"),
            "series": series_title,
            "genre": character.get("series_type", "anime").title(),
            "element": element,
            "rarity": rarity,
            "image_url": character.get("image_url", ""),
            "mal_id": int(character.get("mal_id", 0)),
            "base_stats": base_stats,
            "birthday": birthday,
            "favorite_gifts": favorite_gifts,
            "special_dialogue": {
                "greeting": f"Hello! I'm {character.get('name', 'Unknown')} from {series_title}!",
                "bond_1": "It's nice to meet you!",
                "bond_3": "I'm getting to know you better.",
                "bond_5": "We've become good friends!",
                "bond_7": "I really trust you now.",
                "bond_10": "You mean so much to me!",
            },
        }

    async def upload_characters(self):
        """Main function to upload characters to MySQL database."""
        try:
            logger.info("💾 Starting character upload to MySQL...")

            # Load character data
            characters = self.load_characters()
            if not characters:
                return False

            # Load anime data for series lookup
            anime_data = self.load_anime_data()

            # Check database connection
            logger.info("🔗 Testing database connection...")
            if not await self.db_service.test_connection():
                logger.error("❌ Database connection failed!")
                return False

            logger.info("✅ Database connection successful!")

            # Process and upload each character
            successful_uploads = 0
            failed_uploads = 0

            for i, character in enumerate(characters, 1):
                try:
                    char_name = character.get("name", "Unknown")
                    logger.info(f"Uploading character {i}/{len(characters)}: {char_name}")

                    # Check if character already exists
                    mal_id = int(character.get("mal_id", 0))
                    if mal_id:
                        existing = await self.db_service.get_waifu_by_mal_id(mal_id)
                        if existing:
                            logger.info(f"  Character {char_name} already exists in database (MAL ID: {mal_id})")
                            continue

                    # Prepare character data
                    char_data = self.prepare_character_for_db(character, anime_data)

                    # Add to database
                    await self.db_service.add_waifu(char_data)
                    successful_uploads += 1
                    
                    logger.info(f"  ✅ Successfully uploaded {char_name}")

                except Exception as e:
                    failed_uploads += 1
                    logger.error(f"  ❌ Failed to upload {char_name}: {e}")

            # Summary
            logger.info(f"📊 Upload Summary:")
            logger.info(f"  ✅ Successful: {successful_uploads}")
            logger.info(f"  ❌ Failed: {failed_uploads}")
            logger.info(f"  📝 Total processed: {len(characters)}")

            if successful_uploads > 0:
                logger.info("✅ Character upload completed successfully!")
                return True
            else:
                logger.warning("⚠️ No characters were uploaded!")
                return False

        except Exception as e:
            logger.error(f"❌ Error during character upload: {e}")
            return False


async def main():
    """Main function."""
    try:
        config = Config.create()

        async with MySQLUploader(config) as uploader:
            success = await uploader.upload_characters()

        return success

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
