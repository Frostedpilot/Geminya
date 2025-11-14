#!/usr/bin/env python3
"""Stella Sora (SS) Processor for game character data collection.

This processor crawls the Stella Sora wiki for character information and
supports manual data input. It always re-crawls data on each run.
"""

import asyncio
import aiohttp
import json
import os
import sys
import logging
import re
import time
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from urllib.parse import urljoin

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data.processors.base_processor import BaseProcessor

# Setup logging
logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
except ImportError:
    logger.error("BeautifulSoup4 is required. Install with: pip install beautifulsoup4")
    raise


class SSProcessor(BaseProcessor):
    """Processor for Stella Sora game character data collection and processing.
    
    This processor handles:
    1. Web crawling of Stella Sora wiki character pages
    2. Loading manual character data from JSON files
    3. Merging and standardizing all character data
    4. Always re-crawls fresh data (no lookup files)
    
    The processor creates a single series entry for "Stella Sora" and 
    multiple character entries with SS-prefixed IDs.
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the SS processor."""
        super().__init__(config)
        
        # Wiki configuration
        self.characters_page_url = "https://stellasora.miraheze.org/wiki/Characters"
        
        # Manual data configuration  
        self.manual_data_file = Path("data/input_sources/ss_manual_data.json")
        
        # HTTP session for requests (will be set during execution)
        self.session = None
        
        logger.info("Initialized SS processor for Stella Sora")

    # ===== ABSTRACT METHOD IMPLEMENTATIONS =====
    
    def get_source_type(self) -> str:
        """Return the source type identifier for SS."""
        return "ss"
    
    def is_configured(self) -> bool:
        """SS processor is always configured (uses hardcoded URLs)."""
        return True

    def standardize_series_data(self, raw_series: Dict) -> Dict:
        """Standardize Stella Sora game data to common format."""
        return {
            'source_type': 'ss',
            'source_id': 'ss',  # Single series ID
            'name': 'Stella Sora',
            'english_name': 'Stella Sora',
            'creator': json.dumps({"developer":"Yostar","publisher":"Yostar"}),
            'media_type': 'game',
            'image_link': 'https://webusstatic.yo-star.com/web-cms-prod/upload/content/2025/05/29/jDbKDLEc.jpeg',
            'genres': 'Fantasy|Adventure',  # Simple game genre
            'synopsis': 'Stella Sora is a game featuring various characters.',
            'favorites': 0,
            'members': 0,
            'score': 0.0
        }

    def standardize_character_data(self, raw_character: Dict) -> Dict:
        """Standardize SS character data to common format."""
        # Generate character ID from name
        character_name = raw_character.get('name', 'Unknown')
        character_id = self._generate_character_id(character_name)
        
        # Extract image URL from profile_image_link
        image_url = raw_character.get('profile_image_link', '')
        
        return {
            'source_type': 'ss',
            'source_id': character_id,
            'name': character_name,
            'series': 'Stella Sora',
            'series_source_id': 'ss',
            'genre': 'Game',  # Character genre
            'rarity': 3,  # Default middle rarity
            'image_url': image_url,
            'about': raw_character.get('profile', ''),
            'favorites': 0  # No favorites data available
        }

    async def pull_raw_data(self) -> Tuple[List[Dict], List[Dict]]:
        """Pull data from Stella Sora wiki and manual sources."""
        logger.info("Starting SS data collection from wiki and manual sources")
        
        # Series data - single entry for Stella Sora
        series_data = [{'name': 'Stella Sora', 'type': 'game'}]
        character_data = []
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            # Get wiki character data
            wiki_characters = await self._crawl_wiki_characters()
            logger.info(f"Crawled {len(wiki_characters)} characters from wiki")
            
            # Get manual character data
            manual_characters = self._load_manual_data()
            logger.info(f"Loaded {len(manual_characters)} characters from manual data")
            
            # Merge data (manual overrides wiki by name)
            merged_characters = self._merge_character_data(wiki_characters, manual_characters)
            logger.info(f"Total characters after merge: {len(merged_characters)}")
            
            character_data = merged_characters
        
        logger.info("SS data collection complete: 1 series, %d characters", len(character_data))
        return series_data, character_data

    # ===== STELLA SORA WIKI CRAWLING METHODS =====

    async def _crawl_wiki_characters(self) -> List[Dict]:
        """Crawl character data from Stella Sora wiki."""
        try:
            # Get character URLs from main page
            character_urls = await self._get_character_links()
            logger.info(f"Found {len(character_urls)} character links")
            
            if not character_urls:
                logger.warning("No character links found on wiki")
                return []
            
            # Crawl each character page
            characters = []
            for i, url in enumerate(character_urls, 1):
                logger.info(f"Crawling character {i}/{len(character_urls)}: {url}")
                
                character_data = await self._get_character_info(url)
                if character_data:
                    characters.append(character_data)
                
                # Be polite to the server
                await asyncio.sleep(1.0)
            
            return characters
            
        except Exception as e:
            logger.error(f"Error crawling wiki characters: {e}")
            return []

    async def _get_character_links(self) -> List[str]:
        """Get character page URLs from the main Characters page."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with self.session.get(self.characters_page_url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch character list page: HTTP {response.status}")
                    return []
                
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Find the main character table
                character_table = soup.select_one('table.wikitable.sortable')
                if not character_table:
                    logger.error("Could not find the character table on the page")
                    return []
                
                character_urls = []
                # Find all table rows (tr) within the table, skipping the first one (header row)
                for row in character_table.find_all('tr')[1:]:
                    # The link is in the second table cell (td)
                    cells = row.find_all('td')
                    if len(cells) > 1:  # Ensure the row has enough cells
                        link_tag = cells[1].find('a')
                        if link_tag and link_tag.has_attr('href'):
                            # Join the base URL with the relative href to get the full URL
                            full_url = urljoin(self.characters_page_url, link_tag['href'])
                            character_urls.append(full_url)
                
                return character_urls
                
        except Exception as e:
            logger.error(f"Error getting character links: {e}")
            return []

    async def _get_character_info(self, url: str) -> Optional[Dict]:
        """Scrape character information from a wiki page."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch character page {url}: HTTP {response.status}")
                    return None
                
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                character_info = {'url': url}
                
                # Extract character name
                name_tag = soup.select_one('h1.firstHeading span.mw-page-title-main')
                character_info['name'] = name_tag.text.strip() if name_tag else 'Unknown'
                
                # Extract profile image link
                image_link_tag = soup.select_one('.portable-infobox .pi-media-collection-tab-content.current a.image')
                if image_link_tag and image_link_tag.has_attr('href'):
                    character_info['profile_image_link'] = urljoin(url, image_link_tag['href'])
                else:
                    character_info['profile_image_link'] = ''
                
                # Extract birthday
                birthday_label = soup.find('h3', class_='pi-data-label', string='Birthday')
                if birthday_label and birthday_label.find_next_sibling('div', class_='pi-data-value'):
                    character_info['birthday'] = birthday_label.find_next_sibling('div').text.strip()
                else:
                    character_info['birthday'] = ''
                
                # Extract profile description
                profile_article = soup.find('article', id='tabber-English')
                if profile_article:
                    paragraphs = [p.text.strip() for p in profile_article.find_all('p') if p.text.strip()]
                    character_info['profile'] = '\n'.join(paragraphs)
                else:
                    character_info['profile'] = ''
                
                logger.debug(f"Successfully extracted data for character: {character_info['name']}")
                return character_info
                
        except Exception as e:
            logger.warning(f"Error parsing character page {url}: {e}")
            return None

    # ===== MANUAL DATA METHODS =====

    def _load_manual_data(self) -> List[Dict]:
        """Load manual character data from JSON file."""
        try:
            if not self.manual_data_file.exists():
                logger.info(f"No manual data file found at {self.manual_data_file}")
                return []
            
            with open(self.manual_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            characters = data.get('characters', [])
            logger.info(f"Loaded {len(characters)} characters from manual data file")
            return characters
            
        except Exception as e:
            logger.error(f"Error loading manual data: {e}")
            return []

    def _merge_character_data(self, wiki_characters: List[Dict], 
                            manual_characters: List[Dict]) -> List[Dict]:
        """Merge wiki and manual character data, with manual taking precedence."""
        # Create a dictionary of wiki characters by name for easy lookup
        wiki_by_name = {char.get('name', '').lower(): char for char in wiki_characters}
        
        merged_characters = []
        used_wiki_names = set()
        
        # Add manual characters (these take precedence)
        for manual_char in manual_characters:
            char_name = manual_char.get('name', '').lower()
            
            # If there's a wiki character with the same name, merge the data
            if char_name in wiki_by_name:
                wiki_char = wiki_by_name[char_name]
                # Manual data overrides wiki data
                merged_char = {**wiki_char, **manual_char}
                merged_char['source'] = 'manual_override'
                merged_characters.append(merged_char)
                used_wiki_names.add(char_name)
                logger.debug(f"Manual override for character: {manual_char.get('name')}")
            else:
                # Manual-only character
                manual_char['source'] = 'manual_only'
                merged_characters.append(manual_char)
                logger.debug(f"Manual-only character: {manual_char.get('name')}")
        
        # Add remaining wiki characters that weren't overridden
        for wiki_char in wiki_characters:
            char_name = wiki_char.get('name', '').lower()
            if char_name not in used_wiki_names:
                wiki_char['source'] = 'wiki_only'
                merged_characters.append(wiki_char)
        
        return merged_characters

    # ===== UTILITY METHODS =====

    def _generate_character_id(self, character_name: str) -> str:
        """Generate SS character ID from character name."""
        # Sanitize name: lowercase, replace spaces with underscores, remove special chars
        sanitized = re.sub(r'[^a-zA-Z0-9\s]', '', character_name.lower())
        sanitized = re.sub(r'\s+', '_', sanitized.strip())
        
        # Ensure it's not empty
        if not sanitized:
            sanitized = 'unknown'
        
        return f"ss_{sanitized}"


# ===== ASYNC CONTEXT MANAGER SUPPORT =====

    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
        return False