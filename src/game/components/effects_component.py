"""
Effects Component - Handles status effects and conditions.

This component manages:
- Active status effects (buffs, debuffs, conditions)
- Effect stacking and duration tracking
- Effect triggers and conditions
- Interaction between different effects
"""

from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

from . import BaseComponent
from ..core.event_system import GameEvent, event_bus, EventPhase

logger = logging.getLogger(__name__)

class EffectType(Enum):
    """Types of status effects"""
    BUFF = "buff"           # Positive effects
    DEBUFF = "debuff"       # Negative effects
    CONDITION = "condition" # Special states (stun, sleep, etc.)
    PASSIVE = "passive"     # Permanent effects
    TEMPORARY = "temporary" # Short-duration effects

class TriggerType(Enum):
    """When effects trigger"""
    ON_APPLY = "on_apply"       # When first applied
    ON_REMOVE = "on_remove"     # When removed/expired
    ON_TURN_START = "on_turn_start"
    ON_TURN_END = "on_turn_end"
    ON_DAMAGE_DEALT = "on_damage_dealt"
    ON_DAMAGE_TAKEN = "on_damage_taken"
    ON_SKILL_USE = "on_skill_use"
    ON_HEAL_RECEIVED = "on_heal_received"
    CONTINUOUS = "continuous"   # Every update

@dataclass
class EffectTrigger:
    """Defines when and how an effect triggers"""
    trigger_type: TriggerType
    callback: Callable[[GameEvent, 'StatusEffect'], GameEvent]
    conditions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 500
    
    def can_trigger(self, event: GameEvent, effect: 'StatusEffect') -> bool:  # pylint: disable=unused-argument
        """Check if this trigger should activate"""
        for condition_key, condition_value in self.conditions.items():
            if condition_key in event.data:
                if event.data[condition_key] != condition_value:
                    return False
            else:
                return False
        return True

@dataclass
class StatusEffect:
    """Individual status effect"""
    effect_id: str
    effect_type: EffectType
    name: str
    description: str
    source: str
    duration: Optional[int] = None  # None = permanent
    stacks: int = 1
    max_stacks: int = 1
    power: float = 1.0
    data: Dict[str, Any] = field(default_factory=dict)
    triggers: List[EffectTrigger] = field(default_factory=list)
    removable: bool = True
    unique: bool = True  # Only one instance can exist
    
    def apply_stack(self, additional_stacks: int = 1):
        """Add stacks to this effect"""
        self.stacks = min(self.stacks + additional_stacks, self.max_stacks)
    
    def get_effective_power(self) -> float:
        """Get power multiplied by stacks"""
        return self.power * self.stacks

