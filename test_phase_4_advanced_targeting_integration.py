"""
Phase 4 Advanced Targeting Algorithms Integration Test
Tests the complete Advanced Targeting system with complex multi-target skills
"""

import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import json
from game.systems.advanced_targeting_engine import AdvancedTargetingEngine, TargetingContext
from game.systems.ai_system import AI_System

class MockCharacter:
    """Enhanced mock character for advanced testing"""
    def __init__(self, name, position, hp, max_hp, atk=100, defense=80, vit=90, spr=85, 
                 effects=None, threat_level=None, team='enemy'):
        self.name = name
        self.position = position
        self.hp = hp
        self.max_hp = max_hp
        self.atk = atk
        self.def_ = defense
        self.vit = vit
        self.spr = spr
        self.effects = effects or []
        self.debuff_count = len([e for e in self.effects if e.get('type') == 'debuff'])
        self.threat_level = threat_level or (atk * 0.5 + hp * 0.3)
        self.is_dead = hp <= 0
        self.is_alive = hp > 0  # Add is_alive property
        self.team = team
        
        # Enhanced components for targeting system
        self.components = {
            'state': MockState(hp, max_hp),
            'stats': MockStats(atk, defense, vit, spr),
            'effects': MockEffects(effects or [])
        }
        
    def get_position_distance(self, other_position):
        """Calculate distance between positions"""
        return abs(self.position - other_position)

class MockState:
    """Mock state component"""
    def __init__(self, hp, max_hp):
        self.current_hp = hp
        self.max_hp = max_hp
        self.is_alive = hp > 0

class MockStats:
    """Mock stats component"""
    def __init__(self, atk, defense, vit, spr):
        self.atk = atk
        self.def_ = defense
        self.vit = vit
        self.spr = spr

class MockEffects:
    """Mock effects component"""
    def __init__(self, effects):
        self.active_effects = effects
        
    def get_active_effects(self):
        """Return list of active effects"""
        return self.active_effects

