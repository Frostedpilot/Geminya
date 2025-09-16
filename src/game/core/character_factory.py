"""Factory for creating Character objects from data."""

from src.game.core.character import Character
from src.game.components.stats_component import StatsComponent
from src.game.components.state_component import StateComponent
from src.game.core.registries import CharacterDataRegistry

class CharacterFactory:
    """Factory for creating Character entities from base data."""
    
    def __init__(self, character_registry):
        self.character_registry = character_registry
    
    def create_character(self, character_id, team, position):
        """Create a character with all necessary components."""
        # Look up base character data
        base_data = self.character_registry.get(character_id)
        if not base_data:
            raise ValueError(f"Character with ID '{character_id}' not found in registry")
        
        # Create the character entity
        character = Character(character_id)
        
        # Create and attach StatsComponent
        base_stats = base_data.get('base_stats', {})
        stats_component = StatsComponent(base_stats)
        character.components['stats'] = stats_component
        
        # Create and attach StateComponent
        max_hp = base_stats.get('hp', 100)
        state_component = StateComponent(
            current_hp=max_hp,
            max_hp=max_hp,
            action_gauge=0,
            is_alive=True
        )
        character.components['state'] = state_component
        
        # Store additional metadata
        character.team = team
        character.position = position
        character.name = base_data.get('name', f'Character_{character_id}')
        
        return character