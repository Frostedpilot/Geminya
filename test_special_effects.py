#!/usr/bin/env python3
"""
Test script to check if special effects from battlefield conditions are being applied
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game.core.battlefield_conditions import battlefield_conditions_system

class TestCharacter:
    def __init__(self, name, base_stats):
        self.name = name
        self.character_id = name.lower()
        self.base_stats = base_stats.copy()
        self.current_stats = base_stats.copy()
        self.battlefield_special_rules = []
        
    def get_elements(self):
        return ["fire"] if "fire" in self.name.lower() else ["neutral"]
        
    def apply_stat_modifier(self, stat_name: str, modifier_value: float, modifier_type: str):
        """Apply battlefield condition stat modifier"""
        old_value = self.current_stats[stat_name]
        if modifier_type == "percentage":
            self.current_stats[stat_name] = self.base_stats[stat_name] * (1 + modifier_value)
        else:  # flat
            self.current_stats[stat_name] = self.base_stats[stat_name] + modifier_value
        
        new_value = self.current_stats[stat_name]
        print(f"  📊 {self.name}: {stat_name.upper()} {old_value:.1f} → {new_value:.1f} ({modifier_value:+.0%})")
        
    def get_stat(self, stat_name: str) -> float:
        return self.current_stats.get(stat_name, 0.0)

def test_special_effects():
    print("🎯 BATTLEFIELD CONDITION SPECIAL EFFECTS TEST")
    print("=" * 65)
    
    # Create test characters
    test_char = TestCharacter("Test_Hero", {
        "atk": 100, "mag": 100, "vit": 100, "spr": 100, 
        "int": 100, "spd": 100, "lck": 100, "hp": 100
    })
    
    characters = [test_char]
    
    # Test conditions with special effects
    special_effect_conditions = [
        "chaos_realm",          # All stat modifiers randomized + 10% random targets
        "hall_of_mirrors",      # 20% miss chance + INT boost
        "desert_mirage",        # 25% wrong target + SPD penalty
        "temporal_storm",       # Action gauge varies ±25%
        "thunderous_skies",     # Chain lightning chance
        "phoenix_rebirth",      # Revive with 50% HP + regen
        "divine_intervention",  # No character below 1 HP
        "vampire_castle",       # Life-steal effect
        "witch_cauldron",       # Random potion effects
        "quantum_entanglement"  # Shared damage/healing
    ]
    
    for condition_id in special_effect_conditions:
        print(f"\n🌟 TESTING: {condition_id.replace('_', ' ').title()}")
        print("-" * 55)
        
        # Reset character
        test_char.current_stats = test_char.base_stats.copy()
        test_char.battlefield_special_rules = []
        
        # Apply battlefield condition
        if battlefield_conditions_system.set_active_condition(condition_id):
            condition = battlefield_conditions_system.active_condition
            print(f"📜 CONDITION: {condition.name} ({condition.rarity.upper()})")
            print(f"   {condition.description}")
            
            # Apply effects
            applied_effects = battlefield_conditions_system.apply_condition_effects(characters)
            
            print(f"\n📊 STAT EFFECTS:")
            if applied_effects:
                for char_id, effects in applied_effects.items():
                    stat_effects = [e for e in effects if any(stat in e for stat in ['atk:', 'mag:', 'hp:', 'spd:', 'int:', 'vit:', 'spr:', 'lck:', 'all_stats:'])]
                    if stat_effects:
                        print(f"  ✅ {stat_effects}")
                    else:
                        print(f"  ❌ No stat modifications")
            else:
                print(f"  ❌ No effects applied")
            
            print(f"\n🎯 SPECIAL RULES:")
            if test_char.battlefield_special_rules:
                for rule in test_char.battlefield_special_rules:
                    print(f"  ✅ Type: {rule['rule_type']}")
                    print(f"     Description: {rule['description']}")
                    print(f"     Effect Data: {rule['effect_data']}")
            else:
                print(f"  ❌ No special rules applied")
                
            # Show raw condition effects for debugging
            print(f"\n🔍 RAW CONDITION EFFECTS:")
            for i, effect in enumerate(condition.effects):
                print(f"  Effect {i+1}: {effect.effect_type} - {effect.description}")
                if effect.effect_type == "stat_modifier":
                    print(f"             Stat: {effect.stat_affected}, Value: {effect.modifier_value}, Type: {effect.modifier_type}")
                elif effect.effect_type == "special_rule":
                    print(f"             Target: {effect.target_criteria}")
        else:
            print(f"❌ Failed to find condition: {condition_id}")
    
    print("\n" + "=" * 65)
    print("🎉 SPECIAL EFFECTS TEST COMPLETE!")

if __name__ == "__main__":
    test_special_effects()
