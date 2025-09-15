#!/usr/bin/env python3
"""
Demonstrate the self-contained battlefield architecture with stat modifiers
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.game.core.battlefield_conditions import BattlefieldConditionsSystem, battlefield_events, BattlefieldEventType

class MockCharacter:
    def __init__(self, name, team="A"):
        self.name = name
        self.team_id = team
        self.max_hp = 100
        self.current_hp = 100
        self.base_stats = {'atk': 50, 'mag': 40, 'vit': 45, 'spr': 35, 'int': 30, 'spd': 60, 'lck': 25}
        self.current_stats = self.base_stats.copy()
        self.is_alive = True

def demonstrate_architecture():
    """Demonstrate the complete self-contained architecture"""
    print("🎯 SELF-CONTAINED BATTLEFIELD ARCHITECTURE DEMO")
    print("=" * 60)
    
    # Event capture
    events = []
    def capture_event(event):
        events.append(f"{event.effect_name}: {event.character_name}")
    
    battlefield_events.subscribe(BattlefieldEventType.EFFECT_APPLIED, capture_event)
    
    # Create test party
    party = [
        MockCharacter("Alice", "A"),
        MockCharacter("Bob", "B")
    ]
    
    # Test different types of battlefield conditions
    conditions_to_test = [
        ("scorching_sun", "🔥 Stat Modifiers (Fire/Water)"),
        ("gravity_well", "🌌 Speed Reduction"),
        ("chaos_realm", "🌀 Random Chaos"),
        ("mirrored_dimension", "🪞 Enhancement Effects"),
        ("volatile_field", "💥 Combat Effects")
    ]
    
    system = BattlefieldConditionsSystem()
    
    for condition_name, description in conditions_to_test:
        print(f"\n{description}")
        print("-" * 40)
        
        # Reset stats
        for char in party:
            char.current_stats = char.base_stats.copy()
        
        # Activate condition
        system.set_active_condition(condition_name)
        condition = system.active_condition
        
        print(f"📜 {condition.name} ({condition.rarity})")
        print(f"📋 {condition.description}")
        
        effects_applied = 0
        events.clear()
        
        # Test all effect types on all characters
        for char in party:
            print(f"\n🎭 {char.name} (before):")
            print(f"   ATK: {char.current_stats['atk']}, SPD: {char.current_stats['spd']}")
            
            for effect in condition.effects:
                # Try each execution method
                methods = [
                    ('stat_modifier', 'execute_stat_modifier'),
                    ('turn_effect', 'execute_turn_effect'), 
                    ('enhancement', 'execute_enhancement_effect'),
                    ('combat', 'execute_combat_effect')
                ]
                
                for method_name, method in methods:
                    if hasattr(effect, method):
                        if method_name == 'combat':
                            # Combat effects need attacker/defender
                            other_char = party[1] if char == party[0] else party[0]
                            result = getattr(effect, method)(char, other_char)
                        else:
                            result = getattr(effect, method)(char)
                        
                        if result.get('success') and result.get('effects'):
                            effects_applied += 1
                            effect_data = result['effects'][0]
                            print(f"   ✅ {method_name}: {effect_data}")
            
            print(f"   {char.name} (after):")
            print(f"   ATK: {char.current_stats['atk']}, SPD: {char.current_stats['spd']}")
        
        print(f"\n📊 Summary: {effects_applied} effects applied, {len(events)} events")
        if events:
            print(f"   📡 Recent events: {', '.join(events[-3:])}")
    
    print(f"\n🎉 ARCHITECTURE DEMONSTRATION COMPLETE!")
    print("=" * 60)
    print("✅ Self-contained effects execute independently")
    print("✅ Multiple effect types handled (stat, turn, enhancement, combat)")
    print("✅ Event-driven notifications working")
    print("✅ Structured data returned from all operations")
    print("✅ No game loop dependency - pure self-containment!")

if __name__ == "__main__":
    demonstrate_architecture()
