#!/usr/bin/env python3
"""
Quick script to identify the 26 unhandled special effects
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.game.core.battlefield_conditions import BattlefieldConditionsSystem, EffectData, EffectCategory

def find_unhandled_effects():
    """Find effects that don't parse properly"""
    system = BattlefieldConditionsSystem()
    
    unhandled_effects = []
    
    for condition_id, condition in system.conditions.items():
        for effect in condition.effects:
            if effect.effect_type == "special_rule":
                # Try to parse the effect
                parsed_data = EffectData.from_description(effect.description)
                
                # Check if it parsed to a meaningful category or fell back to default
                if (parsed_data.category == EffectCategory.COMBAT_MODIFIER and 
                    "description" in parsed_data.parameters and 
                    parsed_data.parameters["description"] == effect.description):
                    # This is an unhandled effect that fell back to default
                    unhandled_effects.append({
                        "condition": condition_id,
                        "description": effect.description,
                        "parsed_category": parsed_data.category
                    })
    
    print(f"Found {len(unhandled_effects)} unhandled effects:")
    for i, effect in enumerate(unhandled_effects, 1):
        print(f"{i:2d}. {effect['description']}")
        if i >= 30:  # Limit output
            break
    
    return unhandled_effects

if __name__ == "__main__":
    find_unhandled_effects()
