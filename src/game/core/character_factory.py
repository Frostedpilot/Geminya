"""Factory for creating Character objects from data."""

from src.game.core.character import Character
from src.game.components.stats_component import StatsComponent
from src.game.components.state_component import StateComponent
from src.game.components.effects_component import EffectsComponent
from src.game.components.skills_component import SkillsComponent
from src.game.core.registries import CharacterDataRegistry

class ArchetypeComponent:
    """Simple component to hold archetype data."""
    
    def __init__(self, archetype_data):
        self.archetype_data = archetype_data

class CharacterFactory:
    """Factory for creating Character entities from base data."""
    
    def __init__(self, character_registry, event_bus=None, skill_registry=None, archetype_registry=None):
        """Initialize the character factory.
        
        Args:
            character_registry: Registry containing character data
            event_bus: EventBus instance for effect system
            skill_registry: Registry containing skill data
            archetype_registry: Registry containing archetype data
        """
        self.character_registry = character_registry
        self.event_bus = event_bus
        self.skill_registry = skill_registry
        self.archetype_registry = archetype_registry
    
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
        
        # Create and attach EffectsComponent
        effects_component = EffectsComponent(self.event_bus)
        effects_component.set_character(character)
        character.components['effects'] = effects_component
        
        # Create and attach SkillsComponent
        character_skills = base_data.get('skills', ['basic_attack'])  # Default to basic attack
        skills_component = SkillsComponent(character_skills)
        skills_component.set_character(character)
        if self.skill_registry:
            skills_component.set_skill_registry(self.skill_registry)
        character.components['skills'] = skills_component
        
        # Create and attach ArchetypeComponent
        if self.archetype_registry:
            archetype_name = base_data.get('archetype', 'Defender')  # Default archetype
            archetype_data = self.archetype_registry.get(archetype_name)
            if archetype_data:
                archetype_component = ArchetypeComponent(archetype_data)
                character.components['archetype'] = archetype_component
        
        # Store additional metadata
        character.team = team
        character.position = position
        character.name = base_data.get('name', f'Character_{character_id}')
        
        return character