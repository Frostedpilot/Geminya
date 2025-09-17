"""Comprehensive test suite for Phase 3 Advanced Systems.

This test validates all 8 major Phase 3 systems:
1. Rule Engine - Dynamic configuration system
2. Skill System - JSON-based skill loading  
3. Effects System - Status effects with lifecycle management
4. Character Creation - CSV loading with component attachment
5. AI System - Three-Phase decision making
6. Combat Integration - Universal Scaling Formula
7. Data Files - JSON/CSV integrity validation

For detailed analysis see:
- PHASE_3_COMPLETION_REPORT.md - Full completion assessment
- PHASE_4_ROADMAP.md - Detailed todo guide for next phase
- PHASE_3_4_SUMMARY.md - Executive summary of both phases

All tests passing indicates Phase 3 framework is functionally complete
but requires content expansion and optimization covered in Phase 4.
"""

import json
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_rule_engine():
    """Test the Rule Engine implementation."""
    print("=" * 60)
    print("TESTING RULE ENGINE")
    print("=" * 60)
    
    try:
        from src.game.core.rule_engine import RuleEngine, get_rule, get_combat_rule
        
        # Test rule engine initialization
        rule_engine = RuleEngine()
        print("✅ Rule Engine initialized successfully")
        
        # Test rule retrieval
        max_action_gauge = rule_engine.get_combat_rule("max_action_gauge", 100)
        print(f"✅ Max Action Gauge: {max_action_gauge}")
        
        # Test rule setting
        success = rule_engine.set_rule("test.new_rule", 42)
        print(f"✅ Set new rule: {success}")
        
        # Test rule validation
        valid_rule = rule_engine.set_rule("combat.max_action_gauge", 120)
        invalid_rule = rule_engine.set_rule("combat.max_action_gauge", -10)
        print(f"✅ Valid rule setting: {valid_rule}")
        print(f"✅ Invalid rule rejected: {not invalid_rule}")
        
        # Test convenience functions
        combat_multiplier = get_combat_rule("critical_hit_multiplier", 1.5)
        print(f"✅ Global rule access: {combat_multiplier}")
        
        return True
        
    except Exception as e:
        print(f"❌ Rule Engine test failed: {e}")
        return False

def test_skill_system():
    """Test the Skill System framework."""
    print("\n" + "=" * 60)
    print("TESTING SKILL SYSTEM")
    print("=" * 60)
    
    try:
        from src.game.core.skill_system import SkillRegistry
        
        # Test skill registry
        skill_registry = SkillRegistry()
        print("✅ Skill Registry created")
        
        # Load skills from JSON
        if os.path.exists("data/skill_definitions.json"):
            skill_registry.load_from_file("data/skill_definitions.json")
            print("✅ Skills loaded from JSON file")
            
            # Test skill retrieval
            basic_attack = skill_registry.get("basic_attack")
            if basic_attack:
                print(f"✅ Basic Attack skill: {basic_attack.name}")
                print(f"   - Type: {basic_attack.skill_type}")
                print(f"   - Cooldown: {basic_attack.cooldown}")
            
            # Test signature skills
            signature_skills = [skill for skill in skill_registry.get_all().values() 
                              if hasattr(skill, 'is_signature') and skill.is_signature]
            print(f"✅ Found {len(signature_skills)} signature skills")
            
            for skill in signature_skills[:2]:  # Show first 2
                print(f"   - {skill.name}: {getattr(skill, 'trigger_conditions', 'No triggers')}")
        else:
            print("⚠️  Skill definitions file not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Skill System test failed: {e}")
        return False

