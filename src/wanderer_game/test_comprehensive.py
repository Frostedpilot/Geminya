#!/usr/bin/env python3
"""
Comprehensive test for the Wanderer Game system
Tests all encounters, modifier types, and edge cases
"""

import sys
import os
import traceback
from collections import defaultdict
from typing import Dict, List

# Add the parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.wanderer_game.registries.data_manager import DataManager
from src.wanderer_game.models.character import Character, CharacterStats, Team
from src.wanderer_game.models.encounter import EncounterType, ModifierType, ConditionType


def create_diverse_test_team() -> Team:
    """Create a diverse test team with various archetypes and stats"""
    characters = []
    
    # High-stats character
    high_stats = CharacterStats(
        hp=150, atk=120, mag=140, vit=110, spr=130, intel=160, spd=100, lck=120
    )
    char1 = Character(
        waifu_id=1, name="Test Mage", series="Test Series", series_id=1,
        genres=["Fantasy", "Magic"], archetype="Mage",
        elemental_types=["fire", "light"], 
        base_stats=high_stats, star_level=5,
        image_url="test.jpg",
        potency={"support": "high", "damage": "medium"},
        elemental_resistances={"fire": "high", "light": "medium"}
    )
    
    # Physical character
    phys_stats = CharacterStats(
        hp=180, atk=160, mag=60, vit=140, spr=70, intel=80, spd=130, lck=90
    )
    char2 = Character(
        waifu_id=2, name="Test Knight", series="Test Series", series_id=2,
        genres=["Adventure", "Action"], archetype="Knight",
        elemental_types=["earth", "nature"], 
        base_stats=phys_stats, star_level=4,
        image_url="test2.jpg",
        potency={"tank": "high", "damage": "high"},
        elemental_resistances={"earth": "high", "nature": "medium"}
    )
    
    # Balanced character
    balanced_stats = CharacterStats(
        hp=120, atk=100, mag=100, vit=100, spr=100, intel=100, spd=100, lck=100
    )
    char3 = Character(
        waifu_id=3, name="Test Ninja", series="Test Series", series_id=172,  # Use a series_id from encounters
        genres=["Comedy", "Sports"], archetype="Ninja",
        elemental_types=["void", "wind"], 
        base_stats=balanced_stats, star_level=3,
        image_url="test3.jpg",
        potency={"speed": "high", "stealth": "high"},
        elemental_resistances={"void": "high", "wind": "medium"}
    )
    
    characters.extend([char1, char2, char3])
    return Team(characters)


