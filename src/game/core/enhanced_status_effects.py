"""
Enhanced Status Effect Framework

Implements a comprehensive buff/debuff system with stacking,
interactions, and complex effect mechanics.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod

from ..components.stats_component import StatModifier, StatType, ModifierType

logger = logging.getLogger(__name__)

class StatusEffectType(Enum):
    """Types of status effects"""
    BUFF = "buff"
    DEBUFF = "debuff"
    DOT = "damage_over_time"    # Damage over time
    HOT = "heal_over_time"      # Heal over time
    SPECIAL = "special"         # Unique mechanics

class StackingRule(Enum):
    """How status effects stack"""
    NO_STACK = "no_stack"           # Cannot stack, refreshes duration
    STACK_DURATION = "stack_duration"   # Extends duration only
    STACK_INTENSITY = "stack_intensity" # Increases effect power
    STACK_BOTH = "stack_both"       # Both duration and intensity
    INDEPENDENT = "independent"     # Each application is separate

class StatusPriority(Enum):
    """Priority levels for status effects"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    ABSOLUTE = 5

@dataclass
class StatusEffectInstance:
    """Single instance of an active status effect"""
    effect_id: str
    source_id: str              # Who applied this effect
    target_id: str              # Who is affected
    remaining_duration: int
    current_intensity: float = 1.0
    stack_count: int = 1
    applied_turn: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

