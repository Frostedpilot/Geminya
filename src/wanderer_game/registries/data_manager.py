"""
Data Manager for the Wanderer Game

Coordinates loading and management of all game data.
"""

from .content_loader import ContentLoader
from .character_registry import CharacterRegistry
from ..systems import LootGenerator


class DataManager:
    """
    Central coordinator for all game data loading and management
    
    Provides a unified interface for accessing characters, expeditions, 
    encounters, and other game content.
    """
    
    def __init__(self, data_directory: str = "data"):
        self.content_loader = ContentLoader(f"{data_directory}/expeditions")
        self.character_registry = CharacterRegistry(data_directory)
        self.loot_generator = LootGenerator()
        
        self._expedition_templates = []
        self._encounters = []
        self._affinity_pools = None
        self._loaded = False
    
    def load_all_data(self) -> bool:
        """
        Load all game data from files
        
        Returns:
            True if all data loaded successfully, False otherwise
        """
        success = True
        
        # Load characters
        if not self.character_registry.load_characters():
            print("Failed to load characters")
            success = False
        
        # Load expedition templates
        self._expedition_templates = self.content_loader.load_expedition_templates()
        if not self._expedition_templates:
            print("Failed to load expedition templates")
            success = False
        
        # Load encounters
        self._encounters = self.content_loader.load_encounters()
        if not self._encounters:
            print("Failed to load encounters")
            success = False
        
        # Load affinity pools
        try:
            from src.wanderer_game.utils.equipment_utils import load_affinity_pools
            self._affinity_pools = load_affinity_pools()
            print(f"Loaded affinity pools: {len(self._affinity_pools)} categories")
        except Exception as e:
            print(f"Failed to load affinity pools: {e}")
            success = False
        
        self._loaded = success
        
        if success:
            print("Successfully loaded all game data:")
            print(f"  - {self.character_registry.get_character_count()} characters")
            print(f"  - {len(self._expedition_templates)} expedition templates")
            print(f"  - {len(self._encounters)} encounters")
            print(f"  - {len(self._affinity_pools)} affinity categories")
        
        return success
    
    def is_loaded(self) -> bool:
        """Check if all data has been loaded"""
        return self._loaded
    
    def get_character(self, waifu_id: int):
        """Get a character by their waifu_id"""
        return self.character_registry.get_character(waifu_id)

    def get_character_registry(self) -> CharacterRegistry:
        """Get the character registry"""
        return self.character_registry
    
    def get_expedition_templates(self):
        """Get list of expedition templates"""
        return self._expedition_templates.copy()
    
    def get_encounters(self):
        """Get list of encounters"""
        return self._encounters.copy()
    
    def get_encounters_as_dict(self):
        """Get encounters as a list of dictionaries for ExpeditionResolver"""
        encounter_dicts = []
        for encounter in self._encounters:
            # Convert encounter to dict, handling special objects
            encounter_dict = {
                'encounter_id': encounter.encounter_id,
                'name': encounter.name,
                'type': encounter.type.value,
                'tags': encounter.tags,
                'description_success': encounter.description_success,
                'description_failure': encounter.description_failure,
                'check_stat': encounter.check_stat,
                'difficulty': encounter.difficulty,
                'loot_values': encounter.loot_values,
            }
            
            # Handle condition (convert to dict if present)
            if encounter.condition:
                encounter_dict['condition'] = {
                    'type': encounter.condition.type.value,
                    'value': encounter.condition.value
                }
            else:
                encounter_dict['condition'] = None
                
            # Handle modifier (convert to dict if present)
            if encounter.modifier:
                encounter_dict['modifier'] = {
                    'type': encounter.modifier.type.value,
                    'value': encounter.modifier.value
                }
            else:
                encounter_dict['modifier'] = None
                
            encounter_dicts.append(encounter_dict)
            
        return encounter_dicts
    
    def get_loot_generator(self) -> LootGenerator:
        """Get the loot generator"""
        return self.loot_generator
    
    def get_affinity_pools(self):
        """Get the affinity pools (series_id, archetype, elemental, genre)"""
        return self._affinity_pools if self._affinity_pools else {}
    
    def get_series_name(self, series_id: int):
        """Get the name of a series by its ID"""
        return self.character_registry.get_series_name(series_id)