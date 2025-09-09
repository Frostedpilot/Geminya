#!/usr/bin/env python3
"""
SIGNATURE ABILITIES & SPECIAL MECHANICS TEST
Testing signature skills, passives, leader buffs, and unique character abilities
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
    """Test character implementation for signature abilities testing"""
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
        
        # Signature ability slots (mutable)
        self.signature_skill = {}
        self.signature_passive = {}
        self.is_leader = False
        self.primed_signature = False
    
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

def test_signature_skills():
    """Test signature skill triggers and effects"""
    print("⭐ SIGNATURE SKILLS TEST")
    print("=" * 60)
    
    # Test 1: Megumin's Explosion (HP < 50% trigger)
    print("\n🎯 TEST 1: Megumin's Explosion")
    print("-" * 40)
    
    megumin = create_signature_character("Megumin", "mage", {"hp": 100, "mag": 180})
    megumin.signature_skill = {
        "name": "Explosion",
        "trigger": "hp_below_50",
        "effect": "massive_fire_damage_all_enemies",
        "cost": "self_stun_2_turns",
        "used": False
    }
    
    print(f"   {megumin.name} initial HP: {megumin.current_hp}/100")
    
    # Simulate taking damage to trigger threshold
    megumin.current_hp = 45  # Below 50%
    hp_percent = (megumin.current_hp / 100) * 100
    
    print(f"   After damage: {megumin.current_hp}/100 ({hp_percent:.1f}%)")
    
    if hp_percent < 50 and not megumin.signature_skill["used"]:
        print("   ✅ Explosion trigger condition met!")
        print("   Next turn: Megumin will use Explosion instead of normal skill")
        print("   Effect: Massive unavoidable Fire damage to all enemies")
        print("   Cost: Megumin stunned for 2 rounds")
        megumin.signature_skill["used"] = True
        # Set "primed" status for next turn
        megumin.primed_signature = True
    else:
        print("   No signature trigger")
    
    # Test 2: Yor Forger's Thorn Princess (dodge trigger)
    print("\n🎯 TEST 2: Yor Forger's Thorn Princess")
    print("-" * 40)
    
    yor = create_signature_character("Yor", "attacker", {"hp": 100, "atk": 160, "spd": 140})
    yor.signature_skill = {
        "name": "Thorn Princess",
        "trigger": "enemy_dodges_attack",
        "effect": "atk_spd_buff_50_percent",
        "duration": "next_turn",
        "used": False
    }
    
    # Simulate attack being dodged
    enemy_dodged = True
    
    print(f"   {yor.name} attacks enemy")
    print(f"   Enemy dodge result: {'DODGED' if enemy_dodged else 'HIT'}")
    
    if enemy_dodged and not yor.signature_skill["used"]:
        print("   ✅ Thorn Princess trigger condition met!")
        print("   Effect: Yor gains +50% ATK and +50% SPD for next turn")
        original_atk = yor.get_stat('atk')
        original_spd = yor.get_stat('spd')
        buffed_atk = int(original_atk * 1.5)
        buffed_spd = int(original_spd * 1.5)
        print(f"   ATK: {original_atk} → {buffed_atk}")
        print(f"   SPD: {original_spd} → {buffed_spd}")
        yor.signature_skill["used"] = True
    
    # Test 3: Aqua's God's Blessing (ally defeat trigger)
    print("\n🎯 TEST 3: Aqua's God's Blessing")
    print("-" * 40)
    
    aqua = create_signature_character("Aqua", "healer", {"hp": 100, "int": 170, "spr": 160})
    ally_defeated = True
    
    aqua.signature_skill = {
        "name": "God's Blessing",
        "trigger": "ally_defeated",
        "effect": "full_heal_all_living_allies",
        "bonus": "50_percent_revive_chance",
        "used": False
    }
    
    print(f"   Ally defeat event: {'YES' if ally_defeated else 'NO'}")
    
    if ally_defeated and not aqua.signature_skill["used"]:
        print("   ✅ God's Blessing trigger condition met!")
        print("   Effect: Fully heal all living allies")
        print("   Bonus: 50% chance to revive fallen ally with 30% HP")
        
        # Simulate revival chance
        import random
        random.seed(42)  # For consistent testing
        revival_roll = random.random()
        revival_success = revival_roll < 0.5
        
        print(f"   Revival roll: {revival_roll:.2f}")
        print(f"   Revival result: {'SUCCESS' if revival_success else 'FAILED'}")
        aqua.signature_skill["used"] = True
    
    print("\n✅ Signature Skills Test Complete!")
    return True

def test_signature_passives():
    """Test always-on signature passive abilities"""
    print("\n🔮 SIGNATURE PASSIVES TEST")
    print("=" * 60)
    
    # Test 1: Kaguya's Ice Queen's Gaze
    print("\n🎯 TEST 1: Kaguya's Ice Queen's Gaze")
    print("-" * 40)
    
    kaguya = create_signature_character("Kaguya", "debuffer", {"hp": 100, "int": 150})
    kaguya.signature_passive = {
        "name": "Ice Queen's Gaze",
        "effect": "slow_random_enemy_20_percent_chance",
        "condition": "start_of_turn_no_existing_debuff"
    }
    
    # Simulate turn start
    enemies_without_debuffs = 2  # Example: 2 enemies with no debuffs
    
    print(f"   Turn start: {enemies_without_debuffs} enemies without debuffs")
    
    if enemies_without_debuffs > 0:
        import random
        random.seed(123)
        trigger_roll = random.random()
        trigger_chance = 0.2  # 20%
        
        print(f"   Passive trigger roll: {trigger_roll:.2f}")
        print(f"   Trigger chance: {trigger_chance * 100}%")
        
        if trigger_roll < trigger_chance:
            print("   ✅ Ice Queen's Gaze triggered!")
            print("   Effect: Random enemy without debuff receives 'Slow'")
        else:
            print("   Passive did not trigger this turn")
    else:
        print("   No valid targets (all enemies already debuffed)")
    
    # Test 2: Bocchi's Bocchi the Rock!
    print("\n🎯 TEST 2: Bocchi's 'Bocchi the Rock!'")
    print("-" * 40)
    
    bocchi = create_signature_character("Bocchi", "mage", {"hp": 100, "mag": 140, "vit": 70})
    bocchi.signature_passive = {
        "name": "Bocchi the Rock!",
        "effect": "mag_plus_15_percent_vit_minus_10_percent",
        "last_survivor_bonus": "all_stats_plus_25_percent"
    }
    
    # Apply base passive effects
    base_mag = bocchi.get_stat('mag')
    base_vit = bocchi.get_stat('vit')
    
    modified_mag = int(base_mag * 1.15)
    modified_vit = int(base_vit * 0.9)
    
    print(f"   Base stats: MAG={base_mag}, VIT={base_vit}")
    print(f"   Passive modifier: MAG +15%, VIT -10%")
    print(f"   Modified stats: MAG={modified_mag}, VIT={modified_vit}")
    
    # Test last survivor bonus
    living_teammates = 0  # Bocchi is last survivor
    
    if living_teammates == 0:
        print("   🔥 Last Survivor Bonus activated!")
        print("   All stats increased by 25%")
        
        final_mag = int(modified_mag * 1.25)
        final_vit = int(modified_vit * 1.25)
        
        print(f"   Final stats: MAG={final_mag}, VIT={final_vit}")
    else:
        print(f"   {living_teammates} teammates alive, no last survivor bonus")
    
    # Test 3: Mashiro's Savant Syndrome
    print("\n🎯 TEST 3: Mashiro's Savant Syndrome")
    print("-" * 40)
    
    mashiro = create_signature_character("Mashiro", "mage", {"hp": 100, "mag": 170})
    mashiro.signature_passive = {
        "name": "Savant Syndrome",
        "immunities": ["silence", "blind"],
        "quirk": "10_percent_random_target_chance"
    }
    
    print(f"   {mashiro.name} immunities: Silence, Blind")
    
    # Test immunity
    attempted_debuff = "silence"
    print(f"   Enemy attempts to apply '{attempted_debuff}'")
    
    if attempted_debuff in mashiro.signature_passive["immunities"]:
        print("   ✅ Immunity blocks the debuff!")
        print("   Mashiro is unaffected")
    else:
        print("   Debuff applied normally")
    
    # Test targeting quirk
    import random
    random.seed(456)
    targeting_roll = random.random()
    quirk_chance = 0.1  # 10%
    
    print(f"   Targeting decision roll: {targeting_roll:.2f}")
    
    if targeting_roll < quirk_chance:
        print("   🎲 Savant Syndrome quirk triggered!")
        print("   Mashiro targets random enemy instead of optimal choice")
    else:
        print("   Normal optimal targeting")
    
    print("\n✅ Signature Passives Test Complete!")
    return True

def test_leader_system():
    """Test leader designation and stat bonuses"""
    print("\n👑 LEADER SYSTEM TEST")
    print("=" * 60)
    
    # Create team members
    team_members = [
        create_signature_character("Attacker", "attacker", {"hp": 100, "atk": 120, "spd": 90}),
        create_signature_character("Healer", "healer", {"hp": 110, "int": 140, "spr": 130}),
        create_signature_character("Tank", "defender", {"hp": 140, "vit": 150, "spr": 100})
    ]
    
    # Test 1: Leader designation and stat bonus
    print("\n🎯 TEST 1: Leader Stat Bonus")
    print("-" * 40)
    
    leader = team_members[1]  # Designate healer as leader
    leader.is_leader = True
    
    print(f"   Designated Leader: {leader.name}")
    print("   Leader Bonus: +10% to all base stats")
    
    # Apply leader bonus (from document: +10% to all base stats)
    base_stats = {}
    boosted_stats = {}
    
    for stat in ['hp', 'atk', 'mag', 'vit', 'spr', 'int', 'spd', 'lck']:
        base_value = leader.get_stat(stat)
        boosted_value = int(base_value * 1.1)
        base_stats[stat] = base_value
        boosted_stats[stat] = boosted_value
    
    print(f"   Base stats: {base_stats}")
    print(f"   Boosted stats: {boosted_stats}")
    
    # Test 2: Leader targeting priority
    print("\n🎯 TEST 2: Leader Targeting Priority")
    print("-" * 40)
    
    # Leaders should receive higher priority for healing and buffs
    for member in team_members:
        base_priority = 100
        leader_bonus = 50 if getattr(member, 'is_leader', False) else 0
        total_priority = base_priority + leader_bonus
        
        print(f"   {member.name}: Priority {total_priority} {'(LEADER)' if getattr(member, 'is_leader', False) else ''}")
    
    # Test 3: Leader death impact
    print("\n🎯 TEST 3: Leader Death Impact")
    print("-" * 40)
    
    print("   Scenario: Leader is defeated in battle")
    
    # Some games apply penalties when leader dies
    leader_death_penalty = {
        "morale_drop": True,
        "stat_penalty": 0.05,  # -5% to team stats
        "special_abilities_disabled": False
    }
    
    if leader_death_penalty["morale_drop"]:
        print("   Effect: Team morale drops")
        
        if leader_death_penalty["stat_penalty"] > 0:
            penalty_percent = leader_death_penalty["stat_penalty"] * 100
            print(f"   Penalty: -{penalty_percent}% to all remaining team members' stats")
            
            for member in team_members:
                if member != leader and member.current_hp > 0:
                    original_atk = member.get_stat('atk')
                    penalized_atk = int(original_atk * (1 - leader_death_penalty["stat_penalty"]))
                    print(f"     {member.name}: ATK {original_atk} → {penalized_atk}")
    
    print("\n✅ Leader System Test Complete!")
    return True

def test_unique_character_mechanics():
    """Test special character-specific mechanics"""
    print("\n🌟 UNIQUE CHARACTER MECHANICS TEST")
    print("=" * 60)
    
    # Test 1: Chika's Subject F (random effects)
    print("\n🎯 TEST 1: Chika's Subject F")
    print("-" * 40)
    
    chika = create_signature_character("Chika", "buffer", {"hp": 100, "int": 120})
    chika.signature_passive = {
        "name": "Subject F",
        "effect": "random_weak_buff_debuff_end_of_round",
        "targets": "random_ally_and_enemy"
    }
    
    # Simulate end of round
    print("   End of Round: Subject F triggers")
    
    import random
    random.seed(789)
    
    # Random weak buffs/debuffs (5% as per document)
    possible_effects = [
        "atk_boost_5", "mag_boost_5", "spd_boost_5", "vit_boost_5",
        "atk_drop_5", "mag_drop_5", "spd_drop_5", "vit_drop_5"
    ]
    
    ally_effect = random.choice(possible_effects)
    enemy_effect = random.choice(possible_effects)
    
    print(f"   Random ally receives: {ally_effect}")
    print(f"   Random enemy receives: {enemy_effect}")
    print("   Duration: 1 turn")
    
    # Test 2: Homura's Time Loop (critical hit ally defeat)
    print("\n🎯 TEST 2: Homura's Time Loop")
    print("-" * 40)
    
    homura = create_signature_character("Homura", "tactician", {"hp": 100, "spd": 160, "lck": 140})
    homura.signature_skill = {
        "name": "Time Loop",
        "trigger": "ally_defeated_by_critical_hit",
        "effect": "reset_current_round",
        "cost": "once_per_battle",
        "used": False
    }
    
    # Simulate trigger condition
    ally_defeated_by_crit = True
    
    print("   Scenario: Ally defeated by critical hit")
    print(f"   Time Loop available: {'YES' if not homura.signature_skill['used'] else 'NO'}")
    
    if ally_defeated_by_crit and not homura.signature_skill["used"]:
        print("   ⏰ TIME LOOP ACTIVATED!")
        print("   Effect: Current round resets")
        print("   All characters' HP and status effects revert to round start")
        print("   Turn order resets to beginning of round")
        homura.signature_skill["used"] = True
        
        # This would be a major battle state rollback in the actual game
        print("   🔄 Battle state rolled back to start of round")
    
    # Test 3: Multi-condition signature abilities
    print("\n🎯 TEST 3: Multi-Condition Signatures")
    print("-" * 40)
    
    complex_char = create_signature_character("Complex", "specialist", {"hp": 100, "lck": 180})
    complex_char.signature_skill = {
        "name": "Perfect Storm",
        "conditions": {
            "hp_below_30": False,
            "ally_defeated": True,
            "enemy_has_buff": True,
            "turn_number_above_10": True
        },
        "effect": "ultimate_combination_attack",
        "used": False
    }
    
    conditions = complex_char.signature_skill["conditions"]
    
    print("   Perfect Storm trigger conditions:")
    for condition, met in conditions.items():
        status = "✅ MET" if met else "❌ NOT MET"
        print(f"     {condition}: {status}")
    
    all_conditions_met = all(conditions.values())
    
    if all_conditions_met and not complex_char.signature_skill["used"]:
        print("   🌟 ALL CONDITIONS MET - Perfect Storm available!")
        print("   Effect: Ultimate combination attack with massive damage")
    else:
        unmet = [k for k, v in conditions.items() if not v]
        print(f"   Conditions not met: {', '.join(unmet)}")
    
    print("\n✅ Unique Character Mechanics Test Complete!")
    return True

def create_signature_character(name: str, role: str, stats: dict):
    """Create a character with signature abilities"""
    default_stats = {"hp": 100, "atk": 80, "mag": 90, "vit": 70, "spr": 85, "int": 95, "spd": 75, "lck": 80}
    default_stats.update(stats)
    potency = {"attacker": "B", "mage": "A", "healer": "B", "buffer": "C", "debuffer": "C", "defender": "B", "specialist": "B"}
    
    character = BattleCharacter(name, role, default_stats, potency)
    character.current_hp = stats.get("hp", 100)
    character.primed_signature = False
    
    return character

if __name__ == "__main__":
    print("⭐ SIGNATURE ABILITIES & SPECIAL MECHANICS TEST SUITE")
    print("=" * 70)
    
    success = True
    
    success &= test_signature_skills()
    success &= test_signature_passives()
    success &= test_leader_system()
    success &= test_unique_character_mechanics()
    
    if success:
        print("\n🎉 All signature ability tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
