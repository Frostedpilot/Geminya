"""Test role potency stat modifier implementation."""

import unittest
from unittest.mock import Mock, MagicMock
from src.game.components.stats_component import StatsComponent
from src.game.core.character_factory import CharacterFactory, ArchetypeComponent
from src.game.core.character import Character
from src.game.core.registries import CharacterDataRegistry, ArchetypeDataRegistry


class TestRolePotencyStats(unittest.TestCase):
    """Test role potency stat modifiers."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock registries
        self.character_registry = CharacterDataRegistry()
        self.archetype_registry = ArchetypeDataRegistry()
        
        # Add test character data
        self.character_registry.register('test_mage', {
            'name': 'Test Mage',
            'archetype': 'Mage',
            'base_stats': {
                'hp': 100,
                'atk': 50,
                'mag': 200,
                'vit': 80,
                'spr': 120,
                'int': 150,
                'spd': 90,
                'lck': 60
            }
        })
        
        # Add test archetype data
        self.archetype_registry.register('Mage', {
            'role_potency': {
                'Mage': 'S',        # 1.10 multiplier
                'Healer': 'C',      # 0.95 multiplier
                'Buffer': 'C',      # 0.95 multiplier
                'Attacker': 'D',    # 0.85 multiplier
                'Debuffer': 'D',    # 0.85 multiplier
                'Defender': 'F',    # 0.70 multiplier
                'Specialist': 'C'   # 0.95 multiplier
            }
        })
        
        self.archetype_registry.register('Balanced', {
            'role_potency': {
                'Mage': 'C',        # 0.95 multiplier
                'Healer': 'C',      # 0.95 multiplier
                'Buffer': 'C',      # 0.95 multiplier
                'Attacker': 'C',    # 0.95 multiplier
                'Debuffer': 'C',    # 0.95 multiplier
                'Defender': 'C',    # 0.95 multiplier
                'Specialist': 'C'   # 0.95 multiplier
            }
        })
        
        # Create factory
        self.factory = CharacterFactory(
            character_registry=self.character_registry,
            archetype_registry=self.archetype_registry
        )
    
    def test_role_potency_multiplier_calculation(self):
        """Test that role potency multipliers are calculated correctly."""
        # Create a character with S-tier Mage potency
        character = self.factory.create_character('test_mage', 'team1', 'front_1')
        stats_component = character.components['stats']
        
        # Test that the highest potency rating (S = 1.10) is used
        potency_info = stats_component.get_role_potency_info()
        self.assertEqual(potency_info['multiplier'], 1.10)
        self.assertEqual(potency_info['highest_rating'], 'S')
        self.assertEqual(potency_info['source_role'], 'Mage')
    
    def test_stat_calculation_with_role_potency(self):
        """Test that stats are enhanced by role potency multipliers."""
        # Create a character with S-tier Mage potency
        character = self.factory.create_character('test_mage', 'team1', 'front_1')
        stats_component = character.components['stats']
        
        # Test enhanced stats (base * 1.10 for S-tier)
        expected_mag = int(200 * 1.10)  # 220
        expected_hp = int(100 * 1.10)   # 110
        expected_atk = int(50 * 1.10)   # 55
        
        self.assertEqual(stats_component.get_stat('mag'), expected_mag)
        self.assertEqual(stats_component.get_stat('hp'), expected_hp)
        self.assertEqual(stats_component.get_stat('atk'), expected_atk)
    
    def test_potency_enhanced_base_stats(self):
        """Test getting potency-enhanced base stats."""
        character = self.factory.create_character('test_mage', 'team1', 'front_1')
        stats_component = character.components['stats']
        
        # Test potency-enhanced base (before other modifiers)
        enhanced_mag = stats_component.get_potency_enhanced_base_stat('mag')
        self.assertEqual(enhanced_mag, 200 * 1.10)  # 220.0
        
        # Test original base stat remains unchanged
        base_mag = stats_component.get_base_stat('mag')
        self.assertEqual(base_mag, 200)
    
    def test_balanced_character_potency(self):
        """Test balanced character with all C-tier potencies."""
        # Add balanced character data
        self.character_registry.register('balanced_char', {
            'name': 'Balanced Character',
            'archetype': 'Balanced',
            'base_stats': {
                'hp': 100,
                'atk': 100,
                'mag': 100,
                'vit': 100,
                'spr': 100,
                'int': 100,
                'spd': 100,
                'lck': 100
            }
        })
        
        character = self.factory.create_character('balanced_char', 'team1', 'front_1')
        stats_component = character.components['stats']
        
        # All C-tier potencies should give 0.95 multiplier
        potency_info = stats_component.get_role_potency_info()
        self.assertEqual(potency_info['multiplier'], 0.95)
        self.assertEqual(potency_info['highest_rating'], 'C')
        
        # All stats should be 95% of base (100 * 0.95 = 95)
        for stat in ['hp', 'atk', 'mag', 'vit', 'spr', 'int', 'spd', 'lck']:
            expected = int(100 * 0.95)  # 95
            self.assertEqual(stats_component.get_stat(stat), expected)
    
    def test_no_archetype_defaults_to_baseline(self):
        """Test that characters without archetype default to baseline (1.0) multiplier."""
        # Create character without archetype registry
        factory_no_archetype = CharacterFactory(
            character_registry=self.character_registry
        )
        
        character = factory_no_archetype.create_character('test_mage', 'team1', 'front_1')
        stats_component = character.components['stats']
        
        # Should default to 1.0 multiplier
        potency_info = stats_component.get_role_potency_info()
        self.assertEqual(potency_info['multiplier'], 1.0)
        self.assertEqual(potency_info['highest_rating'], 'C')
        self.assertIsNone(potency_info['source_role'])
        
        # Stats should be unchanged
        self.assertEqual(stats_component.get_stat('mag'), 200)
        self.assertEqual(stats_component.get_stat('hp'), 100)
    
    def test_cache_invalidation(self):
        """Test that potency cache is invalidated correctly."""
        character = self.factory.create_character('test_mage', 'team1', 'front_1')
        stats_component = character.components['stats']
        
        # First calculation should cache the result
        first_multiplier = stats_component._get_role_potency_multiplier()
        self.assertEqual(first_multiplier, 1.10)
        
        # Invalidate cache
        stats_component.invalidate_potency_cache()
        self.assertIsNone(stats_component._cached_potency_multiplier)
        
        # Should recalculate
        second_multiplier = stats_component._get_role_potency_multiplier()
        self.assertEqual(second_multiplier, 1.10)
    
    def test_role_potency_with_modifiers(self):
        """Test that role potency works correctly with other stat modifiers."""
        character = self.factory.create_character('test_mage', 'team1', 'front_1')
        stats_component = character.components['stats']
        
        # Create a mock modifier effect
        mock_modifier = Mock()
        mock_modifier.is_active = True
        mock_modifier.modifier_type = "percentage"
        mock_modifier.modifier_value = 20  # +20%
        
        # Add modifier to MAG stat
        stats_component.active_modifiers['mag'] = [mock_modifier]
        
        # Calculate expected value:
        # Base: 200
        # Potency enhanced: 200 * 1.10 = 220
        # With 20% modifier: 220 + (220 * 0.20) = 220 + 44 = 264
        expected = int(220 + (220 * 0.20))
        
        actual = stats_component.get_stat('mag')
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()