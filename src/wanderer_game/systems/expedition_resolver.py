"""
Expedition Resolver - Core engine for processing expedition encounters

Handles the complete resolution of an expedition by:
- Processing each encounter in sequence
- Applying affinity calculations and modifiers
- Generating loot and tracking outcomes
- Applying final multipliers and generating results
"""

from typing import List, Dict, Optional
import math
import random

from ..models import (
    Expedition, ActiveExpedition, Team,
    Encounter, EncounterType, EncounterResult, EncounterOutcome,
    ExpeditionResult, LootPool, FinalMultiplier,
    Affinity, AffinityType, EncounterModifier, ModifierType
)
from .chance_table import ChanceTable, FinalMultiplierTable


class ExpeditionResolver:
    def _select_encounters_by_type_distribution(self, available_tags, expedition_difficulty, total_count=10, expedition=None):
        """
        Select encounters by fixed type distribution (7 standard, 1 gated, 1 boon, 1 hazard),
        biasing each pick toward encounters whose difficulty matches the expedition's using a normal distribution.
        """
        import math
        def normal_weight(enc_difficulty, exp_difficulty, sigma=100):
            # Gaussian weight centered at exp_difficulty
            return math.exp(-((enc_difficulty - exp_difficulty) ** 2) / (2 * sigma ** 2))

        # Gather all valid encounters for the expedition's tags
        valid_encounters = []
        for tag in available_tags:
            if tag in self.encounters_by_tag:
                valid_encounters.extend(self.encounters_by_tag[tag])
        # Remove duplicates
        seen = set()
        unique_encounters = []
        for encounter in valid_encounters:
            if encounter.encounter_id not in seen:
                unique_encounters.append(encounter)
                seen.add(encounter.encounter_id)
        if not unique_encounters:
            unique_encounters = list(self.encounters.values())
        # Group by type
        type_map = {EncounterType.STANDARD: [], EncounterType.GATED: [], EncounterType.BOON: [], EncounterType.HAZARD: []}
    # Removed debug print
        for encounter in unique_encounters:
            if encounter.type in type_map:
                # Filter STANDARD encounters by dominant_stats if present
                if encounter.type == EncounterType.STANDARD and expedition is not None and getattr(expedition, 'dominant_stats', None):
                    if encounter.check_stat and encounter.check_stat in expedition.dominant_stats:
                        type_map[encounter.type].append(encounter)
                else:
                    type_map[encounter.type].append(encounter)

        # For each type, select encounters using normal distribution weighting
        def weighted_sample(encounters, n, exp_difficulty):
            # Select n unique encounters, weighted by normal distribution
            selected = []
            pool = list(encounters)
            for _ in range(min(n, len(pool))):
                weights = [normal_weight(getattr(e, 'difficulty', exp_difficulty) or exp_difficulty, exp_difficulty) for e in pool]
                total = sum(weights)
                if total == 0:
                    idx = random.randrange(len(pool))
                else:
                    # Normalize weights
                    norm_weights = [w / total for w in weights]
                    idx = random.choices(range(len(pool)), weights=norm_weights, k=1)[0]
                selected.append(pool.pop(idx))
            return selected

        # Weighted random type selection for each slot
        type_weights = [15, 1, 1, 1]
        type_list = [EncounterType.STANDARD, EncounterType.GATED, EncounterType.BOON, EncounterType.HAZARD]
        result = []
        type_map_local = {k: list(v) for k, v in type_map.items()}  # Copy so we can pop
        for _ in range(total_count):
            # Only consider types with remaining encounters
            available_types = [t for t in type_list if type_map_local[t]]
            if not available_types:
                break
            weights = [type_weights[type_list.index(t)] for t in available_types]
            chosen_type = random.choices(available_types, weights=weights, k=1)[0]
            # Pick an encounter of this type, weighted by normal distribution
            encounter = None
            if type_map_local[chosen_type]:
                picks = weighted_sample(type_map_local[chosen_type], 1, expedition_difficulty)
                if picks:
                    encounter = picks[0]
                    type_map_local[chosen_type].remove(encounter)
            if encounter:
                result.append(encounter)
        # If not enough, fill with any left (random)
        if len(result) < total_count:
            leftovers = [e for group in type_map_local.values() for e in group]
            random.shuffle(leftovers)
            result.extend(leftovers[:total_count - len(result)])
        return result[:total_count]
    # Stateless service for resolving completed expeditions
    # Takes an ActiveExpedition and Team, simulates the journey through
    # all encounters, and returns a complete ExpeditionResult.
    
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
    
    def resolve(self, active_expedition: ActiveExpedition, team: Team, equipment=None) -> ExpeditionResult:
        """
        Resolve a complete expedition
        
        Args:
            active_expedition: The expedition to resolve
            team: The team that was dispatched
            equipment: Equipment object (with main_effect and sub_slots)
        Returns:
            Complete expedition result with log and loot
        """
        expedition = active_expedition.expedition
        result = ExpeditionResult(
            expedition_id=expedition.expedition_id,
            expedition_name=expedition.name,
            team_character_ids=active_expedition.team_character_ids
        )

        # === EQUIPMENT EFFECTS: Apply all EncounterModifier effects from equipment (main and sub slots) ===
        if equipment:
            # Apply main_effect if present
            if getattr(equipment, 'main_effect', None):
                self._apply_modifier(equipment.main_effect, expedition)
            # Apply all sub slot effects if present
            sub_slots = getattr(equipment, 'sub_slots', None)
            if sub_slots:
                # Ensure sub_slots is iterable (list/tuple), handle single object gracefully
                if not isinstance(sub_slots, (list, tuple)):
                    sub_slots = [sub_slots]
                for sub in sub_slots:
                    if getattr(sub, 'effect', None):
                        self._apply_modifier(sub.effect, expedition)

        # Use fixed distribution for encounters: 6-2-1-1 (standard, gated, boon, hazard)
        encounter_count = getattr(expedition, 'encounter_count', 10)
        encounters = self._select_encounters_by_type_distribution(
            expedition.encounter_pool_tags, expedition.difficulty, encounter_count, expedition=expedition
        )
        for encounter in encounters:
            encounter_result = self._resolve_encounter(encounter, expedition, team)
            result.add_encounter_result(encounter_result)
            self._apply_encounter_effects(encounter_result, expedition, result.loot_pool, team)

        # Calculate final multiplier and apply to loot, always using expedition.difficulty
        self._apply_final_multiplier(result, team, expedition.difficulty)
        return result
    
    def _select_encounter(self, available_tags: List[str], expedition_difficulty: int = 0) -> Optional[Encounter]:
        """
        Select an encounter that matches the available tags, weighted by difficulty
        
        Args:
            available_tags: List of tags to match against
            expedition_difficulty: Expedition difficulty to bias encounter selection
            
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
        
        if not unique_encounters:
            return None
        
        # If no expedition difficulty provided, use random selection
        if expedition_difficulty <= 0:
            return random.choice(unique_encounters)
        
        # Weight encounters based on how close their difficulty is to expedition difficulty
        weighted_encounters = []
        for encounter in unique_encounters:
            encounter_difficulty = encounter.difficulty or 100  # Default if no difficulty
            
            # Calculate weight based on difficulty proximity using exponential decay
            # Closer difficulties get higher weights
            distance = abs(encounter_difficulty - expedition_difficulty)
            
            # Use similar formula as loot generation but more forgiving
            # At distance 0: weight = 1.0, at distance 100: weight ≈ 0.37, at distance 200: weight ≈ 0.14
            k = 0.01  # Decay factor (less aggressive than loot system)
            weight = math.exp(-k * distance)
            
            # Minimum weight to ensure all encounters have some chance
            weight = max(weight, 0.1)
            
            weighted_encounters.append((encounter, weight))
        
        # Select encounter using weighted random selection
        total_weight = sum(weight for _, weight in weighted_encounters)
        roll = random.uniform(0, total_weight)
        current_weight = 0
        
        for encounter, weight in weighted_encounters:
            current_weight += weight
            if roll <= current_weight:
                return encounter
        
        # Fallback (shouldn't happen)
        return weighted_encounters[0][0] if weighted_encounters else None
    
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
        
        # Check for encounter skipping
        if expedition.consume_skip_encounter():
            return EncounterResult(
                encounter=encounter,
                outcome=EncounterOutcome.SUCCESS,
                description=f"Encounter skipped due to modifier effect. {encounter.description or encounter.name}",
                loot_value_change=encounter.loot_values.get("common", 10) if encounter.loot_values else 10
            )
        
        # Check for guaranteed success
        if expedition.consume_guaranteed_success():
            loot_value_change = encounter.loot_values.get("great", 20) if encounter.loot_values else 20
            return EncounterResult(
                encounter=encounter,
                outcome=EncounterOutcome.GREAT_SUCCESS,
                description=f"Guaranteed success! {encounter.description or encounter.name}",
                loot_value_change=loot_value_change
            )
        
        # Calculate team skill score
        team_score = self._calculate_team_score(encounter.check_stat, expedition, team)
        
        # Apply expedition-specific difficulty modifiers
        effective_difficulty = expedition.get_effective_difficulty(encounter.difficulty)
        
        # Calculate success threshold with expedition bonuses
        success_threshold = ChanceTable.calculate_success_threshold(team_score, effective_difficulty)
        
        # Apply success rate bonuses
        success_threshold += expedition.success_rate_bonus
        success_threshold = max(0.0, success_threshold)
        
        # Roll for outcome
        outcome = ChanceTable.roll_outcome(success_threshold)
        
        # Apply mishap prevention
        if outcome == EncounterOutcome.MISHAP and expedition.prevent_mishaps:
            outcome = EncounterOutcome.FAILURE  # Downgrade mishap to failure
        
        # Apply failure prevention
        if outcome == EncounterOutcome.FAILURE and expedition.prevent_failure:
            outcome = EncounterOutcome.SUCCESS  # Upgrade failure to success
        
        # Generate loot based on outcome with modifiers
        loot_value_change = 0
        if outcome == EncounterOutcome.GREAT_SUCCESS:
            base_loot = encounter.loot_values.get("great", 20) if encounter.loot_values else 20
        elif outcome == EncounterOutcome.SUCCESS:
            base_loot = encounter.loot_values.get("common", 10) if encounter.loot_values else 10
        else:
            base_loot = 0
        
        # Apply loot multipliers
        if base_loot > 0:
            loot_value_change = int(base_loot * expedition.get_effective_loot_multiplier())
            
            # Apply encounter-specific bonuses
            encounter_type = encounter.type.value if encounter.type else "standard"
            if encounter_type in expedition.encounter_specific_loot_bonus:
                bonus_multiplier = 1.0 + expedition.encounter_specific_loot_bonus[encounter_type]
                loot_value_change = int(loot_value_change * bonus_multiplier)
        
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
        
        #buff loot value
        loot_value_change=loot_value_change*4
        
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
        Includes affinity multipliers, expedition modifiers, and series multiplier
        Applies final_stat_check_bonuses after all multipliers.
        """
        # Get base stat sum (with star bonuses already applied)
        base_stat_sum = team.get_total_stat(stat_name)

        # Apply expedition stat modifiers
        effective_stat_sum = expedition.get_effective_stat(base_stat_sum, stat_name)

        # Calculate affinity multiplier
        affinity_multiplier = self._calculate_affinity_multiplier(expedition, team)

        # Calculate series multiplier: 1.2x if all 3 team members are from the same series
        series_multiplier = 1.0
        if len(team.characters) == 3:
            series_ids = [getattr(c, 'series_id', None) for c in team.characters]
            if all(sid is not None for sid in series_ids) and len(set(series_ids)) == 1:
                series_multiplier = 1.2

        # Calculate base score with all multipliers
        score = effective_stat_sum * affinity_multiplier * series_multiplier

        # Apply final stat check bonus (after all multipliers)
        bonus = 0
        if hasattr(expedition, 'final_stat_check_bonuses') and expedition.final_stat_check_bonuses:
            # Try stat-specific bonus first
            bonus = expedition.final_stat_check_bonuses.get(stat_name, 0)
        return score + bonus
    
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
        
        #+ Make buff and nerf multiplicative. Make nerf very stronger, to 40%. Make buff weaker, to 20%
        
        multiplier = 1.2**(favored_matches) * (0.6**(disfavored_matches))
        return max(0.1, min(3.6, multiplier))
    
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
    
    def _apply_encounter_effects(self, encounter_result: EncounterResult, expedition: Expedition, loot_pool: LootPool, team: Team):
        """Apply the effects of an encounter to the expedition state and loot pool"""
        # Handle loot changes with new value-based system
        if encounter_result.loot_value_change > 0:
            # Apply expedition loot multipliers to get effective loot value
            effective_loot_value = int(encounter_result.loot_value_change * expedition.get_effective_loot_multiplier())
            # Calculate total loot value: encounter difficulty + effective loot value
            encounter_difficulty = encounter_result.encounter.difficulty or expedition.difficulty
            team_score = self._calculate_team_score(encounter_result.encounter.check_stat, expedition, team) if encounter_result.encounter.check_stat else 0
            
            total_loot_value = (min(int(encounter_difficulty * 1.5), int(team_score)) + encounter_difficulty)/2 + max(0, int(team_score - encounter_difficulty * 1.5)) * 0.35 + effective_loot_value
            # Determine number of rolls based on outcome
            num_rolls = 2 if encounter_result.outcome == EncounterOutcome.GREAT_SUCCESS else 1
            # Generate loot items using the new value-based system
            loot_items = self.loot_generator.generate_loot(total_loot_value, num_rolls)
            loot_pool.add_items(loot_items)
            # Store generated loot in the encounter result
            encounter_result.loot_items = loot_items
        elif encounter_result.outcome == EncounterOutcome.MISHAP:
            # Only remove item if mishaps aren't prevented
            removed_item = None
            if not expedition.prevent_mishaps:
                removed_item = loot_pool.remove_random_item()
            # Track the removed item in the encounter result for UI
            encounter_result.mishap_removed_item = removed_item
        
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
                        for stat_name in ["hp", "atk", "mag", "vit", "spr", "intel", "spd", "lck"]:
                            expedition.add_stat_bonus(stat_name, int(modifier.value))
                    else:
                        stat_name = "intel" if str(stat) == "int" else str(stat)
                        expedition.add_stat_bonus(stat_name, int(modifier.value))
            else:
                if str(modifier.stat) == "all":
                    for stat_name in ["hp", "atk", "mag", "vit", "spr", "intel", "spd", "lck"]:
                        expedition.add_stat_bonus(stat_name, int(modifier.value))
                else:
                    stat_name = "intel" if str(modifier.stat) == "int" else str(modifier.stat)
                    expedition.add_stat_bonus(stat_name, int(modifier.value))

        elif modifier.type == ModifierType.FINAL_STAT_CHECK_BONUS and modifier.stat and modifier.value:
            # Store final stat check bonuses for use after all multipliers
            if not hasattr(expedition, 'final_stat_check_bonuses') or expedition.final_stat_check_bonuses is None:
                expedition.final_stat_check_bonuses = {}
            if isinstance(modifier.stat, list):
                for stat in modifier.stat:
                    if str(stat) == "all":
                        for stat_name in ["hp", "atk", "mag", "vit", "spr", "intel", "spd", "lck"]:
                            expedition.final_stat_check_bonuses[stat_name] = expedition.final_stat_check_bonuses.get(stat_name, 0) + int(modifier.value)
                    else:
                        stat_name = "intel" if str(stat) == "int" else str(stat)
                        expedition.final_stat_check_bonuses[stat_name] = expedition.final_stat_check_bonuses.get(stat_name, 0) + int(modifier.value)
            else:
                if str(modifier.stat) == "all":
                    for stat_name in ["hp", "atk", "mag", "vit", "spr", "intel", "spd", "lck"]:
                        expedition.final_stat_check_bonuses[stat_name] = expedition.final_stat_check_bonuses.get(stat_name, 0) + int(modifier.value)
                else:
                    stat_name = "intel" if str(modifier.stat) == "int" else str(modifier.stat)
                    expedition.final_stat_check_bonuses[stat_name] = expedition.final_stat_check_bonuses.get(stat_name, 0) + int(modifier.value)
        
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
            expedition.add_difficulty_modifier(multiplier, source=f"DIFFICULTY_INCREASE (modifier.value={modifier.value})")
        
        # ===== MISHAP AND OUTCOME MODIFIERS =====
        elif modifier.type == ModifierType.PREVENT_MISHAP:
            # Prevent next mishap
            expedition.prevent_mishaps = True
        
        elif modifier.type == ModifierType.FINAL_ROLL_PENALTY and modifier.value:
            # Penalty to final outcome rolls (treat as success rate penalty)
            expedition.add_success_rate_bonus(-float(modifier.value) / 100.0)
        
        elif modifier.type == ModifierType.FINAL_ROLL_BONUS and modifier.value:
            # Bonus to final outcome rolls (treat as success rate bonus)
            expedition.add_success_rate_bonus(float(modifier.value) / 100.0)
        
        # ===== LOOT MODIFIERS =====
        elif modifier.type == ModifierType.LOOT_POOL_PENALTY and modifier.value:
            # Reduce loot quality/quantity
            multiplier = 1.0 - (float(modifier.value) / 100.0)
            expedition.add_loot_multiplier(max(0.1, multiplier))
        
        elif modifier.type == ModifierType.LOOT_POOL_BONUS and modifier.value:
            # Improve loot quality/quantity
            multiplier = 1.0 + (float(modifier.value) / 100.0)
            expedition.add_loot_multiplier(multiplier)
        
        elif modifier.type == ModifierType.LOOT_QUALITY_HALVED:
            # Halve loot quality
            expedition.add_loot_multiplier(0.5)
        
        elif modifier.type == ModifierType.PREVENT_MISHAP_LOOT_LOSS:
            # Prevent loot loss on mishap (set prevent mishaps flag)
            expedition.prevent_mishaps = True
        
        # ===== ENCOUNTER TAG MODIFIERS =====
        elif modifier.type == ModifierType.REMOVE_ENCOUNTER_TAG and modifier.value:
            # Remove specific tag from encounters (complex - would need tag modification)
            # For now, treat as minor difficulty reduction
            expedition.add_difficulty_modifier(0.95, source=f"REMOVE_ENCOUNTER_TAG (modifier.value={modifier.value})")
        
        elif modifier.type == ModifierType.ENCOUNTER_TAG_ADD and modifier.value:
            # Add tag to encounters (complex - would need tag modification)
            # For now, treat as minor loot bonus
            expedition.add_loot_multiplier(1.05)
        
        elif modifier.type == ModifierType.ENCOUNTER_TAG_IGNORE and modifier.value:
            # Ignore specific tagged encounters (complex - would need encounter filtering)
            # For now, treat as success rate bonus
            expedition.add_success_rate_bonus(0.1)
        
        elif modifier.type == ModifierType.ENCOUNTER_TAG_SWAP and modifier.value:
            # Swap one tag for another (complex - would need tag swapping)
            # For now, treat as neutral effect with small loot bonus
            expedition.add_loot_multiplier(1.02)
        
        # ===== SKILL AND SUCCESS MODIFIERS =====
        elif modifier.type == ModifierType.SKILL_SCORE_MULTIPLIER and modifier.value:
            # Multiply skill scores (treat as stat bonus)
            multiplier_bonus = int((float(modifier.value) - 1.0) * 10)  # Convert multiplier to flat bonus
            for stat_name in ["hp", "atk", "mag", "vit", "spr", "intel", "spd", "lck"]:
                expedition.add_stat_bonus(stat_name, multiplier_bonus)
        
        elif modifier.type == ModifierType.SUCCESS_CHANCE_INCREASE and modifier.value:
            # Direct success rate bonus
            expedition.add_success_rate_bonus(float(modifier.value) / 100.0)
        
        elif modifier.type == ModifierType.SUCCESS_CHANCE_INCREASE_TAG and modifier.value:
            # Success chance increase for tagged encounters (treat as general success bonus)
            expedition.add_success_rate_bonus(float(modifier.value) / 100.0)
        
        # ===== ENCOUNTER COUNT MODIFIERS =====
        elif modifier.type == ModifierType.ENCOUNTER_COUNT_ADD and modifier.value:
            # Add encounters
            expedition.encounter_count += int(modifier.value)
        
        elif modifier.type == ModifierType.ENCOUNTER_COUNT_SUBTRACT and modifier.value:
            # Remove encounters (don't go below 1)
            expedition.encounter_count = max(1, expedition.encounter_count - int(modifier.value))
        
        elif modifier.type == ModifierType.ENCOUNTER_COUNT_HALVE:
            # Halve encounter count
            expedition.encounter_count = max(1, expedition.encounter_count // 2)
        
        # ===== AFFINITY MULTIPLIER MODIFIERS =====
        elif modifier.type == ModifierType.AFFINITY_MULTIPLIER_HALVE:
            # Halve affinity effects (complex - would need affinity calculation modification)
            # For now, reduce stat bonuses slightly
            for stat_name in ["hp", "atk", "mag", "vit", "spr", "intel", "spd", "lck"]:
                expedition.add_stat_bonus(stat_name, -2)
        
        elif modifier.type == ModifierType.AFFINITY_MULTIPLIER_RESET:
            # Reset affinity multipliers (complex - would need affinity calculation modification)
            # For now, clear dynamic affinities
            expedition.dynamic_favored_affinities.clear()
            expedition.dynamic_disfavored_affinities.clear()
        
        elif modifier.type == ModifierType.AFFINITY_MULTIPLIER_ADD and modifier.value:
            # Add to affinity multiplier (treat as stat bonus)
            bonus = int(float(modifier.value) * 5)  # Scale to reasonable stat bonus
            for stat_name in ["hp", "atk", "mag", "vit", "spr", "intel", "spd", "lck"]:
                expedition.add_stat_bonus(stat_name, bonus)
        
        # ===== MISHAP MODIFIERS =====
        elif modifier.type == ModifierType.MISHAP_CHANCE_HALVE:
            # Halve mishap chance
            expedition.prevent_mishaps = True
        
        # ===== DIFFICULTY MODIFIERS =====
        elif modifier.type == ModifierType.DIFFICULTY_INCREASE_ABSOLUTE and modifier.value:
            # Add flat difficulty (treat as multiplier based on absolute value)
            multiplier = 1.0 + (float(modifier.value) / 50.0)  # Scale absolute to reasonable multiplier
            expedition.add_difficulty_modifier(multiplier, source=f"DIFFICULTY_INCREASE_ABSOLUTE (modifier.value={modifier.value})")
        
        # ===== GUARANTEED OUTCOME MODIFIERS =====
        elif modifier.type == ModifierType.GUARANTEED_SUCCESS_NEXT_ENCOUNTER and modifier.value:
            # Guarantee success for next N encounters
            expedition.guaranteed_success_encounters += int(modifier.value)
        
        elif modifier.type == ModifierType.GUARANTEED_SUCCESS_TAG and modifier.value:
            # Guarantee success on tagged encounters (treat as high success rate bonus)
            expedition.add_success_rate_bonus(0.8)  # Very high bonus
        
        elif modifier.type == ModifierType.GUARANTEED_GREAT_SUCCESS_NEXT_ENCOUNTER and modifier.value:
            # Guarantee great success for next encounters (treat as guaranteed success + bonus)
            expedition.guaranteed_success_encounters += int(modifier.value)
            expedition.add_success_rate_bonus(0.5)  # Extra bonus for great success
        
        # ===== SPECIAL EFFECT MODIFIERS =====
        elif modifier.type == ModifierType.RANDOMIZE_CHECK_STATS:
            # Randomize which stats are checked (complex - would need stat check modification)
            # For now, add small bonus to all stats to represent adaptability
            for stat_name in ["hp", "atk", "mag", "vit", "spr", "intel", "spd", "lck"]:
                expedition.add_stat_bonus(stat_name, 2)
        
        elif modifier.type == ModifierType.PREVENT_NEXT_MISHAP:
            # Prevent next mishap only
            expedition.prevent_mishaps = True
        
        elif modifier.type == ModifierType.PREVENT_ALL_MISHAPS:
            # Prevent all mishaps
            expedition.prevent_mishaps = True
        
        elif modifier.type == ModifierType.SKIP_NEXT_ENCOUNTER and modifier.value:
            # Skip next encounter entirely
            expedition.skip_encounters += int(modifier.value)
    
    def _apply_final_multiplier(self, result: ExpeditionResult, team: Team, expedition_difficulty: int):
        """Calculate and apply the final luck-based multiplier, factoring in expedition difficulty
        Only currency rewards (gems/quartzs) are multiplied; item rewards are unaffected."""
        team_luck = team.get_total_luck()
        final_luck_score = FinalMultiplierTable.calculate_luck_score(
            team_luck, result.great_successes, result.mishaps, expedition_difficulty
        )
        multiplier_name, multiplier_value = FinalMultiplierTable.roll_final_multiplier(final_luck_score)

        # Separate items into currencies and non-currencies
        currency_types = {"gems", "quartzs"}
        currency_items = []
        non_currency_items = []
        for item in result.loot_pool.items:
            if item.item_type.value in currency_types:
                currency_items.append(item)
            else:
                non_currency_items.append(item)

        # Multiply only currency items
        new_currency_items = []
        for item in currency_items:
            # Multiply quantity, but always at least 1 if original was >0
            new_qty = max(1, int(item.quantity * multiplier_value)) if item.quantity > 0 else 0
            new_currency_items.append(type(item)(
                item_type=item.item_type,
                item_id=item.item_id,
                quantity=new_qty,
                rarity=item.rarity,
                value=item.value
            ))

        # Rebuild loot pool: non-currency items + adjusted currency items
    # Use already imported LootPool from module scope
        result.loot_pool = LootPool(non_currency_items + new_currency_items)
        result.final_luck_score = final_luck_score
        result.final_multiplier = FinalMultiplier(multiplier_name)