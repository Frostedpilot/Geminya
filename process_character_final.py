#!/usr/bin/env python3
"""Process character_cleaned.xlsx and output data/character_final.csv for new star system."""

import pandas as pd
import os
import sys
import logging
from typing import Dict, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


class CharacterFinalProcessor:
    """Process cleaned Excel file for the new star system."""

    def __init__(self):
        self.input_file = os.path.join("data", "characters_cleaned.xlsx")
        self.anime_input_file = os.path.join("data", "anime_mal.xlsx")
        self.character_output_file = os.path.join("data", "character_final.csv")
        self.anime_output_file = os.path.join("data", "anime_final.csv")
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
    def load_anime_excel(self) -> Optional[pd.DataFrame]:
        """Load the anime Excel file for series info."""
        try:
            logger.info(f"Loading Anime Excel file: {self.anime_input_file}")
            df = pd.read_excel(self.anime_input_file)
            logger.info(f"✅ Loaded {len(df)} anime/series from Excel file")
            logger.info(f"📋 Anime Columns: {list(df.columns)}")
            return df
        except FileNotFoundError:
            logger.error(f"❌ Anime Excel file {self.anime_input_file} not found!")
            return None
        except Exception as e:
            logger.error(f"❌ Error loading Anime Excel file: {e}")
            return None

    def load_excel_data(self) -> Optional[pd.DataFrame]:
        """Load the cleaned Excel file."""
        try:
            logger.info(f"Loading Excel file: {self.input_file}")
            df = pd.read_excel(self.input_file)
            logger.info(f"✅ Loaded {len(df)} characters from Excel file")
            logger.info(f"📋 Columns: {list(df.columns)}")
            return df
        except FileNotFoundError:
            logger.error(f"❌ Excel file {self.input_file} not found!")
            return None
        except Exception as e:
            logger.error(f"❌ Error loading Excel file: {e}")
            return None

    def determine_element(self, about: str, series: str, name: str) -> str:
        about = about.lower()
        series = series.lower()
        name = name.lower()
        if any(word in about for word in ["magic", "witch", "spell", "mage", "wizard", "sorcerer"]):
            return "magic"
        if any(word in about for word in ["fire", "flame", "burn", "hot", "heat", "dragon"]):
            return "fire"
        if any(word in about for word in ["water", "sea", "ocean", "river", "ice", "snow", "cold"]):
            return "water"
        if any(word in about for word in ["earth", "stone", "rock", "mountain", "forest", "nature"]):
            return "earth"
        if any(word in about for word in ["wind", "air", "sky", "cloud", "flying", "bird"]):
            return "air"
        if any(word in about for word in ["light", "holy", "divine", "angel", "pure", "bright"]):
            return "light"
        if any(word in about for word in ["dark", "shadow", "demon", "evil", "death", "vampire"]):
            return "dark"
        return "neutral"

    def generate_base_stats(self, name: str, about: str, waifu_id: int, favorites: int) -> dict:
        base = 50
        popularity_bonus = min(favorites // 100, 30)
        return {
            "attack": base + popularity_bonus + (hash(name) % 21 - 10),
            "defense": base + popularity_bonus + (hash(name[::-1]) % 21 - 10),
            "speed": base + popularity_bonus + (hash(about[:10]) % 21 - 10),
            "hp": base + popularity_bonus + (hash(str(waifu_id)) % 21 - 10)
        }

    def generate_favorite_gifts(self, about: str) -> list:
        about = about.lower()
        all_gifts = {
            "food": ["Chocolate", "Cake", "Ice Cream", "Cookies", "Candy"],
            "flower": ["Roses", "Sakura Petals", "Sunflower", "Lily", "Tulips"],
            "accessory": ["Hair Ribbon", "Necklace", "Earrings", "Bracelet", "Ring"],
            "book": ["Novel", "Manga", "Poetry Book", "Art Book", "Study Guide"],
            "toy": ["Plushie", "Figurine", "Music Box", "Puzzle", "Game"]
        }
        favorite_gifts = []
        if any(word in about for word in ["food", "eat", "cook", "hungry", "sweet"]):
            favorite_gifts.extend(all_gifts["food"][:2])
        if any(word in about for word in ["flower", "garden", "nature", "beautiful"]):
            favorite_gifts.extend(all_gifts["flower"][:2])
        if any(word in about for word in ["book", "read", "study", "smart", "intelligent"]):
            favorite_gifts.extend(all_gifts["book"][:2])
        if any(word in about for word in ["cute", "pretty", "beautiful", "fashion"]):
            favorite_gifts.extend(all_gifts["accessory"][:2])
        if not favorite_gifts:
            favorite_gifts = ["Chocolate", "Roses", "Hair Ribbon"]
        return favorite_gifts[:5]

    def validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and clean the DataFrame for the new star system, including about column."""
        logger.info("🧹 Validating and cleaning data...")
        original_count = len(df)
        # Required columns for upload_to_mysql.py compatibility
        required_columns = ['waifu_id', 'name', 'series', 'genre', 'rarity', 'image_url', 'favorites']
        # If 'waifu_id' is not present but 'mal_id' is, rename it
        if 'waifu_id' not in df.columns and 'mal_id' in df.columns:
            df = df.rename(columns={"mal_id": "waifu_id"})
        # Check if all required columns exist
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"❌ Missing required columns: {missing_columns}")
            logger.info(f"Available columns: {list(df.columns)}")
            return pd.DataFrame()
        # Add about column if present in input
        about_present = 'about' in df.columns
        output_columns = required_columns + (['about'] if about_present else [])
        # Select only the required columns (plus about if present)
        df_clean = df[output_columns].copy()
        # Clean and validate data
        # Remove rows with missing essential data
        df_clean = df_clean.dropna(subset=['waifu_id', 'name', 'rarity'])
        # Ensure waifu_id is integer
        df_clean['waifu_id'] = pd.to_numeric(df_clean['waifu_id'], errors='coerce')
        df_clean = df_clean.dropna(subset=['waifu_id'])
        df_clean['waifu_id'] = df_clean['waifu_id'].astype(int)
        # Ensure rarity is integer and within valid range (1-3 for new system)
        df_clean['rarity'] = pd.to_numeric(df_clean['rarity'], errors='coerce')
        df_clean = df_clean.dropna(subset=['rarity'])
        df_clean['rarity'] = df_clean['rarity'].astype(int)
        # Use the rarity values from the input file (no automatic assignment)
        logger.info("⭐ Using star ratings from input file (no automatic assignment)")
        df_clean['favorites'] = pd.to_numeric(df_clean['favorites'], errors='coerce').fillna(0).astype(int)
        # Log the star distribution from the input file
        star_dist = df_clean['rarity'].value_counts().sort_index()
        total_chars = len(df_clean)
        logger.info("📊 Star distribution from input file:")
        for rarity, count in star_dist.items():
            percentage = (count / total_chars) * 100
            logger.info(f"  {rarity}★: {count} characters ({percentage:.1f}%)")
        # Validate rarity range for new star system (1-3★ only)
        invalid_rarity = df_clean[(df_clean['rarity'] < 1) | (df_clean['rarity'] > 3)]
        if len(invalid_rarity) > 0:
            logger.warning(f"⚠️  Found {len(invalid_rarity)} characters with invalid rarity (outside 1-3 range)")
            logger.info("Removing characters with invalid rarity...")
            df_clean = df_clean[(df_clean['rarity'] >= 1) & (df_clean['rarity'] <= 3)]
        # Fill missing optional fields
        df_clean['series'] = df_clean['series'].fillna('Unknown Series')
        df_clean['genre'] = df_clean['genre'].fillna('Anime')
        df_clean['image_url'] = df_clean['image_url'].fillna('')
        if about_present:
            df_clean['about'] = df_clean['about'].fillna('')
        # Remove duplicates based on waifu_id
        duplicate_count = df_clean.duplicated(subset=['waifu_id']).sum()
        if duplicate_count > 0:
            logger.warning(f"⚠️  Found {duplicate_count} duplicate waifu_ids, keeping first occurrence")
            df_clean = df_clean.drop_duplicates(subset=['waifu_id'], keep='first')
        cleaned_count = len(df_clean)
        removed_count = original_count - cleaned_count
        logger.info(f"✅ Data validation complete:")
        logger.info(f"  - Original: {original_count} characters")
        logger.info(f"  - Cleaned: {cleaned_count} characters")
        logger.info(f"  - Removed: {removed_count} characters")
        return df_clean

    def get_rarity_description(self, rarity: int) -> str:
        """Get description for rarity level."""
        descriptions = {
            1: "Common - Direct Gacha",
            2: "Uncommon - Direct Gacha",
            3: "Rare - Direct Gacha",
            4: "Epic - Upgrade Only",
            5: "Legendary - Upgrade Only"
        }
        return descriptions.get(rarity, "Unknown")

    def analyze_star_system_impact(self, df: pd.DataFrame):
        """Analyze the impact of the new star system on the character distribution."""
        logger.info("🔍 Analyzing new star system impact...")
        
        total_chars = len(df)
        gacha_chars = len(df[df['rarity'] <= 3])  # 1-3 stars available in gacha (all characters now)
        
        logger.info(f"📈 Star System Analysis:")
        logger.info(f"  Total Characters: {total_chars}")
        logger.info(f"  All characters available in gacha (1-3★): {gacha_chars} (100%)")
        logger.info(f"  Characters can be upgraded to 4-5★ using shards after summoning")
        
        # Show rarity distribution
        logger.info("🎯 Current Rarity Distribution:")
        for rarity in [1, 2, 3]:
            count = len(df[df['rarity'] == rarity])
            if count > 0:
                percentage = count / total_chars * 100
                logger.info(f"    {rarity}★: {count} characters ({percentage:.1f}%)")

    def save_final_csvs(self, df_char: pd.DataFrame, df_anime: pd.DataFrame) -> bool:
        """Save the final processed character and anime data to CSV, including new series fields."""
        try:
            logger.info(f"💾 Saving anime/series data to {self.anime_output_file}")
            anime_column_order = [
                'series_id', 'name', 'english_name', 'image_link',
                'studios', 'genres', 'synopsis', 'favorites', 'members', 'score'
            ]
            # Fill missing columns if not present
            for col in anime_column_order:
                if col not in df_anime.columns:
                    df_anime[col] = '' if col not in ['favorites', 'members', 'score'] else 0
            df_anime_final = df_anime[anime_column_order]
            df_anime_final.to_csv(self.anime_output_file, index=False, encoding='utf-8')
            logger.info(f"✅ Saved {len(df_anime_final)} series to {self.anime_output_file}")
            logger.info(f"📁 File size: {os.path.getsize(self.anime_output_file)} bytes")

            logger.info(f"💾 Saving character data to {self.character_output_file}")
            # Include about column if present
            char_column_order = ['waifu_id', 'name', 'series', 'series_id', 'genre', 'rarity', 'image_url', 'favorites']
            if 'about' in df_char.columns:
                char_column_order.append('about')
            # Add new transformation columns
            char_column_order += ['element', 'base_stats', 'favorite_gifts', 'special_dialogue']
            df_char_final = df_char[char_column_order]
            # Convert dict/list columns to JSON strings for CSV
            for col in ['base_stats', 'favorite_gifts', 'special_dialogue']:
                df_char_final[col] = df_char_final[col].apply(lambda x: x if isinstance(x, str) else __import__('json').dumps(x))
            df_char_final.to_csv(self.character_output_file, index=False, encoding='utf-8')
            logger.info(f"✅ Saved {len(df_char_final)} characters to {self.character_output_file}")
            logger.info(f"📁 File size: {os.path.getsize(self.character_output_file)} bytes")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving CSV files: {e}")
            return False

    def process(self) -> bool:
        """Main processing function for both characters and series."""
        try:
            logger.info("🚀 Starting character and series processing for new star system...")
            # Load character and anime data
            df_char = self.load_excel_data()
            df_anime = self.load_anime_excel()
            if df_char is None or df_anime is None:
                logger.error("❌ Missing input files!")
                return False
            # Clean character data
            df_char_clean = self.validate_and_clean_data(df_char)
            if df_char_clean.empty:
                logger.error("❌ No valid character data after cleaning!")
                return False
            # Clean and deduplicate anime/series data
            # Map anime_mal.xlsx columns to expected names and new fields
            df_anime['name'] = df_anime['title'].astype(str).str.strip()
            df_anime['english_name'] = df_anime['title_english'].astype(str).str.strip() if 'title_english' in df_anime.columns else ''
            df_anime['image_link'] = df_anime['image_url'].astype(str).str.strip() if 'image_url' in df_anime.columns else ''
            df_anime['studios'] = df_anime['studios'].astype(str).str.strip() if 'studios' in df_anime.columns else ''
            df_anime['genres'] = df_anime['genres'].astype(str).str.strip() if 'genres' in df_anime.columns else ''
            df_anime['synopsis'] = df_anime['synopsis'].astype(str).str.strip() if 'synopsis' in df_anime.columns else ''
            df_anime['favorites'] = pd.to_numeric(df_anime['favorites'], errors='coerce').fillna(0).astype(int) if 'favorites' in df_anime.columns else 0
            df_anime['members'] = pd.to_numeric(df_anime['members'], errors='coerce').fillna(0).astype(int) if 'members' in df_anime.columns else 0
            df_anime['score'] = pd.to_numeric(df_anime['score'], errors='coerce').fillna(0).astype(float) if 'score' in df_anime.columns else 0.0
            # Deduplicate by name
            df_anime = df_anime.drop_duplicates(subset=['name'])
            df_anime = df_anime.reset_index(drop=True)
            df_anime['series_id'] = df_anime.index + 1
            # Map series name to series_id for characters
            char_series_map = {n.strip().lower(): sid for n, sid in zip(df_anime['name'], df_anime['series_id'])}
            df_char_clean['series_id'] = df_char_clean['series'].astype(str).str.strip().str.lower().map(char_series_map)
            missing_series = df_char_clean[df_char_clean['series_id'].isnull()]['series'].unique()
            if len(missing_series) > 0:
                logger.warning(f"⚠️ Some characters have series not found in anime_mal.xlsx: {missing_series}")
                # Optionally, assign a default series_id or drop these rows
                df_char_clean = df_char_clean.dropna(subset=['series_id'])
            df_char_clean['series_id'] = df_char_clean['series_id'].astype(int)
            # Add transformation columns for each character
            logger.info("🛠️ Generating transformation columns for each character...")
            df_char_clean['element'] = df_char_clean.apply(
                lambda row: self.determine_element(row.get('about', ''), row.get('series', ''), row.get('name', '')), axis=1)
            df_char_clean['base_stats'] = df_char_clean.apply(
                lambda row: self.generate_base_stats(row.get('name', ''), row.get('about', ''), row.get('waifu_id', 0), row.get('favorites', 0)), axis=1)
            df_char_clean['favorite_gifts'] = df_char_clean.apply(
                lambda row: self.generate_favorite_gifts(row.get('about', '')), axis=1)
            df_char_clean['special_dialogue'] = [{} for _ in range(len(df_char_clean))]
            # Analyze star system impact
            self.analyze_star_system_impact(df_char_clean)
            # Save both CSVs
            success = self.save_final_csvs(df_char_clean, df_anime)
            if success:
                logger.info("🎉 Character and series processing completed successfully!")
                logger.info(f"📤 Outputs: {self.character_output_file}, {self.anime_output_file}")
            return success
        except Exception as e:
            logger.error(f"❌ Fatal error during processing: {e}")
            return False


def main():
    """Main function."""
    processor = CharacterFinalProcessor()
    success = processor.process()
    
    print("\n" + "="*70)
    print("🌟 CHARACTER FINAL PROCESSOR - NEW STAR SYSTEM")
    print("="*70)
    print("📥 Input:  character_cleaned.xlsx (your manually edited file)")
    print("📤 Output: data/character_final.csv (ready for upload_to_mysql.py)")
    print("")
    print("🎯 New Star System Features:")
    print("  ⭐ 1-3★: Available through direct gacha")
    print("  ⭐ 4-5★: Obtainable only through shard upgrades")
    print("  🔄 Automatic validation and cleaning")
    print("  📊 Rarity distribution analysis")
    print("  ✅ Compatible with upload_to_mysql.py")
    print("")
    print("Required Excel columns:")
    print("  - waifu_id, name, series, genre, rarity, image_url, favorites")
    print("="*70)
    
    if success:
        print("✅ SUCCESS: character_final.csv is ready!")
        print("🚀 Next step: Run upload_to_mysql.py to import to database")
    else:
        print("❌ FAILED: Check the logs above for errors")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
