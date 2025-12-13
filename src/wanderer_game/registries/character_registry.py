"""
Character Registry for the Wanderer Game

Manages character data loading and lookups from CSV files.
"""

import csv
from typing import Dict, List, Optional
from pathlib import Path

from ..models import Character


class CharacterRegistry:
    """
    Registry for loading and managing character data
    
    Loads character data from CSV files and provides lookup functionality.
    """
    
    def __init__(self, data_directory: str = "data"):
        self.data_directory = Path(data_directory)
        self.characters: Dict[int, Character] = {}
        self.characters_by_series: Dict[int, List[Character]] = {}
    
    def load_characters(self, filename: str = "final/characters_final.csv") -> bool:
        """
        Load characters from CSV file, using series_final.csv for anime_genres.
        """
        file_path = self.data_directory / filename
        anime_file_path = self.data_directory / "final/series_final.csv"
        anime_genres_map = {}
        # Build anime_genres_map: {series_id: [genres]}
        try:
            with open(anime_file_path, 'r', encoding='utf-8') as af:
                anime_reader = csv.DictReader(af)
                for row in anime_reader:
                    try:
                        sid = int(row['series_id'])
                        genres_str = row.get('genres', '')
                        genres = [g.strip() for g in genres_str.split('|') if g.strip()]
                        anime_genres_map[sid] = genres
                    except Exception as e:
                        print(f"Error parsing anime row {row.get('series_id', 'unknown')}: {e}")
                        continue
        except Exception as e:
            print(f"Warning: Could not load anime genres from {anime_file_path}: {e}")
            anime_genres_map = {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        character = Character.from_csv_row(row, anime_genres_map)
                        self.characters[character.waifu_id] = character
                        # Index by series
                        if character.series_id not in self.characters_by_series:
                            self.characters_by_series[character.series_id] = []
                        self.characters_by_series[character.series_id].append(character)
                    except Exception as e:
                        print(f"Error parsing character row {row.get('waifu_id', 'unknown')}: {e}")
                        continue
            print(f"Loaded {len(self.characters)} characters from {filename}")
            return True
        except FileNotFoundError:
            print(f"Warning: Could not find character file: {file_path}")
            return False
        except Exception as e:
            print(f"Error loading characters: {e}")
            return False
    
    def get_character(self, waifu_id: int) -> Optional[Character]:
        """Get a character by their waifu_id"""
        return self.characters.get(waifu_id)
    
    def get_characters_by_series(self, series_id: int) -> List[Character]:
        """Get all characters from a specific series"""
        return self.characters_by_series.get(series_id, [])
    
    def get_series_name(self, series_id: int) -> Optional[str]:
        """Get the series name for a given series_id"""
        characters = self.get_characters_by_series(series_id)
        if characters:
            return characters[0].series
        return None
    
    def get_all_characters(self) -> List[Character]:
        """Get all loaded characters"""
        return list(self.characters.values())
    
    def search_characters(self, name_query: Optional[str] = None, series_query: Optional[str] = None, 
                         archetype: Optional[str] = None, elemental_type: Optional[str] = None) -> List[Character]:
        """
        Search for characters based on various criteria
        
        Args:
            name_query: Partial character name to search for
            series_query: Partial series name to search for
            archetype: Specific archetype to match
            elemental_type: Specific elemental type to match
            
        Returns:
            List of matching characters
        """
        results = []
        
        for character in self.characters.values():
            # Check name match
            if name_query and name_query.lower() not in character.name.lower():
                continue
            
            # Check series match
            if series_query and series_query.lower() not in character.series.lower():
                continue
            
            # Check archetype match
            if archetype and not character.has_archetype(archetype):
                continue
            
            # Check elemental type match
            if elemental_type and not character.has_elemental_type(elemental_type):
                continue
            
            results.append(character)
        
        return results
    
    def get_character_count(self) -> int:
        """Get total number of loaded characters"""
        return len(self.characters)
    
    def get_series_count(self) -> int:
        """Get total number of unique series"""
        return len(self.characters_by_series)
    
    def get_characters_by_ids(self, character_ids: List[int]) -> List[Character]:
        """
        Get multiple characters by their IDs
        
        Args:
            character_ids: List of waifu_ids to retrieve
            
        Returns:
            List of Character objects (excludes any not found)
        """
        characters = []
        for char_id in character_ids:
            character = self.get_character(char_id)
            if character:
                characters.append(character)
            else:
                print(f"Warning: Character with ID {char_id} not found")
        
        return characters