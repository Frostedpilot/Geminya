"""
Stats Component - Handles character statistics and modifiers.

This component manages:
- Base character stats (HP, ATK, MAG, etc.)
- Stat modifiers from various sources (equipment, buffs, etc.)
- Dynamic stat calculation with layered modifier system
- Stat caps and validation
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

from . import BaseComponent
from ..core.event_system import GameEvent, event_bus, EventPhase

logger = logging.getLogger(__name__)

class StatType(Enum):
    """Available character stats"""
    HP = "hp"           # Health Points
    ATK = "atk"         # Physical Attack
    MAG = "mag"         # Magical Attack  
    VIT = "vit"         # Vitality (Physical Defense)
    SPR = "spr"         # Spirit (Magical Defense)
    INT = "int"         # Intelligence (Magic Power modifier)
    SPD = "spd"         # Speed (Action Gauge speed)
    LCK = "lck"         # Luck (Critical and proc chances)

class ModifierType(Enum):
    """Types of stat modifications"""
    FLAT = "flat"                    # +50 ATK
    PERCENTAGE = "percentage"        # +25% ATK
    MULTIPLICATIVE = "multiplicative" # x1.5 ATK

@dataclass
class StatModifier:
    """Individual stat modification"""
    modifier_id: str
    stat_type: StatType
    modifier_type: ModifierType
    value: float
    source: str
    layer: int = 0          # Higher layers apply later
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
            return base_value * total_value
        
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
        
        # Define calculation layers for proper modifier ordering
        self.calculation_layers = [
            "base",           # Base character stats
            "equipment",      # Equipment bonuses
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
        
        # Set base stats
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
        
        # Special caps for certain stats
        self.stat_caps[StatType.HP]["min"] = 1.0  # Characters must have at least 1 HP
        self.stat_caps[StatType.SPD]["min"] = 1.0  # Must have at least 1 speed
        
        self.cache_valid = False
        self._recalculate_stats()
        
        # Publish initialization event
        event = GameEvent(
            event_type="stats.initialized",
            source=self.character_id,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "base_stats": {stat.value: value for stat, value in self.base_stats.items()},
                "current_stats": {stat.value: value for stat, value in self.current_stats.items()}
            },
            phase=EventPhase.PROCESS
        )
        event_bus.publish(event)
        
        logger.debug("Initialized stats for character %s", self.character_id)
    
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
            "component_type": self.component_type,
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
            try:
                stat_type = StatType(stat_name)
                self.base_stats[stat_type] = float(value)
            except (ValueError, TypeError) as e:
                logger.warning("Invalid stat %s with value %s: %s", stat_name, value, e)
        
        # Ensure stat caps are initialized
        if not self.stat_caps:
            for stat in StatType:
                self.stat_caps[stat] = {
                    "min": 0.0,
                    "max": float('inf'),
                    "soft_cap": 999.0
                }
            # Special caps for certain stats
            self.stat_caps[StatType.HP]["min"] = 1.0
            self.stat_caps[StatType.SPD]["min"] = 1.0
        
        # Set modifiers
        modifiers_data = data.get("modifiers", {})
        self.modifiers.clear()
        
        for mod_id, mod_data in modifiers_data.items():
            try:
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
            except (ValueError, KeyError) as e:
                logger.warning("Invalid modifier %s: %s", mod_id, e)
        
        self.cache_valid = False
        self._recalculate_stats()
    
    def get_stat(self, stat_type: Union[StatType, str]) -> float:
        """Get current value of a stat"""
        if isinstance(stat_type, str):
            try:
                stat_type = StatType(stat_type)
            except ValueError:
                logger.warning("Unknown stat type: %s", stat_type)
                return 0.0
        
        if not self.cache_valid:
            self._recalculate_stats()
        
        return self.current_stats.get(stat_type, 0.0)
    
    def get_base_stat(self, stat_type: Union[StatType, str]) -> float:
        """Get base value of a stat"""
        if isinstance(stat_type, str):
            try:
                stat_type = StatType(stat_type)
            except ValueError:
                logger.warning("Unknown stat type: %s", stat_type)
                return 0.0
        
        return self.base_stats.get(stat_type, 0.0)
    
    def set_base_stat(self, stat_type: Union[StatType, str], value: float):
        """Set base value of a stat"""
        if isinstance(stat_type, str):
            try:
                stat_type = StatType(stat_type)
            except ValueError:
                logger.warning("Unknown stat type: %s", stat_type)
                return
        
        old_value = self.base_stats.get(stat_type, 0.0)
        self.base_stats[stat_type] = float(value)
        self.cache_valid = False
        
        # Publish stat change event
        event = GameEvent(
            event_type="stat.base_changed",
            source=self.character_id,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "stat_type": stat_type.value,
                "old_value": old_value,
                "new_value": value
            },
            phase=EventPhase.PROCESS
        )
        event_bus.publish(event)
        
        logger.debug("Set base stat %s to %f for character %s", 
                    stat_type.value, value, self.character_id)
    
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
                
                existing.stacks += modifier.stacks
                existing.stacks = min(existing.stacks, existing.max_stacks)
                self.cache_valid = False
                
                logger.debug("Stacked modifier %s to %d stacks for character %s", 
                           modifier.modifier_id, existing.stacks, self.character_id)
                return True
            else:
                logger.warning("Modifier %s already exists and cannot stack", modifier.modifier_id)
                return False
        
        # Add new modifier
        self.modifiers[modifier.modifier_id] = modifier
        self.cache_valid = False
        
        # Publish modifier added event
        event = GameEvent(
            event_type="stat.modifier_added",
            source=modifier.source,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "modifier_id": modifier.modifier_id,
                "stat_type": modifier.stat_type.value,
                "modifier_type": modifier.modifier_type.value,
                "value": modifier.value,
                "stacks": modifier.stacks
            },
            phase=EventPhase.PROCESS
        )
        event_bus.publish(event)
        
        logger.debug("Added modifier %s (%s %s %f) to character %s", 
                    modifier.modifier_id, modifier.stat_type.value, 
                    modifier.modifier_type.value, modifier.value, self.character_id)
        return True
    
    def remove_modifier(self, modifier_id: str) -> bool:
        """Remove a stat modifier"""
        if modifier_id not in self.modifiers:
            return False
        
        modifier = self.modifiers[modifier_id]
        del self.modifiers[modifier_id]
        self.cache_valid = False
        
        # Publish modifier removed event
        event = GameEvent(
            event_type="stat.modifier_removed",
            source=modifier.source,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "modifier_id": modifier_id,
                "stat_type": modifier.stat_type.value,
                "reason": "expired" if modifier.duration == 0 else "removed"
            },
            phase=EventPhase.PROCESS
        )
        event_bus.publish(event)
        
        logger.debug("Removed modifier %s from character %s", 
                    modifier_id, self.character_id)
        return True
    
    def apply_leader_bonus(self) -> bool:
        """Apply +10% leader bonus to all base stats"""
        # Remove any existing leader bonus first
        self.remove_modifier("leader_bonus_hp")
        self.remove_modifier("leader_bonus_atk") 
        self.remove_modifier("leader_bonus_mag")
        self.remove_modifier("leader_bonus_vit")
        self.remove_modifier("leader_bonus_spr")
        self.remove_modifier("leader_bonus_int")
        self.remove_modifier("leader_bonus_spd")
        self.remove_modifier("leader_bonus_lck")
        
        # Apply +10% bonus to each stat
        stats_to_boost = [StatType.HP, StatType.ATK, StatType.MAG, StatType.VIT, 
                         StatType.SPR, StatType.INT, StatType.SPD, StatType.LCK]
        
        for stat in stats_to_boost:
            bonus_modifier = StatModifier(
                modifier_id=f"leader_bonus_{stat.value}",
                stat_type=stat,
                modifier_type=ModifierType.PERCENTAGE,
                value=0.10,  # +10%
                source="leader_designation",
                layer=1,  # Apply in base layer
                duration=None  # Permanent while leader
            )
            self.add_modifier(bonus_modifier)
        
        logger.info("Applied leader bonus to character %s", self.character_id)
        return True
    
    def remove_leader_bonus(self) -> bool:
        """Remove leader bonus modifiers"""
        stats_removed = 0
        stats_to_remove = [StatType.HP, StatType.ATK, StatType.MAG, StatType.VIT,
                          StatType.SPR, StatType.INT, StatType.SPD, StatType.LCK]
        
        for stat in stats_to_remove:
            if self.remove_modifier(f"leader_bonus_{stat.value}"):
                stats_removed += 1
        
        logger.info("Removed leader bonus from character %s (%d stats)", 
                   self.character_id, stats_removed)
        return stats_removed > 0
    
    def get_modifiers_for_stat(self, stat_type: Union[StatType, str]) -> List[StatModifier]:
        """Get all modifiers affecting a specific stat"""
        if isinstance(stat_type, str):
            try:
                stat_type = StatType(stat_type)
            except ValueError:
                return []
        
        return [mod for mod in self.modifiers.values() if mod.stat_type == stat_type]
    
    def _setup_event_listeners(self):
        """Set up event listeners for this component"""
        def on_stat_requested(event: GameEvent) -> GameEvent:
            """Handle stat value requests"""
            if event.data.get("character_id") == self.character_id:
                stat_name = event.data.get("stat_name")
                if stat_name:
                    value = self.get_stat(stat_name)
                    event.modify("stat_value", value)
            return event
        
        self.register_event_listener("stat.request", on_stat_requested)
    
    def _recalculate_stats(self):
        """Recalculate all current stats from base stats and modifiers"""
        # Start with base stats
        for stat_type in StatType:
            self.current_stats[stat_type] = self.base_stats.get(stat_type, 0.0)
        
        # Apply modifiers by layer and type
        for layer_name in self.calculation_layers:
            # Get modifiers for this layer
            layer_modifiers = [mod for mod in self.modifiers.values() if mod.layer == self._get_layer_priority(layer_name)]
            
            # Sort by modifier type (flat -> percentage -> multiplicative)
            flat_mods = [mod for mod in layer_modifiers if mod.modifier_type == ModifierType.FLAT]
            pct_mods = [mod for mod in layer_modifiers if mod.modifier_type == ModifierType.PERCENTAGE]
            mult_mods = [mod for mod in layer_modifiers if mod.modifier_type == ModifierType.MULTIPLICATIVE]
            
            # Apply in order: flat, percentage, multiplicative
            for modifier_group in [flat_mods, pct_mods, mult_mods]:
                for modifier in modifier_group:
                    old_value = self.current_stats[modifier.stat_type]
                    new_value = modifier.apply(old_value)
                    self.current_stats[modifier.stat_type] = new_value
        
        # Apply stat caps
        for stat_type in StatType:
            caps = self.stat_caps[stat_type]
            value = self.current_stats[stat_type]
            
            # Apply hard caps
            value = max(value, caps["min"])
            value = min(value, caps["max"])
            
            # Apply soft cap (diminishing returns)
            soft_cap = caps["soft_cap"]
            if value > soft_cap:
                excess = value - soft_cap
                # Diminishing returns formula: soft_cap + excess * 0.5
                value = soft_cap + (excess * 0.5)
            
            self.current_stats[stat_type] = value
        
        self.cache_valid = True
        
        # Publish stats recalculated event
        event = GameEvent(
            event_type="stats.recalculated",
            source=self.character_id,
            target=self.character_id,
            data={
                "character_id": self.character_id,
                "current_stats": {stat.value: value for stat, value in self.current_stats.items()}
            },
            phase=EventPhase.PROCESS
        )
        event_bus.publish(event)
    
    def _get_layer_priority(self, layer_name: str) -> int:
        """Get numerical priority for a layer name"""
        try:
            return self.calculation_layers.index(layer_name)
        except ValueError:
            return 999  # Unknown layers go last