class EffectsComponent(BaseComponent):
    """Component handling status effects and conditions"""
    
    def __init__(self, character_id: str):
        super().__init__(character_id)
        self.active_effects: Dict[str, StatusEffect] = {}
        self.effect_groups: Dict[str, List[str]] = {}  # Group name -> effect IDs
        self.immunities: Dict[str, List[str]] = {}  # Immunity type -> effect types
        self.resistances: Dict[str, float] = {}  # Effect type -> resistance multiplier
        
        # Setup event listeners
        self._setup_event_listeners()
    
    def initialize(self, character_data: Dict[str, Any]):
        """Initialize effects from character data"""
        effects_data = character_data.get("effects", {})
        
        # Set initial immunities
        immunities = effects_data.get("immunities", {})
        for immunity_type, effect_types in immunities.items():
            self.immunities[immunity_type] = effect_types
        
        # Set resistances
        resistances = effects_data.get("resistances", {})
        for effect_type, resistance in resistances.items():
            self.resistances[effect_type] = float(resistance)
        
        # Apply starting effects
        starting_effects = effects_data.get("starting_effects", [])
        for effect_data in starting_effects:
            effect = self._create_effect_from_data(effect_data)
            if effect:
                self.apply_effect(effect)
        
        logger.debug("Initialized effects for character %s", self.character_id)
    
    def update(self, delta_time: float = 0.0):
        """Update component state"""
        expired_effects = []
        
        # Update effect durations and trigger continuous effects
        for effect_id, effect in self.active_effects.items():
            # Trigger continuous effects
            self._trigger_effect(effect, TriggerType.CONTINUOUS)
            
            # Update duration
            if effect.duration is not None:
                effect.duration -= 1
                if effect.duration <= 0:
                    expired_effects.append(effect_id)
        
        # Remove expired effects
        for effect_id in expired_effects:
            self.remove_effect(effect_id, "expired")
    
    def get_data(self) -> Dict[str, Any]:
        """Get component's current data"""
        return {
            "component_type": self.component_type,
            "active_effects": {
                effect_id: {
                    "effect_type": effect.effect_type.value,
                    "name": effect.name,
                    "description": effect.description,
                    "source": effect.source,
                    "duration": effect.duration,
                    "stacks": effect.stacks,
                    "max_stacks": effect.max_stacks,
                    "power": effect.power,
                    "data": effect.data,
                    "removable": effect.removable,
                    "unique": effect.unique
                }
                for effect_id, effect in self.active_effects.items()
            },
            "immunities": dict(self.immunities),
            "resistances": dict(self.resistances)
        }
    
    def set_data(self, data: Dict[str, Any]):
        """Set component data"""
        # Clear existing effects
        self.active_effects.clear()
        
        # Set immunities and resistances
        self.immunities = data.get("immunities", {})
        self.resistances = data.get("resistances", {})
        
        # Restore effects
        active_effects = data.get("active_effects", {})
        for effect_id, effect_data in active_effects.items():
            effect = self._create_effect_from_data(effect_data, effect_id)
            if effect:
                self.active_effects[effect_id] = effect
    
    def apply_effect(self, effect: StatusEffect) -> bool:
        """Apply a status effect"""
        # Check immunities
        if self._is_immune_to_effect(effect):
            logger.debug("Character %s is immune to effect %s", 
                        self.character_id, effect.effect_id)
            return False
        
        # Apply resistances
        if effect.effect_type.value in self.resistances:
            resistance = self.resistances[effect.effect_type.value]
            effect.power *= (1.0 - resistance)
            if effect.duration:
                effect.duration = int(effect.duration * (1.0 - resistance))
        
        # Check if effect already exists
        if effect.effect_id in self.active_effects:
            existing = self.active_effects[effect.effect_id]
            
            if effect.unique:
                # Replace existing effect
                self.remove_effect(effect.effect_id, "replaced")
            elif existing.stacks < existing.max_stacks:
                # Stack the effect
                existing.apply_stack()
                # Refresh duration if new effect has longer duration
                if effect.duration and (existing.duration is None or effect.duration > existing.duration):
                    existing.duration = effect.duration
                
                logger.debug("Stacked effect %s to %d stacks for character %s", 
                           effect.effect_id, existing.stacks, self.character_id)
                return True
            else:
                logger.debug("Effect %s already at max stacks for character %s", 
                           effect.effect_id, self.character_id)
                return False
        
        # Add new effect
        self.active_effects[effect.effect_id] = effect
        
        # Trigger on_apply effects
        self._trigger_effect(effect, TriggerType.ON_APPLY)
        
        # Publish effect applied event
        event = GameEvent(
            event_type="effect.applied",
            source=effect.source,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "effect_id": effect.effect_id,
                "effect_type": effect.effect_type.value,
                "effect_name": effect.name,
                "source": effect.source,
                "duration": effect.duration,
                "stacks": effect.stacks,
                "power": effect.power
            },
            phase=EventPhase.PROCESS
        )
        event_bus.publish(event)
        
        logger.debug("Applied effect %s to character %s", 
                    effect.effect_id, self.character_id)
        return True
    
    def remove_effect(self, effect_id: str, reason: str = "removed") -> bool:
        """Remove a status effect"""
        if effect_id not in self.active_effects:
            return False
        
        effect = self.active_effects[effect_id]
        
        # Check if effect is removable
        if not effect.removable and reason != "expired":
            logger.debug("Effect %s is not removable", effect_id)
            return False
        
        # Trigger on_remove effects
        self._trigger_effect(effect, TriggerType.ON_REMOVE)
        
        # Remove the effect
        del self.active_effects[effect_id]
        
        # Publish effect removed event
        event = GameEvent(
            event_type="effect.removed",
            source=effect.source,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "effect_id": effect_id,
                "effect_type": effect.effect_type.value,
                "effect_name": effect.name,
                "reason": reason
            },
            phase=EventPhase.PROCESS
        )
        event_bus.publish(event)
        
        logger.debug("Removed effect %s from character %s (reason: %s)", 
                    effect_id, self.character_id, reason)
        return True
    
    def has_effect(self, effect_id: str) -> bool:
        """Check if character has a specific effect"""
        return effect_id in self.active_effects
    
    def has_effect_type(self, effect_type: Union[EffectType, str]) -> bool:
        """Check if character has any effect of a specific type"""
        if isinstance(effect_type, str):
            try:
                effect_type = EffectType(effect_type)
            except ValueError:
                return False
        
        return any(effect.effect_type == effect_type for effect in self.active_effects.values())
    
    def get_effect(self, effect_id: str) -> Optional[StatusEffect]:
        """Get a specific effect"""
        return self.active_effects.get(effect_id)
    
    def get_effects_by_type(self, effect_type: Union[EffectType, str]) -> List[StatusEffect]:
        """Get all effects of a specific type"""
        if isinstance(effect_type, str):
            try:
                effect_type = EffectType(effect_type)
            except ValueError:
                return []
        
        return [effect for effect in self.active_effects.values() if effect.effect_type == effect_type]
    
    def clear_effects_by_type(self, effect_type: Union[EffectType, str], reason: str = "cleared"):
        """Remove all effects of a specific type"""
        if isinstance(effect_type, str):
            try:
                effect_type = EffectType(effect_type)
            except ValueError:
                return
        
        effects_to_remove = [
            effect_id for effect_id, effect in self.active_effects.items()
            if effect.effect_type == effect_type and effect.removable
        ]
        
        for effect_id in effects_to_remove:
            self.remove_effect(effect_id, reason)
    
    def add_immunity(self, immunity_type: str, effect_types: List[str]):
        """Add immunity to specific effect types"""
        if immunity_type not in self.immunities:
            self.immunities[immunity_type] = []
        self.immunities[immunity_type].extend(effect_types)
    
    def remove_immunity(self, immunity_type: str):
        """Remove an immunity"""
        if immunity_type in self.immunities:
            del self.immunities[immunity_type]
    
    def set_resistance(self, effect_type: str, resistance: float):
        """Set resistance to an effect type (0.0 = no resistance, 1.0 = immune)"""
        self.resistances[effect_type] = max(0.0, min(1.0, resistance))
    
    def _setup_event_listeners(self):
        """Set up event listeners for this component"""
        def on_turn_start(event: GameEvent) -> GameEvent:
            if event.data.get("character_id") == self.character_id:
                for effect in self.active_effects.values():
                    self._trigger_effect(effect, TriggerType.ON_TURN_START, event)
            return event
        
        def on_turn_end(event: GameEvent) -> GameEvent:
            if event.data.get("character_id") == self.character_id:
                for effect in self.active_effects.values():
                    self._trigger_effect(effect, TriggerType.ON_TURN_END, event)
            return event
        
        def on_damage_dealt(event: GameEvent) -> GameEvent:
            if event.data.get("source_id") == self.character_id:
                for effect in self.active_effects.values():
                    self._trigger_effect(effect, TriggerType.ON_DAMAGE_DEALT, event)
            return event
        
        def on_damage_taken(event: GameEvent) -> GameEvent:
            if event.data.get("target_id") == self.character_id:
                for effect in self.active_effects.values():
                    self._trigger_effect(effect, TriggerType.ON_DAMAGE_TAKEN, event)
            return event
        
        self.register_event_listener("turn.start", on_turn_start)
        self.register_event_listener("turn.end", on_turn_end)
        self.register_event_listener("damage.dealt", on_damage_dealt)
        self.register_event_listener("damage.dealt", on_damage_taken)  # Same event, different perspective
    
    def _trigger_effect(self, effect: StatusEffect, trigger_type: TriggerType, event: Optional[GameEvent] = None):
        """Trigger effect callbacks for a specific trigger type"""
        for trigger in effect.triggers:
            if trigger.trigger_type == trigger_type:
                if event is None:
                    # Create a generic event for non-event triggers
                    event = GameEvent(
                        event_type=f"effect.{trigger_type.value}",
                        source=self.character_id,
                        target=self.character_id,
                        data={"character_id": self.character_id, "effect_id": effect.effect_id}
                    )
                
                if trigger.can_trigger(event, effect):
                    try:
                        trigger.callback(event, effect)
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.error("Error triggering effect %s: %s", effect.effect_id, e)
    
    def _is_immune_to_effect(self, effect: StatusEffect) -> bool:
        """Check if character is immune to an effect"""
        for immunity_types in self.immunities.values():
            if effect.effect_type.value in immunity_types:
                return True
        return False
    
    def _create_effect_from_data(self, effect_data: Dict[str, Any], effect_id: Optional[str] = None) -> Optional[StatusEffect]:
        """Create a StatusEffect from data dictionary"""
        try:
            return StatusEffect(
                effect_id=effect_id or effect_data["effect_id"],
                effect_type=EffectType(effect_data["effect_type"]),
                name=effect_data["name"],
                description=effect_data["description"],
                source=effect_data["source"],
                duration=effect_data.get("duration"),
                stacks=effect_data.get("stacks", 1),
                max_stacks=effect_data.get("max_stacks", 1),
                power=effect_data.get("power", 1.0),
                data=effect_data.get("data", {}),
                removable=effect_data.get("removable", True),
                unique=effect_data.get("unique", True)
            )
        except (KeyError, ValueError) as e:
            logger.warning("Failed to create effect from data: %s", e)
            return None
