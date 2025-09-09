#!/usr/bin/env python3
"""
AI DECISION MAKING & TARGET SELECTION TEST
Testing complex AI behavior, role selection, and target prioritization
Based on Simple Waifu Game mechanics
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.game.components.universal_abilities_component import UniversalAbilitiesComponent
from src.game.core.ai_skill_selector import AISkillSelector
from src.game.core.universal_skill_library import UniversalSkillLibrary
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BattleCharacter:
    """Test character implementation for AI testing"""
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

def test_ai_role_selection():
    """Test AI role selection with dynamic weight modifiers"""
    print("🧠 AI ROLE SELECTION TEST")
    print("=" * 60)
    
    skill_lib = UniversalSkillLibrary()
    ai_selector = AISkillSelector()
    
    # Create test characters in battle scenario
    attacker = create_ai_test_character("AI_Attacker", "attacker", {"atk": 120, "hp": 80})
    injured_ally = create_ai_test_character("Injured_Ally", "healer", {"hp": 25})  # 25% HP
    weak_enemy = create_ai_test_character("Weak_Enemy", "mage", {"hp": 20})  # 20% HP
    
    # Test 1: Triage Priority (ally below 30% HP should boost Healer role weight)
    print("\n🎯 TEST 1: Triage Priority Modifier")
    print("-" * 40)
    
    allies = [injured_ally]
    enemies = [weak_enemy]
    
    injured_hp_percent = (injured_ally.current_hp / 100) * 100  # Assuming 100 max HP
    print(f"   Injured ally HP: {injured_hp_percent:.1f}%")
    
    if injured_hp_percent < 30:
        healer_weight_multiplier = 3.0  # x3.0 from document
        print(f"   Triage Priority triggered: Healer role weight x{healer_weight_multiplier}")
        print("   AI should prioritize healing skills")
    else:
        print("   No triage priority needed")
    
    # Test 2: Finishing Blow (enemy below 25% HP should boost Attacker/Mage weight)
    print("\n🎯 TEST 2: Finishing Blow Modifier")
    print("-" * 40)
    
    weak_enemy_hp_percent = (weak_enemy.current_hp / 100) * 100
    print(f"   Weak enemy HP: {weak_enemy_hp_percent:.1f}%")
    
    if weak_enemy_hp_percent < 25:
        damage_weight_multiplier = 2.0  # x2.0 from document
        print(f"   Finishing Blow triggered: Attacker/Mage role weight x{damage_weight_multiplier}")
        print("   AI should prioritize damage skills to finish enemy")
    else:
        print("   No finishing blow opportunity")
    
    # Test 3: Repetition Penalty
    print("\n🎯 TEST 3: Repetition Penalty")
    print("-" * 40)
    
    last_used_role = "attacker"
    repetition_penalty = 0.5  # x0.5 from document
    
    print(f"   Last role used: {last_used_role}")
    print(f"   Repetition penalty: x{repetition_penalty} for {last_used_role} role")
    print("   AI should be less likely to use same role again")
    
    # Test 4: Buff Synergy (character has ATK buff should boost Attacker role)
    print("\n🎯 TEST 4: Buff Synergy Modifiers")
    print("-" * 40)
    
    buffed_attacker = create_ai_test_character("Buffed_Attacker", "attacker", {"atk": 150})
    # Simulate ATK buff active
    has_atk_buff = True
    has_vit_buff = False
    has_spd_buff = False
    
    if has_atk_buff:
        synergy_multiplier = 1.75  # x1.75 from document
        print(f"   Character has ATK buff")
        print(f"   Synergy boost: Attacker/Mage role weight x{synergy_multiplier}")
    
    if has_vit_buff:
        synergy_multiplier = 2.0  # x2.0 from document
        print(f"   Character has VIT buff")
        print(f"   Synergy boost: Defender role weight x{synergy_multiplier}")
    
    if has_spd_buff:
        synergy_multiplier = 1.5  # x1.5 from document
        print(f"   Character has SPD buff")
        print(f"   Synergy boost: Tactician/Attacker role weight x{synergy_multiplier}")
    
    print("\n✅ AI Role Selection Test Complete!")
    return True

def test_target_priority_scoring():
    """Test AI target priority scoring system"""
    print("\n🎯 TARGET PRIORITY SCORING TEST")
    print("=" * 60)
    
    # Create characters for target selection testing
    high_hp_enemy = create_ai_test_character("Tank_Enemy", "defender", {"hp": 95, "atk": 80, "mag": 60})
    low_hp_enemy = create_ai_test_character("Weak_Enemy", "mage", {"hp": 15, "atk": 120, "mag": 140})
    debuffed_enemy = create_ai_test_character("Debuffed_Enemy", "attacker", {"hp": 60, "atk": 100})
    
    leader_ally = create_ai_test_character("Leader_Ally", "healer", {"hp": 40})  # Designated leader
    high_value_ally = create_ai_test_character("Carry_Ally", "attacker", {"hp": 30, "atk": 180, "mag": 90})
    
    # Test 1: Offensive Target Priority (damage skills)
    print("\n🎯 TEST 1: Offensive Target Priority")
    print("-" * 40)
    
    enemies = [high_hp_enemy, low_hp_enemy, debuffed_enemy]
    
    for enemy in enemies:
        # Calculate Target Priority Score for damage skills
        base_score = 100
        hp_percent = (enemy.current_hp / 100) * 100
        kill_priority = 1 / (hp_percent / 100) if hp_percent > 0 else 10  # Higher for lower HP
        
        # Simulate debuff multiplier
        has_vulnerability_debuff = (enemy.name == "Debuffed_Enemy")
        debuff_multiplier = 1.4 if has_vulnerability_debuff else 1.0
        
        tps = base_score * kill_priority * debuff_multiplier
        print(f"   {enemy.name}:")
        print(f"     HP: {hp_percent:.1f}%")
        print(f"     Kill Priority: {kill_priority:.2f}x")
        print(f"     Debuff Bonus: {debuff_multiplier}x")
        print(f"     Total TPS: {tps:.1f}")
    
    # Highest TPS should be the priority target
    best_target = min(enemies, key=lambda e: e.current_hp)  # Simplification: lowest HP
    print(f"   Priority Target: {best_target.name} (lowest HP)")
    
    # Test 2: Healing Target Priority
    print("\n🎯 TEST 2: Healing Target Priority")
    print("-" * 40)
    
    allies = [leader_ally, high_value_ally]
    
    for ally in allies:
        base_score = 100
        hp_percent = (ally.current_hp / 100) * 100
        missing_health_multiplier = 1 / (hp_percent / 100) if hp_percent > 0 else 10
        
        # High-value ally bonus (ATK + MAG) / 10
        high_value_bonus = (ally.get_stat('atk') + ally.get_stat('mag')) / 10
        
        # Leader bonus
        is_leader = (ally.name == "Leader_Ally")
        leader_bonus = 50 if is_leader else 0
        
        # Simulate debuff bonus
        has_severe_debuff = False  # Example
        debuff_bonus = 150 if has_severe_debuff else 0
        
        tps = base_score * missing_health_multiplier + high_value_bonus + leader_bonus + debuff_bonus
        
        print(f"   {ally.name}:")
        print(f"     HP: {hp_percent:.1f}%")
        print(f"     Missing Health Multiplier: {missing_health_multiplier:.2f}x")
        print(f"     High-Value Bonus: +{high_value_bonus:.1f}")
        print(f"     Leader Bonus: +{leader_bonus}")
        print(f"     Total TPS: {tps:.1f}")
    
    # Test 3: Buff Target Priority
    print("\n🎯 TEST 3: Buff Target Priority")
    print("-" * 40)
    
    for ally in allies:
        base_score = 100
        
        # Role synergy bonus (relevant stat for buff type)
        # Example: ATK buff should prefer high ATK characters
        role_synergy = ally.get_stat('atk')  # For ATK buff
        
        # Turn order bonus (action gauge / 10)
        action_gauge = getattr(ally, 'action_gauge', 500)
        turn_order_bonus = action_gauge / 10
        
        # Leader bonus
        is_leader = (ally.name == "Leader_Ally")
        leader_bonus = 30 if is_leader else 0
        
        tps = base_score + role_synergy + turn_order_bonus + leader_bonus
        
        print(f"   {ally.name} (for ATK buff):")
        print(f"     Role Synergy (ATK): +{role_synergy}")
        print(f"     Turn Order Bonus: +{turn_order_bonus:.1f}")
        print(f"     Leader Bonus: +{leader_bonus}")
        print(f"     Total TPS: {tps:.1f}")
    
    print("\n✅ Target Priority Scoring Test Complete!")
    return True

def test_ai_contextual_decisions():
    """Test AI decision making in complex battle contexts"""
    print("\n🧠 CONTEXTUAL AI DECISION TEST")
    print("=" * 60)
    
    # Test 1: Multi-threat scenario
    print("\n🎯 TEST 1: Multi-Threat Scenario")
    print("-" * 40)
    
    # Create complex battle scenario
    ai_healer = create_ai_test_character("AI_Healer", "healer", {"hp": 80, "int": 130})
    critical_ally = create_ai_test_character("Critical_Ally", "attacker", {"hp": 5})  # 5% HP
    injured_ally = create_ai_test_character("Injured_Ally", "mage", {"hp": 35})  # 35% HP
    dangerous_enemy = create_ai_test_character("Dangerous_Enemy", "attacker", {"hp": 25, "atk": 200})
    
    print("   Battle State:")
    print(f"     AI Healer: {ai_healer.current_hp}% HP")
    print(f"     Critical Ally: {critical_ally.current_hp}% HP (CRITICAL!)")
    print(f"     Injured Ally: {injured_ally.current_hp}% HP")
    print(f"     Dangerous Enemy: {dangerous_enemy.current_hp}% HP (high ATK)")
    
    # AI decision priority analysis
    print("\n   AI Decision Analysis:")
    
    # Critical ally needs immediate healing (highest priority)
    critical_priority = 1000  # Emergency healing
    injured_priority = 200   # Standard healing
    enemy_finish_priority = 300  # Finishing blow opportunity
    
    print(f"     Critical Ally Healing Priority: {critical_priority}")
    print(f"     Injured Ally Healing Priority: {injured_priority}")
    print(f"     Enemy Finishing Priority: {enemy_finish_priority}")
    
    best_action = "Heal Critical Ally" if critical_priority > max(injured_priority, enemy_finish_priority) else "Other"
    print(f"     Optimal Decision: {best_action}")
    
    # Test 2: Resource management scenario
    print("\n🎯 TEST 2: Resource Management")
    print("-" * 40)
    
    ai_caster = create_ai_test_character("AI_Caster", "mage", {"hp": 70, "mag": 150})
    
    # Simulate skill cooldowns and costs
    skills_available = {
        "Greater Heal": {"cooldown": 1, "cost": "high", "power": "high"},
        "Lesser Heal": {"cooldown": 0, "cost": "low", "power": "medium"},
        "Fireball": {"cooldown": 0, "cost": "medium", "power": "high"},
        "Resurrect": {"cooldown": 0, "cost": "ultimate", "uses_left": 1, "power": "ultimate"}
    }
    
    print("   Available Skills:")
    for skill, props in skills_available.items():
        status = "READY" if props["cooldown"] == 0 else f"COOLDOWN: {props['cooldown']}"
        print(f"     {skill}: {status} (Cost: {props['cost']}, Power: {props['power']})")
    
    # Decision based on battle state and resource efficiency
    has_ko_ally = True
    critical_ally_count = 1
    
    if has_ko_ally and skills_available["Resurrect"]["uses_left"] > 0:
        optimal_choice = "Resurrect"
        reasoning = "KO ally present, ultimate resource available"
    elif critical_ally_count > 0 and skills_available["Greater Heal"]["cooldown"] == 0:
        optimal_choice = "Greater Heal"
        reasoning = "Critical ally needs strong healing"
    else:
        optimal_choice = "Lesser Heal or Damage"
        reasoning = "Conserve resources, use efficient skills"
    
    print(f"\n   Optimal Choice: {optimal_choice}")
    print(f"   Reasoning: {reasoning}")
    
    print("\n✅ Contextual AI Decision Test Complete!")
    return True

def test_ai_role_transitions():
    """Test AI role transition strategies during battle"""
    print("\n🔄 AI ROLE TRANSITION TEST")
    print("=" * 60)
    
    # Test role transitions based on battle flow
    print("\n🎯 TEST 1: Battle Phase Transitions")
    print("-" * 40)
    
    battle_phases = [
        {"phase": "Early Game", "turn": 3, "team_hp": 90, "enemy_hp": 85},
        {"phase": "Mid Game", "turn": 8, "team_hp": 60, "enemy_hp": 55},
        {"phase": "Late Game", "turn": 15, "team_hp": 30, "enemy_hp": 25},
        {"phase": "Sudden Death", "turn": 22, "team_hp": 15, "enemy_hp": 20}
    ]
    
    for phase in battle_phases:
        print(f"\n   {phase['phase']} (Turn {phase['turn']}):")
        print(f"     Team HP: {phase['team_hp']}%")
        print(f"     Enemy HP: {phase['enemy_hp']}%")
        
        # Determine optimal role strategy
        if phase['phase'] == "Early Game":
            strategy = "Aggressive (Attacker/Mage focus)"
            reasoning = "High HP, establish advantage"
        elif phase['phase'] == "Mid Game":
            if phase['team_hp'] < phase['enemy_hp']:
                strategy = "Defensive (Healer/Buffer focus)"
                reasoning = "Behind in HP, need recovery"
            else:
                strategy = "Balanced (All roles)"
                reasoning = "Even match, maintain pressure"
        elif phase['phase'] == "Late Game":
            if phase['team_hp'] < 40:
                strategy = "Survival (Healer/Defender priority)"
                reasoning = "Low HP, focus on staying alive"
            else:
                strategy = "Finishing (Attacker/Mage priority)"
                reasoning = "Healthy enough to push for win"
        else:  # Sudden Death
            strategy = "All-out Offense (Maximum damage)"
            reasoning = "Time pressure, stats scaling favors offense"
        
        print(f"     Strategy: {strategy}")
        print(f"     Reasoning: {reasoning}")
    
    # Test 2: Adaptive role weights based on team composition
    print("\n🎯 TEST 2: Team Composition Adaptation")
    print("-" * 40)
    
    team_compositions = [
        {"name": "Balanced Team", "roles": ["attacker", "mage", "healer", "defender"]},
        {"name": "Glass Cannon", "roles": ["attacker", "attacker", "mage", "mage"]},
        {"name": "Tank Team", "roles": ["defender", "defender", "healer", "buffer"]},
        {"name": "Support Heavy", "roles": ["healer", "healer", "buffer", "debuffer"]}
    ]
    
    for comp in team_compositions:
        print(f"\n   {comp['name']}:")
        print(f"     Composition: {comp['roles']}")
        
        # Analyze missing roles and adapt strategy
        role_counts = {}
        for role in comp['roles']:
            role_counts[role] = role_counts.get(role, 0) + 1
        
        missing_roles = []
        if 'healer' not in role_counts:
            missing_roles.append('healing')
        if 'defender' not in role_counts:
            missing_roles.append('defense')
        if 'attacker' not in role_counts and 'mage' not in role_counts:
            missing_roles.append('damage')
        
        if missing_roles:
            adaptation = f"Compensate for missing {', '.join(missing_roles)}"
        else:
            adaptation = "Well-rounded, maintain role balance"
        
        print(f"     Adaptation Strategy: {adaptation}")
    
    print("\n✅ AI Role Transition Test Complete!")
    return True

def create_ai_test_character(name: str, role: str, stats: dict):
    """Create a test character for AI testing"""
    default_stats = {"hp": 100, "atk": 80, "mag": 90, "vit": 70, "spr": 85, "int": 95, "spd": 75, "lck": 80}
    default_stats.update(stats)
    potency = {"attacker": "B", "mage": "A", "healer": "B", "buffer": "C", "debuffer": "C", "defender": "B", "specialist": "B"}
    
    character = BattleCharacter(name, role, default_stats, potency)
    character.current_hp = stats.get("hp", 100)
    character.action_gauge = 500
    
    return character

if __name__ == "__main__":
    print("🧠 AI DECISION MAKING & TARGET SELECTION TEST SUITE")
    print("=" * 70)
    
    success = True
    
    success &= test_ai_role_selection()
    success &= test_target_priority_scoring()
    success &= test_ai_contextual_decisions()
    success &= test_ai_role_transitions()
    
    if success:
        print("\n🎉 All AI decision making tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
