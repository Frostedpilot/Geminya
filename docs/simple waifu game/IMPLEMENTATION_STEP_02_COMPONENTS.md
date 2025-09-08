# Implementation Guide - Step 2: Character Component System

## Character Components and Stat Management

### Overview

This step implements the character component system that forms the foundation of character representation in the auto-battler. Each character is composed of modular components that handle different aspects of their functionality: stats, effects, abilities, and state tracking.

### Prerequisites

- Completed Step 1 (Foundation Setup)
- Understanding of component-based design patterns
- Familiarity with the event system from Step 1

### Step 2.1: Base Component Interface

Create the base component interface that all character components will implement:

**File: `src/game/components/__init__.py`**

```python
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
        pass
    
    @abstractmethod
    def update(self, delta_time: float = 0.0):
        """Update component state"""
        pass
    
    @abstractmethod
    def get_data(self) -> Dict[str, Any]:
        """Get component's current data"""
        pass
    
    @abstractmethod
    def set_data(self, data: Dict[str, Any]):
        """Set component data"""
        pass
    
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
```

### Step 2.2: Stats Component Implementation

Create the stats component that handles dynamic stat calculations:

**File: `src/game/components/stats_component.py`**

```python
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from . import BaseComponent
from ..core.event_system import GameEvent, event_bus, EventPhase

class StatType(Enum):
    """Available character stats"""
    HP = "hp"
    ATK = "atk"
    MAG = "mag"
    VIT = "vit"
    SPR = "spr"
    INT = "int"
    SPD = "spd"
    LCK = "lck"

class ModifierType(Enum):
    """Types of stat modifications"""
    FLAT = "flat"
    PERCENTAGE = "percentage"
    MULTIPLICATIVE = "multiplicative"

@dataclass
class StatModifier:
    """Individual stat modification"""
    modifier_id: str
    stat_type: StatType
    modifier_type: ModifierType
    value: float
    source: str
    layer: int = 0  # Higher layers apply later
    duration: Optional[int] = None  # None = permanent
    stacks: int = 1
    max_stacks: int = 1
    
    def apply(self, base_value: float) -> float:
        """Apply this modifier to a base value"""
        total_value = self.value * self.stacks
        
        if self.modifier_type == ModifierType.FLAT:
            return base_value + total_value
        elif self.modifier_type == ModifierType.PERCENTAGE:
            return base_value * (1 + total_value)
        elif self.modifier_type == ModifierType.MULTIPLICATIVE:
            return base_value * (total_value)
        
        return base_value

class StatsComponent(BaseComponent):
    """Component handling character stats and modifications"""
    
    def __init__(self, character_id: str):
        super().__init__(character_id)
        self.base_stats: Dict[StatType, float] = {}
        self.current_stats: Dict[StatType, float] = {}
        self.modifiers: Dict[str, StatModifier] = {}
        self.stat_caps: Dict[StatType, Dict[str, float]] = {}
        self.cache_valid = False
        self.calculation_layers = [
            "base",           # Base character stats
            "equipment",      # Equipment bonuses (future)
            "passive",        # Passive abilities
            "temporary",      # Buffs/debuffs
            "battlefield",    # Environmental effects
            "rules",          # Rule modifications
            "final"           # Final caps and validation
        ]
        
        # Initialize event listeners
        self._setup_event_listeners()
    
    def initialize(self, character_data: Dict[str, Any]):
        """Initialize stats from character data"""
        stats_data = character_data.get("stats", {})
        
        for stat in StatType:
            self.base_stats[stat] = float(stats_data.get(stat.value, 0))
            self.current_stats[stat] = self.base_stats[stat]
        
        # Set default stat caps
        for stat in StatType:
            self.stat_caps[stat] = {
                "min": 0.0,
                "max": float('inf'),
                "soft_cap": 999.0
            }
        
        self.cache_valid = False
        self._recalculate_stats()
        
        # Publish initialization event
        event = GameEvent(
            event_type="stats_initialized",
            source=self,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "base_stats": dict(self.base_stats),
                "current_stats": dict(self.current_stats)
            }
        )
        event_bus.publish(event)
    
    def update(self, delta_time: float = 0.0):
        """Update component state"""
        # Decrease modifier durations
        expired_modifiers = []
        
        for modifier_id, modifier in self.modifiers.items():
            if modifier.duration is not None:
                modifier.duration -= 1
                if modifier.duration <= 0:
                    expired_modifiers.append(modifier_id)
        
        # Remove expired modifiers
        for modifier_id in expired_modifiers:
            self.remove_modifier(modifier_id)
        
        # Recalculate if cache is invalid
        if not self.cache_valid:
            self._recalculate_stats()
    
    def get_data(self) -> Dict[str, Any]:
        """Get component's current data"""
        return {
            "base_stats": {stat.value: value for stat, value in self.base_stats.items()},
            "current_stats": {stat.value: value for stat, value in self.current_stats.items()},
            "modifiers": {
                mod_id: {
                    "stat_type": mod.stat_type.value,
                    "modifier_type": mod.modifier_type.value,
                    "value": mod.value,
                    "source": mod.source,
                    "layer": mod.layer,
                    "duration": mod.duration,
                    "stacks": mod.stacks,
                    "max_stacks": mod.max_stacks
                }
                for mod_id, mod in self.modifiers.items()
            }
        }
    
    def set_data(self, data: Dict[str, Any]):
        """Set component data"""
        # Set base stats
        base_stats_data = data.get("base_stats", {})
        for stat_name, value in base_stats_data.items():
            if hasattr(StatType, stat_name.upper()):
                stat_type = StatType(stat_name)
                self.base_stats[stat_type] = float(value)
        
        # Set modifiers
        modifiers_data = data.get("modifiers", {})
        self.modifiers.clear()
        
        for mod_id, mod_data in modifiers_data.items():
            modifier = StatModifier(
                modifier_id=mod_id,
                stat_type=StatType(mod_data["stat_type"]),
                modifier_type=ModifierType(mod_data["modifier_type"]),
                value=mod_data["value"],
                source=mod_data["source"],
                layer=mod_data.get("layer", 0),
                duration=mod_data.get("duration"),
                stacks=mod_data.get("stacks", 1),
                max_stacks=mod_data.get("max_stacks", 1)
            )
            self.modifiers[mod_id] = modifier
        
        self.cache_valid = False
        self._recalculate_stats()
    
    def get_stat(self, stat_type: Union[StatType, str]) -> float:
        """Get current value of a stat"""
        if isinstance(stat_type, str):
            stat_type = StatType(stat_type)
        
        if not self.cache_valid:
            self._recalculate_stats()
        
        return self.current_stats.get(stat_type, 0.0)
    
    def get_base_stat(self, stat_type: Union[StatType, str]) -> float:
        """Get base value of a stat"""
        if isinstance(stat_type, str):
            stat_type = StatType(stat_type)
        
        return self.base_stats.get(stat_type, 0.0)
    
    def set_base_stat(self, stat_type: Union[StatType, str], value: float):
        """Set base value of a stat"""
        if isinstance(stat_type, str):
            stat_type = StatType(stat_type)
        
        old_value = self.base_stats.get(stat_type, 0.0)
        self.base_stats[stat_type] = float(value)
        self.cache_valid = False
        
        # Publish stat change event
        event = GameEvent(
            event_type="base_stat_changed",
            source=self,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "stat_type": stat_type.value,
                "old_value": old_value,
                "new_value": value
            }
        )
        event_bus.publish(event)
    
    def add_modifier(self, modifier: StatModifier) -> bool:
        """Add a stat modifier"""
        # Check if modifier already exists
        if modifier.modifier_id in self.modifiers:
            existing = self.modifiers[modifier.modifier_id]
            
            # Try to stack if possible
            if (existing.stat_type == modifier.stat_type and
                existing.modifier_type == modifier.modifier_type and
                existing.source == modifier.source and
                existing.stacks < existing.max_stacks):
                
                existing.stacks += 1
                existing.duration = modifier.duration  # Reset duration
                self.cache_valid = False
                
                # Publish stack event
                event = GameEvent(
                    event_type="modifier_stacked",
                    source=self,
                    target=self.character_id,
                    data={
                        "character_id": self.character_id,
                        "modifier_id": modifier.modifier_id,
                        "new_stacks": existing.stacks
                    }
                )
                event_bus.publish(event)
                return True
            else:
                return False  # Cannot stack or replace
        
        # Add new modifier
        self.modifiers[modifier.modifier_id] = modifier
        self.cache_valid = False
        
        # Publish modifier added event
        event = GameEvent(
            event_type="modifier_added",
            source=self,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "modifier": modifier
            }
        )
        event_bus.publish(event)
        return True
    
    def remove_modifier(self, modifier_id: str) -> bool:
        """Remove a stat modifier"""
        if modifier_id in self.modifiers:
            modifier = self.modifiers.pop(modifier_id)
            self.cache_valid = False
            
            # Publish modifier removed event
            event = GameEvent(
                event_type="modifier_removed",
                source=self,
                target=self.character_id,
                data={
                    "character_id": self.character_id,
                    "modifier": modifier
                }
            )
            event_bus.publish(event)
            return True
        return False
    
    def get_modifiers_by_source(self, source: str) -> List[StatModifier]:
        """Get all modifiers from a specific source"""
        return [mod for mod in self.modifiers.values() if mod.source == source]
    
    def remove_modifiers_by_source(self, source: str) -> int:
        """Remove all modifiers from a specific source"""
        to_remove = [mod_id for mod_id, mod in self.modifiers.items() if mod.source == source]
        
        for mod_id in to_remove:
            self.remove_modifier(mod_id)
        
        return len(to_remove)
    
    def set_stat_cap(self, stat_type: Union[StatType, str], cap_type: str, value: float):
        """Set a stat cap (min, max, or soft_cap)"""
        if isinstance(stat_type, str):
            stat_type = StatType(stat_type)
        
        if stat_type not in self.stat_caps:
            self.stat_caps[stat_type] = {}
        
        self.stat_caps[stat_type][cap_type] = value
        self.cache_valid = False
    
    def _recalculate_stats(self):
        """Recalculate all current stats"""
        # Start with base stats
        for stat_type in StatType:
            base_value = self.base_stats.get(stat_type, 0.0)
            calculated_value = base_value
            
            # Apply modifiers by layer and priority
            layer_modifiers = {}
            for modifier in self.modifiers.values():
                if modifier.stat_type == stat_type:
                    layer = modifier.layer
                    if layer not in layer_modifiers:
                        layer_modifiers[layer] = []
                    layer_modifiers[layer].append(modifier)
            
            # Apply modifiers layer by layer
            for layer in sorted(layer_modifiers.keys()):
                modifiers = layer_modifiers[layer]
                
                # Apply flat modifiers first
                for modifier in modifiers:
                    if modifier.modifier_type == ModifierType.FLAT:
                        calculated_value = modifier.apply(calculated_value)
                
                # Then percentage modifiers
                for modifier in modifiers:
                    if modifier.modifier_type == ModifierType.PERCENTAGE:
                        calculated_value = modifier.apply(calculated_value)
                
                # Finally multiplicative modifiers
                for modifier in modifiers:
                    if modifier.modifier_type == ModifierType.MULTIPLICATIVE:
                        calculated_value = modifier.apply(calculated_value)
            
            # Apply caps
            caps = self.stat_caps.get(stat_type, {})
            min_value = caps.get("min", 0.0)
            max_value = caps.get("max", float('inf'))
            soft_cap = caps.get("soft_cap", 999.0)
            
            # Apply soft cap with diminishing returns
            if calculated_value > soft_cap:
                excess = calculated_value - soft_cap
                diminished_excess = excess * 0.1  # 10% efficiency above soft cap
                calculated_value = soft_cap + diminished_excess
            
            # Apply hard caps
            calculated_value = max(min_value, min(calculated_value, max_value))
            
            self.current_stats[stat_type] = calculated_value
        
        self.cache_valid = True
        
        # Publish recalculation event
        event = GameEvent(
            event_type="stats_recalculated",
            source=self,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "stats": {stat.value: value for stat, value in self.current_stats.items()}
            }
        )
        event_bus.publish(event)
    
    def _setup_event_listeners(self):
        """Set up event listeners for this component"""
        # Listen for events that might affect stats
        self.register_event_listener(
            "effect_applied",
            self._on_effect_applied
        )
        
        self.register_event_listener(
            "effect_removed", 
            self._on_effect_removed
        )
        
        self.register_event_listener(
            "battlefield_condition_changed",
            self._on_battlefield_condition_changed
        )
    
    def _on_effect_applied(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle effect applied events"""
        if event.get_value("target_id") == self.character_id:
            effect_data = event.get_value("effect_data", {})
            
            # Check if effect has stat modifiers
            stat_modifiers = effect_data.get("stat_modifiers", [])
            for mod_data in stat_modifiers:
                modifier = StatModifier(
                    modifier_id=f"{event.get_value('effect_id')}_{mod_data['stat_type']}",
                    stat_type=StatType(mod_data["stat_type"]),
                    modifier_type=ModifierType(mod_data["modifier_type"]),
                    value=mod_data["value"],
                    source=event.get_value("effect_id", "unknown"),
                    layer=mod_data.get("layer", 3),  # Temporary layer
                    duration=effect_data.get("duration")
                )
                self.add_modifier(modifier)
        
        return event
    
    def _on_effect_removed(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle effect removed events"""
        if event.get_value("target_id") == self.character_id:
            effect_id = event.get_value("effect_id")
            self.remove_modifiers_by_source(effect_id)
        
        return event
    
    def _on_battlefield_condition_changed(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle battlefield condition changes"""
        # Remove old battlefield modifiers
        self.remove_modifiers_by_source("battlefield")
        
        # Apply new battlefield condition modifiers
        condition_data = event.get_value("condition_data", {})
        stat_modifiers = condition_data.get("stat_modifiers", [])
        
        for mod_data in stat_modifiers:
            modifier = StatModifier(
                modifier_id=f"battlefield_{mod_data['stat_type']}",
                stat_type=StatType(mod_data["stat_type"]),
                modifier_type=ModifierType(mod_data["modifier_type"]),
                value=mod_data["value"],
                source="battlefield",
                layer=4  # Battlefield layer
            )
            self.add_modifier(modifier)
        
        return event
```

