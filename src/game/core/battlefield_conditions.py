"""
Battlefield Conditions System

Implements weekly environmental effects that alter battle mechanics
for all participants, as described in the design document.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
import json
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
        import re
        
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
