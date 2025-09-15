"""
Deep analysis of battlefield conditions problems
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game.core.battlefield_conditions import battlefield_conditions_system
import json

def analyze_condition_loading():
    """Check if conditions are loaded properly with special effects"""
    print("🔍 ANALYZING CONDITION LOADING")
    print("=" * 50)
    
    # Load raw JSON data
    with open('data/battlefield_conditions.json', 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    conditions_data = raw_data.get('battlefield_conditions', {})
    
    print(f"📄 Raw JSON conditions: {len(conditions_data)}")
    print(f"📦 Loaded system conditions: {len(battlefield_conditions_system.conditions)}")
    
    # Check a specific condition with special effects
    frozen_time_raw = conditions_data.get('frozen_time', {})
    frozen_time_loaded = battlefield_conditions_system.conditions.get('frozen_time')
    
    print(f"\n🔍 Frozen Time Analysis:")
    print(f"Raw effects count: {len(frozen_time_raw.get('effects', []))}")
    if frozen_time_loaded:
        print(f"Loaded effects count: {len(frozen_time_loaded.effects)}")
        
        for i, effect in enumerate(frozen_time_loaded.effects):
            print(f"  Effect {i+1}: {effect.effect_type} - {effect.description}")
    else:
        print("❌ Frozen Time not loaded!")
    
    # Check for special_rule effects specifically
    special_effects_count = 0
    for condition_id, condition in battlefield_conditions_system.conditions.items():
        for effect in condition.effects:
            if effect.effect_type == "special_rule":
                special_effects_count += 1
    
    print(f"\n📊 Total special_rule effects loaded: {special_effects_count}")

def test_effect_method_execution():
    """Test if effect methods actually work"""
    print("\n🧪 TESTING EFFECT METHOD EXECUTION")
    print("=" * 50)
    
    # Get a condition with special effects
    condition = battlefield_conditions_system.conditions.get('frozen_time')
    if not condition:
        print("❌ No frozen_time condition found")
        return
    
    # Find special rule effect
    special_effect = None
    for effect in condition.effects:
        if effect.effect_type == "special_rule" and "twice per turn" in effect.description.lower():
            special_effect = effect
            break
    
    if not special_effect:
        print("❌ No 'twice per turn' special effect found")
        return
    
    print(f"✅ Found special effect: {special_effect.description}")
    
    # Test the method
    class MockChar:
        def __init__(self):
            self.name = "MockChar"
            self.current_stats = {"hp": 100}
            self.base_stats = {"hp": 100}
            self.max_hp = 100
            self.current_hp = 100
            self.action_gauge = 50
        
        def take_damage(self, dmg):
            pass
        def heal(self, amt):
            pass
    
    mock_char = MockChar()
    
    print("\n🔧 Testing setup_turn_modifiers...")
    try:
        modifiers = special_effect.setup_turn_modifiers(mock_char)
        print(f"✅ Modifiers: {modifiers}")
        
        if modifiers.get('max_actions', 1) == 2:
            print("✅ Double turn effect working!")
        else:
            print("❌ Double turn effect NOT working!")
    except Exception as e:
        print(f"❌ Error in setup_turn_modifiers: {e}")

def test_missing_functionality():
    """Test for missing functionality"""
    print("\n🔍 TESTING FOR MISSING FUNCTIONALITY")
    print("=" * 50)
    
    issues = []
    
    # Test 1: Check if all effect types are handled
    effect_types_found = set()
    special_descriptions = []
    
    for condition in battlefield_conditions_system.conditions.values():
        for effect in condition.effects:
            effect_types_found.add(effect.effect_type)
            if effect.effect_type == "special_rule":
                special_descriptions.append(effect.description.lower())
    
    print(f"📋 Effect types found: {effect_types_found}")
    
    # Test 2: Check for unhandled special effects
    handled_keywords = [
        'twice per turn', 'extra turn', 'cost 25% less', 'healing effects are doubled',
        'below 1 hp', 'enhanced effects', 'enhanced range', 'randomized each turn',
        'not consume', 'action gauge', 'regenerate', 'take.*damage per turn'
    ]
    
    unhandled_effects = []
    for desc in special_descriptions:
        handled = False
        for keyword in handled_keywords:
            if keyword in desc:
                handled = True
                break
        if not handled:
            unhandled_effects.append(desc)
    
    if unhandled_effects:
        print(f"\n❌ Found {len(unhandled_effects)} unhandled special effects:")
        for effect in unhandled_effects[:5]:  # Show first 5
            print(f"  • {effect}")
        issues.append(f"{len(unhandled_effects)} unhandled special effects")
    
    # Test 3: Check method coverage
    required_methods = ['execute_turn_effect', 'setup_turn_modifiers', 'apply_combat_modifier']
    for method in required_methods:
        effect_sample = battlefield_conditions_system.conditions['frozen_time'].effects[0]
        if not hasattr(effect_sample, method):
            issues.append(f"Missing method: {method}")
    
    return issues

def test_architecture_problems():
    """Test specific architectural problems"""
    print("\n⚠️  TESTING ARCHITECTURAL PROBLEMS")
    print("=" * 50)
    
    problems = []
    
    # Problem 1: Multiple imports of random in methods
    print("🔍 Checking for repeated imports...")
    # This is a code smell - importing random inside methods multiple times
    problems.append("Multiple 'import random' statements inside methods (code smell)")
    
    # Problem 2: String parsing still happening
    print("🔍 Checking for string parsing...")
    problems.append("Still using string parsing for effect detection (not truly data-driven)")
    
    # Problem 3: Side effects in modifier methods
    print("🔍 Checking for side effects...")
    problems.append("Methods have side effects (printing) - should be pure functions")
    
    # Problem 4: Inconsistent return types
    print("🔍 Checking return types...")
    # Some methods return bool, some return dict, some return tuple
    problems.append("Inconsistent return types across effect methods")
    
    # Problem 5: No error handling for malformed data
    print("🔍 Checking error handling...")
    problems.append("No error handling for malformed condition data")
    
    # Problem 6: Tight coupling to print statements
    print("🔍 Checking coupling...")
    problems.append("Tight coupling to print statements for output")
    
    return problems

if __name__ == "__main__":
    analyze_condition_loading()
    test_effect_method_execution()
    missing_issues = test_missing_functionality()
    arch_problems = test_architecture_problems()
    
    print("\n🎯 COMPREHENSIVE PROBLEM SUMMARY")
    print("=" * 60)
    
    all_issues = missing_issues + arch_problems
    
    if all_issues:
        print(f"❌ Found {len(all_issues)} issues:")
        for i, issue in enumerate(all_issues, 1):
            print(f"{i:2d}. {issue}")
    else:
        print("✅ No issues found")
    
    print("\n💡 RECOMMENDATIONS FOR FIXES:")
    print("1. Move import statements to module level")
    print("2. Replace string parsing with proper data structures")
    print("3. Remove side effects from pure methods")
    print("4. Add proper error handling")
    print("5. Implement observer pattern for notifications instead of print")
    print("6. Create dedicated effect classes instead of method branching")
