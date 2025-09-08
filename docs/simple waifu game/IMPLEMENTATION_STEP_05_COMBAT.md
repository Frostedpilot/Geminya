# Implementation Guide - Step 5: Combat System and Damage Resolution

## Damage Calculation and Combat Resolution

### Overview

This step implements the combat system that handles damage calculation, healing, status effect application, and all combat resolution mechanics. It includes the universal scaling formula, potency calculations, and the complete combat resolution pipeline described in the game design.

### Prerequisites

- Completed Step 1 (Foundation Setup)
- Completed Step 2 (Component System)  
- Completed Step 3 (Abilities and Skills)
- Completed Step 4 (Turn System)
- Understanding of the universal scaling formula and combat mechanics

### Step 5.1: Combat System Implementation

Create the core combat system that handles damage and healing calculations:

**File: `src/game/systems/combat_system.py`**

```python
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import random
import math

from ..core.event_system import GameEvent, event_bus
from ..core.battle_context import BattleContext

class DamageType(Enum):
    """Types of damage"""
    PHYSICAL = "physical"
    MAGICAL = "magical"
    TRUE = "true"  # Ignores all defenses
    FIXED = "fixed"  # Fixed amount, no scaling

class ResistanceType(Enum):
    """Types of resistances"""
    ELEMENTAL = "elemental"
    PHYSICAL = "physical"
    MAGICAL = "magical"
    STATUS = "status"

@dataclass
class DamageInstance:
    """A single damage calculation instance"""
    source_id: str
    target_id: str
    skill_id: str
    damage_type: DamageType
    base_damage: float
    scaling_stat: str
    scaling_multiplier: float = 1.0
    element: Optional[str] = None
    can_crit: bool = True
    can_dodge: bool = True
    defense_penetration: float = 0.0
    modifiers: Dict[str, float] = None
    
    def __post_init__(self):
        if self.modifiers is None:
            self.modifiers = {}

@dataclass
class DamageResult:
    """Result of damage calculation"""
    base_damage: float
    scaled_damage: float
    final_damage: float
    is_critical: bool = False
    is_dodged: bool = False
    damage_reductions: Dict[str, float] = None
    damage_multipliers: Dict[str, float] = None
    
    def __post_init__(self):
        if self.damage_reductions is None:
            self.damage_reductions = {}
        if self.damage_multipliers is None:
            self.damage_multipliers = {}

@dataclass
class HealingInstance:
    """A single healing calculation instance"""
    source_id: str
    target_id: str
    skill_id: str
    base_healing: float
    scaling_stat: str
    scaling_multiplier: float = 1.0
    spr_scaling: float = 1.0
    modifiers: Dict[str, float] = None
    
    def __post_init__(self):
        if self.modifiers is None:
            self.modifiers = {}

@dataclass
class HealingResult:
    """Result of healing calculation"""
    base_healing: float
    scaled_healing: float
    final_healing: float
    overheal: float = 0.0
    healing_multipliers: Dict[str, float] = None
    
    def __post_init__(self):
        if self.healing_multipliers is None:
            self.healing_multipliers = {}

class CombatSystem:
    """System for handling combat calculations and resolution"""
    
    def __init__(self, battle_context: BattleContext):
        self.battle_context = battle_context
        self.damage_history: List[Tuple[DamageInstance, DamageResult]] = []
        self.healing_history: List[Tuple[HealingInstance, HealingResult]] = []
        
        self._setup_event_listeners()
    
    def calculate_damage(self, damage_instance: DamageInstance) -> DamageResult:
        """Calculate damage using the universal scaling formula"""
        
        # Get source and target characters
        source_char = self.battle_context.get_character(damage_instance.source_id)
        target_char = self.battle_context.get_character(damage_instance.target_id)
        
        if not source_char or not target_char:
            return DamageResult(0, 0, 0)
        
        # Get components
        source_stats = source_char.get("components", {}).get("stats")
        target_stats = target_char.get("components", {}).get("stats")
        target_state = target_char.get("components", {}).get("state")
        
        if not source_stats or not target_stats or not target_state:
            return DamageResult(0, 0, 0)
        
        # Step 1: Calculate potency value (pre-scaling damage)
        potency_value = self._calculate_potency_value(damage_instance, source_stats, target_stats)
        
        # Step 2: Apply universal scaling formula
        scaled_damage = self._apply_universal_scaling(potency_value, damage_instance)
        
        # Step 3: Check for dodge
        is_dodged = self._check_dodge(damage_instance, source_stats, target_stats)
        if is_dodged:
            return DamageResult(
                base_damage=damage_instance.base_damage,
                scaled_damage=scaled_damage,
                final_damage=0,
                is_dodged=True
            )
        
        # Step 4: Check for critical hit
        is_critical = self._check_critical(damage_instance, source_stats, target_stats)
        
        # Step 5: Apply final modifiers
        final_damage = self._apply_final_modifiers(
            scaled_damage, damage_instance, source_char, target_char, is_critical
        )
        
        # Ensure minimum damage
        final_damage = max(1, final_damage)
        
        result = DamageResult(
            base_damage=damage_instance.base_damage,
            scaled_damage=scaled_damage,
            final_damage=final_damage,
            is_critical=is_critical,
            is_dodged=False
        )
        
        # Store in history
        self.damage_history.append((damage_instance, result))
        
        return result
    
    def apply_damage(self, damage_instance: DamageInstance) -> DamageResult:
        """Calculate and apply damage to a target"""
        
        # Calculate damage
        result = self.calculate_damage(damage_instance)
        
        # Publish pre-damage event (allows for damage modification)
        pre_damage_event = GameEvent(
            event_type="damage_calculated",
            source=damage_instance.source_id,
            target=damage_instance.target_id,
            data={
                "damage_instance": damage_instance,
                "damage_result": result,
                "source_id": damage_instance.source_id,
                "target_id": damage_instance.target_id,
                "skill_id": damage_instance.skill_id
            }
        )
        pre_damage_event = event_bus.publish(pre_damage_event)
        
        # Check if damage was cancelled
        if pre_damage_event.cancelled:
            return DamageResult(0, 0, 0)
        
        # Apply any modifications from events
        modified_damage = pre_damage_event.get_value("final_damage", result.final_damage)
        result.final_damage = modified_damage
        
        # Apply damage to target
        target_char = self.battle_context.get_character(damage_instance.target_id)
        if target_char:
            target_state = target_char.get("components", {}).get("state")
            if target_state:
                actual_damage = target_state.modify_hp(-result.final_damage, f"damage_from_{damage_instance.source_id}")
                
                # Update result with actual damage dealt
                result.final_damage = abs(actual_damage)
        
        # Publish damage dealt event
        damage_dealt_event = GameEvent(
            event_type="damage_dealt",
            source=damage_instance.source_id,
            target=damage_instance.target_id,
            data={
                "damage_instance": damage_instance,
                "damage_result": result,
                "source_id": damage_instance.source_id,
                "target_id": damage_instance.target_id,
                "skill_id": damage_instance.skill_id,
                "final_damage": result.final_damage,
                "is_critical": result.is_critical,
                "is_dodged": result.is_dodged
            }
        )
        event_bus.publish(damage_dealt_event)
        
        return result
    
    def calculate_healing(self, healing_instance: HealingInstance) -> HealingResult:
        """Calculate healing using the healing potency formula"""
        
        # Get source and target characters
        source_char = self.battle_context.get_character(healing_instance.source_id)
        target_char = self.battle_context.get_character(healing_instance.target_id)
        
        if not source_char or not target_char:
            return HealingResult(0, 0, 0)
        
        # Get components
        source_stats = source_char.get("components", {}).get("stats")
        target_state = target_char.get("components", {}).get("state")
        
        if not source_stats or not target_state:
            return HealingResult(0, 0, 0)
        
        # Calculate healing potency: (INT * 0.5) + (SPR * 1.25)
        int_stat = source_stats.get_stat("int")
        spr_stat = source_stats.get_stat("spr")
        potency_value = (int_stat * 0.5) + (spr_stat * healing_instance.spr_scaling)
        
        # Apply base healing
        scaled_healing = healing_instance.base_healing + (potency_value * healing_instance.scaling_multiplier)
        
        # Apply modifiers
        final_healing = scaled_healing
        for modifier_name, modifier_value in healing_instance.modifiers.items():
            final_healing *= modifier_value
        
        # Ensure minimum healing
        final_healing = max(1, final_healing)
        
        result = HealingResult(
            base_healing=healing_instance.base_healing,
            scaled_healing=scaled_healing,
            final_healing=final_healing
        )
        
        # Store in history
        self.healing_history.append((healing_instance, result))
        
        return result
    
    def apply_healing(self, healing_instance: HealingInstance) -> HealingResult:
        """Calculate and apply healing to a target"""
        
        # Calculate healing
        result = self.calculate_healing(healing_instance)
        
        # Publish pre-healing event
        pre_heal_event = GameEvent(
            event_type="healing_calculated",
            source=healing_instance.source_id,
            target=healing_instance.target_id,
            data={
                "healing_instance": healing_instance,
                "healing_result": result,
                "source_id": healing_instance.source_id,
                "target_id": healing_instance.target_id,
                "skill_id": healing_instance.skill_id
            }
        )
        pre_heal_event = event_bus.publish(pre_heal_event)
        
        # Check if healing was cancelled
        if pre_heal_event.cancelled:
            return HealingResult(0, 0, 0)
        
        # Apply any modifications from events
        modified_healing = pre_heal_event.get_value("final_healing", result.final_healing)
        result.final_healing = modified_healing
        
        # Apply healing to target
        target_char = self.battle_context.get_character(healing_instance.target_id)
        if target_char:
            target_state = target_char.get("components", {}).get("state")
            if target_state:
                old_hp = target_state.current_hp
                actual_healing = target_state.modify_hp(result.final_healing, f"healing_from_{healing_instance.source_id}")
                
                # Calculate overheal
                if old_hp + result.final_healing > target_state.max_hp:
                    result.overheal = (old_hp + result.final_healing) - target_state.max_hp
                
                # Update result with actual healing done
                result.final_healing = actual_healing
        
        # Publish healing applied event
        heal_applied_event = GameEvent(
            event_type="healing_applied",
            source=healing_instance.source_id,
            target=healing_instance.target_id,
            data={
                "healing_instance": healing_instance,
                "healing_result": result,
                "source_id": healing_instance.source_id,
                "target_id": healing_instance.target_id,
                "skill_id": healing_instance.skill_id,
                "final_healing": result.final_healing,
                "overheal": result.overheal
            }
        )
        event_bus.publish(heal_applied_event)
        
        return result
    
    def _calculate_potency_value(self, damage_instance: DamageInstance, 
                                source_stats, target_stats) -> float:
        """Calculate initial damage potency value"""
        
        # Get scaling stat value
        scaling_value = source_stats.get_stat(damage_instance.scaling_stat)
        
        # Base damage calculation
        base_damage = scaling_value * damage_instance.scaling_multiplier
        
        # Apply damage type specific calculations
        if damage_instance.damage_type == DamageType.PHYSICAL:
            return self._calculate_physical_potency(base_damage, target_stats, damage_instance.defense_penetration)
        elif damage_instance.damage_type == DamageType.MAGICAL:
            return self._calculate_magical_potency(base_damage, target_stats, damage_instance.defense_penetration)
        elif damage_instance.damage_type == DamageType.TRUE:
            return base_damage  # True damage ignores defenses
        elif damage_instance.damage_type == DamageType.FIXED:
            return damage_instance.base_damage  # Fixed damage doesn't scale
        
        return base_damage
    
    def _calculate_physical_potency(self, base_damage: float, target_stats, defense_penetration: float) -> float:
        """Calculate physical damage potency with defense"""
        target_vit = target_stats.get_stat("vit")
        effective_vit = target_vit * (1 - defense_penetration)
        
        # Physical damage formula: base_damage * (1 - vit/(150 + vit))
        defense_reduction = effective_vit / (150 + effective_vit)
        final_damage = base_damage * (1 - defense_reduction)
        
        return final_damage
    
    def _calculate_magical_potency(self, base_damage: float, target_stats, defense_penetration: float) -> float:
        """Calculate magical damage potency with magic defense"""
        target_vit = target_stats.get_stat("vit") 
        target_spr = target_stats.get_stat("spr")
        
        # Effective defense with penetration
        effective_vit = target_vit * (1 - defense_penetration)
        effective_spr = target_spr * (1 - defense_penetration)
        
        # Magical damage formula: base_damage * (1 - (vit*0.6 + spr*0.4)/(150 + vit*0.6 + spr*0.4))
        combined_defense = (effective_vit * 0.6) + (effective_spr * 0.4)
        defense_reduction = combined_defense / (150 + combined_defense)
        final_damage = base_damage * (1 - defense_reduction)
        
        return final_damage
    
    def _apply_universal_scaling(self, potency_value: float, damage_instance: DamageInstance) -> float:
        """Apply the universal scaling formula"""
        
        # Get scaling parameters from skill data or use defaults
        skill_data = damage_instance.modifiers
        floor = skill_data.get("floor", 20)
        softcap_1 = skill_data.get("softcap_1", 50)
        softcap_2 = skill_data.get("softcap_2", 200)
        post_cap_rate = skill_data.get("post_cap_rate", 0.5)
        
        # Apply universal scaling formula
        if potency_value <= softcap_1:
            return floor
        elif softcap_1 < potency_value <= softcap_2:
            return floor + (potency_value - softcap_1)
        else:  # potency_value > softcap_2
            return (floor + (softcap_2 - softcap_1)) + ((potency_value - softcap_2) * post_cap_rate)
    
    def _check_dodge(self, damage_instance: DamageInstance, source_stats, target_stats) -> bool:
        """Check if attack is dodged"""
        if not damage_instance.can_dodge:
            return False
        
        # Dodge formula: 5 + ((Target SPD + Target LCK) - (Attacker SPD + Attacker LCK)) / 20
        # Capped between 5% and 40%
        
        target_spd = target_stats.get_stat("spd")
        target_lck = target_stats.get_stat("lck")
        source_spd = source_stats.get_stat("spd")
        source_lck = source_stats.get_stat("lck")
        
        dodge_chance = 5 + ((target_spd + target_lck) - (source_spd + source_lck)) / 20
        dodge_chance = max(5, min(40, dodge_chance))  # Cap between 5% and 40%
        
        roll = random.uniform(0, 100)
        is_dodged = roll < dodge_chance
        
        # Publish dodge check event
        dodge_event = GameEvent(
            event_type="dodge_check",
            source=damage_instance.source_id,
            target=damage_instance.target_id,
            data={
                "dodge_chance": dodge_chance,
                "roll": roll,
                "is_dodged": is_dodged,
                "source_id": damage_instance.source_id,
                "target_id": damage_instance.target_id
            }
        )
        event_bus.publish(dodge_event)
        
        return is_dodged
    
    def _check_critical(self, damage_instance: DamageInstance, source_stats, target_stats) -> bool:
        """Check if attack is a critical hit"""
        if not damage_instance.can_crit:
            return False
        
        # Critical formula: 5 + (Attacker LCK - Target LCK) / 10
        # Capped between 5% and 50%
        
        source_lck = source_stats.get_stat("lck")
        target_lck = target_stats.get_stat("lck")
        
        crit_chance = 5 + (source_lck - target_lck) / 10
        crit_chance = max(5, min(50, crit_chance))  # Cap between 5% and 50%
        
        roll = random.uniform(0, 100)
        is_critical = roll < crit_chance
        
        # Publish critical check event
        crit_event = GameEvent(
            event_type="critical_check",
            source=damage_instance.source_id,
            target=damage_instance.target_id,
            data={
                "crit_chance": crit_chance,
                "roll": roll,
                "is_critical": is_critical,
                "source_id": damage_instance.source_id,
                "target_id": damage_instance.target_id
            }
        )
        event_bus.publish(crit_event)
        
        return is_critical
    
    def _apply_final_modifiers(self, base_damage: float, damage_instance: DamageInstance,
                              source_char: Dict[str, Any], target_char: Dict[str, Any], 
                              is_critical: bool) -> float:
        """Apply final damage modifiers"""
        final_damage = base_damage
        
        # Critical hit multiplier
        if is_critical:
            # Check if volatile field is active (2.0x crits instead of 1.5x)
            crit_multiplier = 1.5
            battlefield_conditions = self.battle_context.battlefield_conditions
            if "volatile_field" in battlefield_conditions:
                crit_multiplier = 2.0
            
            final_damage *= crit_multiplier
        
        # Apply elemental modifiers
        if damage_instance.element:
            elemental_modifier = self._get_elemental_modifier(
                damage_instance.element, target_char, source_char
            )
            final_damage *= elemental_modifier
        
        # Apply other damage modifiers from skills/effects
        for modifier_name, modifier_value in damage_instance.modifiers.items():
            if modifier_name.startswith("damage_"):
                final_damage *= modifier_value
        
        return final_damage
    
    def _get_elemental_modifier(self, element: str, target_char: Dict[str, Any], 
                               source_char: Dict[str, Any]) -> float:
        """Get elemental damage modifier"""
        modifier = 1.0
        
        # Check target's elemental resistances/weaknesses
        target_effects = target_char.get("components", {}).get("effects")
        if target_effects:
            # Check for elemental resistance effects
            for effect in target_effects.active_effects.values():
                effect_data = effect.data
                if effect_data.get("type") == "elemental_resistance":
                    if element in effect_data.get("elements", []):
                        modifier *= effect_data.get("resistance_multiplier", 1.0)
                elif effect_data.get("type") == "elemental_weakness":
                    if element in effect_data.get("elements", []):
                        modifier *= effect_data.get("weakness_multiplier", 1.0)
        
        # Check battlefield conditions for elemental effects
        battlefield_conditions = self.battle_context.battlefield_conditions
        for condition_id, condition_data in battlefield_conditions.items():
            if condition_data.get("type") == "elemental_amplification":
                if element in condition_data.get("elements", []):
                    modifier *= condition_data.get("amplification", 1.0)
        
        return modifier
    
    def _setup_event_listeners(self):
        """Set up event listeners for the combat system"""
        event_bus.register_handler(
            "damage_calculated",
            self._on_damage_calculated,
            priority=600  # Higher priority to process before other effects
        )
        
        event_bus.register_handler(
            "heal_calculated", 
            self._on_heal_calculated,
            priority=600
        )
        
        event_bus.register_handler(
            "periodic_effect_triggered",
            self._on_periodic_effect_triggered
        )
    
    def _on_damage_calculated(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle damage calculation events from skill system"""
        # Extract damage information from skill effect
        effect = event.get_value("effect", {})
        caster_id = event.get_value("caster_id")
        target_id = event.get_value("target_id")
        skill_id = event.get_value("skill_id")
        
        if effect.get("type") == "damage" and caster_id and target_id:
            # Create damage instance from effect data
            damage_instance = DamageInstance(
                source_id=caster_id,
                target_id=target_id,
                skill_id=skill_id,
                damage_type=DamageType(effect.get("damage_type", "physical")),
                base_damage=effect.get("base_damage", 0),
                scaling_stat=effect.get("scaling", "atk"),
                scaling_multiplier=effect.get("scaling_multiplier", 1.0),
                element=effect.get("element"),
                defense_penetration=effect.get("defense_penetration", 0.0),
                modifiers=effect.get("modifiers", {})
            )
            
            # Apply damage
            result = self.apply_damage(damage_instance)
            
            # Modify event with result
            event.modify("damage_result", result)
            event.modify("final_damage", result.final_damage)
        
        return event
    
    def _on_heal_calculated(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle healing calculation events from skill system"""
        # Extract healing information from skill effect
        effect = event.get_value("effect", {})
        caster_id = event.get_value("caster_id")
        target_id = event.get_value("target_id")
        skill_id = event.get_value("skill_id")
        
        if effect.get("type") == "heal" and caster_id and target_id:
            # Create healing instance from effect data
            healing_instance = HealingInstance(
                source_id=caster_id,
                target_id=target_id,
                skill_id=skill_id,
                base_healing=effect.get("base_heal", 0),
                scaling_stat=effect.get("scaling", "int"),
                scaling_multiplier=effect.get("scaling_multiplier", 1.0),
                spr_scaling=effect.get("spr_scaling", 1.25),
                modifiers=effect.get("modifiers", {})
            )
            
            # Apply healing
            result = self.apply_healing(healing_instance)
            
            # Modify event with result
            event.modify("healing_result", result)
            event.modify("final_healing", result.final_healing)
        
        return event
    
    def _on_periodic_effect_triggered(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle periodic effects like DoT and HoT"""
        effect_type = event.get_value("effect_type")
        effect_data = event.get_value("effect_data", {})
        source_id = event.get_value("effect_data", {}).get("source_id", "unknown")
        target_id = event.get_value("character_id")
        stacks = event.get_value("stacks", 1)
        
        if effect_type == "damage_over_time":
            # Create damage instance for DoT
            damage_per_stack = effect_data.get("damage_per_stack", 20)
            total_base_damage = damage_per_stack * stacks
            
            damage_instance = DamageInstance(
                source_id=source_id,
                target_id=target_id,
                skill_id="dot_effect",
                damage_type=DamageType(effect_data.get("damage_type", "magical")),
                base_damage=total_base_damage,
                scaling_stat=effect_data.get("scaling_stat", "mag"),
                scaling_multiplier=effect_data.get("scaling_multiplier", 0.3),
                can_crit=False,  # DoT usually can't crit
                can_dodge=False  # DoT usually can't be dodged
            )
            
            self.apply_damage(damage_instance)
        
        elif effect_type == "heal_over_time":
            # Create healing instance for HoT
            healing_per_stack = effect_data.get("healing_per_stack", 30)
            total_base_healing = healing_per_stack * stacks
            
            healing_instance = HealingInstance(
                source_id=source_id,
                target_id=target_id,
                skill_id="hot_effect",
                base_healing=total_base_healing,
                scaling_stat=effect_data.get("scaling_stat", "int"),
                scaling_multiplier=effect_data.get("scaling_multiplier", 0.5),
                spr_scaling=effect_data.get("spr_scaling", 1.0)
            )
            
            self.apply_healing(healing_instance)
        
        return event
```

