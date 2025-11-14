#!/usr/bin/env python3
"""Base Processor for multi-media integration.

This module provides the abstract base class that all media processors inherit from,
containing common processing logic extracted from character_edit.py.
"""

import os
import sys
import csv
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.registries.id_manager import IDManager

# Setup logging
logger = logging.getLogger(__name__)


class BaseProcessor(ABC):
    """Abstract base class for all media processors.
    
    This class provides common functionality for processing character and series data
    from different sources while maintaining standardized formats and ID management.
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the base processor.
        
        Args:
            config: Optional configuration dictionary for the processor
        """
        self.config = config or {}
        self.id_manager = IDManager()
        
        # Gender filtering data (extracted from character_edit.py)
        self.gender_file = os.path.join("data", "characters.csv")
        self.gender_lookup = self._load_gender_data()
        
        logger.info("Initialized %s processor", self.__class__.__name__)

    # ===== ABSTRACT METHODS (must be implemented by subclasses) =====
    
    @abstractmethod
    def get_source_type(self) -> str:
        """Return the source type identifier (e.g., 'mal', 'vndb', 'genshin').
        
        Returns:
            Source type string used for ID management and standardization
        """
        pass
        
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if processor is properly configured and can run.
        
        Returns:
            True if processor can run, False otherwise
        """
        pass
        
    @abstractmethod
    async def pull_raw_data(self) -> Tuple[List[Dict], List[Dict]]:
        """Pull raw data from source.
        
        Returns:
            Tuple of (raw_series_list, raw_characters_list)
        """
        pass

    # ===== GENDER FILTERING (extracted from character_edit.py) =====
    
    def _load_gender_data(self) -> Dict[str, List[int]]:
        """Load gender data from data/characters.csv for filtering male characters.
        
        This is extracted directly from CharacterEditor.load_gender_data()
        """
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
                            
            logger.info("Loaded gender data for %d character names", len(gender_lookup))
        except FileNotFoundError:
            logger.warning("Gender file %s not found - no gender filtering will be applied", self.gender_file)
        except Exception as e:
            logger.warning("Error loading gender data: %s", e)
        return gender_lookup

    def is_female_character(self, character_name: str) -> bool:
        """Check if a character is female based on gender data.
        
        Extracted directly from CharacterEditor.is_female_character()
        
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
        
        # If all instances are male, exclude the character
        if all(sex in male_values for sex in sex_values):
            return False
            
        # If any instance is female or has mixed genders, include the character
        return True

    # ===== RARITY ASSIGNMENT (extracted from character_edit.py) =====
    
    def determine_rarity(self, character: Dict[str, Any]) -> int:
        """Determine character rarity based on favorites count.
        
        Extracted directly from CharacterEditor.determine_rarity()
        Uses the NEW STAR SYSTEM (1-3 stars only for direct gacha).
        """
        favorites = int(character.get("favorites", 0))
        
        # New star system: Only assign 1-3 stars for gacha
        # 4-6 stars will be achieved through upgrade system
        if favorites >= 2000:
            return 3  # 3-star (rare) - highest direct gacha tier
        elif favorites >= 500:
            return 2  # 2-star (uncommon)
        else:
            return 1  # 1-star (common)

    # ===== ABSTRACT PROCESSING METHODS (must be implemented by subclasses) =====
    
    @abstractmethod
    def standardize_series_data(self, raw_series: Dict) -> Dict:
        """Standardize series data to common format.
        
        Args:
            raw_series: Raw series dictionary from source
            
        Returns:
            Standardized series dictionary
        """
        pass
        
    @abstractmethod
    def standardize_character_data(self, raw_character: Dict) -> Dict:
        """Standardize character data to common format.
        
        Args:
            raw_character: Raw character dictionary from source
            
        Returns:
            Standardized character dictionary
        """
        pass
    
    # ===== COMMON PROCESSING WORKFLOW (uses abstract methods) =====
    
    def process_series(self, raw_series: List[Dict]) -> List[Dict]:
        """Process and standardize series data with ID assignment.
        
        Args:
            raw_series: List of raw series dictionaries from source
            
        Returns:
            List of processed series with unique IDs assigned
        """
        processed_series = []
        source_type = self.get_source_type()
        
        logger.info("Processing %d raw series from %s", len(raw_series), source_type)
        
        for i, series in enumerate(raw_series, 1):
            logger.debug("Processing series %d/%d", i, len(raw_series))
            
            try:
                # Standardize using subclass implementation
                std_data = self.standardize_series_data(series)
                
                # Add processing timestamp for tracking new vs existing
                from datetime import datetime
                std_data['processed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # NOTE: Unique ID assignment happens later in process_character_final.py
                
                processed_series.append(std_data)
                logger.debug("Processed series: %s (source: %s)", std_data['name'], std_data['source_id'])
                
            except Exception as e:
                logger.error("Error processing series %s: %s", series.get('name', 'Unknown'), e)
                continue
        
        logger.info("Successfully processed %d/%d series", len(processed_series), len(raw_series))
        return processed_series
        
    def process_characters(self, raw_characters: List[Dict]) -> List[Dict]:
        """Process and standardize character data with ID assignment.
        
        This method uses the abstract standardize_character_data() method that each
        subclass must implement, combined with rarity assignment.
        
        Note: Gender filtering is now only applied in AnimeProcessor, not in base class.
        
        Args:
            raw_characters: List of raw character dictionaries from source
            
        Returns:
            List of processed characters with unique IDs assigned
        """
        processed_characters = []
        source_type = self.get_source_type()
        
        logger.info("Processing %d raw characters from %s", len(raw_characters), source_type)
        
        # Process each character (no gender filtering in base class)
        characters_to_process = raw_characters
        for i, character in enumerate(characters_to_process, 1):
            character_name = character.get("name", "Unknown")
            logger.debug("Processing character %d/%d: %s", i, len(characters_to_process), character_name)
            
            try:
                # Standardize using subclass implementation
                std_data = self.standardize_character_data(character)
                
                # Assign rarity based on favorites (extracted from character_edit.py)
                std_data['rarity'] = self.determine_rarity(std_data)
                
                # Add processing timestamp for tracking new vs existing
                from datetime import datetime
                std_data['processed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # NOTE: Unique ID assignment happens later in process_character_final.py
                
                processed_characters.append(std_data)
                logger.debug("Processed character: %s (source: %s, series: %s)", 
                           character_name, std_data['source_id'], std_data.get('series', 'Unknown'))
                
            except Exception as e:
                logger.error("Error processing character %s: %s", character_name, e)
                continue
        
        logger.info("Successfully processed %d/%d characters", len(processed_characters), len(characters_to_process))
        return processed_characters

    # ===== MAIN PROCESSING WORKFLOW =====
    
    async def pull_and_process(self) -> Tuple[List[Dict], List[Dict]]:
        """Main entry point: pull raw data and process it.
        
        Returns:
            Tuple of (processed_characters, processed_series)
        """
        if not self.is_configured():
            logger.warning("%s processor is not configured - skipping", self.__class__.__name__)
            return [], []
        
        try:
            logger.info("🚀 Starting %s data collection and processing...", self.get_source_type().upper())
            
            # Pull raw data from source (async)
            raw_series, raw_chars = await self.pull_raw_data()
            logger.info("Pulled %d series and %d characters from %s", 
                       len(raw_series), len(raw_chars), self.get_source_type())
            
            # Process the data (sync)
            processed_series = self.process_series(raw_series)
            processed_chars = self.process_characters(raw_chars)
            
            logger.info("✅ %s processing complete: %d characters, %d series", 
                       self.get_source_type().upper(), len(processed_chars), len(processed_series))
            
            return processed_chars, processed_series
            
        except Exception as e:
            logger.error("❌ Error during %s processing: %s", self.get_source_type(), e)
            return [], []

    # ===== UTILITY METHODS =====
    
    def save_debug_output(self, characters: List[Dict], series: List[Dict], 
                         output_dir: str = "data/intermediate") -> bool:
        """Save processed data to debug files for inspection.
        
        Args:
            characters: Processed characters list
            series: Processed series list
            output_dir: Directory to save debug files
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            source_type = self.get_source_type()
            
            # Save characters
            if characters:
                char_file = os.path.join(output_dir, f"debug_{source_type}_characters.csv")
                with open(char_file, 'w', encoding='utf-8', newline='') as f:
                    if characters:
                        writer = csv.DictWriter(f, fieldnames=characters[0].keys())
                        writer.writeheader()
                        writer.writerows(characters)
                logger.info("Saved debug character data to %s", char_file)
            
            # Save series
            if series:
                series_file = os.path.join(output_dir, f"debug_{source_type}_series.csv")
                with open(series_file, 'w', encoding='utf-8', newline='') as f:
                    if series:
                        writer = csv.DictWriter(f, fieldnames=series[0].keys())
                        writer.writeheader()
                        writer.writerows(series)
                logger.info("Saved debug series data to %s", series_file)
            
            return True
            
        except Exception as e:
            logger.error("Error saving debug output: %s", e)
            return False

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics for this processor.
        
        Returns:
            Dictionary with processing statistics
        """
        return {
            'source_type': self.get_source_type(),
            'configured': self.is_configured(),
            'gender_filter_loaded': bool(self.gender_lookup),
            'gender_entries': len(self.gender_lookup),
            'id_manager_status': 'initialized'
        }

    # ===== ASYNC CONTEXT MANAGER (for proper session cleanup) =====
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit.
        
        Base implementation does nothing - subclasses should override
        to implement proper cleanup (e.g., closing HTTP sessions).
        """
        pass


# ===== TESTING =====

class TestProcessor(BaseProcessor):
    """Test implementation of BaseProcessor for testing."""
    
    def __init__(self):
        super().__init__({'test': True})
    
    def get_source_type(self) -> str:
        return "test"
    
    def is_configured(self) -> bool:
        return True
    
    def standardize_series_data(self, raw_series: Dict) -> Dict:
        """Test implementation of series standardization."""
        return {
            'source_type': 'test',
            'source_id': str(raw_series.get('id', 999)),
            'name': raw_series.get('title', 'Test Series'),
            'english_name': raw_series.get('title_english', ''),
            'creator': '{"studio": "Test Studio"}',
            'media_type': 'anime',
            'image_link': '',
            'genres': 'Action|Comedy',
            'synopsis': raw_series.get('synopsis', ''),
            'favorites': raw_series.get('favorites', 0),
            'members': raw_series.get('members', 0),
            'score': raw_series.get('score', 0.0)
        }
    
    def standardize_character_data(self, raw_character: Dict) -> Dict:
        """Test implementation of character standardization."""
        return {
            'source_type': 'test',
            'source_id': str(raw_character.get('id', 9999)),
            'name': raw_character.get('name', 'Test Character'),
            'series': 'Test Series',
            'series_source_id': str(raw_character.get('series_mal_id', 999)),
            'genre': 'anime',
            'image_url': raw_character.get('image_url', ''),
            'about': raw_character.get('about', ''),
            'favorites': raw_character.get('favorites', 0)
        }
    
    async def pull_raw_data(self) -> Tuple[List[Dict], List[Dict]]:
        # Test data mimicking MAL format with proper source IDs
        test_series = [{
            "mal_id": 999,
            "id": 999,  # Add source_id field
            "title": "Test Anime",
            "title_english": "Test Anime EN",
            "synopsis": "A test anime for testing",
            "score": 8.5,
            "favorites": 1000,
            "members": 50000,
            "studios": "Test Studio",
            "genres": "Action|Comedy"
        }]
        
        test_characters = [{
            "mal_id": 9999,
            "id": 9999,  # Add source_id field
            "name": "Test Character",
            "about": "A test character",
            "favorites": 1500,
            "series_type": "anime",
            "series_mal_id": 999,
            "image_url": "https://example.com/test.jpg"
        }]
        
        return test_series, test_characters


async def test_base_processor():
    """Test the base processor functionality."""
    print("Testing Base Processor...")
    
    # Create test processor
    processor = TestProcessor()
    
    # Check stats
    stats = processor.get_processing_stats()
    print(f"Processor stats: {stats}")
    
    # Test processing
    characters, series = await processor.pull_and_process()
    print(f"Processed: {len(characters)} characters, {len(series)} series")
    
    if characters:
        print("Sample character:")
        for key, value in characters[0].items():
            print(f"  {key}: {value}")
    
    if series:
        print("Sample series:")
        for key, value in series[0].items():
            print(f"  {key}: {value}")
    
    # Test debug output
    processor.save_debug_output(characters, series)
    
    print("✅ Base Processor test completed!")


if __name__ == "__main__":
    # Test the base processor
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    
    asyncio.run(test_base_processor())