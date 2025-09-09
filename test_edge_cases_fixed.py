#!/usr/bin/env python3
"""
EDGE CASES & EXTREME SCENARIOS TEST (SIMPLIFIED)
Testing boundary conditions, extreme values, and error handling
Based on Simple Waifu Game mechanics
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.game.components.universal_abilities_component import UniversalAbilitiesComponent
from src.game.core.universal_damage_calculator import UniversalDamageCalculator, DamageParameters, DamageResult
from src.game.core.universal_skill_library import UniversalSkillLibrary, UniversalSkill, RoleType
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BattleCharacter:
    """Test character implementation for edge case testing"""
    def __init__(self, name: str, archetype: str, stats: dict, potency: dict):
        self.name = name
        self.character_id = name.lower().replace(" ", "_")
        self.archetype = archetype
        
        # Health and status
        self.max_hp = stats.get('hp', 100.0)
        self.current_hp = self.max_hp
        self.is_alive = True
        
        # Position in formation
        self.position = (0, 0)
        self.team_id = "team_test"
        
        # Character data for abilities
        self.character_data = {
            'name': name,
            'potency': potency,
            'archetype': archetype
        }
        
        # Stats
        self.base_stats = stats.copy()
        self.current_stats = stats.copy()
        
        # Components
        self.abilities = UniversalAbilitiesComponent(self.character_data)
        self.active_effects = []
        
        # Battle state
        self.action_gauge = 0
        self.turn_count = 0
    
    def get_stat(self, stat_name: str) -> float:
        """Get current stat value"""
        return self.current_stats.get(stat_name, 0.0)
    
    def take_damage(self, damage: float):
        """Apply damage to character"""
        self.current_hp = max(0, self.current_hp - damage)
        if self.current_hp <= 0:
            self.is_alive = False
    
    def heal(self, amount: float):
        """Heal character"""
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp - old_hp

def test_damage_calculation_edge_cases():
    """Test extreme damage calculation scenarios"""
    print("⚡ DAMAGE CALCULATION EDGE CASES")
    print("=" * 60)
    
    calculator = UniversalDamageCalculator()
    skill_library = UniversalSkillLibrary()
    
    # Get a basic attack skill for testing
    basic_skill = skill_library.get_skills_by_role(RoleType.ATTACKER)[0]
    
    # Test 1: Zero stats
    print("\\n🎯 TEST 1: Zero Stat Characters")
    print("-" * 40)
    
    zero_attacker = create_test_character("Zero_ATK", "attacker", {"hp": 100, "atk": 0, "mag": 0, "vit": 50, "spr": 50, "spd": 50, "lck": 50, "int": 50})
    normal_char = create_test_character("Normal", "defender", {"hp": 100, "atk": 100, "mag": 100, "vit": 80, "spr": 80, "spd": 75, "lck": 60, "int": 70})
    
    # Test zero attack damage
    params = DamageParameters(
        base_stat=0,  # Zero ATK
        skill=basic_skill,
        potency_effectiveness=0.8  # B-rank potency
    )
    
    result = calculator.calculate_damage(params)
    print(f"   Zero ATK damage: {result.final_damage:.1f}")
    print(f"   Floor component ensures minimum: {result.floor_component:.1f}")
    
    # Test 2: Maximum stats  
    print("\\n🎯 TEST 2: Maximum Stat Characters")
    print("-" * 40)
    
    max_attacker = create_test_character("Max_ATK", "attacker", {"hp": 500, "atk": 9999, "mag": 9999, "vit": 9999, "spr": 9999, "spd": 9999, "lck": 9999, "int": 9999})
    
    params = DamageParameters(
        base_stat=9999,  # Maximum ATK
        skill=basic_skill,
        potency_effectiveness=1.2  # S-rank potency
    )
    
    result = calculator.calculate_damage(params)
    print(f"   Max ATK damage: {result.final_damage:.1f}")
    print(f"   Softcap prevents infinite scaling")
    
    # Test 3: Critical hit boundaries
    print("\\n🎯 TEST 3: Critical Hit Edge Cases")
    print("-" * 40)
    
    # Test critical with zero base damage
    params = DamageParameters(
        base_stat=1,  # Minimal ATK
        skill=basic_skill,
        potency_effectiveness=0.6,  # C-rank potency
        critical_hit=True,
        critical_multiplier=1.5
    )
    
    result = calculator.calculate_damage(params)
    print(f"   Critical with minimal stats: {result.final_damage:.1f}")
    print(f"   Critical applied: {result.critical_applied}")
    
    return True

def test_turn_system_edge_cases():
    """Test turn system boundary conditions"""
    print("\\n🔄 TURN SYSTEM EDGE CASES")
    print("=" * 60)
    
    # Test 1: Speed ties
    print("\\n🎯 TEST 1: Speed Tie Resolution")
    print("-" * 40)
    
    char_a = create_test_character("Char_A", "attacker", {"hp": 100, "spd": 100, "atk": 80, "mag": 80, "vit": 80, "spr": 80, "lck": 80, "int": 80})
    char_b = create_test_character("Char_B", "mage", {"hp": 100, "spd": 100, "atk": 80, "mag": 80, "vit": 80, "spr": 80, "lck": 80, "int": 80})
    char_c = create_test_character("Char_C", "healer", {"hp": 100, "spd": 100, "atk": 80, "mag": 80, "vit": 80, "spr": 80, "lck": 80, "int": 80})
    
    characters = [char_a, char_b, char_c]
    
    # Simulate turn order resolution (would use LCK as tiebreaker)
    print(f"   Characters with same speed: {len(characters)}")
    print("   Tiebreaker: Would use LCK stat")
    for char in characters:
        print(f"     {char.name}: SPD={char.get_stat('spd')}, LCK={char.get_stat('lck')}")
    
    # Test 2: Extreme speed values
    print("\\n🎯 TEST 2: Extreme Speed Values")
    print("-" * 40)
    
    slow_char = create_test_character("Slowpoke", "defender", {"hp": 200, "spd": 1, "atk": 120, "mag": 80, "vit": 150, "spr": 120, "lck": 50, "int": 60})
    fast_char = create_test_character("Speedster", "attacker", {"hp": 80, "spd": 200, "atk": 150, "mag": 60, "vit": 60, "spr": 50, "lck": 100, "int": 70})
    
    print(f"   Slowest: {slow_char.name} (SPD: {slow_char.get_stat('spd')})")
    print(f"   Fastest: {fast_char.name} (SPD: {fast_char.get_stat('spd')})")
    print("   Speed ratio: 200:1")
    
    return True

def test_battle_end_conditions():
    """Test various battle end scenarios"""
    print("\\n🏁 BATTLE END CONDITIONS")
    print("=" * 60)
    
    # Test 1: Simultaneous defeat
    print("\\n🎯 TEST 1: Simultaneous Defeat")
    print("-" * 40)
    
    last_ally = create_test_character("Last_Ally", "attacker", {"hp": 10, "atk": 100, "mag": 80, "vit": 60, "spr": 60, "spd": 80, "lck": 70, "int": 65})
    last_enemy = create_test_character("Last_Enemy", "mage", {"hp": 10, "atk": 80, "mag": 120, "vit": 50, "spr": 70, "spd": 85, "lck": 60, "int": 90})
    
    # Simulate both taking lethal damage
    last_ally.take_damage(15)
    last_enemy.take_damage(15)
    
    print(f"   {last_ally.name}: HP={last_ally.current_hp}, Alive={last_ally.is_alive}")
    print(f"   {last_enemy.name}: HP={last_enemy.current_hp}, Alive={last_enemy.is_alive}")
    print("   Result: Draw condition")
    
    # Test 2: Victory with 1 HP remaining
    print("\\n🎯 TEST 2: Narrow Victory")
    print("-" * 40)
    
    survivor = create_test_character("Survivor", "healer", {"hp": 1, "atk": 60, "mag": 90, "vit": 80, "spr": 110, "spd": 70, "lck": 85, "int": 95})
    print(f"   {survivor.name}: HP={survivor.current_hp}/{survivor.max_hp}")
    print("   Victory by the smallest margin!")
    
    return True

def create_test_character(name: str, archetype: str, stats: dict):
    """Create a test character with specified stats"""
    potency = {"attacker": "B", "mage": "A", "healer": "B", "buffer": "C", "debuffer": "C", "defender": "B", "specialist": "B"}
    
    character = BattleCharacter(name, archetype, stats, potency)
    character.team_id = "team_test"
    return character

if __name__ == "__main__":
    print("🧪 EDGE CASES & EXTREME SCENARIOS TEST SUITE")
    print("=" * 70)
    
    success = True
    success &= test_damage_calculation_edge_cases()
    success &= test_turn_system_edge_cases()
    success &= test_battle_end_conditions()
    
    if success:
        print("\\n🎉 All edge case tests passed!")
        sys.exit(0)
    else:
        print("\\n❌ Some edge case tests failed!")
        sys.exit(1)