### Step 5.2: Status Effect Application System

Create a system for applying status effects with probability calculations:

**File: `src/game/systems/status_system.py`**

```python
from typing import Dict, Any, List, Optional
import random

from ..core.event_system import GameEvent, event_bus
from ..core.battle_context import BattleContext
from ..components.effects_component import EffectType

class StatusSystem:
    """System for applying and managing status effects"""
    
    def __init__(self, battle_context: BattleContext):
        self.battle_context = battle_context
        self.status_definitions = self._load_status_definitions()
        
        self._setup_event_listeners()
    
    def apply_status_effect(self, source_id: str, target_id: str, status_id: str, 
                           duration: Optional[int] = None, probability: float = 1.0,
                           source_type: str = "skill") -> bool:
        """Apply a status effect with probability check"""
        
        # Get source and target characters
        source_char = self.battle_context.get_character(source_id)
        target_char = self.battle_context.get_character(target_id)
        
        if not source_char or not target_char:
            return False
        
        # Get components
        source_stats = source_char.get("components", {}).get("stats")
        target_stats = target_char.get("components", {}).get("stats")
        target_effects = target_char.get("components", {}).get("effects")
        
        if not source_stats or not target_stats or not target_effects:
            return False
        
        # Calculate application probability
        final_probability = self._calculate_status_probability(
            probability, source_stats, target_stats, status_id
        )
        
        # Roll for application
        roll = random.uniform(0, 100)
        if roll >= final_probability:
            return False  # Failed to apply
        
        # Get status effect definition
        status_data = self.status_definitions.get(status_id, {})
        if not status_data:
            return False
        
        # Override duration if specified
        if duration is not None:
            status_data = status_data.copy()
            status_data["duration"] = duration
        
        # Apply the status effect
        success = target_effects.apply_effect(
            effect_id=status_id,
            effect_data=status_data,
            source_id=source_id,
            source_type=source_type
        )
        
        if success:
            # Publish status application event
            event = GameEvent(
                event_type="status_effect_applied",
                source=source_id,
                target=target_id,
                data={
                    "source_id": source_id,
                    "target_id": target_id,
                    "status_id": status_id,
                    "status_data": status_data,
                    "probability": final_probability,
                    "roll": roll,
                    "source_type": source_type
                }
            )
            event_bus.publish(event)
        
        return success
    
    def remove_status_effect(self, target_id: str, status_id: str) -> bool:
        """Remove a specific status effect"""
        target_char = self.battle_context.get_character(target_id)
        if not target_char:
            return False
        
        target_effects = target_char.get("components", {}).get("effects")
        if not target_effects:
            return False
        
        removed_count = target_effects.remove_effects_by_id(status_id)
        return removed_count > 0
    
    def cleanse_effects(self, target_id: str, cleanse_type: str = "debuffs") -> int:
        """Cleanse status effects from a target"""
        # Publish cleanse event for the effects component to handle
        event = GameEvent(
            event_type="cleanse_effects",
            target=target_id,
            data={
                "target_id": target_id,
                "cleanse_type": cleanse_type
            }
        )
        event_bus.publish(event)
        
        return 0  # Effects component will handle the actual cleansing
    
    def _calculate_status_probability(self, base_probability: float, source_stats, 
                                    target_stats, status_id: str) -> float:
        """Calculate final status application probability"""
        
        # Status application formula: Base% + ((Attacker LCK - Target LCK) / 10)
        # Capped between 10% and 90%
        
        source_lck = source_stats.get_stat("lck")
        target_lck = target_stats.get_stat("lck")
        
        luck_modifier = (source_lck - target_lck) / 10
        final_probability = (base_probability * 100) + luck_modifier
        
        # Apply caps
        final_probability = max(10, min(90, final_probability))
        
        return final_probability
    
    def _load_status_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Load status effect definitions"""
        # This would eventually load from JSON files
        # For now, return basic status effects
        
        return {
            "burning": {
                "type": "damage_over_time",
                "effect_type": "debuff",
                "duration": 3,
                "damage_per_stack": 20,
                "scaling_stat": "mag",
                "scaling_multiplier": 0.3,
                "damage_type": "fire",
                "max_stacks": 5,
                "stacking_rule": "intensity",
                "description": "Taking fire damage over time"
            },
            "regen": {
                "type": "heal_over_time", 
                "effect_type": "buff",
                "duration": 3,
                "healing_per_stack": 30,
                "scaling_stat": "int",
                "scaling_multiplier": 0.5,
                "max_stacks": 3,
                "stacking_rule": "intensity",
                "description": "Regenerating HP over time"
            },
            "poisoned": {
                "type": "damage_over_time",
                "effect_type": "debuff", 
                "duration": 4,
                "damage_per_stack": 15,
                "scaling_stat": "mag",
                "scaling_multiplier": 0.2,
                "damage_type": "poison",
                "max_stacks": 10,
                "stacking_rule": "intensity",
                "description": "Taking poison damage over time"
            },
            "stunned": {
                "type": "disable",
                "effect_type": "debuff",
                "duration": 1,
                "disables": ["actions"],
                "max_stacks": 1,
                "stacking_rule": "duration",
                "description": "Cannot take actions"
            },
            "guard_stance": {
                "type": "stat_modifier",
                "effect_type": "buff",
                "duration": 1,
                "stat_modifiers": [
                    {
                        "stat_type": "vit",
                        "modifier_type": "multiplicative",
                        "value": 2.0,
                        "layer": 3
                    },
                    {
                        "stat_type": "spr", 
                        "modifier_type": "multiplicative",
                        "value": 2.0,
                        "layer": 3
                    }
                ],
                "max_stacks": 1,
                "stacking_rule": "no_stack",
                "description": "Doubling VIT and SPR"
            },
            "provoked": {
                "type": "targeting_override",
                "effect_type": "debuff",
                "duration": 1,
                "forced_target": None,  # Set when applied
                "max_stacks": 1,
                "stacking_rule": "no_stack", 
                "description": "Forced to target specific character"
            },
            "rally": {
                "type": "stat_modifier",
                "effect_type": "buff",
                "duration": 3,
                "stat_modifiers": [
                    {
                        "stat_type": "atk",
                        "modifier_type": "percentage",
                        "value": 0.2,
                        "layer": 3
                    },
                    {
                        "stat_type": "mag",
                        "modifier_type": "percentage", 
                        "value": 0.2,
                        "layer": 3
                    }
                ],
                "max_stacks": 1,
                "stacking_rule": "duration",
                "description": "+20% ATK and MAG"
            },
            "weaken": {
                "type": "stat_modifier",
                "effect_type": "debuff",
                "duration": 3,
                "stat_modifiers": [
                    {
                        "stat_type": "atk",
                        "modifier_type": "percentage",
                        "value": -0.2,
                        "layer": 3
                    },
                    {
                        "stat_type": "mag",
                        "modifier_type": "percentage",
                        "value": -0.2,
                        "layer": 3
                    }
                ],
                "max_stacks": 1,
                "stacking_rule": "duration",
                "description": "-20% ATK and MAG"
            },
            "haste": {
                "type": "stat_modifier",
                "effect_type": "buff",
                "duration": 3,
                "stat_modifiers": [
                    {
                        "stat_type": "spd",
                        "modifier_type": "percentage",
                        "value": 0.3,
                        "layer": 3
                    }
                ],
                "max_stacks": 1,
                "stacking_rule": "duration",
                "description": "+30% SPD"
            },
            "slow": {
                "type": "stat_modifier",
                "effect_type": "debuff",
                "duration": 3,
                "stat_modifiers": [
                    {
                        "stat_type": "spd",
                        "modifier_type": "percentage",
                        "value": -0.3,
                        "layer": 3
                    }
                ],
                "max_stacks": 1,
                "stacking_rule": "duration",
                "description": "-30% SPD"
            }
        }
    
    def _setup_event_listeners(self):
        """Set up event listeners for the status system"""
        event_bus.register_handler(
            "status_effect_applied",
            self._on_status_effect_requested
        )
        
        event_bus.register_handler(
            "stat_modification_applied",
            self._on_stat_modification_requested
        )
    
    def _on_status_effect_requested(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle status effect application requests from skill system"""
        effect = event.get_value("effect", {})
        source_id = event.get_value("caster_id")
        target_id = event.get_value("target_id")
        
        if effect.get("type") == "apply_status" and source_id and target_id:
            status_id = effect.get("status_id")
            duration = effect.get("duration")
            probability = effect.get("probability", 1.0)
            
            if status_id:
                success = self.apply_status_effect(
                    source_id=source_id,
                    target_id=target_id,
                    status_id=status_id,
                    duration=duration,
                    probability=probability
                )
                
                event.modify("status_applied", success)
        
        return event
    
    def _on_stat_modification_requested(self, event: GameEvent) -> Optional[GameEvent]:
        """Handle stat modification requests from skill system"""
        effect = event.get_value("effect", {})
        source_id = event.get_value("caster_id")
        target_id = event.get_value("target_id")
        
        if effect.get("type") == "modify_stats" and source_id and target_id:
            # Create a temporary status effect for stat modification
            temp_status = {
                "type": "stat_modifier",
                "effect_type": "buff" if effect.get("value", 0) > 0 else "debuff",
                "duration": effect.get("duration", 3),
                "stat_modifiers": [
                    {
                        "stat_type": effect.get("stat_type"),
                        "modifier_type": effect.get("modifier_type", "flat"),
                        "value": effect.get("value", 0),
                        "layer": 3
                    }
                ],
                "max_stacks": 1,
                "stacking_rule": "duration"
            }
            
            target_char = self.battle_context.get_character(target_id)
            if target_char:
                target_effects = target_char.get("components", {}).get("effects")
                if target_effects:
                    success = target_effects.apply_effect(
                        effect_id=f"temp_stat_mod_{effect.get('stat_type')}",
                        effect_data=temp_status,
                        source_id=source_id,
                        source_type="skill"
                    )
                    
                    event.modify("stat_modification_applied", success)
        
        return event
```

### Next Steps

This completes Step 5 of the implementation, establishing the combat system with:

1. **Combat System**: Complete damage and healing calculation with universal scaling formula
2. **Status System**: Comprehensive status effect application with probability calculations
3. **Combat Resolution**: Full integration with the event system and other components

The next step (Step 6) will focus on implementing the AI system for automated decision making.

### Integration Notes

- Damage calculation uses the exact formulas from the game design
- Universal scaling formula is properly implemented with softcaps
- Status effects integrate with the effects component system
- All combat actions publish events for extensibility and logging
- Critical hits and dodge mechanics follow the specified formulas

### Testing Recommendations

Create unit tests for:

- Damage calculation with various stat combinations
- Universal scaling formula edge cases
- Status effect probability calculations
- Critical hit and dodge chance calculations
- Damage type interactions (physical vs magical)
- Status effect stacking and interaction rules
