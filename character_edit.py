#!/usr/bin/env python3
"""Placeholder script for character editing - takes data/characters_mal.csv and outputs character_sql.csv."""

import csv
import os
import sys
import logging
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


class CharacterEditor:
    """Service to edit and filter characters from MAL data."""

    def __init__(self):
        self.input_file = os.path.join("data", "characters_mal.csv")
        self.anime_file = os.path.join("data", "anime_mal.csv")
        self.gender_file = os.path.join("data", "characters.csv")
        self.output_file = os.path.join("data", "character_sql.csv")
        self.anime_lookup = self.load_anime_data()
        self.gender_lookup = self.load_gender_data()

    def load_anime_data(self) -> Dict[str, str]:
        """Load anime data for series name lookup."""
        anime_lookup = {}
        try:
            with open(self.anime_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    mal_id = row.get("mal_id")
                    title = row.get("title", "Unknown Series")
                    if mal_id:
                        anime_lookup[mal_id] = title
            logger.info(f"Loaded {len(anime_lookup)} anime titles for series lookup")
        except FileNotFoundError:
            logger.warning(f"Anime file {self.anime_file} not found - series names will use MAL IDs")
        except Exception as e:
            logger.warning(f"Error loading anime data: {e}")
        return anime_lookup

    def load_gender_data(self) -> Dict[str, List[int]]:
        """Load gender data from data/characters.csv for filtering male characters."""
        gender_lookup = {}
        try:
            with open(self.gender_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Use romji (romanized name) as the character name
                    name = row.get("romji", "").strip()
                    sex = row.get("sex", "")
                    
                    if name and sex:
                        try:
                            sex_value = int(sex)
                            if name not in gender_lookup:
                                gender_lookup[name] = []
                            gender_lookup[name].append(sex_value)
                        except ValueError:
                            continue
                            
            logger.info(f"Loaded gender data for {len(gender_lookup)} character names")
        except FileNotFoundError:
            logger.warning(f"Gender file {self.gender_file} not found - no gender filtering will be applied")
        except Exception as e:
            logger.warning(f"Error loading gender data: {e}")
        return gender_lookup

    def is_female_character(self, character_name: str) -> bool:
        """Check if a character is female based on gender data.
        
        Returns True if:
        - Character name not found in gender data (default to include)
        - At least one instance of the character is female (sex in [2,4,5,6])
        
        Returns False if:
        - All instances of the character are male (sex in [0,1,3])
        """
        if not character_name or character_name not in self.gender_lookup:
            return True  # Default to include if no gender data found
            
        sex_values = self.gender_lookup[character_name]
        
        # Check if all instances are male (0, 1, 3)
        male_values = {0, 1, 3}
        female_values = {2, 4, 5, 6}
        
        # If all instances are male, exclude the character
        if all(sex in male_values for sex in sex_values):
            return False
            
        # If any instance is female or has mixed genders, include the character
        return True

    def load_characters(self) -> List[Dict[str, Any]]:
        """Load characters from data/characters_mal.csv."""
        characters = []
        try:
            with open(self.input_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    characters.append(row)
            logger.info(f"Loaded {len(characters)} characters from {self.input_file}")
        except FileNotFoundError:
            logger.error(f"Input file {self.input_file} not found!")
            return []
        except Exception as e:
            logger.error(f"Error loading characters: {e}")
            return []
        
        return characters

    def process_character(self, character: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single character for database insertion."""
        
        # Get series name from anime lookup
        series_mal_id = character.get("series_mal_id", "")
        series_name = self.anime_lookup.get(series_mal_id, f"Unknown Series (MAL ID: {series_mal_id})")
        
        # Calculate rarity based on favorites
        rarity = self.determine_rarity(character)
        
        # Only keep essential columns for the database
        processed = {
            "mal_id": character.get("mal_id", ""),
            "name": character.get("name", ""),
            "series": series_name,
            "genre": "Anime" if character.get("series_type") == "anime" else "Manga",
            "rarity": rarity,
            "image_url": character.get("image_url", ""),
            "favorites": character.get("favorites", "0"),
        }
        
        return processed

    def determine_rarity(self, character: Dict[str, Any]) -> int:
        """Determine character rarity based on favorites count - NEW STAR SYSTEM (1-3 stars only)."""
        favorites = int(character.get("favorites", 0))
        
        # New star system: Only assign 1-3 stars for gacha
        # 4-5 stars will be achieved through upgrade system
        if favorites >= 2000:
            return 3  # 3-star (rare) - highest direct gacha tier
        elif favorites >= 500:
            return 2  # 2-star (uncommon)
        else:
            return 1  # 1-star (common)

    def save_processed_characters(self, characters: List[Dict[str, Any]]):
        """Save processed characters to character_sql.csv."""
        if not characters:
            logger.warning("No characters to save!")
            return

        fieldnames = [
            "mal_id", "name", "series", "genre", "rarity", "image_url", "favorites"
        ]

        try:
            with open(self.output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for character in characters:
                    writer.writerow(character)
                    
            logger.info(f"Saved {len(characters)} processed characters to {self.output_file}")
            
        except Exception as e:
            logger.error(f"Error saving characters: {e}")

    def process_characters(self):
        """Main function to process characters."""
        try:
            logger.info("🔧 Starting character processing...")

            # Load characters from CSV
            characters = self.load_characters()
            if not characters:
                return False

            # Filter out male characters
            filtered_characters = []
            male_count = 0
            
            for character in characters:
                character_name = character.get("name", "")
                if self.is_female_character(character_name):
                    filtered_characters.append(character)
                else:
                    male_count += 1
                    logger.debug(f"Filtered out male character: {character_name}")
            
            logger.info(f"🚺 Gender filtering: {len(filtered_characters)} female/unknown characters kept, {male_count} male characters removed")

            # Process each character
            processed_characters = []
            for i, character in enumerate(filtered_characters, 1):
                logger.info(f"Processing character {i}/{len(filtered_characters)}: {character.get('name', 'Unknown')}")
                
                processed = self.process_character(character)
                processed_characters.append(processed)

            # Save processed characters
            self.save_processed_characters(processed_characters)

            logger.info(f"✅ Successfully processed {len(processed_characters)} characters!")
            return True

        except Exception as e:
            logger.error(f"❌ Error during character processing: {e}")
            return False


def main():
    """Main function."""
    try:
        editor = CharacterEditor()
        success = editor.process_characters()
        return success

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    print("\n" + "="*60)
    print("� CHARACTER EDITOR")
    print("="*60)
    print("Processed characters from data/characters_mal.csv")
    print("Output: data/character_sql.csv with essential columns:")
    print("  - mal_id, name, series, genre, rarity, image_url, favorites")
    print("")
    print("Features:")
    print("  ✅ Drops useless columns (nicknames, about, etc.)")
    print("  ✅ Adds series name lookup from data/anime_mal.csv")
    print("  ✅ Calculates rarity based on favorites count")
    print("  ✅ Converts series_type to genre (Anime/Manga)")
    print("  ✅ Filters out male characters using data/characters.csv")
    print("     - Male: sex values 0/1/3")
    print("     - Female: sex values 2/4/5/6") 
    print("     - Removes characters only if ALL instances are male")
    print("="*60)
    
    sys.exit(0 if success else 1)
