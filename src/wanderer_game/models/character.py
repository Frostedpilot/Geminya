"""
Character models for the Wanderer Game

Based on the character_final.csv and anime_final.csv data structure.
"""

from dataclasses import dataclass
from typing import Dict, List
from enum import Enum
import json


class AffinityType(Enum):
    """Types of affinities that can be matched"""
    ELEMENTAL = "elemental"
    ARCHETYPE = "archetype"
    SERIES_ID = "series_id"
    GENRE = "genre"


@dataclass
class CharacterStats:
    def to_dict(self) -> dict:
        """Return a dict of all stats, including both 'int' and 'intel' keys for compatibility."""
        return {
            'hp': self.hp,
            'atk': self.atk,
            'mag': self.mag,
            'vit': self.vit,
            'spr': self.spr,
            'int': self.intel,   # For compatibility with dominant_stats and stat calculations
            'intel': self.intel, # For internal use if needed
            'spd': self.spd,
            'lck': self.lck
        }
    """Character base statistics"""
    hp: int
    atk: int
    mag: int
    vit: int
    spr: int
    intel: int  # Renamed from 'int' to avoid conflict with built-in type
    spd: int
    lck: int
    
    @classmethod
    def from_dict(cls, stats_dict: Dict[str, int]) -> 'CharacterStats':
        """Create CharacterStats from dictionary"""
        return cls(
            hp=stats_dict.get('hp', 0),
            atk=stats_dict.get('atk', 0),
            mag=stats_dict.get('mag', 0),
            vit=stats_dict.get('vit', 0),
            spr=stats_dict.get('spr', 0),
            intel=stats_dict.get('int', 0),  # Map 'int' from CSV to 'intel' field
            spd=stats_dict.get('spd', 0),
            lck=stats_dict.get('lck', 0)
        )
    
    def get_stat(self, stat_name: str) -> int:
        """Get a stat by name"""
        stat_map = {
            'hp': self.hp,
            'atk': self.atk,
            'mag': self.mag,
            'vit': self.vit,
            'spr': self.spr,
            'int': self.intel,  # Map 'int' stat name to 'intel' field
            'spd': self.spd,
            'lck': self.lck
        }
        return stat_map.get(stat_name, 0)


@dataclass
class Affinity:
    """Represents an affinity that can be matched for expeditions"""
    type: AffinityType
    value: str
    
    def matches(self, character: 'Character') -> bool:
        """Check if this affinity matches a character"""
        if self.type == AffinityType.ELEMENTAL:
            return self.value in character.elemental_types
        elif self.type == AffinityType.ARCHETYPE:
            return self.value == character.archetype
        elif self.type == AffinityType.SERIES_ID:
            return str(self.value) == str(character.series_id)
        elif self.type == AffinityType.GENRE:
            return self.value in character.anime_genres
        return False


@dataclass
class Character:
    """
    Character model based on character_final.csv structure
    """
    waifu_id: int
    name: str
    series: str
    series_id: int
    genres: List[str]  # legacy, not used for genre affinity anymore
    anime_genres: List[str]
    image_url: str
    base_stats: CharacterStats
    elemental_types: List[str]
    archetype: str
    potency: Dict[str, str]  # Role potency ratings
    elemental_resistances: Dict[str, str]
    star_level: int = 1  # Default star level
    
    @classmethod
    def from_csv_row(cls, row: Dict[str, str], anime_genres_map: dict | None = None) -> 'Character':
        """Create Character from CSV row data. anime_genres_map: {series_id: [genres]}"""
        # Parse JSON fields
        stats = json.loads(row['stats'])
        elemental_types = json.loads(row['elemental_type'])
        potency = json.loads(row['potency'])
        resistances = json.loads(row['elemental_resistances'])
        genres = row['genre'].split(',') if row['genre'] else []
        series_id = int(row['series_id'])
        anime_genres = []
        if anime_genres_map and series_id in anime_genres_map:
            anime_genres = anime_genres_map[series_id]
        return cls(
            waifu_id=int(row['waifu_id']),
            name=row['name'],
            series=row['series'],
            series_id=series_id,
            genres=genres,
            anime_genres=anime_genres,
            image_url=row['image_url'],
            base_stats=CharacterStats.from_dict(stats),
            elemental_types=elemental_types,
            archetype=row['archetype'],
            potency=potency,
            elemental_resistances=resistances
        )
    
    def get_expedition_stats(self) -> CharacterStats:
        """Get stats with star bonus applied for expeditions"""
        # Apply star bonus: Stat * (1 + (Star Level - 1) * 0.10)
        multiplier = (1 + (self.star_level - 1) * 0.10) * 0.95
        
        return CharacterStats(
            hp=int(self.base_stats.hp * multiplier),
            atk=int(self.base_stats.atk * multiplier),
            mag=int(self.base_stats.mag * multiplier),
            vit=int(self.base_stats.vit * multiplier),
            spr=int(self.base_stats.spr * multiplier),
            intel=int(self.base_stats.intel * multiplier),
            spd=int(self.base_stats.spd * multiplier),
            lck=int(self.base_stats.lck * multiplier)
        )
    
    def matches_affinity(self, affinity: Affinity) -> bool:
        """Check if this character matches an affinity"""
        return affinity.matches(self)
    
    def has_series_id(self, series_id: int) -> bool:
        """Check if character belongs to a specific series"""
        return self.series_id == series_id
    
    def has_archetype(self, archetype: str) -> bool:
        """Check if character has a specific archetype"""
        return self.archetype.lower() == archetype.lower()
    
    def has_elemental_type(self, elemental_type: str) -> bool:
        """Check if character has a specific elemental type"""
        return elemental_type.lower() in [e.lower() for e in self.elemental_types]
    
    def has_genre(self, genre: str) -> bool:
        """Check if character's anime genres include a specific genre"""
        return genre.lower() in [g.lower() for g in self.anime_genres]


@dataclass 
class Team:
    """Represents a team of characters for an expedition"""
    characters: List[Character]
    
    def __post_init__(self):
        """Validate team size"""
        if len(self.characters) > 4:
            raise ValueError("Team cannot have more than 4 characters")
        if len(self.characters) == 0:
            raise ValueError("Team must have at least 1 character")
    
    def get_total_stat(self, stat_name: str) -> int:
        """Get sum of a stat across all team members (with star bonuses)"""
        total = 0
        for character in self.characters:
            expedition_stats = character.get_expedition_stats()
            total += expedition_stats.get_stat(stat_name)
        return total
    
    def get_total_luck(self) -> int:
        """Get total team luck (used for final multiplier calculations)"""
        return 150
    
    def count_affinity_matches(self, affinities: List[Affinity]) -> int:
        """Count how many affinity matches, max 3 per character"""
        matches = 0
        for character in self.characters:
            char_matches = 0
            for affinity in affinities:
                if character.matches_affinity(affinity):
                    char_matches += 1
                    if char_matches >= 3:
                        break
            matches += min(char_matches, 3)
        return matches
    
    def get_series_ids(self) -> List[int]:
        """Get unique series IDs represented in this team"""
        return list(set(char.series_id for char in self.characters))