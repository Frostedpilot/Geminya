"""
Registries package for the Wanderer Game

Contains data loading and content management:
- ContentLoader: Loads expedition and encounter data from JSON files
- CharacterRegistry: Manages character data and lookups
- DataManager: Coordinates data loading and validation
"""

from .content_loader import ContentLoader
from .character_registry import CharacterRegistry
from .data_manager import DataManager

__all__ = [
    'ContentLoader',
    'CharacterRegistry',
    'DataManager'
]