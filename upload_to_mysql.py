#!/usr/bin/env python3
"""Script to upload character data from data/character_final.csv to MySQL database."""

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
        self.input_file = os.path.join("data", "character_final.csv")

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
        """Load characters from data/character_final.csv."""
        characters = []
        try:
            with open(self.input_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    characters.append(row)
            logger.info(f"Loaded {len(characters)} characters from {self.input_file}")
        except FileNotFoundError:
            logger.error(f"Input file {self.input_file} not found!")
            logger.error("Please run process_character_final.py first to generate data/character_final.csv")
            return []
        except Exception as e:
            logger.error(f"Error loading characters: {e}")
            return []
        
        return characters

    def process_character_for_database(self, character: Dict[str, Any]) -> Dict[str, Any]:
        """Process character data for database insertion."""
        
        # The character_edit.py now provides clean data, we just need to add some database-specific fields
        char_data = {
            "name": character.get("name", ""),
            "series": character.get("series", "Unknown Series"),
            "genre": character.get("genre", "Anime"),
            "element": self.determine_element(character),
            "rarity": int(character.get("rarity", 1)),  # Use rarity from character_edit.py
            "image_url": character.get("image_url", ""),
            "mal_id": character.get("mal_id", ""),
            "base_stats": self.generate_base_stats(character),
            "birthday": "",  # Placeholder - can be enhanced later
            "favorite_gifts": [],  # Placeholder - can be enhanced later
        }
        
        return char_data

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

    async def upload_characters(self):
        """Main function to upload characters to MySQL database."""
        try:
            logger.info("💾 Starting character upload to MySQL...")

            # Load character data
            characters = self.load_characters()
            if not characters:
                return False

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

                    # Prepare character data for database
                    char_data = self.process_character_for_database(character)

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