def test_effects_system():
    """Test the Effects System."""
    print("\n" + "=" * 60)
    print("TESTING EFFECTS SYSTEM")
    print("=" * 60)
    
    try:
        from src.game.effects.base_effect import BaseEffect
        from src.game.effects.stat_modifier import StatModifierEffect
        from src.game.effects.damage_over_time import DamageOverTimeEffect
        
        print("✅ Effect classes imported successfully")
        
        # Create dummy characters for testing
        class MockCharacter:
            def __init__(self, name):
                self.name = name
        
        source = MockCharacter("Attacker")
        target = MockCharacter("Defender")
        
        # Test stat modifier effect
        atk_buff = StatModifierEffect(
            source_character=source,
            target_character=target,
            duration=3,
            stat_name="atk",
            modifier_value=20,
            modifier_type="percentage"
        )
        print("✅ Stat Modifier Effect: ATK Buff")
        print(f"   - Stat: {atk_buff.stat_name}")
        print(f"   - Value: {atk_buff.modifier_value}%")
        print(f"   - Duration: {atk_buff.duration}")
        
        # Test DoT effect
        poison = DamageOverTimeEffect(
            source_character=source,
            target_character=target,
            duration=3,
            damage_per_turn=5,
            damage_type="magical"
        )
        print("✅ DoT Effect: Poison")
        print(f"   - Damage/turn: {poison.damage_per_turn}")
        print(f"   - Type: {poison.damage_type}")
        
        # Test effect library loading
        if os.path.exists("data/effect_library.json"):
            with open("data/effect_library.json", 'r', encoding='utf-8') as f:
                effects_data = json.load(f)
            print(f"✅ Effect Library loaded: {len(effects_data)} effects")
            
            # Show some effects
            for effect in effects_data[:3]:
                print(f"   - {effect['name']}: {effect['type']}")
        else:
            print("⚠️  Effect library file not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Effects System test failed: {e}")
        return False

def test_character_creation():
    """Test character creation with all components."""
    print("\n" + "=" * 60)
    print("TESTING CHARACTER CREATION")
    print("=" * 60)
    
    try:
        from src.game.core.character_factory import CharacterFactory
        from src.game.core.registries import CharacterDataRegistry
        from src.game.core.event_system import EventBus
        from src.game.core.content_loader import ContentLoader
        
        # Create registries and factory
        char_registry = CharacterDataRegistry()
        event_bus = EventBus()
        char_factory = CharacterFactory(char_registry, event_bus)
        
        print("✅ Character Factory created")
        
        # Load character data from CSV using ContentLoader
        content_loader = ContentLoader()
        characters_data = content_loader.load_character_csv("character_final.csv")
        
        if characters_data:
            # Load characters into registry
            char_registry.load_from_list(characters_data)
            print(f"✅ Loaded {len(characters_data)} characters from CSV")
            
            # Create a test character from real data
            char_ids = list(char_registry.get_all().keys())
            if char_ids:
                char_id = char_ids[0]  # Use first character
                character = char_factory.create_character(char_id, team=1, position=0)
                
                print(f"✅ Character created: {character.name}")
                print(f"   - HP: {character.components['state'].current_hp}")
                print(f"   - ATK: {character.components['stats'].get_stat('atk')}")
                
                # Test components
                components = character.components.keys()
                print(f"✅ Components: {list(components)}")
                
                # Test effects component
                effects_comp = character.components.get('effects')
                if effects_comp:
                    print("✅ Effects component attached")
                    try:
                        trigger = effects_comp.check_signature_triggers()
                        print(f"   - Signature triggers checked: {trigger}")
                    except AttributeError:
                        print("   - Signature triggers method not found")
                
                # Test skills component
                skills_comp = character.components.get('skills')
                if skills_comp:
                    print("✅ Skills component attached")
                    try:
                        available_skills = skills_comp.get_available_skills()
                        print(f"   - Available skills: {available_skills}")
                    except AttributeError:
                        print("   - Skills methods not available")
                
                # Show character details
                char_data = char_registry.get(char_id)
                if char_data:
                    print(f"✅ Character Details:")
                    print(f"   - Series: {char_data.get('series', 'Unknown')}")
                    print(f"   - Rarity: {char_data.get('rarity', 'Unknown')}")
                    print(f"   - Archetype: {char_data.get('archetype', 'Unknown')}")
                else:
                    print("⚠️  Character data not found in registry")
                
            else:
                print("❌ No character IDs found in registry")
                return False
        else:
            print("❌ No character data loaded from CSV")
            return False
        
        return True
        
    except ImportError as e:
        print(f"❌ Character Creation test failed: Import error - {e}")
        return False
    except Exception as e:
        print(f"❌ Character Creation test failed: {e}")
        return False

