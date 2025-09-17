"""
Test Suite for Advanced Targeting Engine
Tests complex multi-target patterns and sophisticated targeting algorithms
"""

import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from game.systems.advanced_targeting_engine import AdvancedTargetingEngine, TargetingContext

class MockCharacter:
    """Mock character for testing targeting"""
    def __init__(self, name, position, hp, max_hp, atk=100, effects=None, threat_level=None):
        self.name = name
        self.position = position
        self.hp = hp
        self.max_hp = max_hp
        self.atk = atk
        self.effects = effects or []
        self.debuff_count = len([e for e in self.effects if e.get('type') == 'debuff'])
        self.threat_level = threat_level or (atk * 0.5 + hp * 0.3)
        self.is_dead = hp <= 0
        
        # Create mock components for compatibility
        self.components = {
            'state': MockState(hp, max_hp),
            'stats': MockStats(atk, 100, 100, 100)  # atk, def, vit, spr
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

class TestAdvancedTargeting:
    
    def setup_method(self):
        """Setup test environment"""
        self.targeting_engine = AdvancedTargetingEngine()
        
    def create_battle_scenario(self):
        """Create a standard battle scenario for testing"""
        allies = [
            MockCharacter("Tank", 0, 80, 100, 150, [], 200),      # Front tank, high threat
            MockCharacter("Mage", 1, 40, 80, 180, [], 250),       # Mid mage, highest threat  
            MockCharacter("Healer", 2, 60, 60, 90, [], 120),      # Back healer, low threat
        ]
        
        enemies = [
            MockCharacter("Boss", 0, 150, 200, 220, [], 400),     # Front boss, highest threat
            MockCharacter("Archer", 1, 70, 100, 160, [], 200),    # Mid archer
            MockCharacter("Rogue", 2, 30, 80, 140, [{'type': 'debuff'}], 180), # Back rogue, debuffed
        ]
        
        return allies, enemies
        
    def test_single_target_selection(self):
        """Test basic single target selection"""
        allies, enemies = self.create_battle_scenario()
        caster = allies[1]  # Mage
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "target_type": "enemy",
            "range": "any"
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        assert len(targets) == 1
        assert targets[0] in enemies
        
    def test_all_enemies_targeting(self):
        """Test all enemies targeting pattern"""
        allies, enemies = self.create_battle_scenario()
        caster = allies[1]  # Mage
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "target_type": "all_enemies",
            "range": "any"
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        assert len(targets) == 3
        assert all(target in enemies for target in targets)
        
    def test_chain_targeting(self):
        """Test chain targeting pattern"""
        allies, enemies = self.create_battle_scenario()
        caster = allies[1]  # Mage
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "target_type": "chain_target",
            "range": "any",
            "target_count": 2,
            "chain_count": 2,
            "chain_range": 2
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        assert len(targets) <= 2
        assert all(target in enemies for target in targets)
        
    def test_aoe_splash_targeting(self):
        """Test AOE splash targeting pattern"""
        allies, enemies = self.create_battle_scenario()
        caster = allies[0]  # Tank
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "target_type": "aoe_splash",
            "range": "front",
            "splash_radius": 1
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        assert len(targets) >= 1
        assert all(target in enemies for target in targets)
        
    def test_smart_multi_targeting(self):
        """Test smart multi-targeting for healing"""
        allies, enemies = self.create_battle_scenario()
        caster = allies[2]  # Healer
        
        # Damage some allies to make them good heal targets
        allies[1].hp = 20  # Mage critically wounded
        allies[1].components['state'].current_hp = 20
        allies[0].hp = 50  # Tank moderately wounded
        allies[0].components['state'].current_hp = 50
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "target_type": "smart_multi",
            "type": "heal",  # Specify this is a healing skill
            "range": "any",
            "target_count": 2
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        assert len(targets) <= 2
        assert all(target in allies for target in targets)
        # Should prioritize most wounded allies
        assert allies[1] in targets  # Critically wounded mage should be targeted
        
    def test_formation_line_targeting(self):
        """Test formation line targeting"""
        allies, enemies = self.create_battle_scenario()
        caster = allies[1]  # Mage
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "target_type": "formation_line",
            "range": "any",
            "line_type": "row"
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        assert len(targets) >= 1
        assert all(target in enemies for target in targets)
        
    def test_priority_targeting(self):
        """Test priority targeting patterns"""
        allies, enemies = self.create_battle_scenario()
        caster = allies[0]  # Tank
        
        context = TargetingContext(caster, allies, enemies)
        
        # Test highest threat targeting
        skill_data = {
            "target_type": "enemy_highest_threat",
            "range": "any"
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        assert len(targets) == 1
        assert targets[0] == enemies[0]  # Boss should be highest threat
        
    def test_ally_lowest_hp_targeting(self):
        """Test ally lowest HP targeting"""
        allies, enemies = self.create_battle_scenario()
        caster = allies[2]  # Healer
        
        # Make mage have lowest HP
        allies[1].hp = 15
        allies[1].components['state'].current_hp = 15
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "target_type": "ally_lowest_hp",
            "range": "any"
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        assert len(targets) == 1
        assert targets[0] == allies[1]  # Mage should be targeted (lowest HP)
        
    def test_most_debuffed_targeting(self):
        """Test most debuffed ally targeting"""
        allies, enemies = self.create_battle_scenario()
        caster = allies[2]  # Healer
        
        # Add debuffs to tank
        allies[0].effects = [
            {'type': 'debuff', 'name': 'poison'},
            {'type': 'debuff', 'name': 'slow'},
            {'type': 'debuff', 'name': 'weak'}
        ]
        allies[0].debuff_count = 3
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "target_type": "ally_most_debuffed",
            "range": "any"
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        assert len(targets) == 1
        assert targets[0] == allies[0]  # Tank should be targeted (most debuffed)
        
    def test_random_targeting_fallback(self):
        """Test random targeting fallback"""
        allies, enemies = self.create_battle_scenario()
        caster = allies[1]  # Mage
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "target_type": "unknown_pattern",
            "range": "any"
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        assert len(targets) == 1
        assert targets[0] in enemies  # Should fallback to random enemy
        
    def test_range_filtering(self):
        """Test range-based target filtering"""
        allies, enemies = self.create_battle_scenario()
        caster = allies[2]  # Healer (back position)
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "target_type": "enemy",
            "range": "front"  # Only front enemies
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        assert len(targets) == 1
        # Should only target front enemies (position 0)
        assert all(target.position == 0 for target in targets)
        
    def test_no_valid_targets(self):
        """Test behavior when no valid targets exist"""
        allies, enemies = self.create_battle_scenario()
        caster = allies[1]  # Mage
        
        # Kill all enemies
        for enemy in enemies:
            enemy.hp = 0
            enemy.is_dead = True
            enemy.components['state'].current_hp = 0
            enemy.components['state'].is_alive = False
        
        context = TargetingContext(caster, allies, enemies)
        
        skill_data = {
            "target_type": "enemy",
            "range": "any"
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        assert len(targets) == 0
        
    def test_complex_multi_target_scenario(self):
        """Test complex multi-target scenario with various patterns"""
        allies, enemies = self.create_battle_scenario()
        caster = allies[1]  # Mage
        
        context = TargetingContext(caster, allies, enemies)
        
        # Test meteor storm (all enemies)
        skill_data = {
            "target_type": "all_enemies",
            "range": "any"
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        assert len(targets) == 3
        assert set(targets) == set(enemies)
        
        # Test chain lightning
        skill_data = {
            "target_type": "chain_target",
            "range": "any",
            "target_count": 3,
            "chain_count": 3,
            "chain_range": 2
        }
        
        targets = self.targeting_engine.resolve_targets(skill_data, context)
        assert len(targets) <= 3
        assert all(target in enemies for target in targets)

if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])