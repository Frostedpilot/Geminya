"""
Test script for the enhanced battlefield conditions system
Tests all 53 battlefield conditions and their effects
"""
import sys
import os
sys.path.append('src')

from game.core.battlefield_conditions import battlefield_conditions_system, BattlefieldConditionsSystem
from game.components.stats_component import StatsComponent, StatType
from datetime import datetime, timedelta
import json

class MockCharacter:
    """Mock character for testing battlefield conditions"""
    def __init__(self, character_id: str, elements=None, archetype=None):
        self.character_id = character_id
        self.stats = StatsComponent()
        self.elements = elements or ["neutral"]
        self.archetype = archetype
        self.battlefield_special_rules = []
    
    def get_elements(self):
        return self.elements

def test_all_conditions():
    """Test all battlefield conditions"""
    print("🧪 Testing Enhanced Battlefield Conditions System")
    print("=" * 60)
    
    # Test basic system functionality
    system = battlefield_conditions_system
    print(f"✅ System initialized with {len(system.conditions)} conditions")
    
    # Test condition loading
    with open('data/battlefield_conditions.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    loaded_conditions = len(data['battlefield_conditions'])
    print(f"✅ JSON file contains {loaded_conditions} conditions")
    
    # Count by rarity
    rarity_counts = {}
    type_counts = {}
    effect_counts = {"stat_modifier": 0, "special_rule": 0}
    
    for condition_id, condition in system.conditions.items():
        rarity_counts[condition.rarity] = rarity_counts.get(condition.rarity, 0) + 1
        type_counts[condition.condition_type.value] = type_counts.get(condition.condition_type.value, 0) + 1
        
        for effect in condition.effects:
            effect_counts[effect.effect_type] = effect_counts.get(effect.effect_type, 0) + 1
    
    print(f"\n📊 Condition Statistics:")
    print(f"   Rarity Distribution: {rarity_counts}")
    print(f"   Type Distribution: {type_counts}")
    print(f"   Effect Distribution: {effect_counts}")
    
    # Test random condition selection
    print(f"\n🎲 Testing Random Selection:")
    for rarity in ["common", "rare", "legendary"]:
        condition = system.get_random_condition(rarity)
        print(f"   {rarity.upper()}: {condition.name}")
    
    # Test condition application
    print(f"\n⚔️ Testing Condition Effects:")
    
    # Create test characters with different elements
    characters = [
        MockCharacter("fire_char", ["fire"]),
        MockCharacter("water_char", ["water"]),
        MockCharacter("neutral_char", ["neutral"]),
        MockCharacter("multi_char", ["fire", "water"])
    ]
    
    # Test a few representative conditions
    test_conditions = [
        "scorching_sun",      # Elemental effects
        "rainbow_bridge",     # All stats bonus
        "chaos_realm",        # Special rules
        "blood_moon",         # Multiple stat effects
        "divine_intervention" # Legendary condition
    ]
    
    for condition_id in test_conditions:
        if condition_id in system.conditions:
            print(f"\n   Testing: {system.conditions[condition_id].name}")
            system.set_active_condition(condition_id)
            
            applied_effects = system.apply_condition_effects(characters)
            for char_id, effects in applied_effects.items():
                print(f"     {char_id}: {effects}")
            
            # Test special rule parsing
            for character in characters:
                special_rules = system.get_active_special_rules(character)
                if special_rules:
                    print(f"     {character.character_id} special rules: {len(special_rules)}")
                    for rule in special_rules:
                        print(f"       - {rule['rule_type']}: {rule['effect_data']}")
            
            # Clear effects
            for character in characters:
                system.clear_character_effects(character)
    
    # Test condition summary
    system.set_active_condition("harmony_resonance")
    summary = system.get_condition_summary()
    print(f"\n📋 Condition Summary Example:")
    print(f"   Name: {summary['name']}")
    print(f"   Rarity: {summary['rarity']}")
    print(f"   Total Effects: {summary['total_effects']}")
    print(f"   Stat Effects: {len(summary['stat_effects'])}")
    print(f"   Special Effects: {len(summary['special_effects'])}")
    
    # Test weekly rotation
    print(f"\n🔄 Testing Weekly Rotation:")
    for i in range(5):
        condition = system.rotate_weekly_condition()
        print(f"   Week {i+1}: {condition.name} ({condition.rarity})")
    
    # Test all conditions for errors
    print(f"\n🔍 Validating All Conditions:")
    error_count = 0
    
    for condition_id, condition in system.conditions.items():
        try:
            system.set_active_condition(condition_id)
            applied_effects = system.apply_condition_effects(characters[:1])  # Test with one character
            
            # Validate effect structure
            for effect in condition.effects:
                if effect.effect_type not in ["stat_modifier", "special_rule"]:
                    print(f"   ❌ Invalid effect type in {condition_id}: {effect.effect_type}")
                    error_count += 1
                
                if effect.effect_type == "stat_modifier" and not effect.stat_affected:
                    print(f"   ❌ Missing stat_affected in {condition_id}")
                    error_count += 1
        
        except Exception as e:
            print(f"   ❌ Error testing {condition_id}: {e}")
            error_count += 1
    
    if error_count == 0:
        print(f"   ✅ All {len(system.conditions)} conditions validated successfully!")
    else:
        print(f"   ❌ Found {error_count} errors")
    
    # Test target criteria coverage
    print(f"\n🎯 Target Criteria Analysis:")
    criteria_usage = {}
    for condition in system.conditions.values():
        for effect in condition.effects:
            criteria = effect.target_criteria
            criteria_usage[criteria] = criteria_usage.get(criteria, 0) + 1
    
    print(f"   Criteria Usage: {criteria_usage}")
    
    # Test special rule categories
    print(f"\n⚡ Special Rule Categories:")
    rule_categories = {}
    for condition in system.conditions.values():
        for effect in condition.effects:
            if effect.effect_type == "special_rule":
                category = system._categorize_special_rule(effect.description)
                rule_categories[category] = rule_categories.get(category, 0) + 1
    
    print(f"   Rule Categories: {rule_categories}")
    
    print(f"\n🎉 Battlefield Conditions System Test Complete!")
    print(f"   Total Conditions: {len(system.conditions)}")
    print(f"   System Status: {'✅ FULLY FUNCTIONAL' if error_count == 0 else '❌ ISSUES FOUND'}")

if __name__ == "__main__":
    test_all_conditions()