### Step 2.3: Effects Component Implementation

Create the effects component that manages active status effects:

**File: `src/game/components/effects_component.py`**

```python
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid

from . import BaseComponent
from ..core.event_system import GameEvent, event_bus

class EffectType(Enum):
    """Types of effects"""
    BUFF = "buff"
    DEBUFF = "debuff"
    NEUTRAL = "neutral"
    DAMAGE_OVER_TIME = "dot"
    HEAL_OVER_TIME = "hot"

class StackingRule(Enum):
    """How effects stack with themselves"""
    NO_STACK = "no_stack"          # Replace existing
    INTENSITY = "intensity"        # Stack values
    DURATION = "duration"          # Stack duration
    INDEPENDENT = "independent"    # Independent instances

@dataclass
class ActiveEffect:
    """An active effect on a character"""
    effect_id: str
    effect_type: EffectType
    source_id: str
    source_type: str  # "skill", "passive", "item", etc.
    duration: Optional[int] = None  # None = permanent
    stacks: int = 1
    max_stacks: int = 1
    stacking_rule: StackingRule = StackingRule.NO_STACK
    data: Dict[str, Any] = field(default_factory=dict)
    created_turn: int = 0
    last_trigger_turn: int = -1
    
    def tick(self) -> bool:
        """Decrease duration, return True if effect should be removed"""
        if self.duration is not None:
            self.duration -= 1
            return self.duration <= 0
        return False
    
    def can_stack_with(self, other: 'ActiveEffect') -> bool:
        """Check if this effect can stack with another"""
        return (self.effect_id == other.effect_id and
                self.source_id == other.source_id and
                self.stacking_rule != StackingRule.NO_STACK and
                self.stacks < self.max_stacks)

class EffectsComponent(BaseComponent):
    """Component managing active effects on a character"""
    
    def __init__(self, character_id: str):
        super().__init__(character_id)
        self.active_effects: Dict[str, ActiveEffect] = {}
        self.effect_immunities: Set[str] = set()
        self.max_buffs = 3
        self.max_debuffs = 3
        self.current_turn = 0
        
        self._setup_event_listeners()
    
    def initialize(self, character_data: Dict[str, Any]):
        """Initialize effects from character data"""
        effects_data = character_data.get("active_effects", {})
        
        for effect_instance_id, effect_data in effects_data.items():
            effect = ActiveEffect(
                effect_id=effect_data["effect_id"],
                effect_type=EffectType(effect_data.get("effect_type", "neutral")),
                source_id=effect_data["source_id"],
                source_type=effect_data.get("source_type", "unknown"),
                duration=effect_data.get("duration"),
                stacks=effect_data.get("stacks", 1),
                max_stacks=effect_data.get("max_stacks", 1),
                stacking_rule=StackingRule(effect_data.get("stacking_rule", "no_stack")),
                data=effect_data.get("data", {}),
                created_turn=effect_data.get("created_turn", 0)
            )
            self.active_effects[effect_instance_id] = effect
        
        # Set immunities
        immunities = character_data.get("effect_immunities", [])
        self.effect_immunities.update(immunities)
    
    def update(self, delta_time: float = 0.0):
        """Update component state - called each turn"""
        self.current_turn += 1
        expired_effects = []
        
        # Tick all effects
        for instance_id, effect in self.active_effects.items():
            if effect.tick():
                expired_effects.append(instance_id)
        
        # Remove expired effects
        for instance_id in expired_effects:
            self.remove_effect(instance_id)
        
        # Trigger periodic effects (DoT, HoT, etc.)
        self._trigger_periodic_effects()
    
    def get_data(self) -> Dict[str, Any]:
        """Get component's current data"""
        return {
            "active_effects": {
                instance_id: {
                    "effect_id": effect.effect_id,
                    "effect_type": effect.effect_type.value,
                    "source_id": effect.source_id,
                    "source_type": effect.source_type,
                    "duration": effect.duration,
                    "stacks": effect.stacks,
                    "max_stacks": effect.max_stacks,
                    "stacking_rule": effect.stacking_rule.value,
                    "data": effect.data,
                    "created_turn": effect.created_turn,
                    "last_trigger_turn": effect.last_trigger_turn
                }
                for instance_id, effect in self.active_effects.items()
            },
            "effect_immunities": list(self.effect_immunities),
            "current_turn": self.current_turn
        }
    
    def set_data(self, data: Dict[str, Any]):
        """Set component data"""
        # Clear existing effects
        self.active_effects.clear()
        
        # Load effects
        effects_data = data.get("active_effects", {})
        for instance_id, effect_data in effects_data.items():
            effect = ActiveEffect(
                effect_id=effect_data["effect_id"],
                effect_type=EffectType(effect_data["effect_type"]),
                source_id=effect_data["source_id"],
                source_type=effect_data["source_type"],
                duration=effect_data.get("duration"),
                stacks=effect_data.get("stacks", 1),
                max_stacks=effect_data.get("max_stacks", 1),
                stacking_rule=StackingRule(effect_data["stacking_rule"]),
                data=effect_data.get("data", {}),
                created_turn=effect_data.get("created_turn", 0),
                last_trigger_turn=effect_data.get("last_trigger_turn", -1)
            )
            self.active_effects[instance_id] = effect
        
        # Load immunities
        self.effect_immunities = set(data.get("effect_immunities", []))
        self.current_turn = data.get("current_turn", 0)
    
    def apply_effect(self, effect_id: str, effect_data: Dict[str, Any], source_id: str, source_type: str = "skill") -> bool:
        """Apply an effect to this character"""
        # Check immunity
        if effect_id in self.effect_immunities:
            return False
        
        effect_type = EffectType(effect_data.get("type", "neutral"))
        
        # Check buff/debuff limits
        if not self._can_apply_effect(effect_type):
            return False
        
        # Create effect instance
        new_effect = ActiveEffect(
            effect_id=effect_id,
            effect_type=effect_type,
            source_id=source_id,
            source_type=source_type,
            duration=effect_data.get("duration"),
            stacks=1,
            max_stacks=effect_data.get("max_stacks", 1),
            stacking_rule=StackingRule(effect_data.get("stacking_rule", "no_stack")),
            data=effect_data.copy(),
            created_turn=self.current_turn
        )
        
        # Try to stack with existing effect
        stacked = False
        for instance_id, existing_effect in self.active_effects.items():
            if new_effect.can_stack_with(existing_effect):
                if new_effect.stacking_rule == StackingRule.INTENSITY:
                    existing_effect.stacks += 1
                    existing_effect.duration = new_effect.duration  # Reset duration
                elif new_effect.stacking_rule == StackingRule.DURATION:
                    if existing_effect.duration is not None and new_effect.duration is not None:
                        existing_effect.duration += new_effect.duration
                    
                stacked = True
                
                # Publish stack event
                event = GameEvent(
                    event_type="effect_stacked",
                    source=self,
                    target=self.character_id,
                    data={
                        "character_id": self.character_id,
                        "effect_id": effect_id,
                        "instance_id": instance_id,
                        "new_stacks": existing_effect.stacks,
                        "stacking_rule": new_effect.stacking_rule.value
                    }
                )
                event_bus.publish(event)
                break
        
        if not stacked:
            # Check if we need to remove an existing effect (for NO_STACK)
            if new_effect.stacking_rule == StackingRule.NO_STACK:
                to_remove = []
                for instance_id, existing_effect in self.active_effects.items():
                    if (existing_effect.effect_id == effect_id and
                        existing_effect.source_id == source_id):
                        to_remove.append(instance_id)
                
                for instance_id in to_remove:
                    self.remove_effect(instance_id)
            
            # Add new effect
            instance_id = str(uuid.uuid4())
            self.active_effects[instance_id] = new_effect
            
            # Publish apply event
            event = GameEvent(
                event_type="effect_applied",
                source=self,
                target=self.character_id,
                data={
                    "character_id": self.character_id,
                    "effect_id": effect_id,
                    "instance_id": instance_id,
                    "effect_data": effect_data,
                    "source_id": source_id,
                    "source_type": source_type
                }
            )
            event_bus.publish(event)
        
        return True
    
    def remove_effect(self, instance_id: str) -> bool:
        """Remove a specific effect instance"""
        if instance_id in self.active_effects:
            effect = self.active_effects.pop(instance_id)
            
            # Publish remove event
            event = GameEvent(
                event_type="effect_removed",
                source=self,
                target=self.character_id,
                data={
                    "character_id": self.character_id,
                    "effect_id": effect.effect_id,
                    "instance_id": instance_id,
                    "effect_data": effect.data
                }
            )
            event_bus.publish(event)
            return True
        return False
    
    def remove_effects_by_id(self, effect_id: str) -> int:
        """Remove all instances of a specific effect"""
        to_remove = [
            instance_id for instance_id, effect in self.active_effects.items()
            if effect.effect_id == effect_id
        ]
        
        for instance_id in to_remove:
            self.remove_effect(instance_id)
        
        return len(to_remove)
    
    def remove_effects_by_type(self, effect_type: EffectType) -> int:
        """Remove all effects of a specific type"""
        to_remove = [
            instance_id for instance_id, effect in self.active_effects.items()
            if effect.effect_type == effect_type
        ]
        
        for instance_id in to_remove:
            self.remove_effect(instance_id)
        
        return len(to_remove)
    
    def has_effect(self, effect_id: str) -> bool:
        """Check if character has a specific effect"""
        return any(effect.effect_id == effect_id for effect in self.active_effects.values())
    
    def get_effect_stacks(self, effect_id: str) -> int:
        """Get total stacks of a specific effect"""
        total_stacks = 0
        for effect in self.active_effects.values():
            if effect.effect_id == effect_id:
                total_stacks += effect.stacks
        return total_stacks
    
    def get_effects_by_type(self, effect_type: EffectType) -> List[ActiveEffect]:
        """Get all effects of a specific type"""
        return [effect for effect in self.active_effects.values() if effect.effect_type == effect_type]
    
    def add_immunity(self, effect_id: str):
        """Add immunity to a specific effect"""
        self.effect_immunities.add(effect_id)
        
        # Remove existing instances of this effect
        self.remove_effects_by_id(effect_id)
    
    def remove_immunity(self, effect_id: str):
        """Remove immunity to a specific effect"""
        self.effect_immunities.discard(effect_id)
    
    def _can_apply_effect(self, effect_type: EffectType) -> bool:
        """Check if we can apply another effect of this type"""
        if effect_type == EffectType.BUFF:
            current_buffs = len(self.get_effects_by_type(EffectType.BUFF))
            return current_buffs < self.max_buffs
        elif effect_type == EffectType.DEBUFF:
            current_debuffs = len(self.get_effects_by_type(EffectType.DEBUFF))
            return current_debuffs < self.max_debuffs
        
        return True  # No limit for other types
    
    def _trigger_periodic_effects(self):
        """Trigger periodic effects like DoT and HoT"""
        for instance_id, effect in self.active_effects.items():
            if effect.last_trigger_turn < self.current_turn:
                if effect.effect_type in [EffectType.DAMAGE_OVER_TIME, EffectType.HEAL_OVER_TIME]:
                    effect.last_trigger_turn = self.current_turn
                    
                    # Publish periodic trigger event
                    event = GameEvent(
                        event_type="periodic_effect_triggered",
                        source=self,
                        target=self.character_id,
                        data={
                            "character_id": self.character_id,
                            "effect_id": effect.effect_id,
                            "instance_id": instance_id,
                            "effect_type": effect.effect_type.value,
                            "effect_data": effect.data,
                            "stacks": effect.stacks
                        }
                    )
                    event_bus.publish(event)
    
    def _setup_event_listeners(self):
        """Set up event listeners for this component"""
        self.register_event_listener(
            "turn_started",
            self._on_turn_started
        )
        
        self.register_event_listener(
            "cleanse_effects",
            self._on_cleanse_effects
        )
    
    def _on_turn_started(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle turn started events"""
        if event.get_value("character_id") == self.character_id:
            self.update()
        return event
    
    def _on_cleanse_effects(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle effect cleansing"""
        if event.get_value("target_id") == self.character_id:
            cleanse_type = event.get_value("cleanse_type", "debuffs")
            
            if cleanse_type == "debuffs":
                self.remove_effects_by_type(EffectType.DEBUFF)
            elif cleanse_type == "buffs":
                self.remove_effects_by_type(EffectType.BUFF)
            elif cleanse_type == "all":
                self.active_effects.clear()
        
        return event
```

### Next Steps

This completes Step 2 of the implementation, establishing the character component system with:

1. **Base Component Interface**: Standardized component architecture with event integration
2. **Stats Component**: Dynamic stat calculation with layered modifiers and caching
3. **Effects Component**: Comprehensive status effect management with stacking rules

The next step (Step 3) will focus on implementing the abilities component and basic skill system.

### Integration Notes

- Components communicate through the event system
- Stats are calculated dynamically with intelligent caching
- Effects support complex stacking and interaction rules
- All components integrate with the battle context from Step 1

### Testing Recommendations

Create unit tests for:

- Stat modifier application and calculation
- Effect stacking and interaction rules
- Component event handling
- Cache invalidation and recalculation
- Effect duration and expiration