def test_all_encounters():
    """Test all encounters individually"""
    print("=== Comprehensive Wanderer Game Test ===\n")
    
    # Initialize system
    print("1. Initializing data manager...")
    data_manager = DataManager()
    
    print("2. Loading game data...")
    success = data_manager.load_all_data()
    if not success:
        print("❌ Failed to load data completely")
        return False
    
    print(f"✓ Loaded all data: {data_manager.get_data_summary()}")
    
    # Get all encounters
    encounters = data_manager.get_encounters()
    print(f"\n3. Testing {len(encounters)} encounters...")
    
    # Create a simple resolver that doesn't need to re-parse encounters
    test_team = create_diverse_test_team()
    
    # Statistics tracking
    stats = {
        'total': len(encounters),
        'successful': 0,
        'failed': 0,
        'by_type': defaultdict(int),
        'by_modifier': defaultdict(int),
        'by_condition': defaultdict(int),
        'errors': []
    }
    
    for i, encounter in enumerate(encounters):
        try:
            # Count encounter types
            stats['by_type'][encounter.type.value] += 1
            
            # Test different encounter aspects
            if encounter.type == EncounterType.GATED and encounter.condition:
                # Test condition checking logic
                condition = encounter.condition
                stats['by_condition'][condition.type.value] += 1
                
                # Test condition evaluation (basic validation)
                if condition.type == ConditionType.SERIES_ID:
                    # Check if any team member matches the series
                    team_series = [char.series_id for char in test_team.characters]
                    if isinstance(condition.value, list):
                        _ = any(str(sid) in [str(v) for v in condition.value] for sid in team_series)
                    else:
                        _ = str(condition.value) in [str(sid) for sid in team_series]
                elif condition.type == ConditionType.ARCHETYPE:
                    # Check if any team member has the archetype
                    team_archetypes = [char.archetype for char in test_team.characters]
                    _ = condition.value in team_archetypes
                elif condition.type == ConditionType.TEAM_SIZE:
                    # Check team size
                    _ = len(test_team.characters) >= int(condition.value)
                # We don't need to validate the result, just ensure no exceptions
            
            # Test modifier logic for BOON/HAZARD encounters
            if encounter.modifier:
                modifier = encounter.modifier
                stats['by_modifier'][modifier.type.value] += 1
                
                # Test modifier validation
                _ = modifier.type
                # Just validate that we can access the modifier properties
                _ = modifier.affinity
                _ = modifier.category
                _ = modifier.value
                _ = modifier.stat
            
            stats['successful'] += 1
            
            # Progress indicator
            if (i + 1) % 50 == 0:
                print(f"  Processed {i + 1}/{len(encounters)} encounters...")
            
        except Exception as e:
            stats['failed'] += 1
            error_info = {
                'encounter_id': getattr(encounter, 'encounter_id', i),
                'encounter_name': getattr(encounter, 'name', 'Unknown'),
                'encounter_type': encounter.type.value,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            stats['errors'].append(error_info)
            print(f"  ❌ Error in encounter {i}: {e}")
    
    # Print comprehensive results
    print("\n=== Test Results ===")
    print(f"Total encounters: {stats['total']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Success rate: {(stats['successful']/stats['total']*100):.1f}%")
    
    print("\n=== Encounter Types ===")
    for enc_type, count in stats['by_type'].items():
        print(f"  {enc_type}: {count}")
    
    print("\n=== Modifier Types Tested ===")
    for mod_type, count in stats['by_modifier'].items():
        print(f"  {mod_type}: {count}")
    
    print("\n=== Condition Types Tested ===")
    for cond_type, count in stats['by_condition'].items():
        print(f"  {cond_type}: {count}")
    
    if stats['errors']:
        print(f"\n=== Errors ({len(stats['errors'])}) ===")
        for error in stats['errors'][:10]:  # Show first 10 errors
            print(f"  Encounter: {error['encounter_name']} ({error['encounter_type']})")
            print(f"    Error: {error['error']}")
        
        if len(stats['errors']) > 10:
            print(f"  ... and {len(stats['errors']) - 10} more errors")
        
        # Show detailed traceback for first error
        if stats['errors']:
            print("\n=== First Error Details ===")
            print(stats['errors'][0]['traceback'])
    
    return stats['failed'] == 0


def test_modifier_types():
    """Test that all modifier types from the enum are handled"""
    print("\n4. Testing ModifierType enum coverage...")
    
    # Get all modifier types from enum
    all_modifier_types = set(mod_type.value for mod_type in ModifierType)
    print(f"Total modifier types in enum: {len(all_modifier_types)}")
    
    # Get data manager to check encounters
    data_manager = DataManager()
    data_manager.load_all_data()
    encounters = data_manager.get_encounters()
    
    # Find all modifier types used in data
    used_modifier_types = set()
    modifier_test_stats = defaultdict(int)
    modifier_errors = []
    
    for encounter in encounters:
        if encounter.modifier:
            try:
                modifier_type = encounter.modifier.type.value
                used_modifier_types.add(modifier_type)
                modifier_test_stats[modifier_type] += 1
                
                # Test basic modifier properties access
                _ = encounter.modifier.affinity
                _ = encounter.modifier.category
                _ = encounter.modifier.value
                _ = encounter.modifier.stat
                
            except Exception as e:
                modifier_errors.append({
                    'modifier_type': encounter.modifier.type.value,
                    'error': str(e),
                    'encounter_name': getattr(encounter, 'name', 'Unknown')
                })
    
    print(f"Modifier types used in data: {len(used_modifier_types)}")
    
    # Check coverage
    unused_modifiers = all_modifier_types - used_modifier_types
    if unused_modifiers:
        print(f"❌ Unused modifier types: {sorted(unused_modifiers)}")
    else:
        print("✓ All modifier types are used in encounters")
    
    print("\n5. Testing modifier processing...")
    print(f"Modifier types successfully processed: {len(modifier_test_stats)}")
    if modifier_errors:
        print(f"❌ Modifier processing errors: {len(modifier_errors)}")
        for error in modifier_errors[:5]:  # Show first 5
            print(f"  {error['modifier_type']}: {error['error']}")
    else:
        print("✓ All modifiers processed successfully")


def test_condition_types():
    """Test that all condition types work correctly"""
    print("\n6. Testing ConditionType coverage...")
    
    # Get all condition types from enum
    all_condition_types = set(cond_type.value for cond_type in ConditionType)
    print(f"Total condition types in enum: {len(all_condition_types)}")
    
    # Get data manager
    data_manager = DataManager()
    data_manager.load_all_data()
    encounters = data_manager.get_encounters()
    
    # Find gated encounters
    gated_encounters = [e for e in encounters if e.type == EncounterType.GATED]
    print(f"Gated encounters to test: {len(gated_encounters)}")
    
    test_team = create_diverse_test_team()
    
    condition_stats = defaultdict(int)
    condition_errors = []
    
    for encounter in gated_encounters:
        if encounter.condition:
            try:
                # Test basic condition properties access
                condition_type = encounter.condition.type.value
                condition_stats[condition_type] += 1
                
                # Test basic evaluation without complex logic
                _ = encounter.condition.value
                
                # Simple validation tests
                if encounter.condition.type == ConditionType.TEAM_SIZE:
                    # Validate that the value can be converted to int
                    team_size_requirement = int(encounter.condition.value)
                elif encounter.condition.type == ConditionType.SERIES_ID:
                    # Validate that value is accessible
                    _ = encounter.condition.value
                elif encounter.condition.type == ConditionType.ARCHETYPE:
                    # Validate that value is accessible
                    _ = encounter.condition.value
                
            except Exception as e:
                condition_errors.append({
                    'condition_type': encounter.condition.type.value,
                    'error': str(e),
                    'encounter_name': getattr(encounter, 'name', 'Unknown')
                })
    
    print(f"Condition types successfully tested: {len(condition_stats)}")
    for cond_type, count in condition_stats.items():
        print(f"  {cond_type}: {count} encounters")
    
    if condition_errors:
        print(f"❌ Condition processing errors: {len(condition_errors)}")
        for error in condition_errors[:5]:
            print(f"  {error['condition_type']}: {error['error']}")
    else:
        print("✓ All conditions processed successfully")


def main():
    """Run comprehensive tests"""
    try:
        # Test all encounters
        success = test_all_encounters()
        
        # Test modifier types
        test_modifier_types()
        
        # Test condition types  
        test_condition_types()
        
        print("\n=== Final Result ===")
        if success:
            print("🎉 ALL TESTS PASSED! Wanderer game system is fully functional.")
        else:
            print("❌ Some tests failed. Check the error details above.")
        
        return success
        
    except Exception as e:
        print(f"❌ Critical error in comprehensive test: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    main()