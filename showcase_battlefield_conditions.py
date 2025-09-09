"""
Demonstration of the Enhanced Battlefield Conditions System
Shows off the creative and fun new battlefield conditions
"""
import sys
sys.path.append('src')

from game.core.battlefield_conditions import battlefield_conditions_system
import random

def demonstrate_conditions():
    """Demonstrate the most interesting battlefield conditions"""
    
    print("🌟 ENHANCED BATTLEFIELD CONDITIONS SHOWCASE")
    print("=" * 60)
    print(f"Total Conditions Available: {len(battlefield_conditions_system.conditions)}")
    print()
    
    # Showcase by category
    categories = {
        "🌪️ CHAOTIC & UNPREDICTABLE": [
            "chaos_realm", "hall_of_mirrors", "desert_mirage", "mushroom_forest", 
            "fairy_circle", "dreamscape"
        ],
        "⚡ TIME & REALITY MANIPULATION": [
            "temporal_storm", "speed_force", "frozen_time", "infinity_loop", 
            "time_paradox", "cyber_matrix"
        ],
        "🔥 ELEMENTAL POWERHOUSES": [
            "scorching_sun", "arctic_blizzard", "thunderous_skies", "volcanic_arena",
            "atlantis_depths", "phoenix_rebirth"
        ],
        "🎭 THEMATIC ENVIRONMENTS": [
            "vampires_castle", "pirates_treasure", "witchs_cauldron", "dojo_training",
            "monks_meditation", "gladiator_colosseum"
        ],
        "🌈 EPIC LEGENDARY CONDITIONS": [
            "divine_intervention", "harmony_resonance", "quantum_entanglement",
            "dragons_lair", "phoenix_rebirth"
        ],
        "🎲 LUCK & FORTUNE": [
            "lucky_stars", "golden_hour", "blood_moon", "festival_of_light"
        ]
    }
    
    for category, condition_ids in categories.items():
        print(f"{category}")
        print("-" * 40)
        
        for condition_id in condition_ids:
            if condition_id in battlefield_conditions_system.conditions:
                condition = battlefield_conditions_system.conditions[condition_id]
                print(f"📜 {condition.name} ({condition.rarity.upper()})")
                print(f"   {condition.description}")
                
                # Show effects
                for effect in condition.effects:
                    if effect.effect_type == "stat_modifier":
                        target = effect.target_criteria.replace("_", " ").title()
                        stat = effect.stat_affected.upper() if effect.stat_affected != "all_stats" else "ALL STATS"
                        modifier = f"{effect.modifier_value:+.0%}"
                        print(f"   📊 {target}: {stat} {modifier}")
                    else:
                        print(f"   ⚡ {effect.description}")
                print()
        
        print()
    
    # Show some fun combinations through rotation
    print("🎪 RANDOM WEEKLY ROTATIONS SHOWCASE")
    print("-" * 40)
    
    for week in range(1, 8):
        condition = battlefield_conditions_system.rotate_weekly_condition()
        rarity_icon = {"common": "⚪", "rare": "🔵", "legendary": "🟡"}[condition.rarity]
        
        print(f"Week {week}: {rarity_icon} {condition.name}")
        print(f"   {condition.description}")
        
        # Highlight most interesting effect
        most_interesting = max(condition.effects, 
                             key=lambda e: len(e.description) if e.effect_type == "special_rule" else 0,
                             default=condition.effects[0])
        
        if most_interesting.effect_type == "special_rule":
            print(f"   ✨ Special: {most_interesting.description}")
        else:
            stat = most_interesting.stat_affected or "stats"
            print(f"   💪 Effect: {most_interesting.target_criteria} get {most_interesting.modifier_value:+.0%} {stat.upper()}")
        print()
    
    # Statistics summary
    print("📈 BATTLEFIELD CONDITIONS STATISTICS")
    print("-" * 40)
    
    rarity_counts = {"common": 0, "rare": 0, "legendary": 0}
    effect_types = {"stat_modifier": 0, "special_rule": 0}
    stat_effects = {}
    
    for condition in battlefield_conditions_system.conditions.values():
        rarity_counts[condition.rarity] += 1
        
        for effect in condition.effects:
            effect_types[effect.effect_type] += 1
            
            if effect.effect_type == "stat_modifier" and effect.stat_affected:
                stat = effect.stat_affected
                stat_effects[stat] = stat_effects.get(stat, 0) + 1
    
    print(f"🎯 Rarity Distribution:")
    for rarity, count in rarity_counts.items():
        percentage = (count / len(battlefield_conditions_system.conditions)) * 100
        print(f"   {rarity.upper()}: {count} ({percentage:.1f}%)")
    
    print(f"\n⚔️ Effect Types:")
    for effect_type, count in effect_types.items():
        print(f"   {effect_type.replace('_', ' ').title()}: {count}")
    
    print(f"\n💪 Most Affected Stats:")
    sorted_stats = sorted(stat_effects.items(), key=lambda x: x[1], reverse=True)
    for stat, count in sorted_stats[:5]:
        stat_name = stat.replace("_", " ").upper() if stat != "all_stats" else "ALL STATS"
        print(f"   {stat_name}: {count} effects")
    
    print(f"\n🎉 SYSTEM READY FOR EPIC BATTLES!")
    print(f"   Total battlefield conditions: {len(battlefield_conditions_system.conditions)}")
    print(f"   Creative special rules: {effect_types['special_rule']}")
    print(f"   Stat modifications: {effect_types['stat_modifier']}")
    print(f"   Fun factor: MAXIMUM! 🚀")

if __name__ == "__main__":
    demonstrate_conditions()
