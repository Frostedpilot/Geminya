"""
Enhanced Status Effect Framework

Implements a comprehensive buff/debuff system with stacking,
interactions, and complex effect mechanics.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
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
                 special_type: str, **kwargs):
        super().__init__(effect_id, name, description, StatusEffectType.SPECIAL, **kwargs)
        self.special_type = special_type
    
    def apply_effect(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Apply special effect based on type"""
        if self.special_type == "prevent_actions":
            return self._apply_stun_effect(target, instance, battle_context)
        elif self.special_type == "target_switch":
            return self._apply_charm_effect(target, instance, battle_context)
        elif self.special_type == "action_restriction":
            return self._apply_berserk_effect(target, instance, battle_context)
        elif self.special_type == "status_immunity":
            return self._apply_immunity_effect(target, instance, battle_context)
        else:
            return {"effect": "unknown_special", "active": True}
    
    def _apply_stun_effect(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Stun prevents all actions"""
        # Mark character as stunned in their status
        if hasattr(target, 'combat_status'):
            target.combat_status['stunned'] = True
            target.combat_status['can_act'] = False
            target.combat_status['prevented_actions'] = ['skill', 'attack', 'item']
        
        return {
            "effect": "stun",
            "stunned": True,
            "actions_prevented": True,
            "message": f"{target.character_id} is stunned and cannot act!"
        }
    
    def _apply_charm_effect(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Charm makes target attack allies instead of enemies"""
        if hasattr(target, 'combat_status'):
            target.combat_status['charmed'] = True
            target.combat_status['target_override'] = 'allies'
            
            # Notify battle system that targeting is reversed
            if battle_context and 'battle_system' in battle_context:
                battle_system = battle_context['battle_system']
                if hasattr(battle_system, 'set_target_override'):
                    battle_system.set_target_override(target.character_id, 'allies')
        
        return {
            "effect": "charm",
            "charmed": True,
            "target_switch": "allies",
            "message": f"{target.character_id} is charmed and will attack allies!"
        }
    
    def _apply_berserk_effect(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Berserk forces attack actions only, but increases damage"""
        if hasattr(target, 'combat_status'):
            target.combat_status['berserked'] = True
            target.combat_status['action_restriction'] = 'attack_only'
            target.combat_status['allowed_actions'] = ['attack']
            
            # Add damage bonus for being berserked
            if hasattr(target, 'stats'):
                modifier = StatModifier(
                    modifier_id=f"berserk_damage_{instance.source_id}",
                    stat_type=StatType.ATK,
                    modifier_type=ModifierType.PERCENTAGE,
                    value=0.50,  # +50% attack damage while berserked
                    source=f"status_effect_{self.effect_id}",
                    layer=5,
                    duration=instance.remaining_duration
                )
                target.stats.add_modifier(modifier)
        
        return {
            "effect": "berserk",
            "berserked": True,
            "action_restriction": "attack_only",
            "damage_bonus": 0.50,
            "message": f"{target.character_id} is berserked and can only attack!"
        }
    
    def _apply_immunity_effect(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Immunity prevents new status effects from being applied"""
        if hasattr(target, 'combat_status'):
            target.combat_status['status_immune'] = True
            target.combat_status['immune_to'] = 'all_status_effects'
        
        return {
            "effect": "immunity",
            "immune": True,
            "status_immunity": True,
            "message": f"{target.character_id} is immune to status effects!"
        }
    
    def on_apply(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Initialize combat status when special effect is applied"""
        # Ensure target has combat_status attribute
        if not hasattr(target, 'combat_status'):
            target.combat_status = {}
        
        # Apply the effect immediately
        result = self.apply_effect(target, instance, battle_context)
        
        return {
            "applied": True,
            "special_type": self.special_type,
            "initial_effect": result,
            "message": f"{target.character_id} is affected by {self.name}"
        }
    
    def on_remove(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Clean up special effect when removed"""
        if hasattr(target, 'combat_status'):
            # Remove specific status flags
            if self.special_type == "prevent_actions":
                target.combat_status.pop('stunned', None)
                target.combat_status.pop('can_act', None)
                target.combat_status.pop('prevented_actions', None)
                target.combat_status['can_act'] = True  # Restore ability to act
            
            elif self.special_type == "target_switch":
                target.combat_status.pop('charmed', None)
                target.combat_status.pop('target_override', None)
                
                # Notify battle system to clear target override
                if battle_context and 'battle_system' in battle_context:
                    battle_system = battle_context['battle_system']
                    if hasattr(battle_system, 'clear_target_override'):
                        battle_system.clear_target_override(target.character_id)
            
            elif self.special_type == "action_restriction":
                target.combat_status.pop('berserked', None)
                target.combat_status.pop('action_restriction', None)
                target.combat_status.pop('allowed_actions', None)
                
                # Remove berserk damage bonus
                if hasattr(target, 'stats'):
                    modifier_id = f"berserk_damage_{instance.source_id}"
                    target.stats.remove_modifier(modifier_id)
            
            elif self.special_type == "status_immunity":
                target.combat_status.pop('status_immune', None)
                target.combat_status.pop('immune_to', None)
        
        return {
            "removed": True,
            "special_type": self.special_type,
            "message": f"{target.character_id} recovers from {self.name}"
        }

class AllStatsModifierStatusEffect(StatusEffect):
    """Special status effect that modifies all stats simultaneously"""
    
    def __init__(self, effect_id: str, name: str, description: str,
                 modifier_value: float, modifier_type: ModifierType = ModifierType.PERCENTAGE,
                 **kwargs):
        super().__init__(effect_id, name, description, StatusEffectType.SPECIAL, **kwargs)
        self.modifier_value = modifier_value
        self.modifier_type = modifier_type
    
    def apply_effect(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """All stats modifier is applied via stat modifiers, no per-turn action needed"""
        return {"effect": "all_stats_modifier_active", "value": self.modifier_value}
    
    def on_apply(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Add stat modifiers for all stats when effect is applied"""
        if hasattr(target, 'stats'):
            modifier_value = self.modifier_value * instance.current_intensity
            applied_modifiers = []
            
            # Apply to all relevant stats
            stats_to_modify = [StatType.ATK, StatType.MAG, StatType.VIT, StatType.SPR, 
                             StatType.INT, StatType.SPD, StatType.LCK]
            
            for stat_type in stats_to_modify:
                modifier = StatModifier(
                    modifier_id=f"allstats_{instance.effect_id}_{stat_type.value}_{instance.source_id}",
                    stat_type=stat_type,
                    modifier_type=self.modifier_type,
                    value=modifier_value,
                    source=f"status_effect_{self.effect_id}",
                    layer=5,  # Status effects have very high priority
                    duration=instance.remaining_duration
                )
                target.stats.add_modifier(modifier)
                applied_modifiers.append(stat_type.value)
            
            return {
                "applied": True,
                "modifier_ids": applied_modifiers,
                "stats_affected": applied_modifiers,
                "value": modifier_value
            }
        return {"applied": False, "reason": "no_stats_component"}
    
    def on_remove(self, target, instance: StatusEffectInstance, battle_context) -> Dict[str, Any]:
        """Remove all stat modifiers when effect expires"""
        if hasattr(target, 'stats'):
            removed_modifiers = []
            stats_to_modify = [StatType.ATK, StatType.MAG, StatType.VIT, StatType.SPR, 
                             StatType.INT, StatType.SPD, StatType.LCK]
            
            for stat_type in stats_to_modify:
                modifier_id = f"allstats_{instance.effect_id}_{stat_type.value}_{instance.source_id}"
                if target.stats.remove_modifier(modifier_id):
                    removed_modifiers.append(stat_type.value)
            
            return {"removed": True, "modifier_ids": removed_modifiers}
        return {"removed": False}

class StatusEffectSystem:
    """Manages all status effects in the game"""
    
    def __init__(self):
        self.effect_definitions: Dict[str, StatusEffect] = {}
        self.active_effects: Dict[str, List[StatusEffectInstance]] = {}  # character_id -> effects
        self.turn_counter = 0
        self._character_cache: Dict[str, Any] = {}  # Cache characters to maintain state
        self.battle_context = None  # Initialize battle context
        self.character_registry = None  # Initialize character registry
        self.battle_system = None  # Initialize battle system
        self._initialize_status_effects()
        logger.info("Initialized status effect system with %d effects", len(self.effect_definitions))
    
    def _initialize_status_effects(self):
        """Load status effects from the status_effects.json file"""
        try:
            with open('data/status_effects.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            effects = []
            
            # Helper function to convert string enums
            def get_stacking_rule(rule_str: str) -> StackingRule:
                mapping = {
                    "no_stack": StackingRule.NO_STACK,
                    "stack_duration": StackingRule.STACK_DURATION,
                    "stack_intensity": StackingRule.STACK_INTENSITY,
                    "stack_both": StackingRule.STACK_BOTH,
                    "independent": StackingRule.INDEPENDENT
                }
                return mapping.get(rule_str, StackingRule.NO_STACK)
            
            def get_priority(priority_str: str) -> StatusPriority:
                mapping = {
                    "low": StatusPriority.LOW,
                    "normal": StatusPriority.NORMAL,
                    "high": StatusPriority.HIGH,
                    "critical": StatusPriority.CRITICAL,
                    "absolute": StatusPriority.ABSOLUTE
                }
                return mapping.get(priority_str, StatusPriority.NORMAL)
            
            def get_stat_type(stat_str: str) -> StatType:
                mapping = {
                    "atk": StatType.ATK,
                    "vit": StatType.VIT,
                    "spd": StatType.SPD,
                    "mag": StatType.MAG,
                    "spr": StatType.SPR,
                    "lck": StatType.LCK
                }
                return mapping.get(stat_str, StatType.ATK)
            
            def get_modifier_type(modifier_str: str) -> ModifierType:
                mapping = {
                    "percentage": ModifierType.PERCENTAGE,
                    "flat": ModifierType.FLAT
                }
                return mapping.get(modifier_str, ModifierType.PERCENTAGE)
            
            # Process buffs (stat modifier effects)
            for effect_id, effect_data in data['status_effects']['buffs'].items():
                try:
                    stat_mod = effect_data['stat_modifier']
                    effect = StatModifierStatusEffect(
                        effect_id=effect_id,
                        name=effect_data['name'],
                        description=effect_data['description'],
                        stat_type=get_stat_type(stat_mod['stat_type']),
                        modifier_value=stat_mod['modifier_value'],
                        modifier_type=get_modifier_type(stat_mod.get('modifier_type', 'percentage')),
                        duration=effect_data['duration'],
                        stacking_rule=get_stacking_rule(effect_data.get('stacking_rule', 'no_stack')),
                        max_stacks=effect_data.get('max_stacks', 1),
                        priority=get_priority(effect_data.get('priority', 'normal'))
                    )
                    effects.append(effect)
                except KeyError as e:
                    logger.warning("Missing key in buff data for %s: %s", effect_id, e)
                    continue
            
            # Process debuffs (stat modifier effects)
            for effect_id, effect_data in data['status_effects']['debuffs'].items():
                try:
                    if 'stat_modifier' in effect_data:
                        stat_mod = effect_data['stat_modifier']
                        effect = StatModifierStatusEffect(
                            effect_id=effect_id,
                            name=effect_data['name'],
                            description=effect_data['description'],
                            stat_type=get_stat_type(stat_mod['stat_type']),
                            modifier_value=stat_mod['modifier_value'],
                            modifier_type=get_modifier_type(stat_mod.get('modifier_type', 'percentage')),
                            duration=effect_data['duration'],
                            stacking_rule=get_stacking_rule(effect_data.get('stacking_rule', 'no_stack')),
                            max_stacks=effect_data.get('max_stacks', 1),
                            priority=get_priority(effect_data.get('priority', 'normal'))
                        )
                        effects.append(effect)
                except KeyError as e:
                    logger.warning("Missing key in debuff data for %s: %s", effect_id, e)
                    continue
            
            # Process damage over time effects
            for effect_id, effect_data in data['status_effects']['damage_over_time'].items():
                try:
                    effect = DamageOverTimeStatusEffect(
                        effect_id=effect_id,
                        name=effect_data['name'],
                        description=effect_data['description'],
                        damage_per_turn=effect_data['damage_per_turn'],
                        scaling_stat=effect_data.get('scaling_stat'),
                        duration=effect_data['duration'],
                        stacking_rule=get_stacking_rule(effect_data.get('stacking_rule', 'no_stack')),
                        max_stacks=effect_data.get('max_stacks', 1),
                        priority=get_priority(effect_data.get('priority', 'normal'))
                    )
                    effects.append(effect)
                except KeyError as e:
                    logger.warning("Missing key in DOT data for %s: %s", effect_id, e)
                    continue
            
            # Process healing over time effects
            for effect_id, effect_data in data['status_effects']['heal_over_time'].items():
                try:
                    effect = HealOverTimeStatusEffect(
                        effect_id=effect_id,
                        name=effect_data['name'],
                        description=effect_data['description'],
                        heal_per_turn=effect_data['heal_per_turn'],
                        scaling_stat=effect_data.get('scaling_stat'),
                        duration=effect_data['duration'],
                        stacking_rule=get_stacking_rule(effect_data.get('stacking_rule', 'no_stack')),
                        max_stacks=effect_data.get('max_stacks', 1),
                        priority=get_priority(effect_data.get('priority', 'normal'))
                    )
                    effects.append(effect)
                except KeyError as e:
                    logger.warning("Missing key in HOT data for %s: %s", effect_id, e)
                    continue
            
            # Process special effects with enhanced implementations
            for effect_id, effect_data in data['status_effects']['special_effects'].items():
                try:
                    # Handle special effects that have stat modifiers (like inspiration)
                    if 'stat_modifier' in effect_data:
                        stat_mod = effect_data['stat_modifier']
                        if stat_mod['stat_type'] == 'all_stats':
                            # Use the new AllStatsModifierStatusEffect for inspiration-type effects
                            effect = AllStatsModifierStatusEffect(
                                effect_id=effect_id,
                                name=effect_data['name'],
                                description=effect_data['description'],
                                modifier_value=stat_mod['modifier_value'],
                                modifier_type=get_modifier_type(stat_mod.get('modifier_type', 'percentage')),
                                duration=effect_data['duration'],
                                stacking_rule=get_stacking_rule(effect_data.get('stacking_rule', 'no_stack')),
                                max_stacks=effect_data.get('max_stacks', 1),
                                priority=get_priority(effect_data.get('priority', 'normal'))
                            )
                            effects.append(effect)
                        else:
                            # Regular single-stat modifier
                            effect = StatModifierStatusEffect(
                                effect_id=effect_id,
                                name=effect_data['name'],
                                description=effect_data['description'],
                                stat_type=get_stat_type(stat_mod['stat_type']),
                                modifier_value=stat_mod['modifier_value'],
                                modifier_type=get_modifier_type(stat_mod.get('modifier_type', 'percentage')),
                                duration=effect_data['duration'],
                                stacking_rule=get_stacking_rule(effect_data.get('stacking_rule', 'no_stack')),
                                max_stacks=effect_data.get('max_stacks', 1),
                                priority=get_priority(effect_data.get('priority', 'normal'))
                            )
                            effects.append(effect)
                    else:
                        # Regular special effects with custom behavior
                        special_effect_data = effect_data.get('special_effect', {})
                        special_type = special_effect_data.get('type', effect_id)
                        
                        effect = SpecialStatusEffect(
                            effect_id=effect_id,
                            name=effect_data['name'],
                            description=effect_data['description'],
                            special_type=special_type,
                            duration=effect_data['duration'],
                            stacking_rule=get_stacking_rule(effect_data.get('stacking_rule', 'no_stack')),
                            max_stacks=effect_data.get('max_stacks', 1),
                            priority=get_priority(effect_data.get('priority', 'normal'))
                        )
                        effects.append(effect)
                
                except KeyError as e:
                    logger.warning("Missing key in special effect data for %s: %s", effect_id, e)
                    continue
            
            # Register all effects
            for effect in effects:
                self.effect_definitions[effect.effect_id] = effect
            
            logger.info("Loaded %d status effects from JSON", len(self.effect_definitions))
            
        except FileNotFoundError:
            logger.error("Status effects file not found: data/status_effects.json")
            self._create_fallback_effects()
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in status effects file: %s", e)
            self._create_fallback_effects()
        except KeyError as e:
            logger.error("Missing key in status effects file: %s", e)
            self._create_fallback_effects()
    
    def _create_fallback_effects(self):
        """Create basic fallback effects if JSON loading fails"""
        logger.warning("Creating fallback status effects")
        
        # Basic fallback effects
        basic_effects = [
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
            
            DamageOverTimeStatusEffect(
                effect_id="poison",
                name="Poison",
                description="Deals poison damage each turn",
                damage_per_turn=50.0,
                duration=5,
                stacking_rule=StackingRule.STACK_INTENSITY,
                max_stacks=5
            ),
            
            HealOverTimeStatusEffect(
                effect_id="regeneration",
                name="Regeneration",
                description="Restores HP each turn",
                heal_per_turn=80.0,
                duration=5,
                stacking_rule=StackingRule.STACK_INTENSITY,
                max_stacks=3
            )
        ]
        
        for effect in basic_effects:
            self.effect_definitions[effect.effect_id] = effect
    
    def apply_status_effect(self, target_id: str, effect_id: str, source_id: str,
                          duration_override: Optional[int] = None,
                          intensity_override: Optional[float] = None) -> Dict[str, Any]:
        """Apply a status effect to a target"""
        if effect_id not in self.effect_definitions:
            logger.warning("Unknown status effect: %s", effect_id)
            return {"success": False, "reason": "unknown_effect"}
        
        # Check if target is immune to status effects
        target = self._get_character_by_id(target_id)
        if target and self._is_immune_to_status(target, effect_id):
            logger.debug("Target %s is immune to status effect %s", target_id, effect_id)
            return {"success": False, "reason": "target_immune"}
        
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
        
        # Apply the effect (call on_apply and immediate apply_effect)
        if target:
            battle_context = {
                "source_character": self._get_character_by_id(source_id),
                "battle_system": getattr(self, 'battle_system', None)
            }
            # Call on_apply for initialization
            apply_result = effect_def.on_apply(target, new_instance, battle_context)
            
            # Immediately apply the effect for instant effects (like stun, charm, berserk)
            effect_result = effect_def.apply_effect(target, new_instance, battle_context)
            logger.info("Applied status effect %s to %s: on_apply=%s, effect=%s", 
                       effect_id, target_id, apply_result, effect_result)
        
        return {"success": True, "action": "applied", "instance_id": id(new_instance)}
    
    def _is_immune_to_status(self, target, effect_id: str) -> bool:
        """Check if target is immune to a specific status effect"""
        if not hasattr(target, 'combat_status'):
            return False
        
        combat_status = target.combat_status
        
        # Check for general status immunity
        if combat_status.get('status_immune', False):
            immune_to = combat_status.get('immune_to', '')
            if immune_to == 'all_status_effects':
                return True
            elif isinstance(immune_to, list) and effect_id in immune_to:
                return True
        
        # Check for specific immunities based on effect type
        effect_def = self.effect_definitions.get(effect_id)
        if effect_def:
            if effect_def.effect_type == StatusEffectType.DEBUFF:
                return combat_status.get('debuff_immune', False)
            elif effect_def.effect_type == StatusEffectType.DOT:
                return combat_status.get('dot_immune', False)
            elif effect_def.effect_type == StatusEffectType.SPECIAL:
                return combat_status.get('special_immune', False)
        
        return False
    
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
            battle_context = {
                "source_character": self._get_character_by_id(effect_instance.source_id),
                "battle_system": getattr(self, 'battle_system', None)
            }
            effect_result = effect_def.apply_effect(target, effect_instance, battle_context)
            effect_result["effect_name"] = effect_def.name
            effect_result["effect_id"] = effect_instance.effect_id
            effect_result["source_id"] = effect_instance.source_id
            effect_result["intensity"] = effect_instance.current_intensity
            results.append(effect_result)
            
            # Reduce duration
            effect_instance.remaining_duration -= 1
            
            # Mark for removal if expired
            if effect_instance.remaining_duration <= 0:
                effects_to_remove.append(effect_instance)
        
        # Remove expired effects
        for expired_effect in effects_to_remove:
            effect_def = self.effect_definitions[expired_effect.effect_id]
            battle_context = {
                "source_character": self._get_character_by_id(expired_effect.source_id),
                "battle_system": getattr(self, 'battle_system', None)
            }
            remove_result = effect_def.on_remove(target, expired_effect, battle_context)
            self.active_effects[character_id].remove(expired_effect)
            logger.debug("Expired status effect %s on %s", expired_effect.effect_id, character_id)
            
            # Add expiration info to results
            results.append({
                "effect_name": effect_def.name,
                "effect_id": expired_effect.effect_id,
                "effect": "expired",
                "message": f"{effect_def.name} has worn off",
                "removal_result": remove_result
            })
        
        return results
    
    def can_character_act(self, character_id: str) -> Dict[str, Any]:
        """Check if character can act and what actions are available"""
        target = self._get_character_by_id(character_id)
        if not target:
            return {"can_act": True, "available_actions": ["attack", "skill", "item"]}
        
        if not hasattr(target, 'combat_status'):
            return {"can_act": True, "available_actions": ["attack", "skill", "item"]}
        
        combat_status = target.combat_status
        
        # Check for stun
        if combat_status.get('stunned', False):
            return {
                "can_act": False,
                "available_actions": [],
                "reason": "stunned",
                "message": f"{character_id} is stunned and cannot act"
            }
        
        # Check for action restrictions (berserk)
        if combat_status.get('action_restriction'):
            restriction = combat_status['action_restriction']
            if restriction == 'attack_only':
                return {
                    "can_act": True,
                    "available_actions": ["attack"],
                    "restriction": "attack_only",
                    "message": f"{character_id} is berserked and can only attack"
                }
        
        # Check for allowed actions override
        if 'allowed_actions' in combat_status:
            return {
                "can_act": True,
                "available_actions": combat_status['allowed_actions'],
                "restriction": "custom",
                "message": f"{character_id} has limited actions available"
            }
        
        return {"can_act": True, "available_actions": ["attack", "skill", "item"]}
    
    def get_target_override(self, character_id: str) -> Optional[str]:
        """Get target override for charmed characters"""
        target = self._get_character_by_id(character_id)
        if not target or not hasattr(target, 'combat_status'):
            return None
        
        return target.combat_status.get('target_override')
    
    def has_status_type(self, character_id: str, status_type: StatusEffectType) -> bool:
        """Check if character has any effect of a specific type"""
        if character_id not in self.active_effects:
            return False
        
        for effect_instance in self.active_effects[character_id]:
            effect_def = self.effect_definitions[effect_instance.effect_id]
            if effect_def.effect_type == status_type:
                return True
        
        return False
    
    def get_status_modifiers(self, character_id: str) -> Dict[str, float]:
        """Get all status-based stat modifiers for calculations"""
        modifiers = {}
        
        if character_id not in self.active_effects:
            return modifiers
        
        for effect_instance in self.active_effects[character_id]:
            effect_def = self.effect_definitions[effect_instance.effect_id]
            
            if isinstance(effect_def, StatModifierStatusEffect):
                stat_name = effect_def.stat_type.value
                modifier_value = effect_def.modifier_value * effect_instance.current_intensity
                
                if stat_name not in modifiers:
                    modifiers[stat_name] = 0
                modifiers[stat_name] += modifier_value
            
            elif isinstance(effect_def, AllStatsModifierStatusEffect):
                modifier_value = effect_def.modifier_value * effect_instance.current_intensity
                for stat in ['atk', 'mag', 'vit', 'spr', 'int', 'spd', 'lck']:
                    if stat not in modifiers:
                        modifiers[stat] = 0
                    modifiers[stat] += modifier_value
        
        return modifiers
    
    def set_battle_system(self, battle_system):
        """Set the battle system for integration"""
        self.battle_system = battle_system
    
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
        """Get character object by ID - integrated with battle context"""
        # First check cache
        if character_id in self._character_cache:
            return self._character_cache[character_id]
            
        # Try to get character from battle context if available
        if self.battle_context:
            try:
                all_characters = self.battle_context.get_all_characters()
                for character in all_characters:
                    if character.character_id == character_id:
                        self._character_cache[character_id] = character
                        return character
            except (AttributeError, TypeError) as e:
                logger.warning("Failed to get character from battle context: %s", e)
        
        # Try to get from global character registry if available
        if self.character_registry:
            character = self.character_registry.get(character_id)
            if character:
                self._character_cache[character_id] = character
                return character
        
        # Fallback: create mock object for testing/standalone usage
        from ..components.stats_component import StatsComponent
        
        class MockCharacter:
            def __init__(self, char_id):
                self.character_id = char_id
                self.current_hp = 100
                self.max_hp = 100
                self.stats = StatsComponent(char_id)
                self.combat_status = {}  # Initialize combat status
                
                # Initialize with basic stats
                character_data = {
                    "stats": {
                        "hp": 100, "atk": 100, "mag": 100, "vit": 100,
                        "spr": 100, "int": 100, "spd": 100, "lck": 100
                    }
                }
                self.stats.initialize(character_data)
        
        logger.debug("Using mock character for ID: %s", character_id)
        mock_character = MockCharacter(character_id)
        self._character_cache[character_id] = mock_character
        return mock_character
    
    def set_battle_context(self, battle_context):
        """Set the battle context for character lookups"""
        self.battle_context = battle_context
    
    def set_character_registry(self, registry):
        """Set a character registry for lookups"""
        self.character_registry = registry

# Global status effect system instance
status_effect_system = StatusEffectSystem()
