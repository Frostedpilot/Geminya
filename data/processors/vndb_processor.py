#!/usr/bin/env python3
"""VNDB Processor for Visual Novel Database data collection and processing.

This module handles visual novel data collection from VNDB API,
requiring configuration for series IDs to crawl.
"""

import asyncio
import aiohttp
import json
import os
import sys
import logging
from typing import List, Dict, Optional, Tuple, Any, Set
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data.processors.base_processor import BaseProcessor

# Setup logging
logger = logging.getLogger(__name__)


class VNDBProcessor(BaseProcessor):
    """Processor for VNDB visual novel data collection and processing.
    
    This processor handles:
    1. VNDB API authentication (if needed)
    2. Fetching specified visual novel data by IDs
    3. Getting character information from visual novels
    4. Applying visual novel-specific filtering and processing
    
    Requires configuration with series IDs to process.
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the VNDB processor.
        
        Args:
            config: Configuration dictionary with vndb_series_ids list
        """
        super().__init__(config)
        
        # VNDB API endpoint
        self.base_url = "https://api.vndb.org/kana"
        
        # Track processed IDs to avoid duplicates within this session
        self.processed_character_ids: Set[str] = set()
        self.processed_vn_ids: Set[str] = set()
        
        # Load existing VNDB IDs from lookup files
        self.existing_vn_ids = self._load_existing_vn_ids()
        self.existing_character_ids = self._load_existing_character_ids()
        
        # HTTP session for API requests
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Load series IDs from config
        self.series_ids_to_process = self.config.get('vndb_series_ids', [])
        
        logger.info("Initialized VNDB processor with %d series IDs to process", 
                   len(self.series_ids_to_process))

    # ===== ABSTRACT METHOD IMPLEMENTATIONS =====
    
    def get_source_type(self) -> str:
        """Return the source type identifier for VNDB."""
        return "vndb"
    
    def is_configured(self) -> bool:
        """Check if processor is properly configured with series IDs."""
        return bool(self.series_ids_to_process)

    def standardize_series_data(self, raw_series: Dict) -> Dict:
        """Standardize VNDB visual novel data to common format."""
        # Filter tags to get only theme tags based on VNDB theme hierarchy
        theme_tags = self._extract_theme_tags(raw_series.get('tags', []))
        
        # Extract developer names from the developers array and format as JSON
        developers = raw_series.get('developers', [])
        developer_names = []
        for dev in developers:
            if isinstance(dev, dict) and 'name' in dev:
                developer_names.append(dev['name'])
        
        # Format creator as JSON to match anime/manga format
        if developer_names:
            creator_json = json.dumps({"developer": '|'.join(developer_names)})
        else:
            creator_json = json.dumps({"developer": "Unknown"})
        
        return {
            'source_type': 'vndb',
            'source_id': str(raw_series.get('id', '')),
            'name': raw_series.get('title', 'Unknown'),
            'english_name': '',  # Make english_name blank as requested
            'creator': creator_json,  # JSON format to match anime/manga
            'media_type': 'visual_novel',
            'image_link': raw_series.get('image', {}).get('url', ''),
            'genres': '|'.join(theme_tags),  # Major theme tags with pipe separator (same as anime/manga)
            'synopsis': raw_series.get('description', ''),
            'favorites': 0,  # popularity field deprecated
            'members': raw_series.get('votecount', 0),
            'score': raw_series.get('rating', 0.0)
        }

    def standardize_character_data(self, raw_character: Dict) -> Dict:
        """Standardize VNDB character data to common format."""
        # Series data should be stored in raw_character['series_data'] by pull_raw_data
        series_data = raw_character.get('series_data', {}) or {}
        
        # Add (VN) suffix to character name to differentiate from other media versions
        character_name = raw_character.get('name', 'Unknown')
        if character_name != 'Unknown' and not character_name.endswith('(VN)'):
            character_name = f"{character_name} (VN)"
        
        # Safely get image URL
        image_data = raw_character.get('image') or {}
        image_url = image_data.get('url', '') if isinstance(image_data, dict) else ''
        
        return {
            'source_type': 'vndb',
            'source_id': str(raw_character.get('id', '')),
            'name': character_name,  # Now includes (VN) suffix
            'series': series_data.get('title', 'Unknown') if series_data else 'Unknown',
            'series_source_id': str(series_data.get('id', '')) if series_data else '',
            'genre': 'Visual Novel',  # Display text for UI
            'rarity': self._calculate_character_rarity(raw_character),
            'image_url': image_url,
            'about': raw_character.get('description', ''),
            'favorites': 0  # VNDB API doesn't provide character favorites/popularity data
        }

    def process_characters(self, raw_characters: List[Dict]) -> List[Dict]:
        """Process and filter VNDB characters based on sex field.
        
        Override base method to apply VNDB-specific sex-based filtering.
        """
        logger.info("Processing %d raw characters from %s", len(raw_characters), self.get_source_type())
        
        processed_characters = []
        filtered_out_count = 0
        
        for raw_character in raw_characters:
            try:
                # Apply sex-based filtering for VNDB characters
                sex_data = raw_character.get('sex')
                if sex_data is not None and isinstance(sex_data, list) and len(sex_data) >= 1:
                    # Use non-spoiler sex (first element)
                    sex = sex_data[0]
                    if sex == 'm':  # Skip explicitly male characters
                        char_name = raw_character.get('name', 'Unknown')
                        logger.debug("Filtering out male character: %s", char_name)
                        filtered_out_count += 1
                        continue
                
                # Standardize and add to processed list
                standardized = self.standardize_character_data(raw_character)
                
                processed_characters.append(standardized)
                
            except Exception as e:
                char_name = raw_character.get('name', 'Unknown')
                logger.error("Error processing character %s: %s", char_name, e)
                continue
        
        logger.info("Successfully processed %d/%d characters (%d filtered out by sex)", 
                   len(processed_characters), len(raw_characters), filtered_out_count)
        return processed_characters

    async def pull_raw_data(self) -> Tuple[List[Dict], List[Dict]]:
        """Pull data from VNDB API for configured series IDs."""
        if not self.is_configured():
            logger.warning("VNDB processor not configured - no series IDs provided")
            return [], []
        series_data = []
        character_data = []

        async with aiohttp.ClientSession() as session:
            for i, vn_id in enumerate(self.series_ids_to_process, 1):
                try:
                    # Skip if VN already exists in lookup
                    if self._is_vn_already_mined(vn_id):
                        logger.info("Skipping VN %d/%d: %s - already mined", 
                                   i, len(self.series_ids_to_process), vn_id)
                        continue
                    
                    logger.info("Processing VN %d/%d: %s", i, len(self.series_ids_to_process), vn_id)
                    
                    # Get visual novel data
                    vn_data = await self._fetch_vn_data(vn_id, session)
                    if vn_data:
                        series_data.append(vn_data)
                        self.processed_vn_ids.add(vn_id)
                        
                        # Get characters for this visual novel
                        characters = await self._fetch_vn_characters(vn_id, session)
                        for char in characters:
                            char_id = str(char.get('id', ''))
                            if char_id and char_id not in self.processed_character_ids:
                                char['series_data'] = vn_data
                                character_data.append(char)
                                self.processed_character_ids.add(char_id)
                            elif char_id in self.processed_character_ids:
                                logger.debug("  Skipped character %s - already processed", char_id)
                    
                    # Rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error("Error processing VNDB series %s: %s", vn_id, e)
                    continue

        # Summary statistics
        total_vns_in_config = len(self.series_ids_to_process)
        vns_already_existed = len([vn for vn in self.series_ids_to_process if self._is_vn_already_mined(vn)])
        vns_processed = total_vns_in_config - vns_already_existed

        logger.info("✅ Successfully pulled VNDB data!")
        logger.info("📊 Processing Summary:")
        logger.info("   - Total VNs in config: %d", total_vns_in_config)
        logger.info("   - VNs already mined (skipped): %d", vns_already_existed)
        logger.info("   - VNs processed: %d", vns_processed)
        logger.info("   - New VNs pulled: %d", len(series_data))
        logger.info("   - New characters pulled: %d", len(character_data))
        
        if vns_processed > len(series_data):
            logger.warning("⚠️  %d VNs were processed but not added (likely due to API errors)", 
                         vns_processed - len(series_data))
        
        # Update lookup files with all processed IDs (including filtered ones)
        # This prevents re-scraping both successful and filtered data
        logger.info("🔄 Updating lookup files...")
        self._update_lookup_files(self.processed_vn_ids, self.processed_character_ids)
        
        logger.info("VNDB data collection complete: %d series, %d characters", 
                   len(series_data), len(character_data))
        return series_data, character_data

    # ===== VNDB API METHODS =====

    async def _fetch_vn_data(self, vn_id: str, session: aiohttp.ClientSession) -> Optional[Dict]:
        """Fetch visual novel data from VNDB API."""
        try:
            url = f"{self.base_url}/vn"
            
            # VNDB API v2 uses POST with JSON data, not GET with params
            request_data = {
                'filters': ["id", "=", vn_id],
                'fields': 'id,title,alttitle,description,image{url},developers{name},tags{id,name,category},votecount,rating'
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Geminya/1.0 (https://github.com/Frostedpilot/Geminya)'
            }
            
            async with session.post(url, json=request_data, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('results', [])
                    if results:
                        logger.debug("Successfully fetched VNDB data for: %s", results[0].get('title', vn_id))
                        return results[0]
                    else:
                        logger.warning("No VNDB data found for VN ID: %s", vn_id)
                        
                elif response.status == 429:  # Rate limited
                    logger.warning("VNDB API rate limit hit, waiting...")
                    await asyncio.sleep(2.0)
                    # Try once more
                    async with session.post(url, json=request_data, headers=headers) as retry_response:
                        if retry_response.status == 200:
                            data = await retry_response.json()
                            results = data.get('results', [])
                            if results:
                                return results[0]
                        else:
                            logger.error("VNDB API still failing after retry for VN %s: %d", 
                                       vn_id, retry_response.status)
                else:
                    logger.error("VNDB API error for VN %s: %d", vn_id, response.status)
                    
        except Exception as e:
            logger.error("Error fetching VNDB VN %s: %s", vn_id, e)
        
        return None

    async def _fetch_vn_characters(self, vn_id: str, session: aiohttp.ClientSession) -> List[Dict]:
        """Fetch character data for a visual novel from VNDB API."""
        try:
            url = f"{self.base_url}/character"
            
            # VNDB API v2 uses POST with JSON data
            request_data = {
                'filters': ["vn", "=", ["id", "=", vn_id]],
                'fields': 'id,name,description,image{url},sex,traits{id}',
                'results': 100  # Get up to 100 characters (default is only 10)
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Geminya/1.0 (https://github.com/Frostedpilot/Geminya)'
            }
            
            async with session.post(url, json=request_data, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    characters = data.get('results', [])
                    
                    # Return ALL characters in raw data - filtering happens during processing
                    logger.debug("VNDB characters for %s: %d total characters found", 
                               vn_id, len(characters))
                    return characters
                    
                elif response.status == 429:  # Rate limited
                    logger.warning("VNDB API rate limit hit, waiting longer...")
                    await asyncio.sleep(2.0)  # Wait longer and retry once
                    async with session.post(url, json=request_data, headers=headers) as retry_response:
                        if retry_response.status == 200:
                            data = await retry_response.json()
                            return data.get('results', [])
                        else:
                            logger.error("VNDB API still failing after retry for VN %s: %d", 
                                       vn_id, retry_response.status)
                else:
                    logger.error("VNDB API error for characters of VN %s: %d", vn_id, response.status)
                    
        except Exception as e:
            logger.error("Error fetching VNDB characters for VN %s: %s", vn_id, e)
        
        return []

    def _extract_theme_tags(self, tags: List[Dict]) -> List[str]:
        """Extract only major theme tags from VNDB tag data.
        
        Returns only the main theme categories (Drama, Fantasy, Romance, etc.)
        and excludes child/specific tags.
        
        Args:
            tags: List of tag objects from VNDB API
            
        Returns:
            List of major theme tag names
        """
        # Major theme categories only - no child tags
        major_theme_categories = {
            'Drama', 'Fantasy', 'Romance', 'Science Fiction', 'Comedy', 
            'Mystery', 'Horror', 'Action', 'Educational', 'Thriller',
            'Sexual Content', 'Slice of Life', 'Adventure', 'Supernatural'
        }
        
        # Child tags to parent mapping - if we find a child tag, include its parent
        child_to_parent_mapping = {
            # Drama children -> Drama
            'Apocalypse': 'Drama', 'Betrayal': 'Drama', 'Bullying': 'Drama', 
            'Child Abuse': 'Drama', 'Coming-of-Age Drama': 'Drama', 'Tragedy': 'Drama', 
            'Psychological Drama': 'Drama',
            
            # Fantasy children -> Fantasy  
            'Alchemy': 'Fantasy', 'Body Swapping': 'Fantasy', 'Contemporary Fantasy': 'Fantasy', 
            'Curse': 'Fantasy', 'Dark Fantasy': 'Fantasy', 'High Fantasy': 'Fantasy', 
            'Magic': 'Fantasy', 'Supernatural': 'Fantasy', 'Mythology': 'Fantasy', 
            'Fairy Tale': 'Fantasy',
            
            # Romance children -> Romance
            'Both Male and Female Love Interests': 'Romance', 'Boy x Boy Romance': 'Romance', 
            'Girl x Girl Romance': 'Romance', 'Forbidden Love': 'Romance', 'Elopement': 'Romance', 
            'Tragic Love': 'Romance', 'Childhood Friend Romance': 'Romance', 'Love Triangle': 'Romance', 
            'Romantic Comedy': 'Romance', 'Harem': 'Romance',
            
            # Science Fiction children -> Science Fiction
            'Alternate Dimensions': 'Science Fiction', 'Artificial Intelligence': 'Science Fiction', 
            'Cyberpunk': 'Science Fiction', 'Genetic Research': 'Science Fiction', 
            'Hard Science Fiction': 'Science Fiction', 'Time Travel': 'Science Fiction', 
            'Space Opera': 'Science Fiction', 'Post-Apocalyptic': 'Science Fiction', 
            'Dystopia': 'Science Fiction', 'Robots': 'Science Fiction',
            
            # Mystery children -> Mystery
            'Amnesia': 'Mystery', 'Detective Work': 'Mystery', 'Disappearance': 'Mystery', 
            'Existential Crisis': 'Mystery', 'Memory Alteration': 'Mystery', 
            'Investigation': 'Mystery', 'Murder Mystery': 'Mystery',
            
            # Horror children -> Horror
            'Body Horror': 'Horror', 'Haunted House': 'Horror', 'Jump Scares': 'Horror', 
            'Lovecraftian Horror': 'Horror', 'Psychological Horror': 'Horror', 
            'Supernatural Horror': 'Horror', 'Gore': 'Horror',
            
            # Action children -> Action
            'Combat': 'Action', 'Sports': 'Action', 'War': 'Action', 'Martial Arts': 'Action', 
            'Military': 'Action', 'Fighting': 'Action',
            
            # Comedy children -> Comedy
            'Absurdist Comedy': 'Comedy', 'Black Comedy': 'Comedy', 'Comedic Love Triangle': 'Comedy', 
            'Family Life Comedy': 'Comedy', 'Parody': 'Comedy', 'Slapstick': 'Comedy'
        }
        
        # Collect major themes
        found_themes = set()
        
        for tag in tags:
            tag_name = tag.get('name', '')
            
            # Check if it's a major theme category
            if tag_name in major_theme_categories:
                found_themes.add(tag_name)
            
            # Check if it's a child tag and map to parent
            elif tag_name in child_to_parent_mapping:
                parent_theme = child_to_parent_mapping[tag_name]
                found_themes.add(parent_theme)
        
        return list(found_themes)

    def _calculate_character_rarity(self, character_data: Dict) -> int:
        """Calculate character rarity based on VNDB data."""
        # VNDB characters don't have votecount, use description length and traits as indicators
        description = character_data.get('description', '')
        traits = character_data.get('traits', [])
        
        # Characters with more detailed descriptions and traits are likely more important
        description_length = len(description) if description else 0
        trait_count = len(traits) if traits else 0
        
        # Rarity calculation based on available data
        if description_length > 500 and trait_count >= 10:
            return 5  # SSR - Very detailed character
        elif description_length > 200 and trait_count >= 5:
            return 4  # SR - Well-developed character
        elif description_length > 50 and trait_count >= 3:
            return 3  # R - Moderate detail
        elif description_length > 0 or trait_count > 0:
            return 2  # N - Some detail
        else:
            return 1  # Common - Minimal info

    def _load_config_from_file(self, config_file: str) -> Dict:
        """Load VNDB configuration from file."""
        config_path = f"data/input_sources/configs/{config_file}"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                logger.info("Loaded VNDB config from %s", config_path)
                return config_data
        except FileNotFoundError:
            logger.warning("VNDB config file not found: %s", config_path)
            logger.info("Run 'python data/processors/vndb_processor.py' to create template")
            return {}
        except Exception as e:
            logger.error("Error loading VNDB config from %s: %s", config_path, e)
            return {}

    @classmethod
    def from_config_file(cls, config_file: str = "vndb_config.json"):
        """Create VNDB processor from configuration file.
        
        Args:
            config_file: Name of config file in data/input_sources/configs/
            
        Returns:
            Configured VNDBProcessor instance
        """
        processor = cls()
        config = processor._load_config_from_file(config_file)
        processor.config.update(config)
        processor.series_ids_to_process = config.get('vndb_series_ids', [])
        
        logger.info("Loaded VNDB processor from config with %d series IDs", 
                   len(processor.series_ids_to_process))
        return processor

    # ===== ID LOOKUP FILE MANAGEMENT =====
    
    def _load_existing_vn_ids(self) -> Set[str]:
        """Load existing VN IDs from lookup file to avoid re-scraping."""
        try:
            lookup_file = Path("data/registries/vndb/existing_vn_ids.json")
            if lookup_file.exists():
                with open(lookup_file, 'r', encoding='utf-8') as f:
                    ids = json.load(f)
                logger.info("Loaded %d existing VN IDs from lookup file", len(ids))
                return set(ids)
            else:
                logger.info("No existing VN lookup file found - creating new one")
                # Create directory and empty file
                lookup_file.parent.mkdir(parents=True, exist_ok=True)
                with open(lookup_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                return set()
        except Exception as e:
            logger.error("Error loading VN lookup file: %s", e)
            return set()

    def _load_existing_character_ids(self) -> Set[str]:
        """Load existing character IDs from lookup file to avoid re-scraping."""
        try:
            lookup_file = Path("data/registries/vndb/existing_character_ids.json")
            if lookup_file.exists():
                with open(lookup_file, 'r', encoding='utf-8') as f:
                    ids = json.load(f)
                logger.info("Loaded %d existing character IDs from VNDB lookup file", len(ids))
                return set(ids)
            else:
                logger.info("No existing VNDB character lookup file found - creating new one")
                # Create directory and empty file
                lookup_file.parent.mkdir(parents=True, exist_ok=True)
                with open(lookup_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                return set()
        except Exception as e:
            logger.error("Error loading VNDB character lookup file: %s", e)
            return set()
    
    def _is_vn_already_mined(self, vn_id: str) -> bool:
        """Check if VN is already mined using lookup file."""
        return vn_id in self.existing_vn_ids
    
    def _is_character_already_mined(self, character_id: str) -> bool:
        """Check if character is already mined using lookup file."""
        return character_id in self.existing_character_ids
    
    def _update_lookup_files(self, processed_vn_ids: Set[str], processed_character_ids: Set[str]) -> None:
        """Update lookup files with newly processed IDs to prevent re-scraping."""
        try:
            # Update VN lookup file
            updated_vn_ids = self.existing_vn_ids.union(processed_vn_ids)
            vn_lookup_file = Path("data/registries/vndb/existing_vn_ids.json")
            with open(vn_lookup_file, 'w', encoding='utf-8') as f:
                json.dump(sorted(list(updated_vn_ids)), f, indent=2)
            logger.info("Updated VN lookup: added %d new VN IDs (total: %d)", 
                       len(processed_vn_ids), len(updated_vn_ids))
            
            # Update character lookup file  
            updated_character_ids = self.existing_character_ids.union(processed_character_ids)
            character_lookup_file = Path("data/registries/vndb/existing_character_ids.json")
            with open(character_lookup_file, 'w', encoding='utf-8') as f:
                json.dump(sorted(list(updated_character_ids)), f, indent=2)
            logger.info("Updated VNDB character lookup: added %d new character IDs (total: %d)", 
                       len(processed_character_ids), len(updated_character_ids))
                       
        except Exception as e:
            logger.error("Error updating VNDB lookup files: %s", e)

    # ===== UTILITY METHODS =====
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics for this processor."""
        return {
            'processor_type': 'VNDBProcessor',
            'source_type': self.get_source_type(),
            'is_configured': self.is_configured(),
            'series_ids_to_process': len(self.series_ids_to_process),
            'existing_vn_ids_loaded': len(self.existing_vn_ids),
            'existing_characters_loaded': len(self.existing_character_ids),
            'processed_vn_ids': len(self.processed_vn_ids),
            'processed_character_ids': len(self.processed_character_ids)
        }

    # ===== ASYNC CONTEXT MANAGER SUPPORT =====
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # VNDB processor uses local sessions with 'async with' pattern
        # so no cleanup needed here - sessions are automatically managed
        pass


# ===== CONVENIENCE FUNCTIONS =====

def create_vndb_config_template(output_file: str = "vndb_config.json"):
    """Create a template VNDB configuration file.
    
    Args:
        output_file: Output filename in data/input_sources/configs/
    """
    template_config = {
        "vndb_series_ids": [
            "v17",      # Fate/stay night
            "v11",      # Katawa Shoujo  
            "v24",      # Tsukihime
            "v4",       # Planetarian
            "v36"       # Narcissu
        ],
        "description": "Configuration for VNDB processor - add VNDB series IDs to crawl",
        "usage": "Each ID should be a VNDB visual novel ID (e.g., 'v17' for Fate/stay night)"
    }
    
    output_path = f"data/input_sources/configs/{output_file}"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(template_config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created VNDB config template: {output_path}")
    print("📝 Edit this file to add the VNDB series IDs you want to process")



# ===== TESTING =====

async def test_vndb_processor():
    """Test the VNDB processor."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    
    print("Testing VNDB Processor...")
    
    try:
        # Test with sample config
        test_config = {"vndb_series_ids": ["v17", "v11"]}  # Small test set
        
        async with VNDBProcessor(test_config) as processor:
            # Check configuration
            print(f"Configured: {processor.is_configured()}")
            print(f"Source type: {processor.get_source_type()}")
            print(f"Series IDs: {processor.series_ids_to_process}")
            
            # Note: Full testing requires API calls
            # For now, just test initialization
            print("✅ VNDB Processor initialization test completed!")
            
    except Exception as e:
        print(f"❌ Error testing VNDB processor: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run test mode
        import asyncio
        asyncio.run(test_vndb_processor())
    else:
        # Create config template if run directly
        create_vndb_config_template()