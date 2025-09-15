#!/usr/bin/env python3
"""
Diagnose why some battlefield conditions aren't working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.game.core.battlefield_conditions import BattlefieldConditionsSystem

def diagnose_failed_conditions():
    """Diagnose the battlefield conditions that aren't working"""
    print("🔍 DIAGNOSING FAILED BATTLEFIELD CONDITIONS")
    print("=" * 60)
    
    failed_conditions = [
        "scorching_sun",
        "gravity_well", 
        "magic_overflow",
        "blood_moon"
    ]
    
    system = BattlefieldConditionsSystem()
    
    for condition_name in failed_conditions:
        print(f"\n🔍 Diagnosing: {condition_name}")
        print("-" * 40)
        
        success = system.set_active_condition(condition_name)
        if not success:
            print(f"❌ Failed to load condition: {condition_name}")
            continue
            
        condition = system.active_condition
        print(f"📜 {condition.name} ({condition.rarity})")
        print(f"📋 {condition.description}")
        print(f"⚡ Number of effects: {len(condition.effects)}")
        
        # Analyze each effect in detail
        for i, effect in enumerate(condition.effects):
            print(f"\n   Effect {i+1}: {effect.name}")
            print(f"   • Type: {effect.effect_type}")
            print(f"   • Target: {effect.target_criteria}")
            print(f"   • Description: {effect.description}")
            
            # Check what methods this effect has
            methods = []
            if hasattr(effect, 'execute_turn_effect'):
                methods.append("turn_effect")
            if hasattr(effect, 'execute_combat_effect'):
                methods.append("combat_effect")
            if hasattr(effect, 'execute_enhancement_effect'):
                methods.append("enhancement_effect")
            if hasattr(effect, 'execute_targeting_effect'):
                methods.append("targeting_effect")
            
            print(f"   • Available methods: {methods}")
            
            # Try to parse the effect description
            from src.game.core.battlefield_conditions import EffectData
            try:
                effect_data = EffectData.from_description(effect.description)
                print(f"   • ✅ Parsed category: {effect_data.category.value}")
                print(f"   • Data: {effect_data.data}")
            except Exception as e:
                print(f"   • ❌ Parsing error: {str(e)}")
                print(f"   • This is likely why the effect isn't working!")

if __name__ == "__main__":
    diagnose_failed_conditions()