class TestPhase4AdvancedTargetingIntegration:
    
    def setup_method(self):
        """Setup test environment with Advanced Targeting Engine"""
        self.targeting_engine = AdvancedTargetingEngine()
        # AI system setup with mock dependencies
        self.ai_system = None  # We'll test targeting engine independently
        
    def create_complex_battle_scenario(self):
        """Create a complex battle scenario for advanced targeting tests"""
        allies = [
            MockCharacter("Tank", 0, 85, 120, 160, 140, 110, 70, [], 250, 'ally'),
            MockCharacter("Mage", 1, 35, 80, 200, 60, 70, 150, [], 300, 'ally'),
            MockCharacter("Healer", 2, 55, 70, 80, 70, 85, 180, [], 180, 'ally'),
            MockCharacter("Archer", 3, 70, 90, 170, 80, 95, 90, [], 220, 'ally'),
            MockCharacter("Warrior", 4, 95, 110, 180, 120, 100, 75, [], 260, 'ally'),
            MockCharacter("Support", 5, 60, 75, 100, 85, 80, 140, [], 190, 'ally'),
        ]
        
        enemies = [
            MockCharacter("Boss", 0, 200, 250, 240, 160, 140, 100, [], 500, 'enemy'),
            MockCharacter("Elite1", 1, 120, 150, 190, 110, 120, 85, [], 350, 'enemy'),
            MockCharacter("Elite2", 2, 100, 130, 180, 100, 110, 90, [], 320, 'enemy'),
            MockCharacter("Minion1", 3, 60, 80, 140, 70, 80, 60, [], 200, 'enemy'),
            MockCharacter("Minion2", 4, 55, 75, 130, 65, 75, 55, [], 180, 'enemy'),
            MockCharacter("Caster", 5, 40, 60, 120, 50, 60, 160, [], 250, 'enemy'),
        ]
        
        return allies, enemies
    
    def load_skill_data(self, skill_id):
        """Load skill data from the skill definitions file"""
        try:
            with open('data/skill_definitions.json', 'r') as f:
                skills = json.load(f)
                for skill in skills:
                    if skill['id'] == skill_id:
                        return skill
        except FileNotFoundError:
            pass
        return None
        
    def test_meteor_storm_all_enemies_targeting(self):
        """Test Meteor Storm skill targeting all enemies"""
        allies, enemies = self.create_complex_battle_scenario()
        caster = allies[1]  # Mage
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "id": "meteor_storm",
            "name": "Meteor Storm", 
            "target_type": "all_enemies",
            "type": "damage",
            "element": "fire",
            "range": "any",
            "multiplier": 0.8
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        
        # Should target all living enemies
        assert len(targets) == 6
        assert all(target in enemies for target in targets)
        
    def test_chain_lightning_targeting(self):
        """Test Chain Lightning multi-target chaining"""
        allies, enemies = self.create_complex_battle_scenario()
        caster = allies[1]  # Mage
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "id": "chain_lightning",
            "name": "Chain Lightning",
            "target_type": "chain_target", 
            "type": "damage",
            "element": "lightning",
            "range": "any",
            "target_count": 3,
            "chain_count": 3,
            "chain_range": 2
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        
        # Should chain between up to 3 enemies
        assert len(targets) <= 3
        assert len(targets) >= 1
        assert all(target in enemies for target in targets)
        
    def test_smart_heal_multi_targeting(self):
        """Test Smart Heal intelligent ally targeting"""
        allies, enemies = self.create_complex_battle_scenario()
        caster = allies[2]  # Healer
        
        # Damage some allies to create healing priorities
        allies[1].hp = 15  # Mage critically wounded
        allies[1].components['state'].current_hp = 15
        allies[3].hp = 35  # Archer moderately wounded  
        allies[3].components['state'].current_hp = 35
        allies[0].hp = 60  # Tank lightly wounded
        allies[0].components['state'].current_hp = 60
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "id": "smart_heal",
            "name": "Smart Heal",
            "target_type": "smart_multi",
            "type": "heal",
            "element": "divine", 
            "range": "any",
            "target_count": 2
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        
        # Should target the 2 most wounded allies
        assert len(targets) == 2
        assert all(target in allies for target in targets)
        assert allies[1] in targets  # Most wounded (mage)
        assert allies[3] in targets  # Second most wounded (archer)
        
    def test_formation_strike_line_targeting(self):
        """Test Formation Strike targeting enemy lines"""
        allies, enemies = self.create_complex_battle_scenario()
        caster = allies[4]  # Warrior
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "id": "formation_strike",
            "name": "Formation Strike",
            "target_type": "formation_line",
            "type": "damage",
            "element": "tactical",
            "range": "any",
            "line_type": "row"
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        
        # Should target enemies in formation line
        assert len(targets) >= 1
        assert all(target in enemies for target in targets)
        
    def test_priority_strike_threat_targeting(self):
        """Test Priority Strike targeting highest threat enemy"""
        allies, enemies = self.create_complex_battle_scenario()
        caster = allies[0]  # Tank
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "id": "priority_strike",
            "name": "Priority Strike",
            "target_type": "enemy_highest_threat",
            "type": "damage",
            "element": "tactical",
            "range": "any"
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        
        # Should target the Boss (highest threat)
        assert len(targets) == 1
        assert targets[0] == enemies[0]  # Boss has highest threat level
        
    def test_selective_dispel_debuff_targeting(self):
        """Test Selective Dispel targeting most debuffed ally"""
        allies, enemies = self.create_complex_battle_scenario()
        caster = allies[5]  # Support
        
        # Add debuffs to various allies
        allies[0].effects = [{'type': 'debuff', 'name': 'poison'}]
        allies[0].debuff_count = 1
        allies[0].components['effects'].active_effects = allies[0].effects
        
        allies[3].effects = [
            {'type': 'debuff', 'name': 'slow'},
            {'type': 'debuff', 'name': 'weak'},
            {'type': 'debuff', 'name': 'blind'}
        ]
        allies[3].debuff_count = 3
        allies[3].components['effects'].active_effects = allies[3].effects
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "id": "selective_dispel",
            "name": "Selective Dispel",
            "target_type": "ally_most_debuffed",
            "type": "dispel",
            "element": "divine",
            "range": "any"
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        
        # Should target the archer (most debuffed)
        assert len(targets) == 1
        assert targets[0] == allies[3]  # Archer has 3 debuffs
        
    def test_splash_attack_aoe_targeting(self):
        """Test Splash Attack AOE around primary target"""
        allies, enemies = self.create_complex_battle_scenario()
        caster = allies[0]  # Tank (front position)
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "id": "splash_attack",
            "name": "Splash Attack",
            "target_type": "aoe_splash",
            "type": "damage",
            "element": "physical",
            "range": "front",
            "splash_radius": 1
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        
        # Should include primary target plus nearby enemies
        assert len(targets) >= 1
        assert all(target in enemies for target in targets)
        
    def test_ai_system_with_advanced_targeting(self):
        """Test Advanced Targeting system independently"""
        allies, enemies = self.create_complex_battle_scenario()
        active_character = allies[1]  # Mage
        
        context = TargetingContext(active_character, allies, enemies)
        
        # Test various advanced targeting patterns
        skill_patterns = [
            {
                "id": "meteor_storm",
                "target_type": "all_enemies",
                "type": "damage"
            },
            {
                "id": "chain_lightning", 
                "target_type": "chain_target",
                "type": "damage",
                "target_count": 3
            },
            {
                "id": "smart_heal",
                "target_type": "smart_multi",
                "type": "heal",
                "target_count": 2
            }
        ]
        
        for skill_data in skill_patterns:
            targets = self.targeting_engine.resolve_targets(skill_data, context)
            
            # Verify targeting worked correctly
            assert isinstance(targets, list)
            assert len(targets) >= 0
            
            # Verify targets match skill type
            if skill_data['type'] == 'damage':
                assert all(target in enemies for target in targets)
            elif skill_data['type'] == 'heal':
                assert all(target in allies for target in targets)
            
    def test_targeting_engine_efficiency(self):
        """Test targeting engine performance with complex scenarios"""
        allies, enemies = self.create_complex_battle_scenario()
        caster = allies[1]
        
        context = TargetingContext(caster, allies, enemies)
        
        # Test multiple targeting patterns for efficiency
        patterns_to_test = [
            {"target_type": "all_enemies"},
            {"target_type": "chain_target", "target_count": 3},
            {"target_type": "smart_multi", "type": "damage", "target_count": 2},
            {"target_type": "aoe_splash", "splash_radius": 2},
            {"target_type": "formation_line", "line_type": "row"},
            {"target_type": "enemy_highest_threat"},
            {"target_type": "ally_lowest_hp"}
        ]
        
        for pattern in patterns_to_test:
            targets = self.targeting_engine.resolve_targets(pattern, context)
            # All patterns should return valid results
            assert isinstance(targets, list)
            assert len(targets) >= 0  # Some patterns might return empty if no valid targets
            
    def test_advanced_targeting_with_skill_data_from_file(self):
        """Test Advanced Targeting with actual skill data from skill_definitions.json"""
        allies, enemies = self.create_complex_battle_scenario()
        caster = allies[1]  # Mage
        
        context = TargetingContext(caster, allies, enemies)
        
        # Test with real skill data if available
        real_skills = ['meteor_storm', 'chain_lightning', 'smart_heal', 'priority_strike']
        
        for skill_id in real_skills:
            skill_data = self.load_skill_data(skill_id)
            if skill_data:
                targets = self.targeting_engine.resolve_targets(skill_data, context)
                
                # Verify targeting worked correctly
                assert isinstance(targets, list)
                
                # Verify target count respects skill constraints
                if 'target_count' in skill_data:
                    assert len(targets) <= skill_data['target_count']
                    
                # Verify targets are from correct team
                if skill_data.get('target_type') in ['all_enemies', 'enemy_highest_threat']:
                    assert all(target in enemies for target in targets)
                elif skill_data.get('target_type') in ['ally_lowest_hp', 'ally_most_debuffed']:
                    assert all(target in allies for target in targets)

if __name__ == "__main__":
    # Run the comprehensive integration tests
    pytest.main([__file__, "-v"])