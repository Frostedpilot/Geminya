"""
Battlefield Conditions System

Implements weekly environmental effects that alter battle mechanics
for all participants, as described in the design document.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
import random
from datetime import datetime, timedelta

from ..components.stats_component import StatModifier, StatType, ModifierType

logger = logging.getLogger(__name__)

class ConditionType(Enum):
    """Types of battlefield conditions"""
    ENVIRONMENTAL = "environmental"
    MAGICAL = "magical"
    WEATHER = "weather"
    COSMIC = "cosmic"
    TEMPORAL = "temporal"

@dataclass
class BattlefieldEffect:
    """Individual effect within a battlefield condition"""
    effect_type: str            # "stat_modifier", "damage_modifier", "special_rule"
    target_criteria: str        # "all", "fire_elemental", "water_elemental", etc.
    stat_affected: Optional[str] = None
    modifier_value: float = 0.0
    modifier_type: str = "percentage"  # "percentage", "flat"
    description: str = ""

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

class BattlefieldConditionsSystem:
    """Manages battlefield conditions and their effects"""
    
    def __init__(self):
        self.conditions: Dict[str, BattlefieldCondition] = {}
        self.active_condition: Optional[BattlefieldCondition] = None
        self.condition_start_date: Optional[datetime] = None
        self._initialize_battlefield_conditions()
        logger.info("Initialized battlefield conditions system with %d conditions", len(self.conditions))
    
    def _initialize_battlefield_conditions(self):
        """Initialize all battlefield conditions from the design document"""
        
        conditions = [
            # Weather Conditions
            BattlefieldCondition(
                condition_id="scorching_sun",
                name="Scorching Sun",
                condition_type=ConditionType.WEATHER,
                description="The blazing sun empowers fire users but weakens water users.",
                effects=[
                    BattlefieldEffect(
                        effect_type="stat_modifier",
                        target_criteria="fire_elemental",
                        stat_affected="atk",
                        modifier_value=0.20,
                        description="Fire-elemental characters gain +20% ATK"
                    ),
                    BattlefieldEffect(
                        effect_type="stat_modifier",
                        target_criteria="fire_elemental",
                        stat_affected="mag",
                        modifier_value=0.20,
                        description="Fire-elemental characters gain +20% MAG"
                    ),
                    BattlefieldEffect(
                        effect_type="stat_modifier",
                        target_criteria="water_elemental",
                        stat_affected="vit",
                        modifier_value=-0.10,
                        description="Water-elemental characters suffer -10% VIT"
                    ),
                    BattlefieldEffect(
                        effect_type="stat_modifier",
                        target_criteria="water_elemental",
                        stat_affected="spr",
                        modifier_value=-0.10,
                        description="Water-elemental characters suffer -10% SPR"
                    )
                ]
            ),
            
            BattlefieldCondition(
                condition_id="mystic_fog",
                name="Mystic Fog",
                condition_type=ConditionType.MAGICAL,
                description="Mystical fog reduces accuracy and critical hit chances.",
                effects=[
                    BattlefieldEffect(
                        effect_type="stat_modifier",
                        target_criteria="all",
                        stat_affected="lck",
                        modifier_value=-0.50,
                        description="All characters' LCK stat is reduced by 50%"
                    ),
                    BattlefieldEffect(
                        effect_type="special_rule",
                        target_criteria="all",
                        description="Critical hits are less likely for all characters"
                    )
                ]
            ),
            
            BattlefieldCondition(
                condition_id="gravity_well",
                name="Gravity Well",
                condition_type=ConditionType.COSMIC,
                description="Intense gravitational forces slow down all movement.",
                effects=[
                    BattlefieldEffect(
                        effect_type="stat_modifier",
                        target_criteria="all",
                        stat_affected="spd",
                        modifier_value=-0.30,
                        description="All characters' SPD is reduced by 30%"
                    )
                ]
            ),
            
            BattlefieldCondition(
                condition_id="magic_overflow",
                name="Magic Overflow",
                condition_type=ConditionType.MAGICAL,
                description="Magical energy saturates the battlefield.",
                effects=[
                    BattlefieldEffect(
                        effect_type="stat_modifier",
                        target_criteria="all",
                        stat_affected="mag",
                        modifier_value=0.25,
                        description="All characters gain +25% MAG"
                    )
                ]
            ),
            
            BattlefieldCondition(
                condition_id="warriors_proving_ground",
                name="Warrior's Proving Ground",
                condition_type=ConditionType.ENVIRONMENTAL,
                description="The battlefield favors physical combat.",
                effects=[
                    BattlefieldEffect(
                        effect_type="stat_modifier",
                        target_criteria="all",
                        stat_affected="atk",
                        modifier_value=0.25,
                        description="All characters gain +25% ATK"
                    )
                ]
            ),
            
            BattlefieldCondition(
                condition_id="volatile_field",
                name="Volatile Field",
                condition_type=ConditionType.MAGICAL,
                description="Unstable energies make critical hits more devastating.",
                effects=[
                    BattlefieldEffect(
                        effect_type="special_rule",
                        target_criteria="all",
                        description="All critical hits deal 2.0x damage instead of 1.5x"
                    )
                ]
            ),
            
            # Advanced Conditions
            BattlefieldCondition(
                condition_id="temporal_storm",
                name="Temporal Storm",
                condition_type=ConditionType.TEMPORAL,
                description="Time distortions affect turn order randomly.",
                effects=[
                    BattlefieldEffect(
                        effect_type="special_rule",
                        target_criteria="all",
                        description="Action gauge accumulation varies randomly by ±25%"
                    )
                ],
                rarity="rare"
            ),
            
            BattlefieldCondition(
                condition_id="elemental_harmony",
                name="Elemental Harmony",
                condition_type=ConditionType.MAGICAL,
                description="All elements are in perfect balance.",
                effects=[
                    BattlefieldEffect(
                        effect_type="stat_modifier",
                        target_criteria="elemental",
                        stat_affected="all_stats",
                        modifier_value=0.15,
                        description="All elemental characters gain +15% to all stats"
                    )
                ],
                rarity="rare"
            ),
            
            BattlefieldCondition(
                condition_id="divine_intervention",
                name="Divine Intervention",
                condition_type=ConditionType.COSMIC,
                description="Divine forces intervene in battle.",
                effects=[
                    BattlefieldEffect(
                        effect_type="special_rule",
                        target_criteria="all",
                        description="No character can be reduced below 1 HP"
                    ),
                    BattlefieldEffect(
                        effect_type="stat_modifier",
                        target_criteria="all",
                        stat_affected="int",
                        modifier_value=0.30,
                        description="All characters gain +30% INT"
                    )
                ],
                rarity="legendary"
            ),
            
            BattlefieldCondition(
                condition_id="chaos_realm",
                name="Chaos Realm",
                condition_type=ConditionType.COSMIC,
                description="Reality becomes unstable and unpredictable.",
                effects=[
                    BattlefieldEffect(
                        effect_type="special_rule",
                        target_criteria="all",
                        description="All stat modifiers are randomized each turn"
                    ),
                    BattlefieldEffect(
                        effect_type="special_rule",
                        target_criteria="all",
                        description="Skills have a 10% chance to hit random targets"
                    )
                ],
                rarity="legendary"
            )
        ]
        
        for condition in conditions:
            self.conditions[condition.condition_id] = condition
    
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
            return getattr(character, 'element', None) == 'fire'
        elif criteria == "water_elemental":
            return getattr(character, 'element', None) == 'water'
        elif criteria == "elemental":
            return hasattr(character, 'element') and character.element is not None
        else:
            # Add more criteria as needed
            return False
    
    def _apply_stat_modifier_effect(self, character, effect: BattlefieldEffect):
        """Apply stat modifier from battlefield condition"""
        if not hasattr(character, 'stats') or not effect.stat_affected or not self.active_condition:
            return
        
        condition_id = self.active_condition.condition_id
        
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
        
        logger.debug("Applied battlefield stat modifier %s to character %s", 
                    effect.stat_affected, character.character_id)
    
    def _apply_special_rule_effect(self, character, effect: BattlefieldEffect):
        """Apply special rule from battlefield condition"""
        # This would integrate with the combat system for special rules
        logger.debug("Applied battlefield special rule to character %s: %s", 
                    character.character_id, effect.description)
        # In a full implementation, we'd register event handlers for special rules
    
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

# Global battlefield conditions system instance
battlefield_conditions_system = BattlefieldConditionsSystem()
