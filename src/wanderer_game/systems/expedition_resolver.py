"""
Expedition Resolver - Core engine for processing expedition encounters

Handles the complete resolution of an expedition by:
- Processing each encounter in sequence
- Applying affinity calculations and modifiers
- Generating loot and tracking outcomes
- Applying final multipliers and generating results
"""

from typing import List, Dict, Optional
import random

from ..models import (
    Expedition, ActiveExpedition, Team, Character,
    Encounter, EncounterType, EncounterResult, EncounterOutcome,
    ExpeditionResult, LootPool, LootItem, FinalMultiplier,
    Affinity, AffinityType, EncounterModifier, ModifierType
)
from .chance_table import ChanceTable, FinalMultiplierTable


class ExpeditionResolver:
    """
    Stateless service for resolving completed expeditions
    
    Takes an ActiveExpedition and Team, simulates the journey through
    all encounters, and returns a complete ExpeditionResult.
    """
    
    def __init__(self, encounters_data: List[Dict], loot_generator):
        """
        Initialize resolver with encounter data and loot generator
        
        Args:
            encounters_data: List of encounter dictionaries from JSON
            loot_generator: LootGenerator instance for creating rewards
        """
        self.encounters = {}
        self.encounters_by_tag = {}
        self.loot_generator = loot_generator
        
        # Load encounters
        for encounter_data in encounters_data:
            encounter = Encounter.from_dict(encounter_data)
            self.encounters[encounter.encounter_id] = encounter
            
            # Index by tags for efficient lookup
            for tag in encounter.tags:
                if tag not in self.encounters_by_tag:
                    self.encounters_by_tag[tag] = []
                self.encounters_by_tag[tag].append(encounter)
    
    def resolve(self, active_expedition: ActiveExpedition, team: Team) -> ExpeditionResult:
        """
        Resolve a complete expedition
        
        Args:
            active_expedition: The expedition to resolve
            team: The team that was dispatched
            
        Returns:
            Complete expedition result with log and loot
        """
        expedition = active_expedition.expedition
        result = ExpeditionResult(
            expedition_id=expedition.expedition_id,
            expedition_name=expedition.name,
            team_character_ids=active_expedition.team_character_ids
        )
        
        # Process each encounter
        for encounter_num in range(expedition.encounter_count):
            encounter = self._select_encounter(expedition.encounter_pool_tags)
            if encounter:
                encounter_result = self._resolve_encounter(encounter, expedition, team)
                result.add_encounter_result(encounter_result)
                
                # Apply encounter effects to expedition state
                self._apply_encounter_effects(encounter_result, expedition, result.loot_pool)
        
        # Calculate final multiplier and apply to loot
        self._apply_final_multiplier(result, team)
        
        return result
    
    def _select_encounter(self, available_tags: List[str]) -> Optional[Encounter]:
        """
        Select a random encounter that matches the available tags
        
        Args:
            available_tags: List of tags to match against
            
        Returns:
            Selected encounter or None if no matches found
        """
        valid_encounters = []
        
        # Find all encounters that match any of the available tags
        for tag in available_tags:
            if tag in self.encounters_by_tag:
                valid_encounters.extend(self.encounters_by_tag[tag])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_encounters = []
        for encounter in valid_encounters:
            if encounter.encounter_id not in seen:
                unique_encounters.append(encounter)
                seen.add(encounter.encounter_id)
        
        if not unique_encounters:
            # Fallback to any encounter if no tag matches
            unique_encounters = list(self.encounters.values())
        
        return random.choice(unique_encounters) if unique_encounters else None
    
    def _resolve_encounter(self, encounter: Encounter, expedition: Expedition, team: Team) -> EncounterResult:
        """
        Resolve a single encounter based on its type
        """
        if encounter.type == EncounterType.STANDARD:
            return self._resolve_standard_encounter(encounter, expedition, team)
        elif encounter.type == EncounterType.GATED:
            return self._resolve_gated_encounter(encounter, expedition, team)
        elif encounter.type == EncounterType.BOON:
            return self._resolve_boon_encounter(encounter, expedition, team)
        elif encounter.type == EncounterType.HAZARD:
            return self._resolve_hazard_encounter(encounter, expedition, team)
        else:
            # Fallback
            return EncounterResult(
                encounter=encounter,
                outcome=EncounterOutcome.FAILURE,
                description="Unknown encounter type"
            )
    
    def _resolve_standard_encounter(self, encounter: Encounter, expedition: Expedition, team: Team) -> EncounterResult:
        """Resolve a standard skill check encounter"""
        # Safety checks for required fields
        if not encounter.check_stat or encounter.difficulty is None:
            return EncounterResult(
                encounter=encounter,
                outcome=EncounterOutcome.FAILURE,
                description="Invalid standard encounter - missing check_stat or difficulty"
            )
        
        # Calculate team skill score
        team_score = self._calculate_team_score(encounter.check_stat, expedition, team)
        
        # Apply expedition-specific difficulty modifiers
        effective_difficulty = expedition.get_effective_difficulty(encounter.difficulty)
        
        # Calculate success threshold
        success_threshold = ChanceTable.calculate_success_threshold(team_score, effective_difficulty)
        
        # Roll for outcome
        outcome = ChanceTable.roll_outcome(success_threshold)
        
        # Generate loot based on outcome
        loot_value_change = 0
        if outcome == EncounterOutcome.GREAT_SUCCESS:
            loot_value_change = encounter.loot_values.get("great", 20) if encounter.loot_values else 20
        elif outcome == EncounterOutcome.SUCCESS:
            loot_value_change = encounter.loot_values.get("common", 10) if encounter.loot_values else 10
        
        return EncounterResult(
            encounter=encounter,
            outcome=outcome,
            description=encounter.get_description_for_outcome(outcome),
            loot_value_change=loot_value_change
        )
    
    def _resolve_gated_encounter(self, encounter: Encounter, _expedition: Expedition, team: Team) -> EncounterResult:
        """Resolve a gated (conditional) encounter"""
        if not encounter.condition:
            return EncounterResult(
                encounter=encounter,
                outcome=EncounterOutcome.FAILURE,
                description="Invalid gated encounter - no condition specified"
            )
        
        # Check if team meets the condition
        team_passes = self._check_team_condition(encounter.condition, team)
        
        if team_passes:
            outcome = EncounterOutcome.SUCCESS
            loot_value_change = encounter.success_loot_value or 30
        else:
            outcome = EncounterOutcome.FAILURE
            loot_value_change = 0
        
        return EncounterResult(
            encounter=encounter,
            outcome=outcome,
            description=encounter.get_description_for_outcome(outcome),
            loot_value_change=loot_value_change,
            team_passed_condition=team_passes
        )
    
    def _resolve_boon_encounter(self, encounter: Encounter, _expedition: Expedition, _team: Team) -> EncounterResult:
        """Resolve a beneficial modifier encounter"""
        return EncounterResult(
            encounter=encounter,
            outcome=EncounterOutcome.SUCCESS,  # Boons are always positive
            description=encounter.description or f"{encounter.name} - Beneficial effect applied!",
            modifier_applied=encounter.modifier
        )
    
    def _resolve_hazard_encounter(self, encounter: Encounter, _expedition: Expedition, _team: Team) -> EncounterResult:
        """Resolve a detrimental modifier encounter"""
        return EncounterResult(
            encounter=encounter,
            outcome=EncounterOutcome.FAILURE,  # Hazards are always negative
            description=encounter.description or f"{encounter.name} - Detrimental effect applied!",
            modifier_applied=encounter.modifier
        )
    
    def _calculate_team_score(self, stat_name: str, expedition: Expedition, team: Team) -> float:
        """
        Calculate the team's total score for a stat check
        Includes affinity multipliers and expedition modifiers
        """
        # Get base stat sum (with star bonuses already applied)
        base_stat_sum = team.get_total_stat(stat_name)
        
        # Apply expedition stat modifiers
        effective_stat_sum = expedition.get_effective_stat(base_stat_sum, stat_name)
        
        # Calculate affinity multiplier
        affinity_multiplier = self._calculate_affinity_multiplier(expedition, team)
        
        return effective_stat_sum * affinity_multiplier
    
    def _calculate_affinity_multiplier(self, expedition: Expedition, team: Team) -> float:
        """
        Calculate the affinity multiplier based on team composition
        Formula: 1.0 + (favored_matches * 0.25) - (disfavored_matches * 0.25)
        Clamped between 0.1 and 3.0
        """
        favored_affinities = expedition.get_all_favored_affinities()
        disfavored_affinities = expedition.get_all_disfavored_affinities()
        
        favored_matches = team.count_affinity_matches(favored_affinities)
        disfavored_matches = team.count_affinity_matches(disfavored_affinities)
        
        multiplier = 1.0 + (favored_matches * 0.25) - (disfavored_matches * 0.25)
        
        # Clamp between 0.1 and 3.0
        return max(0.1, min(3.0, multiplier))
    
    def _check_team_condition(self, condition, team: Team) -> bool:
        """Check if the team meets a gated encounter condition"""
        for character in team.characters:
            if condition.type.value == "elemental":
                # Handle elemental condition (should be string, not list)
                if isinstance(condition.value, str):
                    if character.has_elemental_type(condition.value):
                        return True
            elif condition.type.value == "archetype":
                # Handle both single archetype and list of archetypes
                if isinstance(condition.value, list):
                    for archetype in condition.value:
                        if character.has_archetype(str(archetype)):
                            return True
                else:
                    if character.has_archetype(str(condition.value)):
                        return True
            elif condition.type.value == "series_id":
                # Handle both single series_id and list of series_ids
                if isinstance(condition.value, list):
                    for series_id in condition.value:
                        if character.has_series_id(int(series_id)):
                            return True
                else:
                    if character.has_series_id(int(condition.value)):
                        return True
            elif condition.type.value == "genre":
                # Handle genre condition (should be string, not list)
                if isinstance(condition.value, str):
                    if character.has_genre(condition.value):
                        return True
            elif condition.type.value == "team_size":
                # Check if team has exactly the required size
                if isinstance(condition.value, (int, str)):
                    return len(team.characters) == int(condition.value)
                return False
        
        return False
    
    def _apply_encounter_effects(self, encounter_result: EncounterResult, expedition: Expedition, loot_pool: LootPool):
        """Apply the effects of an encounter to the expedition state and loot pool"""
        # Handle loot changes
        if encounter_result.loot_value_change > 0:
            # Generate loot items
            success_level = "great" if encounter_result.outcome == EncounterOutcome.GREAT_SUCCESS else "common"
            loot_items = self.loot_generator.generate_loot(
                expedition.difficulty, 
                success_level
            )
            loot_pool.add_items(loot_items)
        elif encounter_result.outcome == EncounterOutcome.MISHAP:
            # Remove random item on mishap
            loot_pool.remove_random_item()
        
        # Apply modifiers (BOON/HAZARD effects)
        if encounter_result.modifier_applied:
            self._apply_modifier(encounter_result.modifier_applied, expedition)
    
    def _apply_modifier(self, modifier: EncounterModifier, expedition: Expedition):
        """Apply a modifier to the expedition state"""
        if modifier.type == ModifierType.AFFINITY_ADD:
            # Add temporary affinity
            if modifier.category and modifier.value:
                affinity_type = AffinityType(modifier.category)
                affinity = Affinity(affinity_type, str(modifier.value))
                
                if modifier.affinity == "favored":
                    expedition.add_dynamic_favored_affinity(affinity)
                elif modifier.affinity == "disfavored":
                    expedition.add_dynamic_disfavored_affinity(affinity)
        
        elif modifier.type == ModifierType.STAT_CHECK_BONUS and modifier.stat and modifier.value:
            # Handle both single stat and list of stats
            if isinstance(modifier.stat, list):
                for stat in modifier.stat:
                    if str(stat) == "all":
                        # Apply to all stats
                        for stat_name in ["hp", "atk", "mag", "vit", "spr", "intel", "spd", "lck"]:
                            expedition.add_stat_bonus(stat_name, int(modifier.value))
                    else:
                        # Convert 'int' to 'intel' for compatibility
                        stat_name = "intel" if str(stat) == "int" else str(stat)
                        expedition.add_stat_bonus(stat_name, int(modifier.value))
            else:
                if str(modifier.stat) == "all":
                    # Apply to all stats
                    for stat_name in ["hp", "atk", "mag", "vit", "spr", "intel", "spd", "lck"]:
                        expedition.add_stat_bonus(stat_name, int(modifier.value))
                else:
                    # Convert 'int' to 'intel' for compatibility
                    stat_name = "intel" if str(modifier.stat) == "int" else str(modifier.stat)
                    expedition.add_stat_bonus(stat_name, int(modifier.value))
        
        elif modifier.type == ModifierType.STAT_CHECK_PENALTY and modifier.stat and modifier.value:
            # Handle both single stat and list of stats
            if isinstance(modifier.stat, list):
                for stat in modifier.stat:
                    if str(stat) == "all":
                        # Apply to all stats
                        for stat_name in ["hp", "atk", "mag", "vit", "spr", "intel", "spd", "lck"]:
                            expedition.add_stat_bonus(stat_name, -int(modifier.value))
                    else:
                        # Convert 'int' to 'intel' for compatibility
                        stat_name = "intel" if str(stat) == "int" else str(stat)
                        expedition.add_stat_bonus(stat_name, -int(modifier.value))
            else:
                if str(modifier.stat) == "all":
                    # Apply to all stats
                    for stat_name in ["hp", "atk", "mag", "vit", "spr", "intel", "spd", "lck"]:
                        expedition.add_stat_bonus(stat_name, -int(modifier.value))
                else:
                    # Convert 'int' to 'intel' for compatibility
                    stat_name = "intel" if str(modifier.stat) == "int" else str(modifier.stat)
                    expedition.add_stat_bonus(stat_name, -int(modifier.value))
        
        elif modifier.type == ModifierType.DIFFICULTY_INCREASE and modifier.value:
            # Convert percentage to multiplier (e.g., 20 -> 1.20)
            multiplier = 1.0 + (float(modifier.value) / 100.0)
            expedition.add_difficulty_modifier(multiplier)
    
    def _apply_final_multiplier(self, result: ExpeditionResult, team: Team):
        """Calculate and apply the final luck-based multiplier"""
        # Calculate final luck score
        team_luck = team.get_total_luck()
        final_luck_score = FinalMultiplierTable.calculate_luck_score(
            team_luck, result.great_successes, result.mishaps
        )
        
        # Roll for multiplier
        multiplier_name, multiplier_value = FinalMultiplierTable.roll_final_multiplier(final_luck_score)
        
        # Apply to loot pool
        result.loot_pool = result.loot_pool.apply_multiplier(multiplier_value)
        
        # Store results
        result.final_luck_score = final_luck_score
        result.final_multiplier = FinalMultiplier(multiplier_name)