class StatusEffect(ABC):
    """Base class for all status effects"""
    
    def __init__(self, effect_id: str, name: str, description: str,
                 effect_type: StatusEffectType, duration: int,
                 stacking_rule: StackingRule = StackingRule.NO_STACK,
                 priority: StatusPriority = StatusPriority.NORMAL,
                 max_stacks: int = 1):
        self.effect_id = effect_id
        self.name = name
        self.description = description
        self.effect_type = effect_type
        self.base_duration = duration
        self.stacking_rule = stacking_rule
        self.priority = priority
        self.max_stacks = max_stacks
    
    @abstractmethod
    def apply_effect(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Apply the effect to the target"""
        pass
    
    @abstractmethod
    def on_apply(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Called when effect is first applied"""
        pass
    
    @abstractmethod
    def on_remove(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Called when effect is removed"""
        pass
    
    def can_stack_with(self, existing_instance: StatusEffectInstance, new_source: str) -> bool:
        """Check if this effect can stack with an existing instance"""
        if self.stacking_rule == StackingRule.NO_STACK:
            return existing_instance.source_id == new_source
        elif self.stacking_rule == StackingRule.INDEPENDENT:
            return True
        else:
            return existing_instance.stack_count < self.max_stacks

class StatModifierStatusEffect(StatusEffect):
    """Status effect that modifies stats"""
    
    def __init__(self, effect_id: str, name: str, description: str,
                 stat_type: StatType, modifier_value: float,
                 modifier_type: ModifierType = ModifierType.PERCENTAGE,
                 **kwargs):
        super().__init__(effect_id, name, description, StatusEffectType.BUFF if modifier_value > 0 else StatusEffectType.DEBUFF, **kwargs)
        self.stat_type = stat_type
        self.modifier_value = modifier_value
        self.modifier_type = modifier_type
    
    def apply_effect(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Apply stat modification"""
        # Effect is applied through stat modifiers, no per-turn action needed
        return {"effect": "stat_modifier_active"}
    
    def on_apply(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Add stat modifier when effect is applied"""
        if hasattr(target, 'stats'):
            modifier_value = self.modifier_value * instance.current_intensity
            modifier = StatModifier(
                modifier_id=f"status_{instance.effect_id}_{instance.source_id}",
                stat_type=self.stat_type,
                modifier_type=self.modifier_type,
                value=modifier_value,
                source=f"status_effect_{self.effect_id}",
                layer=5,  # Status effects have very high priority
                duration=instance.remaining_duration
            )
            target.stats.add_modifier(modifier)
            
            return {
                "applied": True,
                "modifier_id": modifier.modifier_id,
                "stat": self.stat_type.value,
                "value": modifier_value
            }
        return {"applied": False, "reason": "no_stats_component"}
    
    def on_remove(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Remove stat modifier when effect expires"""
        if hasattr(target, 'stats'):
            modifier_id = f"status_{instance.effect_id}_{instance.source_id}"
            target.stats.remove_modifier(modifier_id)
            return {"removed": True, "modifier_id": modifier_id}
        return {"removed": False}

class DamageOverTimeStatusEffect(StatusEffect):
    """Status effect that deals damage over time"""
    
    def __init__(self, effect_id: str, name: str, description: str,
                 damage_per_turn: float, scaling_stat: Optional[str] = None,
                 **kwargs):
        super().__init__(effect_id, name, description, StatusEffectType.DOT, **kwargs)
        self.damage_per_turn = damage_per_turn
        self.scaling_stat = scaling_stat
    
    def apply_effect(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Deal damage each turn"""
        base_damage = self.damage_per_turn * instance.current_intensity
        
        # Scale with source character's stats if specified
        if self.scaling_stat and battle_context.get('source_character'):
            source_char = battle_context['source_character']
            if hasattr(source_char, 'stats'):
                scaling_value = getattr(source_char.stats, self.scaling_stat, 100)
                base_damage = base_damage * (scaling_value / 100.0)
        
        # Apply damage
        damage_dealt = base_damage
        if hasattr(target, 'current_hp'):
            target.current_hp = max(0, target.current_hp - damage_dealt)
        
        return {
            "damage_dealt": damage_dealt,
            "target_hp": getattr(target, 'current_hp', 0)
        }
    
    def on_apply(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Effect applied message"""
        return {"applied": True, "message": f"{target.character_id} is affected by {self.name}"}
    
    def on_remove(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Effect removed message"""
        return {"removed": True, "message": f"{target.character_id} recovers from {self.name}"}

class HealOverTimeStatusEffect(StatusEffect):
    """Status effect that heals over time"""
    
    def __init__(self, effect_id: str, name: str, description: str,
                 heal_per_turn: float, scaling_stat: Optional[str] = None,
                 **kwargs):
        super().__init__(effect_id, name, description, StatusEffectType.HOT, **kwargs)
        self.heal_per_turn = heal_per_turn
        self.scaling_stat = scaling_stat
    
    def apply_effect(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Heal each turn"""
        base_heal = self.heal_per_turn * instance.current_intensity
        
        # Scale with source character's stats if specified
        if self.scaling_stat and battle_context.get('source_character'):
            source_char = battle_context['source_character']
            if hasattr(source_char, 'stats'):
                scaling_value = getattr(source_char.stats, self.scaling_stat, 100)
                base_heal = base_heal * (scaling_value / 100.0)
        
        # Apply healing
        heal_amount = base_heal
        if hasattr(target, 'current_hp') and hasattr(target, 'max_hp'):
            old_hp = target.current_hp
            target.current_hp = min(target.max_hp, target.current_hp + heal_amount)
            actual_heal = target.current_hp - old_hp
        else:
            actual_heal = heal_amount
        
        return {
            "healing_done": actual_heal,
            "target_hp": getattr(target, 'current_hp', 0)
        }
    
    def on_apply(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Effect applied message"""
        return {"applied": True, "message": f"{target.character_id} begins regenerating"}
    
    def on_remove(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Effect removed message"""
        return {"removed": True, "message": f"{target.character_id} stops regenerating"}

class SpecialStatusEffect(StatusEffect):
    """Status effect with custom behavior"""
    
    def __init__(self, effect_id: str, name: str, description: str,
                 effect_function: Callable, **kwargs):
        super().__init__(effect_id, name, description, StatusEffectType.SPECIAL, **kwargs)
        self.effect_function = effect_function
    
    def apply_effect(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Apply custom effect"""
        return self.effect_function(target, instance, battle_context)
    
    def on_apply(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Custom application logic"""
        return {"applied": True, "message": f"{target.character_id} is affected by {self.name}"}
    
    def on_remove(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Custom removal logic"""
        return {"removed": True, "message": f"{target.character_id} recovers from {self.name}"}

class StatusEffectSystem:
    """Manages all status effects in the game"""
    
    def __init__(self):
        self.effect_definitions: Dict[str, StatusEffect] = {}
        self.active_effects: Dict[str, List[StatusEffectInstance]] = {}  # character_id -> effects
        self.turn_counter = 0
        self._initialize_status_effects()
        logger.info("Initialized status effect system with %d effects", len(self.effect_definitions))
    
    def _initialize_status_effects(self):
        """Initialize all status effect definitions"""
        
        # Stat modifier effects
        effects = [
            StatModifierStatusEffect(
                effect_id="attack_boost",
                name="Attack Boost",
                description="Increases ATK by 30%",
                stat_type=StatType.ATK,
                modifier_value=0.30,
                duration=5,
                stacking_rule=StackingRule.STACK_DURATION,
                max_stacks=3
            ),
            
            StatModifierStatusEffect(
                effect_id="defense_boost",
                name="Defense Boost", 
                description="Increases VIT by 25%",
                stat_type=StatType.VIT,
                modifier_value=0.25,
                duration=4,
                stacking_rule=StackingRule.STACK_INTENSITY,
                max_stacks=2
            ),
            
            StatModifierStatusEffect(
                effect_id="speed_boost",
                name="Haste",
                description="Increases SPD by 50%",
                stat_type=StatType.SPD,
                modifier_value=0.50,
                duration=3,
                priority=StatusPriority.HIGH
            ),
            
            StatModifierStatusEffect(
                effect_id="attack_debuff",
                name="Weakness",
                description="Decreases ATK by 20%",
                stat_type=StatType.ATK,
                modifier_value=-0.20,
                duration=4,
                stacking_rule=StackingRule.STACK_BOTH,
                max_stacks=3
            ),
            
            StatModifierStatusEffect(
                effect_id="magic_boost",
                name="Magic Power",
                description="Increases MAG by 40%",
                stat_type=StatType.MAG,
                modifier_value=0.40,
                duration=6,
                priority=StatusPriority.HIGH
            ),
            
            # Damage over time effects
            DamageOverTimeStatusEffect(
                effect_id="poison",
                name="Poison",
                description="Deals poison damage each turn",
                damage_per_turn=50.0,
                duration=5,
                stacking_rule=StackingRule.STACK_INTENSITY,
                max_stacks=5
            ),
            
            DamageOverTimeStatusEffect(
                effect_id="burn",
                name="Burn",
                description="Deals fire damage based on caster's MAG",
                damage_per_turn=30.0,
                scaling_stat="mag",
                duration=4,
                stacking_rule=StackingRule.STACK_DURATION,
                max_stacks=3
            ),
            
            DamageOverTimeStatusEffect(
                effect_id="bleed",
                name="Bleed",
                description="Deals physical damage based on caster's ATK",
                damage_per_turn=40.0,
                scaling_stat="atk",
                duration=3,
                stacking_rule=StackingRule.INDEPENDENT,
                max_stacks=10
            ),
            
            # Healing over time effects
            HealOverTimeStatusEffect(
                effect_id="regeneration",
                name="Regeneration",
                description="Restores HP each turn",
                heal_per_turn=80.0,
                duration=5,
                stacking_rule=StackingRule.STACK_INTENSITY,
                max_stacks=3
            ),
            
            HealOverTimeStatusEffect(
                effect_id="divine_blessing",
                name="Divine Blessing",
                description="Restores HP based on caster's SPR",
                heal_per_turn=60.0,
                scaling_stat="spr",
                duration=7,
                priority=StatusPriority.HIGH
            )
        ]
        
        # Add special effects with custom functions
        def stun_effect(target, instance, battle_context):
            """Stun prevents all actions"""
            return {"stunned": True, "actions_prevented": True}
        
        def charm_effect(target, instance, battle_context):
            """Charm makes target attack allies"""
            return {"charmed": True, "target_switch": "allies"}
        
        def berserk_effect(target, instance, battle_context):
            """Berserk forces attack actions only"""
            return {"berserked": True, "action_restriction": "attack_only"}
        
        special_effects = [
            SpecialStatusEffect(
                effect_id="stun",
                name="Stun",
                description="Cannot take any actions",
                effect_function=stun_effect,
                duration=2,
                priority=StatusPriority.CRITICAL
            ),
            
            SpecialStatusEffect(
                effect_id="charm",
                name="Charm",
                description="Attacks allies instead of enemies",
                effect_function=charm_effect,
                duration=3,
                priority=StatusPriority.HIGH
            ),
            
            SpecialStatusEffect(
                effect_id="berserk",
                name="Berserk",
                description="Can only use attack actions",
                effect_function=berserk_effect,
                duration=4,
                priority=StatusPriority.NORMAL
            )
        ]
        
        # Register all effects
        all_effects = effects + special_effects
        for effect in all_effects:
            self.effect_definitions[effect.effect_id] = effect
    
    def apply_status_effect(self, target_id: str, effect_id: str, source_id: str,
                          duration_override: Optional[int] = None,
                          intensity_override: Optional[float] = None) -> Dict[str, Any]:
        """Apply a status effect to a target"""
        if effect_id not in self.effect_definitions:
            logger.warning("Unknown status effect: %s", effect_id)
            return {"success": False, "reason": "unknown_effect"}
        
        effect_def = self.effect_definitions[effect_id]
        duration = duration_override if duration_override is not None else effect_def.base_duration
        intensity = intensity_override if intensity_override is not None else 1.0
        
        # Check for existing effects
        if target_id not in self.active_effects:
            self.active_effects[target_id] = []
        
        existing_effects = [e for e in self.active_effects[target_id] if e.effect_id == effect_id]
        
        # Handle stacking
        if existing_effects:
            existing_effect = existing_effects[0]  # Take first matching effect
            
            if not effect_def.can_stack_with(existing_effect, source_id):
                # Refresh existing effect
                existing_effect.remaining_duration = duration
                logger.debug("Refreshed status effect %s on %s", effect_id, target_id)
                return {"success": True, "action": "refreshed"}
            else:
                # Apply stacking rules
                if effect_def.stacking_rule == StackingRule.STACK_DURATION:
                    existing_effect.remaining_duration += duration
                elif effect_def.stacking_rule == StackingRule.STACK_INTENSITY:
                    existing_effect.current_intensity += intensity
                    existing_effect.stack_count += 1
                elif effect_def.stacking_rule == StackingRule.STACK_BOTH:
                    existing_effect.remaining_duration += duration
                    existing_effect.current_intensity += intensity
                    existing_effect.stack_count += 1
                elif effect_def.stacking_rule == StackingRule.INDEPENDENT:
                    # Create new independent instance
                    pass  # Fall through to create new instance
                
                if effect_def.stacking_rule != StackingRule.INDEPENDENT:
                    logger.debug("Stacked status effect %s on %s", effect_id, target_id)
                    return {"success": True, "action": "stacked"}
        
        # Create new effect instance
        new_instance = StatusEffectInstance(
            effect_id=effect_id,
            source_id=source_id,
            target_id=target_id,
            remaining_duration=duration,
            current_intensity=intensity,
            applied_turn=self.turn_counter
        )
        
        self.active_effects[target_id].append(new_instance)
        
        # Apply the effect (call on_apply)
        target = self._get_character_by_id(target_id)
        if target:
            battle_context = {"source_character": self._get_character_by_id(source_id)}
            apply_result = effect_def.on_apply(target, new_instance, battle_context)
            logger.info("Applied status effect %s to %s: %s", effect_id, target_id, apply_result)
        
        return {"success": True, "action": "applied", "instance_id": id(new_instance)}
    
    def remove_status_effect(self, target_id: str, effect_id: str, source_id: Optional[str] = None) -> bool:
        """Remove a specific status effect"""
        if target_id not in self.active_effects:
            return False
        
        effects_to_remove = []
        for effect in self.active_effects[target_id]:
            if effect.effect_id == effect_id:
                if source_id is None or effect.source_id == source_id:
                    effects_to_remove.append(effect)
        
        if not effects_to_remove:
            return False
        
        # Remove effects and call on_remove
        target = self._get_character_by_id(target_id)
        effect_def = self.effect_definitions[effect_id]
        
        for effect in effects_to_remove:
            self.active_effects[target_id].remove(effect)
            if target:
                battle_context = {"source_character": self._get_character_by_id(effect.source_id)}
                remove_result = effect_def.on_remove(target, effect, battle_context)
                logger.debug("Removed status effect %s from %s: %s", effect_id, target_id, remove_result)
        
        return True
    
    def process_turn_effects(self, character_id: str) -> List[Dict[str, Any]]:
        """Process all status effects for a character's turn"""
        if character_id not in self.active_effects:
            return []
        
        results = []
        effects_to_remove = []
        
        target = self._get_character_by_id(character_id)
        if not target:
            return results
        
        for effect_instance in self.active_effects[character_id]:
            effect_def = self.effect_definitions[effect_instance.effect_id]
            
            # Apply the effect
            battle_context = {"source_character": self._get_character_by_id(effect_instance.source_id)}
            effect_result = effect_def.apply_effect(target, effect_instance, battle_context)
            effect_result["effect_name"] = effect_def.name
            effect_result["effect_id"] = effect_instance.effect_id
            results.append(effect_result)
            
            # Reduce duration
            effect_instance.remaining_duration -= 1
            
            # Mark for removal if expired
            if effect_instance.remaining_duration <= 0:
                effects_to_remove.append(effect_instance)
        
        # Remove expired effects
        for expired_effect in effects_to_remove:
            effect_def = self.effect_definitions[expired_effect.effect_id]
            battle_context = {"source_character": self._get_character_by_id(expired_effect.source_id)}
            remove_result = effect_def.on_remove(target, expired_effect, battle_context)
            self.active_effects[character_id].remove(expired_effect)
            logger.debug("Expired status effect %s on %s", expired_effect.effect_id, character_id)
        
        return results
    
    def get_active_effects(self, character_id: str) -> List[Dict[str, Any]]:
        """Get all active effects for a character"""
        if character_id not in self.active_effects:
            return []
        
        effect_info = []
        for instance in self.active_effects[character_id]:
            effect_def = self.effect_definitions[instance.effect_id]
            effect_info.append({
                "effect_id": instance.effect_id,
                "name": effect_def.name,
                "description": effect_def.description,
                "type": effect_def.effect_type.value,
                "remaining_duration": instance.remaining_duration,
                "intensity": instance.current_intensity,
                "stack_count": instance.stack_count,
                "source": instance.source_id
            })
        
        return effect_info
    
    def clear_all_effects(self, character_id: str):
        """Clear all status effects from a character"""
        if character_id in self.active_effects:
            target = self._get_character_by_id(character_id)
            
            # Call on_remove for all effects
            if target:
                for effect_instance in self.active_effects[character_id]:
                    effect_def = self.effect_definitions[effect_instance.effect_id]
                    battle_context = {"source_character": self._get_character_by_id(effect_instance.source_id)}
                    effect_def.on_remove(target, effect_instance, battle_context)
            
            self.active_effects[character_id] = []
            logger.info("Cleared all status effects from %s", character_id)
    
    def advance_turn(self):
        """Advance the turn counter"""
        self.turn_counter += 1
    
    def _get_character_by_id(self, character_id: str):
        """Get character object by ID (placeholder - would integrate with character system)"""
        # In a full implementation, this would get the actual character object
        # For now, return a mock object with basic stats support
        from ..components.stats_component import StatsComponent
        
        class MockCharacter:
            def __init__(self, char_id):
                self.character_id = char_id
                self.current_hp = 100
                self.max_hp = 100
                self.stats = StatsComponent(char_id)
                
                # Initialize with basic stats
                character_data = {
                    "stats": {
                        "hp": 100, "atk": 100, "mag": 100, "vit": 100,
                        "spr": 100, "int": 100, "spd": 100, "lck": 100
                    }
                }
                self.stats.initialize(character_data)
        
        return MockCharacter(character_id)

# Global status effect system instance
status_effect_system = StatusEffectSystem()
