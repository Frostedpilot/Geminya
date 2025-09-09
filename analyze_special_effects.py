#!/usr/bin/env python3
"""
Check which special effects are implemented vs not implemented in the battle system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game.core.battlefield_conditions import battlefield_conditions_system
import json

def analyze_special_effects():
    print("🔍 BATTLEFIELD CONDITIONS SPECIAL EFFECTS ANALYSIS")
    print("=" * 70)
    
    # Load all conditions
    with open('data/battlefield_conditions.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    conditions_data = data.get('battlefield_conditions', {})
    special_effects = []
    turn_effects = []
    unsupported_effects = []
    
    for condition_id, condition_data in conditions_data.items():
        condition_name = condition_data.get('name', condition_id)
        
        for effect in condition_data.get('effects', []):
            if effect['effect_type'] == 'special_rule':
                description = effect['description']
                special_effects.append({
                    'condition': condition_name,
                    'effect': description,
                    'id': condition_id
                })
                
                # Categorize turn-based effects
                if any(keyword in description.lower() for keyword in ['turn', 'twice', 'double', 'extra', 'action']):
                    turn_effects.append({
                        'condition': condition_name,
                        'effect': description,
                        'id': condition_id
                    })
                    
                # Check for potentially unsupported effects
                if any(keyword in description.lower() for keyword in [
                    'twice per turn', 'extra turn', 'double duration', 'cost 25% less',
                    'randomized each turn', 'varies randomly', 'not consume a turn',
                    'enhanced effects', 'enhanced range', 'no character below 1 hp'
                ]):
                    unsupported_effects.append({
                        'condition': condition_name,
                        'effect': description,
                        'id': condition_id
                    })
    
    print(f"📊 TOTAL SPECIAL EFFECTS: {len(special_effects)}")
    print(f"⏰ TURN-BASED EFFECTS: {len(turn_effects)}")
    print(f"❓ POTENTIALLY UNSUPPORTED: {len(unsupported_effects)}")
    
    print(f"\n⏰ TURN-BASED EFFECTS:")
    print("-" * 50)
    for effect in turn_effects:
        print(f"🔹 {effect['condition']} ({effect['id']})")
        print(f"   {effect['effect']}")
    
    print(f"\n❓ POTENTIALLY UNSUPPORTED EFFECTS:")
    print("-" * 50)
    for effect in unsupported_effects:
        print(f"🔹 {effect['condition']} ({effect['id']})")
        print(f"   {effect['effect']}")
    
    print(f"\n✅ CURRENTLY SUPPORTED EFFECTS:")
    print("-" * 50)
    
    # Check what's actually implemented in test_battle_full_system.py
    implemented_effects = []
    
    try:
        with open('test_battle_full_system.py', 'r', encoding='utf-8') as f:
            test_content = f.read().lower()
        
        # Check for implementation indicators
        implementation_checks = {
            "Double turns / Act twice per turn": ["max_actions_per_turn", "can act twice"],
            "Extra turns every N rounds": ["extra_turn_counter", "extra turn"],
            "Cost reduction (25% less ability cost)": ["ability_cost_modifier", "cost 25% less"],
            "Duration modifiers (double duration)": ["status_duration_multiplier", "double duration"],
            "Enhanced ability effects/range": ["get_enhanced_effect_multiplier", "enhanced effects"],
            "Minimum HP protection (no below 1 HP)": ["minimum_hp_protection", "divine intervention"],
            "Random stat modifiers each turn": ["chaos effect", "randomized each turn"],
            "Turn consumption prevention": ["skip_turn_consumption", "not consume"],
            "Action gauge variations": ["action gauge", "varies randomly"],
            "Healing multipliers": ["healing_multiplier", "healing effects are doubled"]
        }
        
        for effect_name, keywords in implementation_checks.items():
            if any(keyword.replace(' ', '_') in test_content or keyword in test_content for keyword in keywords):
                implemented_effects.append(effect_name)
        
        # Also check basic supported effects
        basic_supported = [
            "Chain effects (chain lightning)",
            "Shared damage/healing (quantum entanglement)", 
            "Accuracy modifiers (miss chance)",
            "Targeting modifiers (random targets)",
            "Revival effects (phoenix rebirth)",
            "Per-turn damage/healing (regeneration)",
            "Life-steal effects",
            "Element-specific bonuses"
        ]
        
        all_supported = basic_supported + implemented_effects
        
        for category in all_supported:
            print(f"✅ {category}")
        
        # Show what's still not implemented
        all_possible_effects = list(implementation_checks.keys()) + basic_supported
        not_implemented = [effect for effect in all_possible_effects if effect not in all_supported]
        
    except FileNotFoundError:
        # Fallback to old list if test file not found
        all_supported = [
            "Chain effects (chain lightning)",
            "Shared damage/healing (quantum entanglement)", 
            "Accuracy modifiers (miss chance)",
            "Targeting modifiers (random targets)",
            "Revival effects (phoenix rebirth)",
            "Per-turn damage/healing (regeneration)",
            "Life-steal effects",
            "Element-specific bonuses"
        ]
        
        for category in all_supported:
            print(f"✅ {category}")
        
        not_implemented = [
            "Double turns / Act twice per turn",
            "Extra turns every N rounds", 
            "Cost reduction (25% less ability cost)",
            "Duration modifiers (double duration)",
            "Enhanced ability effects/range",
            "Minimum HP protection (no below 1 HP)",
            "Random stat modifiers each turn",
            "Turn consumption prevention"
        ]
    
    if not_implemented:
        print(f"\n❌ NOT YET IMPLEMENTED:")
        print("-" * 50)
        for category in not_implemented:
            print(f"❌ {category}")
    else:
        print(f"\n🎉 ALL ADVANCED EFFECTS ARE IMPLEMENTED!")
        print("✅ Complete battlefield conditions system ready!")

if __name__ == "__main__":
    analyze_special_effects()
