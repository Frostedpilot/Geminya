#!/usr/bin/env python3
"""
Test script to specifically test battlefield conditions with special effects in combat
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_battle_full_system import BattleSimulator

def test_special_effects_in_combat():
    print("🎯 BATTLEFIELD CONDITION SPECIAL EFFECTS IN COMBAT TEST")
    print("=" * 70)
    
    simulator = BattleSimulator()
    
    # Test different special effect conditions
    special_conditions = [
        "thunderous_skies",     # Chain lightning effect
        "phoenix_rebirth",      # Revival effect 
        "vampires_castle",      # Life-steal effect
        "quantum_entanglement", # Shared damage/healing
        "hall_of_mirrors",      # Miss chance
        "chaos_realm"           # Random targeting
    ]
    
    for condition_id in special_conditions:
        print(f"\n🌟 TESTING SPECIAL EFFECTS: {condition_id.replace('_', ' ').title()}")
        print("=" * 70)
        
        # Setup battle
        team_a_configs = [
            ("Fire_Mage", "Mage", 10),
            ("Water_Healer", "Healer", 10)
        ]
        
        team_b_configs = [
            ("Earth_Warrior", "Attacker", 10),
            ("Air_Defender", "Defender", 10)
        ]
        
        simulator.setup_battle(team_a_configs, team_b_configs)
        
        # Apply specific battlefield condition
        print(f"\n🎪 Applying battlefield condition: {condition_id}")
        success = simulator.apply_battlefield_condition(condition_id)
        
        if success:
            print(f"\n⚡ Starting combat to test special effects...")
            
            # Run a few turns to see special effects
            max_turns = 15
            for turn in range(1, max_turns + 1):
                simulator.turn_count = turn
                print(f"\n🔄 Turn {turn}")
                print(f"🌟 Condition: {simulator.active_battlefield_condition.name}")
                print("-" * 30)
                
                current_char = simulator.get_next_character()
                if not current_char:
                    print("No characters available")
                    break
                
                should_continue = simulator.execute_turn(current_char)
                
                # Check victory conditions
                team_a_alive = any(c.is_alive for c in simulator.team_a)
                team_b_alive = any(c.is_alive for c in simulator.team_b)
                
                if not team_a_alive or not team_b_alive:
                    print(f"\n🏆 Battle ended! Team A alive: {team_a_alive}, Team B alive: {team_b_alive}")
                    break
                    
                if not should_continue:
                    break
                    
                # Stop after a few turns to see effects
                if turn >= 10:
                    print(f"\n⏹️ Stopping test after {turn} turns to check next condition")
                    break
        else:
            print(f"❌ Failed to apply condition: {condition_id}")
    
    print("\n" + "=" * 70)
    print("🎉 SPECIAL EFFECTS COMBAT TEST COMPLETE!")

if __name__ == "__main__":
    test_special_effects_in_combat()