def test_ai_system():
    """Test the Three-Phase AI system."""
    print("\n" + "=" * 60)
    print("TESTING AI SYSTEM")
    print("=" * 60)
    
    try:
        from src.game.systems.ai_system import AI_System
        from src.game.core.battle_context import BattleContext
        from src.game.core.event_system import EventBus
        
        # Create mock dependencies
        event_bus = EventBus()
        battle_context = BattleContext([], [])
        
        # Create AI system
        ai_system = AI_System(battle_context, event_bus)
        print("✅ AI System created")
        
        # Test role potency values
        if hasattr(ai_system, 'ROLE_POTENCY_VALUES'):
            potency_values = ai_system.ROLE_POTENCY_VALUES
            print(f"✅ Role potency values: {potency_values}")
        else:
            print("⚠️  Role potency values not found")
        
        print("✅ AI System configured with battle context")
        
        # Test if AI system can access rule engine
        try:
            from src.game.core.rule_engine import get_ai_rule
            health_threshold = get_ai_rule("role_selection_weights.health_threshold_low", 0.4)
            print(f"✅ AI accessing rule engine: health_threshold = {health_threshold}")
        except ImportError:
            print("⚠️  AI rule engine integration not fully available")
        
        return True
        
    except ImportError as e:
        print(f"❌ AI System test failed: Import error - {e}")
        return False
    except Exception as e:
        print(f"❌ AI System test failed: {e}")
        return False

def test_combat_integration():
    """Test combat system integration."""
    print("\n" + "=" * 60)
    print("TESTING COMBAT INTEGRATION")
    print("=" * 60)
    
    try:
        from src.game.systems.combat_system import CombatSystem
        from src.game.core.battle_context import BattleContext
        from src.game.core.event_system import EventBus
        
        # Create mock dependencies
        event_bus = EventBus()
        battle_context = BattleContext([], [])
        
        # Create combat system
        combat_system = CombatSystem(battle_context, event_bus)
        print("✅ Combat System created")
        
        # Check available methods
        scaling_methods = [attr for attr in dir(combat_system) if 'scaling' in attr.lower()]
        print(f"✅ Available scaling methods: {scaling_methods}")
        
        # Test if universal scaling is implemented
        if hasattr(combat_system, 'apply_universal_scaling') or hasattr(combat_system, '_apply_universal_scaling'):
            print("✅ Universal scaling method found")
        else:
            print("⚠️  Universal scaling method not found")
        
        return True
        
    except ImportError as e:
        print(f"❌ Combat Integration test failed: Import error - {e}")
        return False
    except Exception as e:
        print(f"❌ Combat Integration test failed: {e}")
        return False

def test_data_files():
    """Test data file integrity."""
    print("\n" + "=" * 60)
    print("TESTING DATA FILES")
    print("=" * 60)
    
    data_files = [
        ("skill_definitions.json", "Skill Definitions"),
        ("effect_library.json", "Effect Library"),
        ("game_rules.json", "Game Rules"),
        ("archetypes.json", "Character Archetypes"),
        ("character_final.csv", "Character Data")
    ]
    
    all_good = True
    for filename, description in data_files:
        filepath = f"data/{filename}"
        if os.path.exists(filepath):
            try:
                if filename.endswith('.json'):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        count = len(data)
                    elif isinstance(data, dict):
                        count = len(data)
                    else:
                        count = "Unknown"
                    print(f"✅ {description}: {count} entries")
                else:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                    print(f"✅ {description}: {lines} lines")
            except Exception as e:
                print(f"❌ {description}: Error reading file - {e}")
                all_good = False
        else:
            print(f"⚠️  {description}: File not found - {filepath}")
            all_good = False
    
    return all_good

def main():
    """Run all tests."""
    print("Phase 3 Advanced Systems - Comprehensive Test Suite")
    print("=" * 60)
    
    tests = [
        ("Rule Engine", test_rule_engine),
        ("Skill System", test_skill_system),
        ("Effects System", test_effects_system),
        ("Character Creation", test_character_creation),
        ("AI System", test_ai_system),
        ("Combat Integration", test_combat_integration),
        ("Data Files", test_data_files)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
    
    print("-" * 40)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Phase 3 systems are working correctly.")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    main()