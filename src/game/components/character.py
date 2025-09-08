"""
Character Class - Main character entity that aggregates all components.

This class provides a unified interface to all character functionality:
- Component management and lifecycle
- Event delegation and coordination
- High-level character operations
- Serialization and persistence
"""

from typing import Dict, Any, Optional, Union, Type, List, cast
import logging

from .stats_component import StatsComponent, StatType
from .effects_component import EffectsComponent, StatusEffect
from .state_component import StateComponent
from .abilities_component import AbilitiesComponent, BaseSkill, BasePassive
from . import BaseComponent
from ..core.event_system import GameEvent, event_bus, EventPhase

logger = logging.getLogger(__name__)

class Character:
    """
    Main character class that aggregates all components.
    
    Provides a unified interface for character operations while maintaining
    component separation for modularity and extensibility.
    """
    
    def __init__(self, character_id: str, character_data: Optional[Dict[str, Any]] = None):
        self.character_id = character_id
        self.character_data = character_data or {}
        
        # Core components
        self.components: Dict[str, BaseComponent] = {}
        
        # Initialize core components
        self._initialize_components()
        
        # Character metadata
        self.name = self.character_data.get("name", character_id)
        self.description = self.character_data.get("description", "")
        self.archetype = self.character_data.get("archetype", "balanced")
        self.series = self.character_data.get("series", "unknown")
        self.rarity = self.character_data.get("rarity", "common")
        
        # Current HP tracking (initialized after stats are set)
        self.current_hp = 0.0
        
        # Initialize all components with data
        if character_data:
            self.initialize_from_data(character_data)
        
        logger.info("Created character %s (%s)", self.character_id, self.name)
    
    def _initialize_components(self):
        """Initialize all core components"""
        # Always initialize these core components
        self.components["stats"] = StatsComponent(self.character_id)
        self.components["effects"] = EffectsComponent(self.character_id)
        self.components["state"] = StateComponent(self.character_id)
        self.components["abilities"] = AbilitiesComponent(self.character_id)
        
        # Set character reference for abilities component (after components dict is set)
        self.abilities.set_character(self)
        
        logger.debug("Initialized core components for character %s", self.character_id)
    
    def initialize_from_data(self, character_data: Dict[str, Any]):
        """Initialize character from data dictionary"""
        self.character_data = character_data
        
        # Update metadata
        self.name = character_data.get("name", self.character_id)
        self.description = character_data.get("description", "")
        self.archetype = character_data.get("archetype", "balanced")
        self.series = character_data.get("series", "unknown")
        self.rarity = character_data.get("rarity", "common")
        
        # Initialize all components
        for component in self.components.values():
            component.initialize(character_data)
        
        # Initialize current HP to max HP after stats are ready
        self.current_hp = self.get_stat("hp")
        
        # Publish character initialized event
        event = GameEvent(
            event_type="character.initialized",
            source=self.character_id,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "name": self.name,
                "archetype": self.archetype
            },
            phase=EventPhase.PROCESS
        )
        event_bus.publish(event)
        
        logger.info("Initialized character %s from data", self.character_id)
    
    def update(self, delta_time: float = 0.0):
        """Update all components"""
        for component in self.components.values():
            if component.active:
                component.update(delta_time)
    
    def cleanup(self):
        """Clean up all components"""
        for component in self.components.values():
            component.cleanup()
        
        # Publish character destroyed event
        event = GameEvent(
            event_type="character.destroyed",
            source=self.character_id,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "name": self.name
            },
            phase=EventPhase.PROCESS
        )
        event_bus.publish(event)
        
        logger.info("Cleaned up character %s", self.character_id)
    
    def get_component(self, component_type: Union[str, Type[BaseComponent]]) -> Optional[BaseComponent]:
        """Get a specific component"""
        if isinstance(component_type, type):
            component_type = component_type.__name__.lower().replace("component", "")
        
        return self.components.get(component_type)
    
    def add_component(self, component: BaseComponent):
        """Add a new component"""
        component_type = component.component_type.lower().replace("component", "")
        self.components[component_type] = component
        
        # Initialize the component with current character data
        component.initialize(self.character_data)
        
        logger.debug("Added component %s to character %s", 
                    component_type, self.character_id)
    
    def remove_component(self, component_type: str) -> bool:
        """Remove a component"""
        if component_type in self.components:
            component = self.components[component_type]
            component.cleanup()
            del self.components[component_type]
            
            logger.debug("Removed component %s from character %s", 
                        component_type, self.character_id)
            return True
        return False
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize character to dictionary"""
        data = {
            "character_id": self.character_id,
            "name": self.name,
            "description": self.description,
            "archetype": self.archetype,
            "series": self.series,
            "rarity": self.rarity,
            "current_hp": self.current_hp,
            "components": {}
        }
        
        # Serialize all components
        for component_type, component in self.components.items():
            data["components"][component_type] = component.get_data()
        
        return data
    
    def deserialize(self, data: Dict[str, Any]):
        """Restore character from serialized data"""
        # Restore metadata
        self.name = data.get("name", self.character_id)
        self.description = data.get("description", "")
        self.archetype = data.get("archetype", "balanced")
        self.series = data.get("series", "unknown")
        self.rarity = data.get("rarity", "common")
        self.current_hp = data.get("current_hp", 0.0)
        
        # Restore components
        components_data = data.get("components", {})
        for component_type, component_data in components_data.items():
            if component_type in self.components:
                self.components[component_type].set_data(component_data)
        
        # If current_hp is 0, set it to max HP
        if self.current_hp <= 0:
            self.current_hp = self.get_stat("hp")
        
        logger.debug("Deserialized character %s", self.character_id)
    
    # Convenience methods for common operations
    
    @property
    def stats(self) -> StatsComponent:
        """Get stats component"""
        return self.components["stats"]  # type: ignore
    
    @property
    def effects(self) -> EffectsComponent:
        """Get effects component"""
        return self.components["effects"]  # type: ignore
    
    @property
    def state(self) -> StateComponent:
        """Get state component"""
        return self.components["state"]  # type: ignore
    
    @property
    def abilities(self) -> AbilitiesComponent:
        """Get abilities component"""
        return self.components["abilities"]  # type: ignore
    
    def get_stat(self, stat_type: Union[StatType, str]) -> float:
        """Get current stat value"""
        return self.stats.get_stat(stat_type)
    
    def get_base_stat(self, stat_type: Union[StatType, str]) -> float:
        """Get base stat value"""
        return self.stats.get_base_stat(stat_type)
    
    def is_alive(self) -> bool:
        """Check if character is alive"""
        return self.state.is_alive()
    
    def is_ready_to_act(self) -> bool:
        """Check if character can perform an action"""
        return self.state.is_ready_to_act()
    
    def has_effect(self, effect_id: str) -> bool:
        """Check if character has a specific effect"""
        return self.effects.has_effect(effect_id)
    
    def apply_effect(self, effect: StatusEffect) -> bool:
        """Apply a status effect"""
        return self.effects.apply_effect(effect)
    
    def remove_effect(self, effect_id: str, reason: str = "removed") -> bool:
        """Remove a status effect"""
        return self.effects.remove_effect(effect_id, reason)
    
    def take_damage(self, damage: float, damage_type: str = "physical", source: Optional[str] = None) -> float:
        """Apply damage to character"""
        # This would integrate with a health/damage system
        # For now, just publish the event
        event = GameEvent(
            event_type="damage.taken",
            source=source,
            target=self.character_id,
            data={
                "target_id": self.character_id,
                "source_id": source,
                "damage_amount": damage,
                "damage_type": damage_type,
                "original_damage": damage
            },
            phase=EventPhase.PROCESS
        )
        
        result = event_bus.publish(event)
        final_damage = result.get_value("damage_amount", damage)
        
        # Actually reduce current HP
        self.current_hp = max(0.0, self.current_hp - final_damage)
        
        # Update performance tracking
        self.state.total_damage_taken += final_damage
        
        logger.debug("Character %s took %f %s damage from %s (HP: %f/%f)", 
                    self.character_id, final_damage, damage_type, source,
                    self.current_hp, self.get_stat("hp"))
        
        return final_damage
    
    def heal(self, amount: float, source: Optional[str] = None) -> float:
        """Heal the character"""
        event = GameEvent(
            event_type="healing.received",
            source=source,
            target=self.character_id,
            data={
                "target_id": self.character_id,
                "source_id": source,
                "heal_amount": amount,
                "original_heal": amount
            },
            phase=EventPhase.PROCESS
        )
        
        result = event_bus.publish(event)
        final_heal = result.get_value("heal_amount", amount)
        
        # Actually restore HP (capped at max HP)
        max_hp = self.get_stat("hp")
        old_hp = self.current_hp
        self.current_hp = min(max_hp, self.current_hp + final_heal)
        actual_heal = self.current_hp - old_hp
        
        # Update performance tracking
        self.state.total_healing_done += actual_heal
        
        logger.debug("Character %s healed for %f from %s (HP: %f/%f)", 
                    self.character_id, actual_heal, source, self.current_hp, max_hp)
        
        return actual_heal
    
    def set_target(self, target_id: Optional[str]):
        """Set current target"""
        self.state.set_target(target_id)
    
    def start_cooldown(self, ability_id: str, turns: int):
        """Start ability cooldown"""
        self.state.start_cooldown(ability_id, turns)
    
    def can_use_ability(self, ability_id: str) -> bool:
        """Check if ability is available"""
        return self.state.can_use_ability(ability_id)
    
    def reset_action_gauge(self):
        """Reset action gauge"""
        self.state.reset_action_gauge()
    
    # Abilities methods
    
    def get_skill(self, skill_id: str) -> Optional[BaseSkill]:
        """Get a skill by ID"""
        return self.abilities.get_skill(skill_id)
    
    def get_passive(self, passive_id: str) -> Optional[BasePassive]:
        """Get a passive by ID"""
        return self.abilities.get_passive(passive_id)
    
    def get_skills(self) -> List[BaseSkill]:
        """Get all skills"""
        all_skills = []
        for skill_list in self.abilities.skills.values():
            all_skills.extend(skill_list)
        return all_skills
    
    def get_passives(self) -> List[BasePassive]:
        """Get all passives"""
        all_passives = []
        for passive_list in self.abilities.passives.values():
            all_passives.extend(passive_list)
        return all_passives
    
    def get_current_hp(self) -> float:
        """Get current HP"""
        return self.current_hp
    
    def get_max_hp(self) -> float:
        """Get maximum HP"""
        return self.get_stat("hp")
    
    def get_hp_ratio(self) -> float:
        """Get current HP as ratio of max HP"""
        max_hp = self.get_max_hp()
        return self.current_hp / max_hp if max_hp > 0 else 0.0
    
    def is_defeated(self) -> bool:
        """Check if character is defeated (HP <= 0)"""
        return self.current_hp <= 0
    
    def get_available_skills(self):
        """Get all currently available skills"""
        return self.abilities.get_available_skills(self)
    
    def add_skill(self, skill: BaseSkill):
        """Add a skill to the character"""
        self.abilities.add_skill(skill)
    
    def add_passive(self, passive: BasePassive):
        """Add a passive to the character"""
        self.abilities.add_passive(passive)
    
    def use_skill(self, skill_id: str, targets, battle_context=None):
        """Use a skill"""
        skill = self.get_skill(skill_id)
        if not skill:
            return {"success": False, "error": f"Skill {skill_id} not found"}
        
        if not skill.can_use(self):
            return {"success": False, "error": f"Cannot use skill {skill_id}"}
        
        return skill.execute(self, targets, battle_context)
    
    def has_resource(self, resource: str, amount: float) -> bool:
        """Check if character has enough of a resource (for skill costs)"""
        # Placeholder for future resource system
        return True
    
    def consume_resource(self, resource: str, amount: float):
        """Consume a resource (for skill costs)"""
        # Placeholder for future resource system
        pass
    
    def get_summary(self) -> Dict[str, Any]:
        """Get character summary"""
        abilities_summary = self.abilities.get_summary()
        
        return {
            "character_id": self.character_id,
            "name": self.name,
            "archetype": self.archetype,
            "is_alive": self.is_alive(),
            "is_ready": self.is_ready_to_act(),
            "current_hp": self.current_hp,
            "max_hp": self.get_max_hp(),
            "hp_ratio": self.get_hp_ratio(),
            "action_gauge": self.state.action_gauge,
            "action_gauge_max": self.state.action_gauge_max,
            "character_state": self.state.character_state.value,
            "action_state": self.state.action_state.value,
            "current_target": self.state.current_target,
            "active_effects_count": len(self.effects.active_effects),
            "cooldowns_count": len(self.state.cooldowns),
            "total_skills": abilities_summary["total_skills"],
            "total_passives": abilities_summary["total_passives"],
            "available_skills": abilities_summary["available_skills"],
            "active_passives": abilities_summary["active_passives"],
            "stats": {
                stat.value: self.get_stat(stat) for stat in StatType
            }
        }
    
    def __str__(self) -> str:
        """String representation"""
        return f"Character({self.character_id}: {self.name})"
    
    def __repr__(self) -> str:
        """Debug representation"""
        return (f"Character(id={self.character_id}, name={self.name}, "
                f"archetype={self.archetype}, "
                f"alive={self.is_alive()}, ready={self.is_ready_to_act()})")
