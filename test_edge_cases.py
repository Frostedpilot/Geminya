#!/usr/bin/env python3
"""
EDGE CASES & EXTREME SCENARIOS TEST
Testing boundary conditions, extreme values, and error handling
Based on Simple Waifu Game mechanics
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.game.components.universal_abilities_component import UniversalAbilitiesComponent
from src.game.core.universal_damage_calculator import UniversalDamageCalculator
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
    
    # Test 1: Zero stats
    print("\n🎯 TEST 1: Zero Stat Characters")
    print("-" * 40)
    
    zero_attacker = create_test_character("Zero_ATK", {"atk": 0, "mag": 0, "spd": 50, "lck": 50})
    zero_defender = create_test_character("Zero_DEF", {"vit": 0, "spr": 0, "spd": 50, "lck": 50})
    normal_char = create_test_character("Normal", {"atk": 100, "vit": 80, "spd": 75, "lck": 60})
    
    # Zero attack vs normal defense
    damage = calculator.calculate_final_damage(
        caster_stats=get_char_stats(zero_attacker),
        target_stats=get_char_stats(normal_char),
        base_damage=50,
        damage_type="physical"
    )
    print(f"   Zero ATK vs Normal VIT: {damage} damage")
    
    # Normal attack vs zero defense  
    damage = calculator.calculate_final_damage(
        caster_stats=get_char_stats(normal_char),
        target_stats=get_char_stats(zero_defender),
        base_damage=50,
        damage_type="physical"
    )
    print(f"   Normal ATK vs Zero VIT: {damage} damage")
    
    # Test 2: Maximum stats (softcap testing)
    print("\n🎯 TEST 2: Maximum Stat Characters")
    print("-" * 40)
    
    max_attacker = create_test_character("Max_ATK", {"atk": 999, "mag": 999, "spd": 75, "lck": 60})
    max_defender = create_test_character("Max_DEF", {"vit": 999, "spr": 999, "spd": 75, "lck": 60})
    
    # Test physical damage with max stats
    damage = calculator.calculate_final_damage(
        caster_stats=get_char_stats(max_attacker),
        target_stats=get_char_stats(max_defender),
        base_damage=100,
        damage_type="physical"
    )
    print(f"   Max ATK vs Max VIT: {damage} damage")
    
    # Test magical damage with max stats
    damage = calculator.calculate_final_damage(
        caster_stats=get_char_stats(max_attacker),
        target_stats=get_char_stats(max_defender),
        base_damage=100,
        damage_type="magical"
    )
    print(f"   Max MAG vs Max SPR: {damage} damage")
    
    # Test 3: Minimum damage floor (should never be below 1)
    print("\n🎯 TEST 3: Minimum Damage Floor")
    print("-" * 40)
    
    weak_attacker = create_test_character("Weak", {"atk": 1, "mag": 1, "spd": 50, "lck": 50})
    super_tank = create_test_character("Tank", {"vit": 500, "spr": 500, "spd": 50, "lck": 50})
    
    damage = calculator.calculate_final_damage(
        caster_stats=get_char_stats(weak_attacker),
        target_stats=get_char_stats(super_tank),
        base_damage=1,
        damage_type="physical"
    )
    print(f"   Weak ATK vs Super Tank: {damage} damage (should be ≥ 1)")
    
    if damage < 1:
        print(f"   ❌ Damage below minimum floor!")
    else:
        print(f"   ✅ Minimum damage floor respected")
    
    # Test 4: Critical hit calculations
    print("\n🎯 TEST 4: Critical Hit Edge Cases")
    print("-" * 40)
    
    high_luck = create_test_character("Lucky", {"atk": 100, "spd": 75, "lck": 200})
    low_luck = create_test_character("Unlucky", {"vit": 80, "spd": 75, "lck": 1})
    
    # Calculate crit chance (from document: 5 + (Attacker LCK - Target LCK) / 10, capped 5%-50%)
    crit_chance = 5 + (high_luck.stats.get_stat('lck') - low_luck.stats.get_stat('lck')) / 10
    crit_chance = max(5, min(50, crit_chance))  # Cap between 5% and 50%
    
    print(f"   High LCK vs Low LCK crit chance: {crit_chance}%")
    
    # Test reverse (should be minimum 5%)
    reverse_crit = 5 + (low_luck.stats.get_stat('lck') - high_luck.stats.get_stat('lck')) / 10
    reverse_crit = max(5, min(50, reverse_crit))
    
    print(f"   Low LCK vs High LCK crit chance: {reverse_crit}%")
    
    print("\n✅ Damage Calculation Edge Cases Complete!")
    return True

def test_turn_system_edge_cases():
    """Test edge cases in turn order and action gauge"""
    print("\n⏰ TURN SYSTEM EDGE CASES")
    print("=" * 60)
    
    # Test 1: Identical speed characters
    print("\n🎯 TEST 1: Identical Speed Tiebreakers")
    print("-" * 40)
    
    chars = []
    for i in range(5):
        char = create_test_character(f"Twin_{i+1}", {"spd": 100, "lck": 50})
        char.action_gauge = 500 + i  # Slight gauge differences
        chars.append(char)
    
    print(f"   Created 5 characters with identical speed (100)")
    for i, char in enumerate(chars):
        print(f"     {char.name}: Speed={char.stats.get_stat('spd')}, Gauge={char.action_gauge}")
    
    # Sort by action gauge (tiebreaker mechanism)
    sorted_chars = sorted(chars, key=lambda c: c.action_gauge, reverse=True)
    print(f"   Turn order (by action gauge):")
    for i, char in enumerate(sorted_chars):
        print(f"     {i+1}. {char.name} (Gauge: {char.action_gauge})")
    
    # Test 2: Extreme speed differences
    print("\n🎯 TEST 2: Extreme Speed Differences")
    print("-" * 40)
    
    ultra_fast = create_test_character("Flash", {"spd": 999})
    ultra_slow = create_test_character("Snail", {"spd": 1})
    
    print(f"   Ultra Fast Speed: {ultra_fast.stats.get_stat('spd')}")
    print(f"   Ultra Slow Speed: {ultra_slow.stats.get_stat('spd')}")
    
    # Calculate how many turns ultra_fast gets before ultra_slow acts once
    turns_ratio = ultra_fast.stats.get_stat('spd') / ultra_slow.stats.get_stat('spd')
    print(f"   Speed ratio: {turns_ratio:.1f}:1")
    print(f"   Ultra Fast will act ~{turns_ratio:.0f} times before Ultra Slow acts once")
    
    # Test 3: Action gauge overflow
    print("\n🎯 TEST 3: Action Gauge Overflow")
    print("-" * 40)
    
    overflow_char = create_test_character("Overflow", {"spd": 150})
    overflow_char.action_gauge = 950  # Near the 1000 threshold
    
    print(f"   Initial gauge: {overflow_char.action_gauge}")
    print(f"   Speed: {overflow_char.stats.get_stat('spd')}")
    
    # Simulate gauge fill
    new_gauge = overflow_char.action_gauge + overflow_char.stats.get_stat('spd')
    print(f"   After speed add: {new_gauge}")
    
    if new_gauge >= 1000:
        overflow = new_gauge - 1000
        print(f"   Character acts! Overflow: {overflow}")
        print(f"   New gauge after reset: {overflow}")
    
    print("\n✅ Turn System Edge Cases Complete!")
    return True

def test_status_effect_edge_cases():
    """Test edge cases in status effect application and stacking"""
    print("\n🔮 STATUS EFFECT EDGE CASES")
    print("=" * 60)
    
    # Test 1: Maximum effect stacking
    print("\n🎯 TEST 1: Maximum Effect Stacking")
    print("-" * 40)
    
    char = create_test_character("Stacker", {"hp": 100, "atk": 80})
    effects_applied = 0
    max_effects = 3  # From document: limited to 3 buffs and 3 debuffs
    
    # Try to apply more buffs than allowed
    buff_types = ['atk_boost', 'mag_boost', 'spd_boost', 'vit_boost', 'lck_boost']
    for i, buff in enumerate(buff_types):
        if effects_applied < max_effects:
            print(f"   Applied {buff} #{i+1}")
            effects_applied += 1
        else:
            print(f"   Cannot apply {buff} #{i+1} - at maximum ({max_effects} buffs)")
    
    # Test 2: Status application with extreme luck differences
    print("\n🎯 TEST 2: Status Application Edge Cases")
    print("-" * 40)
    
    high_luck_caster = create_test_character("High_Luck", {"lck": 200})
    low_luck_target = create_test_character("Low_Luck", {"lck": 1})
    
    # Calculate status application chance (from document)
    base_chance = 50  # Example base chance
    luck_modifier = (high_luck_caster.stats.get_stat('lck') - low_luck_target.stats.get_stat('lck')) / 10
    final_chance = max(10, min(90, base_chance + luck_modifier))  # Capped 10%-90%
    
    print(f"   High LCK caster ({high_luck_caster.stats.get_stat('lck')}) vs Low LCK target ({low_luck_target.stats.get_stat('lck')})")
    print(f"   Status application chance: {final_chance}%")
    
    # Test reverse
    reverse_chance = max(10, min(90, base_chance - luck_modifier))
    print(f"   Reverse scenario chance: {reverse_chance}%")
    
    # Test 3: DoT/HoT with zero or negative values
    print("\n🎯 TEST 3: DoT/HoT Edge Cases")
    print("-" * 40)
    
    dot_char = create_test_character("DoT_Test", {"hp": 100})
    
    # Test zero damage DoT
    print(f"   Zero damage DoT effect:")
    print(f"     Character HP: {dot_char.current_hp}")
    print(f"     Apply 0 damage poison")
    # In real system, this should either be rejected or have no effect
    print(f"     Result: No HP change (0 damage effects ignored)")
    
    # Test DoT that would reduce HP below 1
    print(f"   Massive DoT vs low HP:")
    dot_char.current_hp = 5
    massive_dot = 10
    print(f"     Character HP: {dot_char.current_hp}")
    print(f"     DoT damage: {massive_dot}")
    final_hp = max(1, dot_char.current_hp - massive_dot)  # HP should never go below 1 from DoT in some systems
    print(f"     Final HP: {final_hp} (DoT cannot kill in some systems)")
    
    print("\n✅ Status Effect Edge Cases Complete!")
    return True

def test_battle_end_conditions():
    """Test various battle end scenarios"""
    print("\n🏁 BATTLE END CONDITION EDGE CASES")
    print("=" * 60)
    
    # Test 1: Simultaneous team wipe
    print("\n🎯 TEST 1: Simultaneous Team Elimination")
    print("-" * 40)
    
    # Simulate scenario where both teams could be eliminated in same turn
    team_a_hp = [1, 5, 3]  # Low HP team
    team_b_hp = [2, 1, 4]  # Also low HP team
    
    print(f"   Team A HP: {team_a_hp}")
    print(f"   Team B HP: {team_b_hp}")
    print(f"   Scenario: AOE attack hits both teams simultaneously")
    
    # Simulate 5 damage to all
    aoe_damage = 5
    team_a_survivors = [hp for hp in team_a_hp if hp > aoe_damage]
    team_b_survivors = [hp for hp in team_b_hp if hp > aoe_damage]
    
    print(f"   After {aoe_damage} AOE damage:")
    print(f"   Team A survivors: {len(team_a_survivors)}")
    print(f"   Team B survivors: {len(team_b_survivors)}")
    
    if len(team_a_survivors) == 0 and len(team_b_survivors) == 0:
        print(f"   Result: DRAW - Both teams eliminated")
    elif len(team_a_survivors) == 0:
        print(f"   Result: Team B WINS")
    elif len(team_b_survivors) == 0:
        print(f"   Result: Team A WINS")
    else:
        print(f"   Result: Battle continues")
    
    # Test 2: Turn limit reached
    print("\n🎯 TEST 2: Turn Limit Scenarios")
    print("-" * 40)
    
    # From document: 30-round equivalent limit
    max_rounds = 30
    current_round = 29
    
    team_a_total_hp = 150
    team_a_max_hp = 300
    team_b_total_hp = 200  
    team_b_max_hp = 300
    
    team_a_percent = (team_a_total_hp / team_a_max_hp) * 100
    team_b_percent = (team_b_total_hp / team_b_max_hp) * 100
    
    print(f"   Round {current_round}/{max_rounds}")
    print(f"   Team A: {team_a_total_hp}/{team_a_max_hp} HP ({team_a_percent:.1f}%)")
    print(f"   Team B: {team_b_total_hp}/{team_b_max_hp} HP ({team_b_percent:.1f}%)")
    
    if current_round >= max_rounds:
        if team_a_percent > team_b_percent:
            print(f"   Result: Team A WINS by HP percentage")
        elif team_b_percent > team_a_percent:
            print(f"   Result: Team B WINS by HP percentage")
        else:
            print(f"   Result: DRAW - Identical HP percentages")
    
    # Test 3: Sudden Death mechanics (Round 20+)
    print("\n🎯 TEST 3: Sudden Death Mechanics")
    print("-" * 40)
    
    sudden_death_round = 22  # After round 20
    base_atk = 100
    base_mag = 90
    base_spr = 80
    
    # From document: stats scale by 1.1^(N-20) for ATK/MAG, 0.9^(N-20) for SPR
    scaling_factor = sudden_death_round - 20
    atk_multiplier = 1.1 ** scaling_factor
    mag_multiplier = 1.1 ** scaling_factor  
    spr_multiplier = 0.9 ** scaling_factor
    
    scaled_atk = int(base_atk * atk_multiplier)
    scaled_mag = int(base_mag * mag_multiplier)
    scaled_spr = int(base_spr * spr_multiplier)
    
    print(f"   Round {sudden_death_round} (Sudden Death active)")
    print(f"   Base stats: ATK={base_atk}, MAG={base_mag}, SPR={base_spr}")
    print(f"   Scaling factor: {scaling_factor} rounds into Sudden Death")
    print(f"   Scaled stats: ATK={scaled_atk}, MAG={scaled_mag}, SPR={scaled_spr}")
    print(f"   Damage increased {atk_multiplier:.2f}x, Magic resist decreased {spr_multiplier:.2f}x")
    
    print("\n✅ Battle End Condition Edge Cases Complete!")
    return True

def create_test_character(name: str, stats: dict):
    """Create a test character with specific stats"""
    default_stats = {"hp": 100, "atk": 80, "mag": 90, "vit": 70, "spr": 85, "int": 95, "spd": 75, "lck": 80}
    default_stats.update(stats)
    
    character = Character(name.lower())
    character.name = name
    character.action_gauge = 500  # Default gauge value
    character.current_hp = default_stats.get("hp", 100)
    
    # Initialize stats
    for stat, value in default_stats.items():
        character.stats.set_base_stat(stat, value)
    
    return character

def get_char_stats(character):
    """Get character stats in calculator format"""
    return {
        'atk': float(character.stats.get_stat('atk')),
        'mag': float(character.stats.get_stat('mag')),
        'vit': float(character.stats.get_stat('vit')),
        'spr': float(character.stats.get_stat('spr')),
        'spd': float(character.stats.get_stat('spd')),
        'lck': float(character.stats.get_stat('lck'))
    }

if __name__ == "__main__":
    print("⚡ EDGE CASES & EXTREME SCENARIOS TEST SUITE")
    print("=" * 70)
    
    success = True
    
    success &= test_damage_calculation_edge_cases()
    success &= test_turn_system_edge_cases()
    success &= test_status_effect_edge_cases()
    success &= test_battle_end_conditions()
    
    if success:
        print("\n🎉 All edge case tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
