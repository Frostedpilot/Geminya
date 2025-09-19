"""
Encounter models for the Wanderer Game

Based on the encounters.json structure.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum


class EncounterType(Enum):
    """Types of encounters that can occur during expeditions"""
    STANDARD = "STANDARD"  # Skill check encounter
    GATED = "GATED"        # Conditional check encounter
    BOON = "BOON"          # Beneficial modifier encounter
    HAZARD = "HAZARD"      # Detrimental modifier encounter


class EncounterOutcome(Enum):
    """Possible outcomes from standard encounters"""
    GREAT_SUCCESS = "great_success"
    SUCCESS = "success"
    FAILURE = "failure"
    MISHAP = "mishap"


class ConditionType(Enum):
    """Types of conditions for gated encounters"""
    ELEMENTAL = "elemental"
    ARCHETYPE = "archetype"
    SERIES_ID = "series_id"
    GENRE = "genre"
    TEAM_SIZE = "team_size"


class ModifierType(Enum):
    """Types of modifiers for boon/hazard encounters"""
    AFFINITY_ADD = "affinity_add"           # Add favored/disfavored affinity
    STAT_CHECK_BONUS = "stat_check_bonus"   # Bonus to specific stat checks
    STAT_CHECK_PENALTY = "stat_check_penalty"  # Penalty to specific stat checks
    DIFFICULTY_INCREASE = "difficulty_increase_percent"  # Difficulty modifier
    PREVENT_MISHAP = "prevent_next_mishap"  # Prevents next mishap
    FINAL_ROLL_PENALTY = "final_roll_penalty"  # Penalty to final outcome rolls
    
    # Loot modifiers
    LOOT_POOL_PENALTY = "loot_pool_penalty"  # Reduce loot quality/quantity
    LOOT_POOL_BONUS = "loot_pool_bonus"      # Improve loot quality/quantity
    LOOT_QUALITY_HALVED = "loot_quality_halved"  # Halve loot quality
    PREVENT_MISHAP_LOOT_LOSS = "prevent_mishap_loot_loss"  # Prevent loot loss on mishap
    
    # Encounter tag modifiers
    REMOVE_ENCOUNTER_TAG = "remove_encounter_tag"  # Remove specific tag from encounters
    ENCOUNTER_TAG_ADD = "encounter_tag_add"        # Add tag to encounters
    ENCOUNTER_TAG_IGNORE = "encounter_tag_ignore"  # Ignore specific tagged encounters
    ENCOUNTER_TAG_SWAP = "encounter_tag_swap"      # Swap one tag for another
    
    # Final roll modifiers
    FINAL_ROLL_BONUS = "final_roll_bonus"    # Bonus to final outcome rolls
    
    # Skill and success modifiers
    SKILL_SCORE_MULTIPLIER = "skill_score_multiplier"  # Multiply skill scores
    SUCCESS_CHANCE_INCREASE = "success_chance_increase"  # Increase success chance
    SUCCESS_CHANCE_INCREASE_TAG = "success_chance_increase_tag"  # Increase success for tagged encounters
    
    # Encounter count modifiers
    ENCOUNTER_COUNT_ADD = "encounter_count_add"          # Add encounters
    ENCOUNTER_COUNT_SUBTRACT = "encounter_count_subtract"  # Remove encounters
    ENCOUNTER_COUNT_HALVE = "encounter_count_halve"      # Halve encounter count
    
    # Affinity multiplier modifiers
    AFFINITY_MULTIPLIER_HALVE = "affinity_multiplier_halve"  # Halve affinity effects
    AFFINITY_MULTIPLIER_RESET = "affinity_multiplier_reset"  # Reset affinity multipliers
    AFFINITY_MULTIPLIER_ADD = "affinity_multiplier_add"      # Add to affinity multiplier
    
    # Mishap modifiers
    MISHAP_CHANCE_HALVE = "mishap_chance_halve"  # Halve mishap chance
    
    # Difficulty modifiers
    DIFFICULTY_INCREASE_ABSOLUTE = "difficulty_increase_absolute"  # Add flat difficulty
    
    # Guaranteed outcome modifiers
    GUARANTEED_SUCCESS_NEXT_ENCOUNTER = "guaranteed_success_next_encounter"  # Force next success
    GUARANTEED_SUCCESS_TAG = "guaranteed_success_tag"  # Force success on tagged encounters
    GUARANTEED_GREAT_SUCCESS_NEXT_ENCOUNTER = "guaranteed_great_success_next_encounter"  # Force great success
    
    # Special effect modifiers
    RANDOMIZE_CHECK_STATS = "randomize_check_stats"  # Randomize which stats are checked
    PREVENT_NEXT_MISHAP = "prevent_next_mishap"      # Prevent next mishap only
    PREVENT_ALL_MISHAPS = "prevent_all_mishaps"      # Prevent all mishaps
    SKIP_NEXT_ENCOUNTER = "skip_next_encounter"      # Skip next encounter entirely


@dataclass
class EncounterCondition:
    """Condition for gated encounters"""
    type: ConditionType
    value: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'EncounterCondition':
        """Create condition from dictionary"""
        if data is None:
            return None
        return cls(
            type=ConditionType(data['type']),
            value=data['value']
        )


@dataclass
class EncounterModifier:
    """Modifier for boon/hazard encounters"""
    type: ModifierType
    affinity: Optional[str] = None      # For affinity_add: "favored" or "disfavored"
    category: Optional[str] = None      # For affinity_add: "elemental", "archetype", etc.
    value: Optional[Any] = None         # The actual value (stat name, bonus amount, etc.)
    stat: Optional[str] = None          # For stat modifiers
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncounterModifier':
        """Create modifier from dictionary"""
        if data is None:
            return None
        return cls(
            type=ModifierType(data['type']),
            affinity=data.get('affinity'),
            category=data.get('category'),
            value=data.get('value'),
            stat=data.get('stat')
        )


@dataclass
class Encounter:
    """
    Base encounter model from encounters.json
    """
    encounter_id: str
    name: str
    type: EncounterType
    tags: List[str]
    description_success: Optional[str] = None
    description_failure: Optional[str] = None
    description: Optional[str] = None  # For BOON/HAZARD types
    
    # For STANDARD encounters
    check_stat: Optional[str] = None
    difficulty: Optional[int] = None
    loot_values: Optional[Dict[str, int]] = None
    
    # For GATED encounters
    condition: Optional[EncounterCondition] = None
    success_loot_value: Optional[int] = None
    
    # For BOON/HAZARD encounters
    modifier: Optional[EncounterModifier] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Encounter':
        """Create Encounter from dictionary (JSON data)"""
        encounter_type = EncounterType(data['type'])
        
        # Parse condition for GATED encounters
        condition = None
        if 'condition' in data and data['condition'] is not None:
            condition = EncounterCondition.from_dict(data['condition'])
        
        # Parse modifier for BOON/HAZARD encounters
        modifier = None
        if 'modifier' in data and data['modifier'] is not None:
            modifier = EncounterModifier.from_dict(data['modifier'])
        
        return cls(
            encounter_id=data['encounter_id'],
            name=data['name'],
            type=encounter_type,
            tags=data['tags'],
            description_success=data.get('description_success'),
            description_failure=data.get('description_failure'),
            description=data.get('description'),
            check_stat=data.get('check_stat'),
            difficulty=data.get('difficulty'),
            loot_values=data.get('loot_values'),
            condition=condition,
            success_loot_value=data.get('success_loot_value'),
            modifier=modifier
        )
    
    def matches_tags(self, available_tags: List[str]) -> bool:
        """Check if this encounter matches any of the available tags"""
        return any(tag in available_tags for tag in self.tags)
    
    def get_description_for_outcome(self, outcome: EncounterOutcome) -> str:
        """Get appropriate description based on encounter outcome"""
        if self.type in [EncounterType.BOON, EncounterType.HAZARD]:
            return self.description or f"{self.name} occurred!"
        
        if outcome in [EncounterOutcome.GREAT_SUCCESS, EncounterOutcome.SUCCESS]:
            return self.description_success or f"{self.name} - Success!"
        else:
            return self.description_failure or f"{self.name} - Failure!"



from typing import List
from .loot import LootItem

class EncounterResult:
    """Result of processing an encounter"""
    def __init__(self, encounter, outcome, description, loot_value_change=0, team_passed_condition=False, modifier_applied=None, loot_items=None):
        self.encounter = encounter
        self.outcome = outcome
        self.description = description or (encounter.get_description_for_outcome(outcome) if encounter else "")
        self.loot_value_change = loot_value_change
        self.team_passed_condition = team_passed_condition
        self.modifier_applied = modifier_applied
        self.loot_items = loot_items if loot_items is not None else []