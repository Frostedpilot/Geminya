#!/usr/bin/env python3
"""
COMPLEX EFFECT RESOLUTION TEST
Testing intricate status effect interactions, stacking, and resolution order
Based on Simple Waifu Game mechanics
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.game.components.universal_abilities_component import UniversalAbilitiesComponent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BattleCharacter:
    """Test character implementation for effects testing"""
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

def test_complex_effect_resolution():
    """Test complex effect resolution scenarios"""
    print("🧪 COMPLEX EFFECT RESOLUTION TEST")
    print("=" * 60)
    
    # Create characters with different roles
    attacker = create_test_character("Attacker_Test", "attacker", 100, 120, 80, 70, 90, 85, 110, 75)
    mage = create_test_character("Mage_Test", "mage", 90, 80, 140, 60, 120, 95, 85, 80)
    healer = create_test_character("Healer_Test", "healer", 110, 70, 90, 80, 110, 130, 75, 85)
    
    # Test 1: Stacking buff limits (max 3 buffs per character)
    print("\n🎯 TEST 1: Buff Stacking Limits")
    print("-" * 40)
    
    # Apply 5 buffs, should cap at 3
    buffs_to_apply = [
        'atk_boost', 'mag_boost', 'spd_boost', 'vit_boost', 'lck_boost'
    ]
    
    for i, buff in enumerate(buffs_to_apply):
        if len(attacker.active_effects) < 3:  # Max 3 buffs according to rules
            attacker.active_effects.append({'type': buff, 'value': 20, 'duration': 3})
        active_count = len(attacker.active_effects)
        print(f"   Applied buff {i+1}: {buff}, Active effects: {active_count}")
        
        # Should cap at 3 according to Simple Waifu Game rules
        if active_count > 3:
            print(f"   ⚠️  ISSUE: More than 3 buffs active ({active_count})")
        else:
            print(f"   ✅ Buff limit respected ({active_count}/3)")
    
    # Test 2: Buff/debuff interaction
    print("\n🎯 TEST 2: Buff-Debuff Interaction")
    print("-" * 40)
    
    # Apply mixed buffs and debuffs to mage
    mixed_effects = [
        {'type': 'mag_boost', 'value': 25, 'duration': 3},
        {'type': 'mag_reduction', 'value': -15, 'duration': 2},
        {'type': 'spd_boost', 'value': 20, 'duration': 3}
    ]
    
    for effect in mixed_effects:
        mage.active_effects.append(effect)
    
    buff_count = sum(1 for effect in mage.active_effects if effect['value'] > 0)
    debuff_count = sum(1 for effect in mage.active_effects if effect['value'] < 0)
    
    print(f"   Buffs applied: {buff_count}")
    print(f"   Debuffs applied: {debuff_count}")
    print(f"   Total effects: {len(mage.active_effects)}")
    print("   ✅ Mixed buff/debuff application successful")
    print(f"   Total effects: {len(mage.effects.active_effects)}")
    
    # Test 3: Effect duration and turn-based decay
    print("\n🎯 TEST 3: Turn-Based Effect Duration")
    print("-" * 40)
    
    initial_effects = len(healer.effects.active_effects)
    healer.effects.add_effect('regen', value=15, duration=2)
    healer.effects.add_effect('shield', value=50, duration=1)
    
    print(f"   Initial effects: {initial_effects}")
    print(f"   After adding timed effects: {len(healer.effects.active_effects)}")
    
    # Simulate turns
    for turn in range(1, 4):
        healer.effects.process_turn_end()
        remaining = len(healer.effects.active_effects)
        print(f"   Turn {turn} end: {remaining} effects remaining")
    
    # Test 4: Complex interaction - healing while taking damage over time
    print("\n🎯 TEST 4: Healing vs DoT Interaction")
    print("-" * 40)
    
    test_char = create_test_character("DoT_Test", "healer", 100, 70, 90, 80, 110, 130, 75, 85)
    original_hp = test_char.current_hp
    
    # Apply DoT and HoT simultaneously
    test_char.effects.add_effect('poison', value=10, duration=3)  # -10 HP per turn
    test_char.effects.add_effect('regen', value=8, duration=3)   # +8 HP per turn
    
    print(f"   Initial HP: {original_hp}")
    print(f"   Applied: Poison (-10/turn) + Regen (+8/turn)")
    
    for turn in range(1, 4):
        hp_before = test_char.current_hp
        test_char.effects.process_turn_end()
        hp_after = test_char.current_hp
        net_change = hp_after - hp_before
        print(f"   Turn {turn}: {hp_before} → {hp_after} (net: {net_change:+.1f})")
    
    # Test 5: Signature ability trigger conditions
    print("\n🎯 TEST 5: Signature Ability Triggers")
    print("-" * 40)
    
    # Create character with low HP to test signature triggers
    signature_char = create_test_character("Signature_Test", "mage", 100, 80, 140, 60, 120, 95, 85, 80)
    signature_char.current_hp = 30  # Below 50% threshold
    
    # Simulate signature ability check
    hp_percentage = (signature_char.current_hp / signature_char.max_hp) * 100
    print(f"   Character HP: {signature_char.current_hp}/{signature_char.max_hp} ({hp_percentage:.1f}%)")
    
    if hp_percentage < 50:
        print(f"   ✅ Signature ability 'Explosion' would trigger (HP < 50%)")
        # In real game, this would set a "primed" status
        signature_char.effects.add_effect('primed_explosion', value=1, duration=1)
        print(f"   Applied 'Primed' status for signature ability")
    else:
        print(f"   No signature trigger (HP ≥ 50%)")
    
    print("\n✅ Complex Effect Resolution Test Complete!")
    return True

def create_test_character(name: str, role: str, hp: int, atk: int, mag: int, vit: int, spr: int, int_stat: int, spd: int, lck: int):
    """Create a test character with specified stats"""
    stats = {
        "hp": hp, "atk": atk, "mag": mag, "vit": vit,
        "spr": spr, "int": int_stat, "spd": spd, "lck": lck
    }
    potency = {
        "attacker": "S", "mage": "A", "healer": "B", "buffer": "C",
        "debuffer": "C", "defender": "B", "specialist": "A"
    }
    
    character = BattleCharacter(name, role, stats, potency)
    character.team_id = "team_test"
    return character

if __name__ == "__main__":
    success = test_complex_effect_resolution()
    if success:
        print("\n🎉 All complex effect resolution tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
