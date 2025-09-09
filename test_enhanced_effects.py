"""
Test Enhanced Ability Effects from Battlefield Conditions
Tests Atlantis Depths and Dragon's Lair enhanced effects
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_battle_full_system import BattleSimulator

def test_enhanced_effects():
    """Test enhanced ability effects from battlefield conditions"""
    print("🔮 TESTING ENHANCED ABILITY EFFECTS")
    print("=" * 50)
    
    # Create battle simulator
    battle = BattleSimulator()
    
    # Setup teams
    team_a = [("Test_Mage", "Mage", 3)]
    team_b = [("Test_Warrior", "Attacker", 3)]
    
    battle.setup_battle(team_a, team_b)
    
    # Test Atlantis Depths (enhanced effects due to magical pressure)
    print("\n🧜‍♀️ TESTING ATLANTIS DEPTHS")
    print("-" * 30)
    battle.apply_battlefield_condition("atlantis_depths")
    
    # Get characters
    mage = battle.team_a[0]
    warrior = battle.team_b[0]
    
    # Check enhanced effect multiplier
    mage_multiplier = mage.get_enhanced_effect_multiplier()
    warrior_multiplier = warrior.get_enhanced_effect_multiplier()
    
    print(f"Mage enhancement multiplier: {mage_multiplier}")
    print(f"Warrior enhancement multiplier: {warrior_multiplier}")
    
    # Test Dragon's Lair (enhanced range and area effects)
    print("\n🐉 TESTING DRAGON'S LAIR")
    print("-" * 30)
    battle.apply_battlefield_condition("dragons_lair")
    
    # Check enhanced effect multiplier
    mage_multiplier_dragon = mage.get_enhanced_effect_multiplier()
    warrior_multiplier_dragon = warrior.get_enhanced_effect_multiplier()
    
    print(f"Mage enhancement multiplier (Dragon's Lair): {mage_multiplier_dragon}")
    print(f"Warrior enhancement multiplier (Dragon's Lair): {warrior_multiplier_dragon}")
    
    # Run a few turns to see effects in action
    print("\n⚔️ BATTLE DEMONSTRATION")
    print("-" * 30)
    
    # Reset battle
    battle = BattleSimulator()
    battle.setup_battle(team_a, team_b)
    battle.apply_battlefield_condition("atlantis_depths")
    
    # Run a few turns
    for turn in range(3):
        battle.turn_count += 1
        print(f"\n🔄 Turn {battle.turn_count}")
        
        # Get next character
        current_character = battle.get_next_character()
        if current_character:
            battle.execute_turn(current_character)
        
        # Check if battle ended
        victor = battle.check_victory()
        if victor:
            print(f"🏆 {victor} wins!")
            break

if __name__ == "__main__":
    test_enhanced_effects()
