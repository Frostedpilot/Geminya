#!/usr/bin/env python3
"""
Specifically debug gravity_well condition
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.game.core.battlefield_conditions import BattlefieldConditionsSystem

class TestCharacter:
    def __init__(self, name):
        self.name = name
        self.max_hp = 100
        self.current_hp = 100
        self.action_gauge = 100
        self.base_stats = {'atk': 50, 'mag': 40, 'vit': 45, 'spr': 35, 'int': 30, 'spd': 60, 'lck': 25}
        self.current_stats = self.base_stats.copy()
        self.team_id = 'A'
        self.is_alive = True

def debug_gravity_well():
    """Debug the gravity_well condition specifically"""
    print("🔍 DEBUGGING GRAVITY WELL")
    print("=" * 40)
    
    system = BattlefieldConditionsSystem()
    success = system.set_active_condition("gravity_well")
    
    if not success:
        print("❌ Failed to activate gravity_well")
        return
    
    condition = system.active_condition
    print(f"📜 {condition.name}")
    print(f"📋 {condition.description}")
    print(f"⚡ Effects: {len(condition.effects)}")
    
    # Test character
    alice = TestCharacter("Alice")
    print(f"\n🎭 Before: Alice SPD = {alice.current_stats['spd']}")
    
    # Check each effect
    for i, effect in enumerate(condition.effects):
        print(f"\nEffect {i+1}:")
        print(f"  Type: {effect.effect_type}")
        print(f"  Target: {effect.target_criteria}")
        print(f"  Description: {effect.description}")
        
        # Check if it has stat modifier method
        if hasattr(effect, 'execute_stat_modifier'):
            print("  ✅ Has execute_stat_modifier method")
            
            # Try to execute it
            result = effect.execute_stat_modifier(alice)
            print(f"  Result: {result}")
            
            if result.get('success'):
                print(f"  🎉 SUCCESS! Alice SPD is now: {alice.current_stats['spd']}")
            else:
                print(f"  ❌ Failed: {result.get('message', 'Unknown error')}")
        else:
            print("  ❌ No execute_stat_modifier method")
    
    print(f"\n🎭 After: Alice SPD = {alice.current_stats['spd']}")

if __name__ == "__main__":
    debug_gravity_well()
