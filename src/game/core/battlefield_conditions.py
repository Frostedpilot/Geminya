"""
Battlefield Conditions System

Implements weekly environmental effects that alter battle mechanics
for all participants, as described in the design document.
"""

from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import logging
import json
import random
import re
from datetime import datetime, timedelta

from ..components.stats_component import StatModifier, StatType, ModifierType

logger = logging.getLogger(__name__)

# Event system for decoupling notifications
class BattlefieldEventType(Enum):
    """Types of battlefield events"""
    EFFECT_APPLIED = "effect_applied"
    DAMAGE_MODIFIED = "damage_modified"
    HEALING_MODIFIED = "healing_modified"
    TURN_MODIFIER_APPLIED = "turn_modifier_applied"
    TARGETING_CHANGED = "targeting_changed"
    COMBAT_EFFECT = "combat_effect"

@dataclass
class BattlefieldEvent:
    """Event data for battlefield notifications"""
    event_type: BattlefieldEventType
    character_name: str
    effect_name: str
    details: Dict[str, Any]

class BattlefieldEventSystem:
    """Event system for battlefield notifications"""
    def __init__(self):
        self.handlers: Dict[BattlefieldEventType, List[Callable]] = {}
    
    def subscribe(self, event_type: BattlefieldEventType, handler: Callable):
        """Subscribe to an event type"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    def emit(self, event: BattlefieldEvent):
        """Emit an event to all subscribers"""
        if event.event_type in self.handlers:
            for handler in self.handlers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")

# Global event system instance
battlefield_events = BattlefieldEventSystem()

# Effect type enumeration for proper data-driven design
class EffectCategory(Enum):
    """Categories of battlefield effects"""
    STAT_MODIFIER = "stat_modifier"
    TURN_MODIFIER = "turn_modifier"
    COMBAT_MODIFIER = "combat_modifier"
    TARGETING_MODIFIER = "targeting_modifier"
    PERIODIC_EFFECT = "periodic_effect"
    COMBAT_EFFECT = "combat_effect"
    SETUP_EFFECT = "setup_effect"
    TARGETING_EFFECT = "targeting_effect"
    ENHANCEMENT_EFFECT = "enhancement_effect"

class ConditionType(Enum):
    """Types of battlefield conditions"""
    ENVIRONMENTAL = "environmental"
    MAGICAL = "magical"
    WEATHER = "weather"
    COSMIC = "cosmic"
    TEMPORAL = "temporal"

@dataclass
class EffectData:
    """Structured data for effects instead of string parsing"""
    category: EffectCategory
    trigger: str  # "turn_start", "combat", "target_selection"
    parameters: Dict[str, Any]
    
    @classmethod
    def from_description(cls, description: str) -> 'EffectData':
        """Parse description into structured data"""
        desc_lower = description.lower()
        
        # Turn modifiers
        if 'act twice per turn' in desc_lower or 'double turn' in desc_lower:
            return cls(EffectCategory.TURN_MODIFIER, "turn_start", {"max_actions": 2})
        elif 'extra turn every' in desc_lower:
            return cls(EffectCategory.TURN_MODIFIER, "turn_start", {"extra_turns_frequency": 3})
        elif 'cost 25% less' in desc_lower:
            return cls(EffectCategory.TURN_MODIFIER, "turn_start", {"cost_modifier": 0.75})
        elif 'healing effects are doubled' in desc_lower:
            return cls(EffectCategory.TURN_MODIFIER, "turn_start", {"healing_multiplier": 2.0})
        elif 'below 1 hp' in desc_lower:
            return cls(EffectCategory.TURN_MODIFIER, "turn_start", {"minimum_hp": 1})
        elif 'not consume' in desc_lower and 'turn' in desc_lower:
            return cls(EffectCategory.TURN_MODIFIER, "turn_start", {"skip_consumption_chance": 15})
        
        # Enhancement effects
        elif 'enhanced effects due to magical pressure' in desc_lower:
            return cls(EffectCategory.ENHANCEMENT_EFFECT, "combat", {"enhancement_multiplier": 1.5})
        elif 'enhanced range and area effects' in desc_lower:
            return cls(EffectCategory.ENHANCEMENT_EFFECT, "combat", {"enhancement_multiplier": 1.3})
        
        # Periodic effects
        elif 'regenerate' in desc_lower and 'hp per turn' in desc_lower:
            match = re.search(r'(\d+)%', description)
            percentage = float(match.group(1)) if match else 2.0
            return cls(EffectCategory.PERIODIC_EFFECT, "turn_start", {"heal_percentage": percentage})
        elif 'take' in desc_lower and 'damage per turn' in desc_lower:
            match = re.search(r'(\d+)%', description)
            percentage = float(match.group(1)) if match else 3.0
            return cls(EffectCategory.PERIODIC_EFFECT, "turn_start", {"damage_percentage": percentage})
        
        # Random effects
        elif 'randomized each turn' in desc_lower:
            return cls(EffectCategory.PERIODIC_EFFECT, "turn_start", {"random_stat_modifier": True})
        elif 'random stat gets +20% bonus' in desc_lower:
            return cls(EffectCategory.PERIODIC_EFFECT, "turn_start", {"random_stat_bonus": 0.2})
        elif 'action gauge' in desc_lower and 'varies randomly' in desc_lower:
            return cls(EffectCategory.PERIODIC_EFFECT, "turn_start", {"action_gauge_variance": 0.25})
        
        # Combat modifiers
        elif 'chain' in desc_lower and 'lightning' in desc_lower:
            return cls(EffectCategory.COMBAT_MODIFIER, "combat", {"chain_chance": 30, "chain_multiplier": 0.5})
        elif 'shared' in desc_lower or 'quantum entanglement' in desc_lower:
            return cls(EffectCategory.COMBAT_MODIFIER, "combat", {"share_percentage": 30})
        
        # Targeting modifiers
        elif 'random' in desc_lower and 'target' in desc_lower:
            return cls(EffectCategory.TARGETING_MODIFIER, "target_selection", {"random_chance": 10})
        elif 'miss' in desc_lower:
            return cls(EffectCategory.TARGETING_MODIFIER, "target_selection", {"miss_chance": 15})
        
        # Combat effect patterns
        elif "amplifies" in desc_lower and "damage" in desc_lower:
            # Extract amplification percentage
            percentage_match = re.search(r'(\d+)%', description)
            if percentage_match:
                percentage = float(percentage_match.group(1))
                multiplier = 1.0 + (percentage / 100.0)
                return cls(EffectCategory.COMBAT_EFFECT, "combat", {"damage_multiplier": multiplier})
        
        elif "critical hit" in desc_lower and ("likely" in desc_lower or "chance" in desc_lower):
            return cls(EffectCategory.COMBAT_EFFECT, "combat", {"critical_chance_bonus": 0.2})
        
        elif "accuracy" in desc_lower and ("reduced" in desc_lower or "penalty" in desc_lower):
            return cls(EffectCategory.COMBAT_EFFECT, "combat", {"accuracy_modifier": -0.3})
        
        elif "resistant to" in desc_lower or "immune to" in desc_lower:
            resistance_value = 0.5 if "resistant" in desc_lower else 0.0
            return cls(EffectCategory.COMBAT_EFFECT, "combat", {"element_resistance": resistance_value})
        
        elif "counter" in desc_lower and "attack" in desc_lower:
            return cls(EffectCategory.COMBAT_EFFECT, "combat", {"counter_chance": 0.3})
        
        elif "reflect" in desc_lower and ("magic" in desc_lower or "spell" in desc_lower):
            return cls(EffectCategory.COMBAT_EFFECT, "combat", {"reflect_chance": 0.2})
        
        # Additional special effects - handling the 26 unhandled effects
        elif "critical hits deal 2.0x damage instead of 1.5x" in desc_lower:
            return cls(EffectCategory.COMBAT_EFFECT, "combat", {"critical_multiplier": 2.0})
        
        elif "status effects have double duration" in desc_lower:
            return cls(EffectCategory.ENHANCEMENT_EFFECT, "status", {"duration_multiplier": 2.0})
        
        elif "chance for random beneficial effects each turn" in desc_lower:
            return cls(EffectCategory.PERIODIC_EFFECT, "turn_start", {"random_beneficial": True})
        
        elif "defeated characters revive once with 25% hp" in desc_lower:
            return cls(EffectCategory.ENHANCEMENT_EFFECT, "revival", {"revive_hp_percent": 25})
        
        elif "abilities have 25% increased effect potency" in desc_lower:
            return cls(EffectCategory.ENHANCEMENT_EFFECT, "ability", {"potency_multiplier": 1.25})
        
        elif "healing effects are increased by 50%" in desc_lower:
            return cls(EffectCategory.ENHANCEMENT_EFFECT, "healing", {"healing_multiplier": 1.5})
        
        elif "chance for targeted abilities to hit wrong target" in desc_lower:
            percentage_match = re.search(r'(\d+)%', description)
            chance = float(percentage_match.group(1)) if percentage_match else 25
            return cls(EffectCategory.TARGETING_EFFECT, "misdirection", {"misdirection_chance": chance})
        
        elif "when one character takes damage, all others take" in desc_lower:
            percentage_match = re.search(r'(\d+)%', description)
            shared_percent = float(percentage_match.group(1)) if percentage_match else 10
            return cls(EffectCategory.COMBAT_EFFECT, "damage_sharing", {"damage_share_percent": shared_percent})
        
        elif "when one character heals, all others heal for" in desc_lower:
            percentage_match = re.search(r'(\d+)%', description)
            heal_percent = float(percentage_match.group(1)) if percentage_match else 20
            return cls(EffectCategory.COMBAT_EFFECT, "healing_sharing", {"heal_share_percent": heal_percent})
        
        elif "abilities can target any number of enemies" in desc_lower:
            return cls(EffectCategory.TARGETING_EFFECT, "multi_target", {"unlimited_targets": True})
        
        elif "attacks have life-steal effect" in desc_lower:
            percentage_match = re.search(r'(\d+)%', description)
            lifesteal_percent = float(percentage_match.group(1)) if percentage_match else 5
            return cls(EffectCategory.COMBAT_EFFECT, "lifesteal", {"lifesteal_percent": lifesteal_percent})
        
        elif "random potion effect applied to random character each turn" in desc_lower:
            return cls(EffectCategory.PERIODIC_EFFECT, "turn_start", {"random_potion": True})
        
        elif "characters see hidden patterns and weaknesses" in desc_lower:
            return cls(EffectCategory.ENHANCEMENT_EFFECT, "insight", {"pattern_sight": True})
        
        elif "critical hits restore small amount of hp" in desc_lower:
            return cls(EffectCategory.COMBAT_EFFECT, "critical_heal", {"crit_heal_percent": 5})
        
        elif "characters revive immediately upon defeat with 50% hp" in desc_lower:
            return cls(EffectCategory.ENHANCEMENT_EFFECT, "instant_revival", {"revive_hp_percent": 50})
        
        elif "each character exists in two timelines simultaneously" in desc_lower:
            return cls(EffectCategory.ENHANCEMENT_EFFECT, "dual_timeline", {"timeline_split": True})
        
        elif "actions affect both present and future versions" in desc_lower:
            return cls(EffectCategory.ENHANCEMENT_EFFECT, "temporal_effect", {"affects_future": True})
        
        # Default fallback
        return cls(EffectCategory.COMBAT_MODIFIER, "combat", {"description": description})

@dataclass
class BattlefieldEffect:
    """Individual effect within a battlefield condition"""
    effect_type: str            # "stat_modifier", "damage_modifier", "special_rule"
    target_criteria: str        # "all", "fire_elemental", "water_elemental", etc.
    name: str = "Unknown Effect"  # Name for the effect
    stat_affected: Optional[str] = None
    modifier_value: float = 0.0
    modifier_type: str = "percentage"  # "percentage", "flat"
    description: str = ""
    
    def __post_init__(self):
        """Initialize structured effect data"""
        if self.effect_type == "special_rule":
            self.effect_data = EffectData.from_description(self.description)
        else:
            self.effect_data = None
    
    def execute_turn_effect(self, character) -> Dict[str, Any]:
        """Execute per-turn effects - pure function with no side effects"""
        if not self.effect_data or self.effect_data.category != EffectCategory.PERIODIC_EFFECT:
            return {"success": False, "message": "No periodic effect"}
        
        try:
            result = {"success": True, "effects": []}
            params = self.effect_data.parameters
            
            # Handle healing effects
            if "heal_percentage" in params:
                heal_amount = character.max_hp * params["heal_percentage"] / 100
                character.heal(heal_amount)
                result["effects"].append({
                    "type": "healing",
                    "amount": heal_amount,
                    "character": character.name
                })
                
                # Emit event instead of printing
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.EFFECT_APPLIED,
                    character.name,
                    "Regeneration",
                    {"amount": heal_amount}
                ))
            
            # Handle damage effects
            elif "damage_percentage" in params:
                damage_amount = character.max_hp * params["damage_percentage"] / 100
                character.take_damage(damage_amount)
                result["effects"].append({
                    "type": "damage",
                    "amount": damage_amount,
                    "character": character.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.EFFECT_APPLIED,
                    character.name,
                    "Periodic Damage",
                    {"amount": damage_amount}
                ))
            
            # Handle random stat modifiers
            elif "random_stat_modifier" in params:
                stats = ['atk', 'mag', 'vit', 'spr', 'int', 'spd', 'lck']
                chosen_stat = random.choice(stats)
                modifier = random.uniform(-0.2, 0.3)
                
                if hasattr(character, 'current_stats') and chosen_stat in character.current_stats:
                    old_value = character.current_stats[chosen_stat]
                    character.current_stats[chosen_stat] = character.base_stats[chosen_stat] * (1 + modifier)
                    
                    result["effects"].append({
                        "type": "stat_change",
                        "stat": chosen_stat,
                        "old_value": old_value,
                        "new_value": character.current_stats[chosen_stat],
                        "character": character.name
                    })
                    
                    battlefield_events.emit(BattlefieldEvent(
                        BattlefieldEventType.EFFECT_APPLIED,
                        character.name,
                        "Chaos Effect",
                        {"stat": chosen_stat, "modifier": modifier}
                    ))
            
            # Handle fairy circle bonus
            elif "random_stat_bonus" in params:
                stats = ['atk', 'mag', 'vit', 'spr', 'int', 'spd', 'lck']
                chosen_stat = random.choice(stats)
                bonus = params["random_stat_bonus"]
                
                if hasattr(character, 'current_stats') and chosen_stat in character.current_stats:
                    character.current_stats[chosen_stat] = character.base_stats[chosen_stat] * (1 + bonus)
                    
                    result["effects"].append({
                        "type": "stat_bonus",
                        "stat": chosen_stat,
                        "bonus": bonus,
                        "character": character.name
                    })
                    
                    battlefield_events.emit(BattlefieldEvent(
                        BattlefieldEventType.EFFECT_APPLIED,
                        character.name,
                        "Fairy Magic",
                        {"stat": chosen_stat, "bonus": bonus}
                    ))
            
            # Handle action gauge variations
            elif "action_gauge_variance" in params:
                variance = params["action_gauge_variance"]
                variation = random.uniform(-variance, variance)
                character.action_gauge = int(max(0, character.action_gauge * (1 + variation)))
                
                result["effects"].append({
                    "type": "action_gauge_change",
                    "variation": variation,
                    "character": character.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.EFFECT_APPLIED,
                    character.name,
                    "Temporal Variation",
                    {"variation": variation}
                ))
            
            # Handle random beneficial effects
            elif "random_beneficial" in params:
                # Apply a random beneficial effect
                beneficial_effects = [
                    {"type": "heal", "amount": character.max_hp * 0.1},
                    {"type": "stat_boost", "stat": random.choice(['atk', 'mag', 'spd']), "bonus": 0.2},
                    {"type": "shield", "amount": character.max_hp * 0.05}
                ]
                chosen_effect = random.choice(beneficial_effects)
                
                if chosen_effect["type"] == "heal":
                    character.heal(chosen_effect["amount"])
                elif chosen_effect["type"] == "stat_boost":
                    stat = chosen_effect["stat"]
                    if hasattr(character, 'current_stats') and stat in character.current_stats:
                        character.current_stats[stat] *= (1 + chosen_effect["bonus"])
                
                result["effects"].append({
                    "type": "random_beneficial",
                    "effect": chosen_effect,
                    "character": character.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.EFFECT_APPLIED,
                    character.name,
                    "Random Blessing",
                    {"effect": chosen_effect}
                ))
            
            # Handle random potion effects
            elif "random_potion" in params:
                potion_effects = [
                    {"type": "heal", "amount": character.max_hp * 0.15},
                    {"type": "mana_restore", "amount": 50},
                    {"type": "stat_temp_boost", "duration": 3},
                    {"type": "resistance", "element": "all", "duration": 2}
                ]
                chosen_potion = random.choice(potion_effects)
                
                result["effects"].append({
                    "type": "random_potion",
                    "potion_effect": chosen_potion,
                    "character": character.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.EFFECT_APPLIED,
                    character.name,
                    "Random Potion",
                    {"potion": chosen_potion}
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing turn effect: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_combat_effect(self, attacker, defender, ability_name=None) -> Dict[str, Any]:
        """Execute combat effects - pure function with structured results"""
        if not self.effect_data or self.effect_data.category != EffectCategory.COMBAT_EFFECT:
            return {"success": False, "message": "No combat effect"}
        
        try:
            result = {"success": True, "effects": []}
            params = self.effect_data.parameters
            
            # Handle damage modifiers
            if "damage_multiplier" in params:
                multiplier = params["damage_multiplier"]
                result["effects"].append({
                    "type": "damage_modifier",
                    "multiplier": multiplier,
                    "attacker": attacker.name,
                    "defender": defender.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.COMBAT_EFFECT,
                    attacker.name,
                    self.name,
                    {"multiplier": multiplier, "target": defender.name}
                ))
            
            # Handle critical hit modifiers
            elif "critical_chance_bonus" in params:
                bonus = params["critical_chance_bonus"]
                result["effects"].append({
                    "type": "critical_bonus",
                    "bonus": bonus,
                    "attacker": attacker.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.COMBAT_EFFECT,
                    attacker.name,
                    self.name,
                    {"critical_bonus": bonus}
                ))
            
            # Handle accuracy modifiers
            elif "accuracy_modifier" in params:
                modifier = params["accuracy_modifier"]
                result["effects"].append({
                    "type": "accuracy_modifier",
                    "modifier": modifier,
                    "attacker": attacker.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.COMBAT_EFFECT,
                    attacker.name,
                    self.name,
                    {"accuracy_modifier": modifier}
                ))
            
            # Handle element resistance changes
            elif "element_resistance" in params:
                element = params.get("element", "unknown")
                resistance_change = params["element_resistance"]
                
                result["effects"].append({
                    "type": "resistance_change",
                    "element": element,
                    "change": resistance_change,
                    "defender": defender.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.COMBAT_EFFECT,
                    defender.name,
                    self.name,
                    {"element": element, "resistance_change": resistance_change}
                ))
            
            # Handle counter-attack triggers
            elif "counter_chance" in params:
                chance = params["counter_chance"]
                if random.random() < chance:
                    result["effects"].append({
                        "type": "counter_attack",
                        "triggered": True,
                        "defender": defender.name,
                        "attacker": attacker.name
                    })
                    
                    battlefield_events.emit(BattlefieldEvent(
                        BattlefieldEventType.COMBAT_EFFECT,
                        defender.name,
                        "Counter Attack",
                        {"original_attacker": attacker.name}
                    ))
            
            # Handle spell reflection
            elif "reflect_chance" in params:
                chance = params["reflect_chance"]
                if random.random() < chance:
                    result["effects"].append({
                        "type": "spell_reflect",
                        "triggered": True,
                        "defender": defender.name,
                        "attacker": attacker.name
                    })
                    
                    battlefield_events.emit(BattlefieldEvent(
                        BattlefieldEventType.COMBAT_EFFECT,
                        defender.name,
                        "Spell Reflection",
                        {"reflected_to": attacker.name}
                    ))
            
            # Handle enhanced critical hits
            elif "critical_multiplier" in params:
                multiplier = params["critical_multiplier"]
                result["effects"].append({
                    "type": "critical_multiplier",
                    "multiplier": multiplier,
                    "attacker": attacker.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.COMBAT_EFFECT,
                    attacker.name,
                    "Enhanced Critical",
                    {"multiplier": multiplier}
                ))
            
            # Handle damage sharing
            elif "damage_share_percent" in params:
                share_percent = params["damage_share_percent"]
                result["effects"].append({
                    "type": "damage_sharing",
                    "share_percent": share_percent,
                    "all_characters": True
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.COMBAT_EFFECT,
                    "all_characters",
                    "Damage Sharing",
                    {"share_percent": share_percent}
                ))
            
            # Handle healing sharing
            elif "heal_share_percent" in params:
                heal_percent = params["heal_share_percent"]
                result["effects"].append({
                    "type": "healing_sharing",
                    "heal_percent": heal_percent,
                    "all_characters": True
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.COMBAT_EFFECT,
                    "all_characters",
                    "Healing Sharing",
                    {"heal_percent": heal_percent}
                ))
            
            # Handle lifesteal
            elif "lifesteal_percent" in params:
                lifesteal_percent = params["lifesteal_percent"]
                result["effects"].append({
                    "type": "lifesteal",
                    "percent": lifesteal_percent,
                    "attacker": attacker.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.COMBAT_EFFECT,
                    attacker.name,
                    "Lifesteal",
                    {"percent": lifesteal_percent}
                ))
            
            # Handle critical healing
            elif "crit_heal_percent" in params:
                heal_percent = params["crit_heal_percent"]
                result["effects"].append({
                    "type": "critical_heal",
                    "heal_percent": heal_percent,
                    "attacker": attacker.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.COMBAT_EFFECT,
                    attacker.name,
                    "Critical Healing",
                    {"heal_percent": heal_percent}
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing combat effect: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_enhancement_effect(self, character, **kwargs) -> Dict[str, Any]:
        """Execute enhancement effects - passive effects that modify character capabilities"""
        if not self.effect_data or self.effect_data.category != EffectCategory.ENHANCEMENT_EFFECT:
            return {"success": False, "message": "No enhancement effect"}
        
        try:
            result = {"success": True, "effects": []}
            params = self.effect_data.parameters
            
            # Handle revival effects
            if "revive_hp_percent" in params:
                revive_percent = params["revive_hp_percent"]
                result["effects"].append({
                    "type": "revival_enhancement",
                    "revive_hp_percent": revive_percent,
                    "character": character.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.EFFECT_APPLIED,
                    character.name,
                    "Revival Protection",
                    {"revive_hp_percent": revive_percent}
                ))
            
            # Handle ability potency
            elif "potency_multiplier" in params:
                multiplier = params["potency_multiplier"]
                result["effects"].append({
                    "type": "ability_enhancement",
                    "potency_multiplier": multiplier,
                    "character": character.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.EFFECT_APPLIED,
                    character.name,
                    "Ability Enhancement",
                    {"multiplier": multiplier}
                ))
            
            # Handle healing enhancement
            elif "healing_multiplier" in params:
                multiplier = params["healing_multiplier"]
                result["effects"].append({
                    "type": "healing_enhancement",
                    "healing_multiplier": multiplier,
                    "character": character.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.HEALING_MODIFIED,
                    character.name,
                    "Healing Enhancement",
                    {"multiplier": multiplier}
                ))
            
            # Handle status duration enhancement
            elif "duration_multiplier" in params:
                multiplier = params["duration_multiplier"]
                result["effects"].append({
                    "type": "status_duration_enhancement",
                    "duration_multiplier": multiplier,
                    "character": character.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.EFFECT_APPLIED,
                    character.name,
                    "Status Duration Enhancement",
                    {"multiplier": multiplier}
                ))
            
            # Handle pattern sight
            elif "pattern_sight" in params:
                result["effects"].append({
                    "type": "pattern_sight",
                    "enabled": True,
                    "character": character.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.EFFECT_APPLIED,
                    character.name,
                    "Pattern Sight",
                    {"enabled": True}
                ))
            
            # Handle dual timeline
            elif "timeline_split" in params:
                result["effects"].append({
                    "type": "dual_timeline",
                    "enabled": True,
                    "character": character.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.EFFECT_APPLIED,
                    character.name,
                    "Dual Timeline",
                    {"enabled": True}
                ))
            
            # Handle temporal effects
            elif "affects_future" in params:
                result["effects"].append({
                    "type": "temporal_effect",
                    "affects_future": True,
                    "character": character.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.EFFECT_APPLIED,
                    character.name,
                    "Temporal Effect",
                    {"affects_future": True}
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing enhancement effect: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_targeting_effect(self, attacker, original_target, all_characters) -> Dict[str, Any]:
        """Execute targeting effects that modify target selection"""
        if not self.effect_data or self.effect_data.category != EffectCategory.TARGETING_EFFECT:
            return {"success": False, "message": "No targeting effect", "target": original_target}
        
        try:
            result = {"success": True, "effects": [], "target": original_target}
            params = self.effect_data.parameters
            
            # Handle misdirection
            if "misdirection_chance" in params:
                chance = params["misdirection_chance"] / 100.0
                if random.random() < chance:
                    # Find valid alternative targets
                    if hasattr(attacker, 'team_id'):
                        enemy_team = 'B' if attacker.team_id == 'A' else 'A'
                        possible_targets = [c for c in all_characters 
                                         if hasattr(c, 'team_id') and c.team_id == enemy_team 
                                         and c != original_target and getattr(c, 'is_alive', True)]
                    else:
                        possible_targets = [c for c in all_characters 
                                         if c != original_target and c != attacker 
                                         and getattr(c, 'is_alive', True)]
                    
                    if possible_targets:
                        new_target = random.choice(possible_targets)
                        result["target"] = new_target
                        result["effects"].append({
                            "type": "target_misdirection",
                            "original_target": original_target.name if hasattr(original_target, 'name') else str(original_target),
                            "new_target": new_target.name if hasattr(new_target, 'name') else str(new_target)
                        })
                        
                        battlefield_events.emit(BattlefieldEvent(
                            BattlefieldEventType.TARGETING_CHANGED,
                            attacker.name if hasattr(attacker, 'name') else str(attacker),
                            "Misdirection",
                            {"original": str(original_target), "new": str(new_target)}
                        ))
            
            # Handle unlimited targeting
            elif "unlimited_targets" in params:
                result["effects"].append({
                    "type": "unlimited_targeting",
                    "enabled": True
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.TARGETING_CHANGED,
                    attacker.name if hasattr(attacker, 'name') else str(attacker),
                    "Unlimited Targeting",
                    {"enabled": True}
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing targeting effect: {e}")
            return {"success": False, "error": str(e), "target": original_target}
    
    def setup_turn_modifiers(self, character) -> Dict[str, Any]:
        """Setup turn-specific modifiers for the character"""
        modifiers = {
            'max_actions': 1,
            'skip_turn_consumption': False,
            'cost_modifier': 1.0,
            'healing_multiplier': 1.0,
            'minimum_hp': 0,
            'enhancement_multiplier': 1.0
        }
        
        if self.effect_type != "special_rule":
            return modifiers
            
        description = self.description.lower()
        
        # Double turns / Act twice per turn
        if 'act twice per turn' in description:
            modifiers['max_actions'] = 2
            battlefield_events.emit(BattlefieldEvent(
                BattlefieldEventType.TURN_MODIFIER_APPLIED,
                character.name,
                "Double Action",
                {"modifier": "max_actions", "value": 2}
            ))
        
        # Cost reduction
        elif 'cost 25% less' in description:
            modifiers['cost_modifier'] = 0.75
            battlefield_events.emit(BattlefieldEvent(
                BattlefieldEventType.TURN_MODIFIER_APPLIED,
                character.name,
                "Cost Reduction",
                {"modifier": "cost_modifier", "value": 0.75}
            ))
        
        # Healing multiplier
        elif 'healing effects are doubled' in description:
            modifiers['healing_multiplier'] = 2.0
            battlefield_events.emit(BattlefieldEvent(
                BattlefieldEventType.HEALING_MODIFIED,
                character.name,
                "Healing Boost",
                {"multiplier": 2.0}
            ))
        
        # Minimum HP protection
        elif 'no character can be reduced below 1 hp' in description:
            modifiers['minimum_hp'] = 1
            battlefield_events.emit(BattlefieldEvent(
                BattlefieldEventType.EFFECT_APPLIED,
                character.name,
                "HP Protection",
                {"minimum_hp": 1}
            ))
        
        # Turn consumption prevention
        elif 'chance to not consume a turn' in description:
            if random.randint(1, 100) <= 15:  # 15% chance
                modifiers['skip_turn_consumption'] = True
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.TURN_MODIFIER_APPLIED,
                    character.name,
                    "Turn Preservation",
                    {"skip_turn_consumption": True}
                ))
        
        # Enhanced effects from magical pressure
        elif 'enhanced effects due to magical pressure' in description:
            modifiers['enhancement_multiplier'] *= 1.5
            battlefield_events.emit(BattlefieldEvent(
                BattlefieldEventType.EFFECT_APPLIED,
                character.name,
                "Magical Enhancement",
                {"enhancement_multiplier": 1.5}
            ))
        
        # Enhanced range and area effects
        elif 'enhanced range and area effects' in description:
            modifiers['enhancement_multiplier'] *= 1.3
            battlefield_events.emit(BattlefieldEvent(
                BattlefieldEventType.EFFECT_APPLIED,
                character.name,
                "Area Enhancement",
                {"enhancement_multiplier": 1.3}
            ))
        
        return modifiers
    
    def apply_combat_modifier(self, damage: float = 0, healing: float = 0, is_attacker: bool = True) -> Tuple[float, float]:
        """Apply combat modifiers to damage and healing"""
        if self.effect_type != "special_rule":
            return damage, healing
            
        description = self.description.lower()
        
        # Chain lightning effect
        if 'chain' in description and damage > 0:
            if random.randint(1, 100) <= 30:  # 30% chance
                chain_damage = damage * 0.5
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.DAMAGE_MODIFIED,
                    "battlefield",
                    "Chain Lightning",
                    {"additional_damage": chain_damage}
                ))
                return damage + chain_damage, healing
        
        # Shared damage/healing
        elif 'shared' in description or 'quantum entanglement' in description:
            if damage > 0:
                shared_damage = damage * 0.3
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.DAMAGE_MODIFIED,
                    "battlefield",
                    "Quantum Entanglement",
                    {"shared_damage": shared_damage}
                ))
                return damage + shared_damage, healing
            elif healing > 0:
                shared_healing = healing * 0.3
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.HEALING_MODIFIED,
                    "battlefield",
                    "Quantum Entanglement",
                    {"shared_healing": shared_healing}
                ))
                return damage, healing + shared_healing
        
        return damage, healing
    
    def execute_stat_modifier(self, character) -> Dict[str, Any]:
        """Execute stat modifier effects - pure function with structured results"""
        if self.effect_type != "stat_modifier":
            return {"success": False, "message": "Not a stat modifier effect"}
        
        try:
            result = {"success": True, "effects": []}
            
            # Parse the effect description to extract stat modifications
            description = self.description.lower()
            
            # Extract stat type and value from description
            stat_type = None
            modifier_value = 0
            modifier_type = "percentage"  # or "flat"
            
            # Parse patterns like "+20% ATK", "-10% VIT", "gain +25% MAG", "SPD is reduced by 30%"
            import re
            
            # Look for percentage modifiers - various patterns (order matters!)
            percentage_patterns = [
                r'(atk|mag|vit|spr|int|spd|lck).*?reduced by (\d+)%',  # "SPD is reduced by 30%" - MUST BE FIRST
                r'(atk|mag|vit|spr|int|spd|lck).*?increased by (\d+)%',  # "SPD is increased by 30%" - MUST BE SECOND
                r'([+-]?\d+)%\s*(atk|mag|vit|spr|int|spd|lck)',  # "+20% ATK"
                r'(atk|mag|vit|spr|int|spd|lck).*?([+-]?\d+)%',  # "ATK increased by 20%" - GENERAL PATTERN LAST
            ]
            
            for pattern in percentage_patterns:
                match = re.search(pattern, description)
                if match:
                    if pattern.endswith('reduced by (\\d+)%'):
                        # Handle "reduced by" pattern
                        stat_type = match.group(1).upper()
                        modifier_value = -int(match.group(2))  # Negative for reduction
                    elif pattern.endswith('increased by (\\d+)%'):
                        # Handle "increased by" pattern  
                        stat_type = match.group(1).upper()
                        modifier_value = int(match.group(2))
                    elif len(match.groups()) == 2:
                        if match.group(1).isdigit() or (match.group(1).startswith('-') and match.group(1)[1:].isdigit()) or (match.group(1).startswith('+') and match.group(1)[1:].isdigit()):
                            # First group is number
                            modifier_value = int(match.group(1))
                            stat_type = match.group(2).upper()
                        else:
                            # Second group is number
                            stat_type = match.group(1).upper()
                            modifier_value = int(match.group(2))
                    modifier_type = "percentage"
                    break
            
            # Look for flat modifiers if no percentage modifier was found
            if not stat_type:
                flat_match = re.search(r'([+-]?\d+)\s*(atk|mag|vit|spr|int|spd|lck)', description)
                if flat_match:
                    modifier_value = int(flat_match.group(1))
                    stat_type = flat_match.group(2).upper()
                    modifier_type = "flat"
            
            if stat_type and modifier_value != 0:
                # Apply the stat modifier to the character
                old_value = character.current_stats.get(stat_type.lower(), 0)
                
                if modifier_type == "percentage":
                    new_value = old_value * (1 + modifier_value / 100.0)
                else:  # flat
                    new_value = old_value + modifier_value
                
                # Update character stats
                character.current_stats[stat_type.lower()] = new_value
                
                result["effects"].append({
                    "type": "stat_modifier",
                    "stat": stat_type.lower(),
                    "old_value": old_value,
                    "new_value": new_value,
                    "modifier_value": modifier_value,
                    "modifier_type": modifier_type,
                    "character": character.name
                })
                
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.EFFECT_APPLIED,
                    character.name,
                    f"Stat Modifier ({stat_type})",
                    {"stat": stat_type, "old": old_value, "new": new_value}
                ))
            else:
                result["success"] = False
                result["message"] = f"Could not parse stat modifier from: {self.description}"
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing stat modifier: {e}")
            return {"success": False, "error": str(e)}

@dataclass
class BattlefieldCondition:
    """Complete battlefield condition definition"""
    condition_id: str
    name: str
    condition_type: ConditionType
    description: str
    effects: List[BattlefieldEffect]
    duration_days: int = 7  # Default weekly duration
    rarity: str = "common"  # "common", "rare", "legendary"
    
    def apply_to_character(self, character):
        """Apply initial condition effects to character"""
        # Store condition reference
        if not hasattr(character, 'active_battlefield_condition'):
            character.active_battlefield_condition = self
        
        # Apply stat modifiers
        for effect in self.effects:
            if effect.effect_type == "stat_modifier":
                self._apply_stat_modifier_effect(character, effect)
        
        # Store special rules for later execution
        special_rules = []
        for effect in self.effects:
            if effect.effect_type == "special_rule":
                special_rules.append({
                    'effect': effect,
                    'description': effect.description,
                    'rule_type': self._categorize_special_rule(effect.description)
                })
        
        if not hasattr(character, 'battlefield_special_effects'):
            character.battlefield_special_effects = []
        character.battlefield_special_effects = special_rules
        
        return special_rules
    
    def process_turn_start(self, character, turn_count: int = 0) -> Dict[str, Any]:
        """Process all turn-start effects and return modifiers"""
        combined_modifiers = {
            'max_actions': 1,
            'skip_turn_consumption': False,
            'cost_modifier': 1.0,
            'healing_multiplier': 1.0,
            'minimum_hp': 0,
            'enhancement_multiplier': 1.0,
            'extra_turns': 0
        }
        
        # Execute per-turn effects
        for effect in self.effects:
            if effect.effect_type == "special_rule":
                effect.execute_turn_effect(character)
                
                # Get turn modifiers and combine them
                modifiers = effect.setup_turn_modifiers(character)
                for key, value in modifiers.items():
                    if key == 'enhancement_multiplier':
                        combined_modifiers[key] *= value
                    elif key in ['max_actions', 'minimum_hp']:
                        combined_modifiers[key] = max(combined_modifiers[key], value)
                    elif key in ['cost_modifier']:
                        combined_modifiers[key] = min(combined_modifiers[key], value)
                    elif key in ['healing_multiplier']:
                        combined_modifiers[key] *= value
                    else:
                        combined_modifiers[key] = value or combined_modifiers[key]
                
                # Handle extra turns every N rounds
                if 'extra turn every' in effect.description.lower():
                    if turn_count % 3 == 0:  # Every 3rd round
                        combined_modifiers['extra_turns'] += 1
                        battlefield_events.emit(BattlefieldEvent(
                            BattlefieldEventType.TURN_MODIFIER_APPLIED,
                            character.name,
                            "Extra Turn",
                            {"turn_count": turn_count}
                        ))
        
        return combined_modifiers
    
    def modify_combat_values(self, damage: float = 0, healing: float = 0, attacker=None, target=None) -> tuple[float, float]:
        """Apply combat modifiers to damage and healing values"""
        modified_damage = damage
        modified_healing = healing
        
        for effect in self.effects:
            if effect.effect_type == "special_rule":
                mod_damage, mod_healing = effect.apply_combat_modifier(modified_damage, modified_healing)
                modified_damage = mod_damage
                modified_healing = mod_healing
        
        return modified_damage, modified_healing
    
    def check_special_targeting(self, attacker, original_target, all_characters) -> Any:
        """Check for special targeting effects and return modified target"""
        for effect in self.effects:
            if effect.effect_type == "special_rule":
                description = effect.description.lower()
                
                # Random targeting
                if 'random' in description and 'target' in description:
                    if random.randint(1, 100) <= 10:  # 10% chance
                        # Find valid targets (opponents)
                        if attacker in [c for c in all_characters if hasattr(c, 'team_id') and c.team_id == 'A']:
                            possible_targets = [c for c in all_characters if hasattr(c, 'team_id') and c.team_id == 'B' and c.is_alive and c != original_target]
                        else:
                            possible_targets = [c for c in all_characters if hasattr(c, 'team_id') and c.team_id == 'A' and c.is_alive and c != original_target]
                        
                        if possible_targets:
                            new_target = random.choice(possible_targets)
                            battlefield_events.emit(BattlefieldEvent(
                                BattlefieldEventType.TARGETING_CHANGED,
                                attacker.name,
                                "Random Targeting",
                                {"original_target": original_target.name, "new_target": new_target.name}
                            ))
                            return new_target
                
                # Miss chance
                elif 'miss' in description:
                    if random.randint(1, 100) <= 15:  # 15% chance to miss
                        battlefield_events.emit(BattlefieldEvent(
                            BattlefieldEventType.TARGETING_CHANGED,
                            attacker.name,
                            "Attack Miss",
                            {"reason": self.name}
                        ))
                        return None  # Indicates miss
        
        return original_target
    
    def _categorize_special_rule(self, description: str) -> str:
        """Categorize special rules for easier processing"""
        desc_lower = description.lower()
        
        if any(keyword in desc_lower for keyword in ['twice per turn', 'double turn']):
            return 'double_turn'
        elif any(keyword in desc_lower for keyword in ['extra turn', 'additional turn']):
            return 'extra_turn'
        elif any(keyword in desc_lower for keyword in ['cost', 'less']):
            return 'cost_reduction'
        elif any(keyword in desc_lower for keyword in ['healing', 'doubled']):
            return 'healing_multiplier'
        elif any(keyword in desc_lower for keyword in ['below 1 hp', 'minimum hp']):
            return 'minimum_hp'
        elif any(keyword in desc_lower for keyword in ['enhanced effects', 'enhanced range']):
            return 'enhancement'
        elif any(keyword in desc_lower for keyword in ['randomized', 'random']):
            return 'random_effect'
        elif any(keyword in desc_lower for keyword in ['not consume', 'doesn\'t consume']):
            return 'skip_consumption'
        else:
            return 'other'
    
    def _apply_stat_modifier_effect(self, character, effect: BattlefieldEffect):
        """Apply stat modifier effect to character"""
        if not effect.stat_affected:
            return
            
        if hasattr(character, 'apply_stat_modifier'):
            # Use character's own method if available
            character.apply_stat_modifier(effect.stat_affected, effect.modifier_value, effect.modifier_type)
        elif hasattr(character, 'current_stats') and effect.stat_affected in character.current_stats:
            # Fallback for simple character objects
            if effect.modifier_type == "percentage":
                character.current_stats[effect.stat_affected] = character.base_stats[effect.stat_affected] * (1 + effect.modifier_value)
            else:
                character.current_stats[effect.stat_affected] = character.base_stats[effect.stat_affected] + effect.modifier_value
        else:
            # Skip if stat doesn't exist
            battlefield_events.emit(BattlefieldEvent(
                BattlefieldEventType.EFFECT_APPLIED,
                character.name,
                "Stat Modifier Skipped",
                {"stat": effect.stat_affected, "reason": "stat not found"}
            ))

class BattlefieldConditionsSystem:
    """Manages battlefield conditions and their effects"""
    
    def __init__(self):
        self.conditions: Dict[str, BattlefieldCondition] = {}
        self.active_condition: Optional[BattlefieldCondition] = None
        self.condition_start_date: Optional[datetime] = None
        self._initialize_battlefield_conditions()
        logger.info("Initialized battlefield conditions system with %d conditions", len(self.conditions))
    
    def _initialize_battlefield_conditions(self):
        """Load battlefield conditions from the battlefield_conditions.json file"""
        try:
            with open('data/battlefield_conditions.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Helper function to convert string enums
            def get_condition_type(type_str: str) -> ConditionType:
                mapping = {
                    "environmental": ConditionType.ENVIRONMENTAL,
                    "magical": ConditionType.MAGICAL,
                    "weather": ConditionType.WEATHER,
                    "cosmic": ConditionType.COSMIC,
                    "temporal": ConditionType.TEMPORAL
                }
                return mapping.get(type_str, ConditionType.ENVIRONMENTAL)
            
            # Process each battlefield condition
            for condition_id, condition_data in data['battlefield_conditions'].items():
                try:
                    # Create effects list
                    effects = []
                    for effect_data in condition_data['effects']:
                        effect = BattlefieldEffect(
                            effect_type=effect_data['effect_type'],
                            target_criteria=effect_data['target_criteria'],
                            stat_affected=effect_data.get('stat_affected'),
                            modifier_value=effect_data.get('modifier_value', 0.0),
                            modifier_type=effect_data.get('modifier_type', 'percentage'),
                            description=effect_data['description']
                        )
                        effects.append(effect)
                    
                    # Create battlefield condition
                    condition = BattlefieldCondition(
                        condition_id=condition_id,
                        name=condition_data['name'],
                        condition_type=get_condition_type(condition_data['type']),
                        description=condition_data['description'],
                        effects=effects,
                        duration_days=condition_data.get('duration_days', 7),
                        rarity=condition_data.get('rarity', 'common')
                    )
                    
                    self.conditions[condition_id] = condition
                    
                except KeyError as e:
                    logger.warning("Missing key in battlefield condition data for %s: %s", condition_id, e)
                    continue
                    
            logger.info("Loaded %d battlefield conditions from JSON", len(self.conditions))
            
        except FileNotFoundError:
            logger.error("Battlefield conditions file not found: data/battlefield_conditions.json")
            self._create_fallback_conditions()
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in battlefield conditions file: %s", e)
            self._create_fallback_conditions()
        except KeyError as e:
            logger.error("Missing key in battlefield conditions file: %s", e)
            self._create_fallback_conditions()
    
    def _create_fallback_conditions(self):
        """Create basic fallback conditions if JSON loading fails"""
        logger.warning("Creating fallback battlefield conditions")
        
        # Basic fallback condition
        fallback_condition = BattlefieldCondition(
            condition_id="neutral_battlefield",
            name="Neutral Battlefield",
            condition_type=ConditionType.ENVIRONMENTAL,
            description="Normal battlefield conditions with no special effects.",
            effects=[],
            duration_days=7,
            rarity="common"
        )
        
        self.conditions["neutral_battlefield"] = fallback_condition
    
    def set_active_condition(self, condition_id: str) -> bool:
        """Set the active battlefield condition"""
        if condition_id not in self.conditions:
            logger.warning("Unknown battlefield condition: %s", condition_id)
            return False
        
        self.active_condition = self.conditions[condition_id]
        self.condition_start_date = datetime.now()
        
        logger.info("Activated battlefield condition: %s", self.active_condition.name)
        return True
    
    def get_random_condition(self, rarity_filter: Optional[str] = None) -> BattlefieldCondition:
        """Get a random battlefield condition, optionally filtered by rarity"""
        available_conditions = []
        
        for condition in self.conditions.values():
            if rarity_filter is None or condition.rarity == rarity_filter:
                available_conditions.append(condition)
        
        if not available_conditions:
            # Fallback to common conditions
            available_conditions = [c for c in self.conditions.values() if c.rarity == "common"]
        
        return random.choice(available_conditions)
    
    def activate_condition_for_characters(self, condition_id: str, characters: List[Any]) -> bool:
        """Activate a battlefield condition and apply it to all characters"""
        if not self.set_active_condition(condition_id):
            return False
        
        if not self.active_condition:
            return False
        
        # Emit battlefield condition activation event
        battlefield_events.emit(BattlefieldEvent(
            BattlefieldEventType.EFFECT_APPLIED,
            "battlefield_system",
            "Condition Activated",
            {
                "condition_name": self.active_condition.name,
                "rarity": self.active_condition.rarity,
                "description": self.active_condition.description
            }
        ))
        
        special_rules = []
        for character in characters:
            rules = self.active_condition.apply_to_character(character)
            special_rules.extend(rules)
        
        # Display special rules
        if special_rules:
            unique_rules = []
            for rule in special_rules:
                if rule['description'] not in [r['description'] for r in unique_rules]:
                    unique_rules.append(rule)
            
            if unique_rules:
                # Emit special rules event
                battlefield_events.emit(BattlefieldEvent(
                    BattlefieldEventType.EFFECT_APPLIED,
                    "battlefield_system",
                    "Special Rules Applied",
                    {"rules": [rule['description'] for rule in unique_rules]}
                ))
        
        print()
        return True
    
    def process_turn_start_for_character(self, character, turn_count: int = 0) -> Dict[str, Any]:
        """Process turn start effects for a character"""
        if not self.active_condition:
            return {
                'max_actions': 1,
                'skip_turn_consumption': False,
                'cost_modifier': 1.0,
                'healing_multiplier': 1.0,
                'minimum_hp': 0,
                'enhancement_multiplier': 1.0,
                'extra_turns': 0
            }
        
        return self.active_condition.process_turn_start(character, turn_count)
    
    def modify_damage_and_healing(self, damage: float = 0, healing: float = 0, attacker=None, target=None) -> Tuple[float, float]:
        """Apply battlefield condition modifiers to damage and healing"""
        if not self.active_condition:
            return damage, healing
        
        return self.active_condition.modify_combat_values(damage, healing, attacker, target)
    
    def check_targeting_effects(self, attacker, original_target, all_characters):
        """Check for special targeting effects and return modified target or None for miss"""
        if not self.active_condition:
            return original_target
        
        return self.active_condition.check_special_targeting(attacker, original_target, all_characters)
    
    def apply_character_modifiers(self, character, damage: float = 0, healing: float = 0) -> Tuple[float, float]:
        """Apply character-specific battlefield modifiers"""
        if not hasattr(character, 'battlefield_special_effects'):
            return damage, healing
        
        # Apply enhancement multiplier if character has it
        enhancement = getattr(character, 'enhancement_multiplier', 1.0)
        if enhancement != 1.0:
            if damage > 0:
                damage *= enhancement
            if healing > 0:
                healing *= enhancement
        
        # Apply healing multiplier
        healing_mult = getattr(character, 'healing_multiplier', 1.0)
        if healing_mult != 1.0:
            healing *= healing_mult
        
        return damage, healing
    
    def rotate_weekly_condition(self) -> BattlefieldCondition:
        """Rotate to a new weekly battlefield condition"""
        # Weighted random selection based on rarity
        rarity_weights = {
            "common": 0.70,     # 70% chance
            "rare": 0.25,       # 25% chance
            "legendary": 0.05   # 5% chance
        }
        
        rarity_roll = random.random()
        selected_rarity = "common"
        
        cumulative = 0.0
        for rarity, weight in rarity_weights.items():
            cumulative += weight
            if rarity_roll <= cumulative:
                selected_rarity = rarity
                break
        
        new_condition = self.get_random_condition(selected_rarity)
        self.active_condition = new_condition
        self.condition_start_date = datetime.now()
        
        logger.info("Rotated to new battlefield condition: %s (%s)", 
                   new_condition.name, new_condition.rarity)
        return new_condition
    
    def is_condition_expired(self) -> bool:
        """Check if the current condition has expired"""
        if not self.active_condition or not self.condition_start_date:
            return True
        
        expiry_date = self.condition_start_date + timedelta(days=self.active_condition.duration_days)
        return datetime.now() > expiry_date
    
    def apply_condition_effects(self, characters: List) -> Dict[str, List[str]]:
        """Apply battlefield condition effects to characters"""
        if not self.active_condition:
            return {}
        
        applied_effects: Dict[str, List[str]] = {}
        
        for character in characters:
            character_effects = []
            
            for effect in self.active_condition.effects:
                if self._character_matches_criteria(character, effect.target_criteria):
                    if effect.effect_type == "stat_modifier":
                        self._apply_stat_modifier_effect(character, effect)
                        character_effects.append(f"{effect.stat_affected}: {effect.modifier_value:+.0%}")
                    elif effect.effect_type == "special_rule":
                        self._apply_special_rule_effect(character, effect)
                        character_effects.append(effect.description)
            
            if character_effects:
                applied_effects[character.character_id] = character_effects
        
        logger.info("Applied battlefield condition '%s' to %d characters", 
                   self.active_condition.name, len(applied_effects))
        return applied_effects
    
    def _character_matches_criteria(self, character, criteria: str) -> bool:
        """Check if character matches the effect criteria"""
        if criteria == "all":
            return True
        elif criteria == "fire_elemental":
            character_elements = getattr(character, 'get_elements', lambda: [])()
            return "fire" in character_elements
        elif criteria == "water_elemental":
            character_elements = getattr(character, 'get_elements', lambda: [])()
            return "water" in character_elements
        elif criteria == "earth_elemental":
            character_elements = getattr(character, 'get_elements', lambda: [])()
            return "earth" in character_elements
        elif criteria == "air_elemental":
            character_elements = getattr(character, 'get_elements', lambda: [])()
            return "air" in character_elements
        elif criteria == "light_elemental":
            character_elements = getattr(character, 'get_elements', lambda: [])()
            return "light" in character_elements
        elif criteria == "dark_elemental":
            character_elements = getattr(character, 'get_elements', lambda: [])()
            return "dark" in character_elements
        elif criteria == "elemental":
            character_elements = getattr(character, 'get_elements', lambda: ["neutral"])()
            return len(character_elements) > 0 and "neutral" not in character_elements
        elif criteria == "non_elemental":
            character_elements = getattr(character, 'get_elements', lambda: ["neutral"])()
            return "neutral" in character_elements or len(character_elements) == 0
        elif criteria.startswith("archetype_"):
            # Support archetype-based targeting
            archetype_name = criteria.replace("archetype_", "")
            character_archetype = getattr(character, 'archetype', None)
            if character_archetype:
                return character_archetype.value == archetype_name
            return False
        elif criteria.startswith("stat_"):
            # Support stat-based targeting (e.g., "stat_high_atk", "stat_low_spd")
            stat_condition = criteria.replace("stat_", "")
            return self._check_stat_condition(character, stat_condition)
        else:
            # Add more criteria as needed
            return False
    
    def _check_stat_condition(self, character, stat_condition: str) -> bool:
        """Check if character meets stat-based condition"""
        if not hasattr(character, 'stats'):
            return False
        
        # Parse conditions like "high_atk", "low_spd", etc.
        if stat_condition.startswith("high_"):
            stat_name = stat_condition.replace("high_", "")
            stat_value = getattr(character.stats, f"get_{stat_name}", lambda: 0)()
            # Consider "high" as above average (you can adjust threshold)
            return stat_value > 100  # Adjust threshold as needed
        elif stat_condition.startswith("low_"):
            stat_name = stat_condition.replace("low_", "")
            stat_value = getattr(character.stats, f"get_{stat_name}", lambda: 0)()
            # Consider "low" as below average
            return stat_value < 80   # Adjust threshold as needed
        
        return False

    def _apply_stat_modifier_effect(self, character, effect: BattlefieldEffect):
        """Apply stat modifier from battlefield condition"""
        if not effect.stat_affected or not self.active_condition:
            return
        
        condition_id = self.active_condition.condition_id
        
        # Handle both complex stats system and simple character stats
        if hasattr(character, 'stats') and hasattr(character.stats, 'add_modifier'):
            # Full stats system (for full game)
            if effect.stat_affected == "all_stats":
                # Apply to all stats
                for stat in ["hp", "atk", "mag", "vit", "spr", "int", "spd", "lck"]:
                    modifier = StatModifier(
                        modifier_id=f"battlefield_{condition_id}_{stat}",
                        stat_type=getattr(StatType, stat.upper()),
                        modifier_type=getattr(ModifierType, effect.modifier_type.upper()),
                        value=effect.modifier_value,
                        source=f"battlefield_{condition_id}",
                        layer=3,  # Battlefield conditions apply after synergies
                        duration=None  # Permanent while condition is active
                    )
                    character.stats.add_modifier(modifier)
            else:
                # Apply to specific stat
                modifier = StatModifier(
                    modifier_id=f"battlefield_{condition_id}_{effect.stat_affected}",
                    stat_type=getattr(StatType, effect.stat_affected.upper()),
                    modifier_type=getattr(ModifierType, effect.modifier_type.upper()),
                    value=effect.modifier_value,
                    source=f"battlefield_{condition_id}",
                    layer=3,
                    duration=None
                )
                character.stats.add_modifier(modifier)
        elif hasattr(character, 'apply_stat_modifier'):
            # Simple character with basic stat modification (for tests)
            if effect.stat_affected == "all_stats":
                # Apply to all stats
                for stat in ["hp", "atk", "mag", "vit", "spr", "int", "spd", "lck"]:
                    character.apply_stat_modifier(stat, effect.modifier_value, effect.modifier_type)
            else:
                # Apply to specific stat
                character.apply_stat_modifier(effect.stat_affected, effect.modifier_value, effect.modifier_type)
        else:
            logger.warning("Character %s doesn't support stat modifications", 
                          getattr(character, 'character_id', 'unknown'))
            return
        
        logger.debug("Applied battlefield stat modifier %s to character %s", 
                    effect.stat_affected, character.character_id)
    
    def _apply_special_rule_effect(self, character, effect: BattlefieldEffect):
        """Apply special rule from battlefield condition"""
        # Enhanced special rule handling for new creative effects
        if not self.active_condition:
            return
            
        condition_id = self.active_condition.condition_id
        
        # Store special rules on the character for combat system to use
        if not hasattr(character, 'battlefield_special_rules'):
            character.battlefield_special_rules = []
        
        # Create a special rule data structure
        special_rule = {
            'condition_id': condition_id,
            'condition_name': self.active_condition.name,
            'rule_type': self._categorize_special_rule(effect.description),
            'description': effect.description,
            'effect_data': self._parse_special_rule_data(effect.description)
        }
        
        # Add to character's special rules if not already present
        existing_rule = next(
            (rule for rule in character.battlefield_special_rules 
             if rule['condition_id'] == condition_id and rule['description'] == effect.description),
            None
        )
        
        if not existing_rule:
            character.battlefield_special_rules.append(special_rule)
            logger.debug("Applied battlefield special rule to character %s: %s", 
                        character.character_id, effect.description)
    
    def _categorize_special_rule(self, description: str) -> str:
        """Categorize special rule by type for easier combat system integration"""
        description_lower = description.lower()
        
        if 'critical' in description_lower:
            return 'critical_modifier'
        elif 'damage' in description_lower and 'deal' in description_lower:
            return 'damage_modifier'
        elif 'heal' in description_lower or 'hp' in description_lower:
            return 'healing_modifier'
        elif 'miss' in description_lower or 'accuracy' in description_lower:
            return 'accuracy_modifier'
        elif 'revive' in description_lower or 'defeat' in description_lower:
            return 'revival_effect'
        elif 'turn' in description_lower or 'action' in description_lower:
            return 'turn_modifier'
        elif 'target' in description_lower and 'random' in description_lower:
            return 'targeting_modifier'
        elif 'regenerate' in description_lower or 'per turn' in description_lower:
            return 'per_turn_effect'
        elif 'chain' in description_lower or 'lightning' in description_lower:
            return 'chain_effect'
        elif 'double' in description_lower or 'twice' in description_lower:
            return 'action_multiplier'
        else:
            return 'general_effect'
    
    def _parse_special_rule_data(self, description: str) -> Dict[str, Any]:
        """Parse numerical data from special rule descriptions"""
        
        data = {}
        description_lower = description.lower()
        
        # Extract percentages
        percentage_matches = re.findall(r'(\d+)%', description)
        if percentage_matches:
            data['percentage'] = int(percentage_matches[0])
        
        # Extract multipliers (like 2.0x, 1.5x)
        multiplier_matches = re.findall(r'(\d+\.?\d*)x', description)
        if multiplier_matches:
            data['multiplier'] = float(multiplier_matches[0])
        
        # Extract HP values
        hp_matches = re.findall(r'(\d+)%?\s*hp', description_lower)
        if hp_matches:
            data['hp_amount'] = int(hp_matches[0])
        
        # Extract turn counts
        turn_matches = re.findall(r'(\d+)\s*turn', description_lower)
        if turn_matches:
            data['turn_count'] = int(turn_matches[0])
        
        # Check for special keywords
        if 'all' in description_lower and 'targets' in description_lower:
            data['target_all'] = True
        if 'random' in description_lower:
            data['random_effect'] = True
        if 'twice' in description_lower or 'double' in description_lower:
            data['double_effect'] = True
        
        return data

    def get_active_special_rules(self, character) -> List[Dict[str, Any]]:
        """Get all active special rules for a character"""
        if not hasattr(character, 'battlefield_special_rules'):
            return []
        
        # Filter out rules from expired conditions
        if not self.active_condition:
            return []
        
        return [rule for rule in character.battlefield_special_rules 
                if rule['condition_id'] == self.active_condition.condition_id]
    
    def get_condition_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current battlefield condition"""
        if not self.active_condition:
            return None
        
        time_remaining = None
        if self.condition_start_date:
            expiry_date = self.condition_start_date + timedelta(days=self.active_condition.duration_days)
            time_remaining = expiry_date - datetime.now()
        
        return {
            "name": self.active_condition.name,
            "description": self.active_condition.description,
            "type": self.active_condition.condition_type.value,
            "rarity": self.active_condition.rarity,
            "effects": [
                {
                    "description": effect.description,
                    "targets": effect.target_criteria
                }
                for effect in self.active_condition.effects
            ],
            "time_remaining_hours": time_remaining.total_seconds() / 3600 if time_remaining else None,
            "is_expired": self.is_condition_expired()
        }
    
    def get_all_conditions(self) -> List[BattlefieldCondition]:
        """Get all available battlefield conditions"""
        return list(self.conditions.values())
    
    def clear_active_condition(self):
        """Clear the current battlefield condition"""
        if self.active_condition:
            logger.info("Cleared battlefield condition: %s", self.active_condition.name)
        
        self.active_condition = None
        self.condition_start_date = None
    
    def clear_character_effects(self, character):
        """Remove all battlefield effects from a character"""
        if not self.active_condition:
            return
        
        condition_id = self.active_condition.condition_id
        
        # Remove stat modifiers
        if hasattr(character, 'stats'):
            modifiers_to_remove = []
            for modifier in character.stats.modifiers:
                if modifier.source.startswith(f"battlefield_{condition_id}"):
                    modifiers_to_remove.append(modifier)
            
            for modifier in modifiers_to_remove:
                character.stats.remove_modifier(modifier.modifier_id)
        
        # Clear special rules
        if hasattr(character, 'battlefield_special_rules'):
            character.battlefield_special_rules = [
                rule for rule in character.battlefield_special_rules 
                if rule['condition_id'] != condition_id
            ]
        
        logger.debug("Cleared battlefield effects from character %s", character.character_id)
    
    def get_condition_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of the current battlefield condition"""
        if not self.active_condition:
            return {"active": False, "message": "No active battlefield condition"}
        
        # Count effects by type
        stat_effects = []
        special_effects = []
        
        for effect in self.active_condition.effects:
            if effect.effect_type == "stat_modifier":
                stat_effects.append({
                    "stat": effect.stat_affected,
                    "modifier": f"{effect.modifier_value:+.0%}",
                    "targets": effect.target_criteria,
                    "description": effect.description
                })
            elif effect.effect_type == "special_rule":
                special_effects.append({
                    "targets": effect.target_criteria,
                    "description": effect.description
                })
        
        time_remaining = None
        if self.condition_start_date:
            expiry_date = self.condition_start_date + timedelta(days=self.active_condition.duration_days)
            time_remaining = expiry_date - datetime.now()
        
        return {
            "active": True,
            "condition_id": self.active_condition.condition_id,
            "name": self.active_condition.name,
            "description": self.active_condition.description,
            "type": self.active_condition.condition_type.value,
            "rarity": self.active_condition.rarity,
            "duration_days": self.active_condition.duration_days,
            "time_remaining_hours": time_remaining.total_seconds() / 3600 if time_remaining else None,
            "is_expired": self.is_condition_expired(),
            "stat_effects": stat_effects,
            "special_effects": special_effects,
            "total_effects": len(self.active_condition.effects)
        }

# Global battlefield conditions system instance
battlefield_conditions_system = BattlefieldConditionsSystem()
