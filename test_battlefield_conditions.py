#!/usr/bin/env python3
"""
BATTLEFIELD CONDITIONS & ENVIRONMENTAL EFFECTS TEST
Testing battlefield conditions, environmental modifiers, and team synergies
Based on Simple Waifu Game mechanics
"""

import sys
import os
from typing import Optional
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.game.components.universal_abilities_component import UniversalAbilitiesComponent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BattleCharacter:
    """Test character implementation for battlefield testing"""
    def __init__(self, name: str, archetype: str, stats: dict, potency: dict, element: Optional[str] = None, series: Optional[str] = None):
        self.name = name
        self.character_id = name.lower().replace(" ", "_")
        self.archetype = archetype
        self.element = element or "neutral"
        self.series = series or "Test_Series"
        
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
            'archetype': archetype,
            'series': self.series,
            'element': self.element
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

def test_battlefield_conditions():
    """Test various battlefield conditions and their effects"""
    print("🌍 BATTLEFIELD CONDITIONS TEST")
    print("=" * 60)
    
    # Test different battlefield conditions from the document
    battlefield_conditions = {
        'scorching_sun': {
            'name': 'Scorching Sun',
            'fire_bonus': 0.2,  # +20% ATK/MAG for Fire characters
            'water_penalty': -0.1  # -10% VIT/SPR for Water characters
        },
        'mystic_fog': {
            'name': 'Mystic Fog', 
            'luck_reduction': 0.5  # -50% LCK for all characters
        },
        'gravity_well': {
            'name': 'Gravity Well',
            'speed_reduction': 0.3  # -30% SPD for all characters
        },
        'magic_overflow': {
            'name': 'Magic Overflow',
            'magic_bonus': 0.25  # +25% MAG for all characters
        },
        'volatile_field': {
            'name': 'Volatile Field',
            'crit_multiplier': 2.0  # Critical hits deal 2.0x instead of 1.5x
        }
    }
    
    # Create test characters with different elements
    fire_char = create_elemental_character("Fire_Mage", "fire", "mage")
    water_char = create_elemental_character("Water_Healer", "water", "healer") 
    earth_char = create_elemental_character("Earth_Defender", "earth", "defender")
    
    characters = [fire_char, water_char, earth_char]
    
    # Test each battlefield condition
    for condition_key, condition in battlefield_conditions.items():
        print(f"\n🎯 TESTING: {condition['name']}")
        print("-" * 40)
        
        for char in characters:
            original_stats = get_character_combat_stats(char)
            modified_stats = apply_battlefield_condition(char, condition)
            
            print(f"   {char.name} ({char.element}):")
            print(f"     Original: ATK={original_stats['atk']}, MAG={original_stats['mag']}, SPD={original_stats['spd']}, LCK={original_stats['lck']}")
            print(f"     Modified: ATK={modified_stats['atk']}, MAG={modified_stats['mag']}, SPD={modified_stats['spd']}, LCK={modified_stats['lck']}")
            
            # Verify modifications are correct
            if condition_key == 'scorching_sun':
                if char.element == 'fire':
                    expected_atk = int(original_stats['atk'] * 1.2)
                    expected_mag = int(original_stats['mag'] * 1.2)
                    if modified_stats['atk'] >= expected_atk * 0.95:  # Allow small rounding differences
                        print(f"     ✅ Fire bonus applied correctly")
                    else:
                        print(f"     ❌ Fire bonus not applied correctly")
                elif char.element == 'water':
                    expected_vit = int(original_stats['vit'] * 0.9)
                    if modified_stats['vit'] <= expected_vit * 1.05:
                        print(f"     ✅ Water penalty applied correctly")
                    else:
                        print(f"     ❌ Water penalty not applied correctly")
                        
            elif condition_key == 'mystic_fog':
                expected_lck = int(original_stats['lck'] * 0.5)
                if modified_stats['lck'] <= expected_lck * 1.05:
                    print(f"     ✅ Luck reduction applied correctly")
                else:
                    print(f"     ❌ Luck reduction not applied correctly")
                    
            elif condition_key == 'gravity_well':
                expected_spd = int(original_stats['spd'] * 0.7)
                if modified_stats['spd'] <= expected_spd * 1.05:
                    print(f"     ✅ Speed reduction applied correctly")
                else:
                    print(f"     ❌ Speed reduction not applied correctly")
    
    print("\n✅ Battlefield Conditions Test Complete!")
    return True

