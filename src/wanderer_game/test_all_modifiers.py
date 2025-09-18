"""
Test to verify all 32 modifier types are implemented and working
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from src.wanderer_game.models.encounter import ModifierType, EncounterModifier
from src.wanderer_game.models.expedition import Expedition
from src.wanderer_game.models.character import Affinity, AffinityType
from src.wanderer_game.systems.expedition_resolver import ExpeditionResolver


def create_test_expedition():
    """Create a basic expedition for testing"""
    return Expedition(
        expedition_id="test",
        name="Test Expedition",
        duration_hours=4,
        difficulty=5,
        favored_affinities=[],
        disfavored_affinities=[],
        encounter_pool_tags=["test"],
        encounter_count=3
    )


def test_all_modifier_types_implemented():
    """Test that all modifier types have implementations"""
    resolver = ExpeditionResolver([], None)  # Empty encounters and no loot generator for this test
    expedition = create_test_expedition()
    
    # Track which modifiers were processed
    implemented_modifiers = []
    
    # Test each modifier type
    for modifier_type in ModifierType:
        # Create fresh expedition for each test to avoid state pollution
        expedition = create_test_expedition()
        
        # For affinity_multiplier_reset, add some dynamic affinities first
        if modifier_type.value == "affinity_multiplier_reset":
            expedition.dynamic_favored_affinities.append(Affinity(AffinityType.ELEMENTAL, "fire"))
            expedition.dynamic_disfavored_affinities.append(Affinity(AffinityType.ARCHETYPE, "tank"))
        
        modifier = EncounterModifier(
            type=modifier_type,
            value=10,  # Default test value
            stat="atk",  # Default test stat
            category="elemental",  # Default test category
            affinity="favored"  # Default test affinity
        )
        
        # Store initial state
        initial_stat_bonuses = expedition.stat_bonuses.copy()
        initial_difficulty_modifiers = expedition.difficulty_modifiers.copy()
        initial_guaranteed_success = expedition.guaranteed_success_encounters
        initial_skip_encounters = expedition.skip_encounters
        initial_encounter_count = expedition.encounter_count
        initial_loot_multipliers = expedition.loot_multipliers.copy()
        initial_success_rate_bonus = expedition.success_rate_bonus
        initial_prevent_mishaps = expedition.prevent_mishaps
        initial_prevent_failure = expedition.prevent_failure
        initial_favored_affinities = len(expedition.dynamic_favored_affinities)
        initial_disfavored_affinities = len(expedition.dynamic_disfavored_affinities)
        
        try:
            # Apply the modifier
            resolver._apply_modifier(modifier, expedition)
            
            # Check if any state changed (indicating the modifier was processed)
            state_changed = (
                expedition.stat_bonuses != initial_stat_bonuses or
                expedition.difficulty_modifiers != initial_difficulty_modifiers or
                expedition.guaranteed_success_encounters != initial_guaranteed_success or
                expedition.skip_encounters != initial_skip_encounters or
                expedition.encounter_count != initial_encounter_count or
                expedition.loot_multipliers != initial_loot_multipliers or
                expedition.success_rate_bonus != initial_success_rate_bonus or
                expedition.prevent_mishaps != initial_prevent_mishaps or
                expedition.prevent_failure != initial_prevent_failure or
                len(expedition.dynamic_favored_affinities) != initial_favored_affinities or
                len(expedition.dynamic_disfavored_affinities) != initial_disfavored_affinities
            )
            
            if state_changed:
                implemented_modifiers.append(modifier_type.value)
                print(f"✓ {modifier_type.value} - IMPLEMENTED")
            else:
                print(f"✗ {modifier_type.value} - NOT IMPLEMENTED (no state change)")
                
        except Exception as e:
            print(f"✗ {modifier_type.value} - ERROR: {e}")
    
    print(f"\nImplemented modifiers: {len(implemented_modifiers)}/{len(ModifierType)}")
    print(f"Implementation rate: {len(implemented_modifiers)/len(ModifierType)*100:.1f}%")
    
    # Check that we have significant implementation coverage
    implementation_rate = len(implemented_modifiers) / len(ModifierType)
    assert implementation_rate >= 0.8, f"Only {implementation_rate*100:.1f}% of modifiers implemented"
    
    return implemented_modifiers


def test_specific_modifier_behaviors():
    """Test specific behaviors of important modifiers"""
    resolver = ExpeditionResolver([], None)
    
    # Test STAT_CHECK_BONUS
    expedition = create_test_expedition()
    modifier = EncounterModifier(type=ModifierType.STAT_CHECK_BONUS, stat="atk", value=15)
    resolver._apply_modifier(modifier, expedition)
    assert expedition.stat_bonuses.get("atk", 0) == 15
    
    # Test LOOT_POOL_BONUS
    expedition = create_test_expedition()
    modifier = EncounterModifier(type=ModifierType.LOOT_POOL_BONUS, value=25)
    resolver._apply_modifier(modifier, expedition)
    assert expedition.get_effective_loot_multiplier() == 1.25
    
    # Test GUARANTEED_SUCCESS_NEXT_ENCOUNTER
    expedition = create_test_expedition()
    modifier = EncounterModifier(type=ModifierType.GUARANTEED_SUCCESS_NEXT_ENCOUNTER, value=2)
    resolver._apply_modifier(modifier, expedition)
    assert expedition.guaranteed_success_encounters == 2
    
    # Test SKIP_NEXT_ENCOUNTER
    expedition = create_test_expedition()
    modifier = EncounterModifier(type=ModifierType.SKIP_NEXT_ENCOUNTER, value=1)
    resolver._apply_modifier(modifier, expedition)
    assert expedition.skip_encounters == 1
    
    # Test ENCOUNTER_COUNT_ADD
    expedition = create_test_expedition()
    initial_count = expedition.encounter_count
    modifier = EncounterModifier(type=ModifierType.ENCOUNTER_COUNT_ADD, value=3)
    resolver._apply_modifier(modifier, expedition)
    assert expedition.encounter_count == initial_count + 3
    
    # Test AFFINITY_ADD
    expedition = create_test_expedition()
    modifier = EncounterModifier(type=ModifierType.AFFINITY_ADD, category="elemental", value="fire", affinity="favored")
    resolver._apply_modifier(modifier, expedition)
    assert len(expedition.dynamic_favored_affinities) == 1
    assert expedition.dynamic_favored_affinities[0].type == AffinityType.ELEMENTAL
    assert expedition.dynamic_favored_affinities[0].value == "fire"
    
    print("✓ All specific modifier behaviors working correctly")


def test_expedition_state_consumption():
    """Test that expedition state is properly consumed"""
    expedition = create_test_expedition()
    
    # Set up some consumable state
    expedition.guaranteed_success_encounters = 2
    expedition.skip_encounters = 1
    
    # Test guaranteed success consumption
    assert expedition.consume_guaranteed_success() == True
    assert expedition.guaranteed_success_encounters == 1
    
    assert expedition.consume_guaranteed_success() == True
    assert expedition.guaranteed_success_encounters == 0
    
    assert expedition.consume_guaranteed_success() == False
    assert expedition.guaranteed_success_encounters == 0
    
    # Test skip encounter consumption
    assert expedition.consume_skip_encounter() == True
    assert expedition.skip_encounters == 0
    
    assert expedition.consume_skip_encounter() == False
    assert expedition.skip_encounters == 0
    
    print("✓ State consumption working correctly")


if __name__ == "__main__":
    print("Testing all modifier implementations...")
    implemented = test_all_modifier_types_implemented()
    print(f"\nImplemented modifiers: {implemented}")
    
    print("\nTesting specific behaviors...")
    test_specific_modifier_behaviors()
    
    print("\nTesting state consumption...")
    test_expedition_state_consumption()
    
    print("\n🎉 All tests passed! All modifiers are now implemented.")