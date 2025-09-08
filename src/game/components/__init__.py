"""
Character Component System

This module implements a component-based architecture for characters in the auto-battler.
Each character is composed of modular components that handle different aspects:
- Stats: Core attributes and modifiers
- Effects: Status effects and conditions
- Abilities: Skills and passive abilities
- State: Battle state and action tracking

Components communicate through the event system and can be dynamically added/removed.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from ..core.event_system import GameEvent, event_bus

class BaseComponent(ABC):
    """Base class for all character components"""
    
    def __init__(self, character_id: str):
        self.character_id = character_id
        self.component_type = self.__class__.__name__
        self.event_listeners: List[str] = []
        self.active = True
        
    @abstractmethod
    def initialize(self, character_data: Dict[str, Any]):
        """Initialize component with character data"""
        raise NotImplementedError
    
    @abstractmethod
    def update(self, delta_time: float = 0.0):
        """Update component state"""
        raise NotImplementedError
    
    @abstractmethod
    def get_data(self) -> Dict[str, Any]:
        """Get component's current data"""
        raise NotImplementedError
    
    @abstractmethod
    def set_data(self, data: Dict[str, Any]):
        """Set component data"""
        raise NotImplementedError
    
    def cleanup(self):
        """Clean up component resources"""
        for listener_id in self.event_listeners:
            event_bus.unregister_global_handler(listener_id)
        self.event_listeners.clear()
    
    def register_event_listener(self, event_type: str, callback, priority: int = 500):
        """Register an event listener for this component"""
        listener_id = event_bus.register_handler(
            event_type=event_type,
            callback=callback,
            priority=priority,
            conditions={"character_id": self.character_id}
        )
        self.event_listeners.append(listener_id)
        return listener_id

# Import all component classes
from .stats_component import (
    StatsComponent, StatType, ModifierType, StatModifier
)
from .effects_component import (
    EffectsComponent, EffectType, TriggerType, StatusEffect, EffectTrigger
)
from .state_component import (
    StateComponent, CharacterState, ActionState, ActionRecord, Cooldown
)
from .abilities_component import (
    AbilitiesComponent, BaseSkill, BasePassive, SkillType, PassiveType,
    TargetType, SkillState, SkillCost, SkillCondition
)
from .character import Character

__all__ = [
    # Base component
    'BaseComponent',
    
    # Stats system
    'StatsComponent',
    'StatType',
    'ModifierType', 
    'StatModifier',
    
    # Effects system
    'EffectsComponent',
    'EffectType',
    'TriggerType',
    'StatusEffect',
    'EffectTrigger',
    
    # State system
    'StateComponent',
    'CharacterState',
    'ActionState',
    'ActionRecord',
    'Cooldown',
    
    # Abilities system
    'AbilitiesComponent',
    'BaseSkill',
    'BasePassive',
    'SkillType',
    'PassiveType',
    'TargetType',
    'SkillState',
    'SkillCost',
    'SkillCondition',
    
    # Main character class
    'Character'
]