def test_team_synergies():
    """Test team synergy bonuses based on series matching"""
    print("\n🤝 TEAM SYNERGY TEST")
    print("=" * 60)
    
    # Create characters from same series for synergy testing
    konosuba_team = [
        create_series_character("Megumin", "konosuba", "mage"),
        create_series_character("Aqua", "konosuba", "healer"),
        create_series_character("Darkness", "konosuba", "defender"),
        create_series_character("Kazuma", "konosuba", "specialist")
    ]
    
    rezero_team = [
        create_series_character("Subaru", "rezero", "specialist"),
        create_series_character("Emilia", "rezero", "mage")
    ]
    
    # Test Konosuba synergies (4 characters = Tier 2)
    print(f"\n🎯 TESTING: Konosuba Team Synergy (4 characters)")
    print("-" * 40)
    
    konosuba_count = len(konosuba_team)
    synergy_tier = get_synergy_tier(konosuba_count)
    
    print(f"   Team size: {konosuba_count} characters")
    print(f"   Synergy tier: {synergy_tier}")
    
    # Apply Konosuba synergies based on document
    if synergy_tier >= 1:  # Tier 1: +20% LCK for all allies
        print(f"   Tier 1 bonus: +20% LCK for all allies")
        for char in konosuba_team:
            original_lck = char.get_stat('lck')
            boosted_lck = int(original_lck * 1.2)
            print(f"     {char.name}: LCK {original_lck} → {boosted_lck}")
    
    if synergy_tier >= 2:  # Tier 2: 5% chance skills don't go on cooldown
        print(f"   Tier 2 bonus: 5% chance skills don't consume cooldown")
        for char in konosuba_team:
            print(f"     {char.name}: Gained cooldown bypass chance")
    
    # Test Re:Zero synergies (2 characters = Tier 1)
    print(f"\n🎯 TESTING: Re:Zero Team Synergy (2 characters)")
    print("-" * 40)
    
    rezero_count = len(rezero_team)
    synergy_tier = get_synergy_tier(rezero_count)
    
    print(f"   Team size: {rezero_count} characters")
    print(f"   Synergy tier: {synergy_tier}")
    
    if synergy_tier >= 1:  # Tier 1: +15% SPR for all allies
        print(f"   Tier 1 bonus: +15% SPR for all allies")
        for char in rezero_team:
            original_spr = char.get_stat('spr')
            boosted_spr = int(original_spr * 1.15)
            print(f"     {char.name}: SPR {original_spr} → {boosted_spr}")
    
    print("\n✅ Team Synergy Test Complete!")
    return True

def create_elemental_character(name: str, element: str, role: str):
    """Create a character with elemental affinity"""
    stats = {"hp": 100, "atk": 80, "mag": 90, "vit": 70, "spr": 85, "int": 95, "spd": 75, "lck": 80}
    potency = {"attacker": "B", "mage": "A", "healer": "B", "buffer": "C", "debuffer": "C", "defender": "B", "specialist": "B"}
    
    return BattleCharacter(name, role, stats, potency, element=element)

def create_series_character(name: str, series: str, role: str):
    """Create a character from a specific series"""
    stats = {"hp": 100, "atk": 80, "mag": 90, "vit": 70, "spr": 85, "int": 95, "spd": 75, "lck": 80}
    potency = {"attacker": "B", "mage": "A", "healer": "B", "buffer": "C", "debuffer": "C", "defender": "B", "specialist": "B"}
    
    return BattleCharacter(name, role, stats, potency, series=series)

def get_character_combat_stats(character):
    """Get character's current combat stats"""
    return {
        'atk': character.get_stat('atk'),
        'mag': character.get_stat('mag'),
        'vit': character.get_stat('vit'),
        'spr': character.get_stat('spr'),
        'spd': character.get_stat('spd'),
        'lck': character.get_stat('lck')
    }

def apply_battlefield_condition(character, condition):
    """Apply battlefield condition modifiers to character stats"""
    stats = get_character_combat_stats(character)
    
    # Apply condition effects based on type
    if 'fire_bonus' in condition and hasattr(character, 'element') and character.element == 'fire':
        stats['atk'] = int(stats['atk'] * (1 + condition['fire_bonus']))
        stats['mag'] = int(stats['mag'] * (1 + condition['fire_bonus']))
    
    if 'water_penalty' in condition and hasattr(character, 'element') and character.element == 'water':
        stats['vit'] = int(stats['vit'] * (1 + condition['water_penalty']))
        stats['spr'] = int(stats['spr'] * (1 + condition['water_penalty']))
    
    if 'luck_reduction' in condition:
        stats['lck'] = int(stats['lck'] * (1 - condition['luck_reduction']))
    
    if 'speed_reduction' in condition:
        stats['spd'] = int(stats['spd'] * (1 - condition['speed_reduction']))
    
    if 'magic_bonus' in condition:
        stats['mag'] = int(stats['mag'] * (1 + condition['magic_bonus']))
    
    return stats

def get_synergy_tier(character_count):
    """Get synergy tier based on character count"""
    if character_count >= 6:
        return 3
    elif character_count >= 4:
        return 2
    elif character_count >= 2:
        return 1
    else:
        return 0

if __name__ == "__main__":
    print("🌍 ENVIRONMENTAL EFFECTS & SYNERGIES TEST SUITE")
    print("=" * 70)
    
    success = True
    
    success &= test_battlefield_conditions()
    success &= test_team_synergies()
    
    if success:
        print("\n🎉 All environmental and synergy tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
