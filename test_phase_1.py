"""Test script to validate Phase 1 implementation."""

from src.game.core.content_loader import ContentLoader
from src.game.core.registries import CharacterDataRegistry, SkillRegistry, EffectRegistry, SynergyRegistry
from src.game.core.character_factory import CharacterFactory
from src.game.core.battle_setup import BattleSetup
from src.game.core.event_system import EventBus

def test_phase_1():
    """Test all Phase 1 components working together."""
    print("Testing Phase 1 Implementation...")
    
    # 1. Test ContentLoader
    print("\n1. Testing ContentLoader...")
    content_loader = ContentLoader()
    content = content_loader.load_all_content()
    print(f"Loaded content keys: {list(content.keys())}")
    print(f"Characters loaded: {len(content['characters'])}")
    
    # 2. Test Registries
    print("\n2. Testing Registries...")
    char_registry = CharacterDataRegistry()
    char_registry.load_from_list(content['characters'])
    
    skill_registry = SkillRegistry()
    skill_registry.load_from_list(content['skills'])
    
    effect_registry = EffectRegistry()
    effect_registry.load_from_list(content['effects'])
    
    synergy_registry = SynergyRegistry()
    synergy_registry.load_from_list(content['synergies'])
    
    print(f"Character registry has {len(char_registry.get_all())} characters")
    
    # 3. Test CharacterFactory
    print("\n3. Testing CharacterFactory...")
    char_factory = CharacterFactory(char_registry)
    
    # Try to create a character
    if char_registry.get_all():
        char_id = list(char_registry.get_all().keys())[0]
        character = char_factory.create_character(char_id, team=1, position=0)
        print(f"Created character: {character.name} (ID: {character.character_id})")
        print(f"Character HP: {character.components['state'].current_hp}")
        print(f"Character ATK: {character.components['stats'].get_stat('atk')}")
    
    # 4. Test BattleSetup
    print("\n4. Testing BattleSetup...")
    battle_setup = BattleSetup(char_factory)
    
    # Create a mock battle (using the same character for both teams)
    if char_registry.get_all():
        char_id = list(char_registry.get_all().keys())[0]
        battle_context = battle_setup.create_battle([char_id], [char_id])
        print(f"Battle created with {len(battle_context.team_one)} vs {len(battle_context.team_two)} characters")
        print(f"Round number: {battle_context.round_number}")
    
    # 5. Test EventBus integration
    print("\n5. Testing EventBus integration...")
    event_bus = EventBus()
    
    def on_phase_test(data):
        print(f"Phase 1 test event received: {data}")
    
    event_bus.subscribe("PHASE_1_TEST", on_phase_test)
    event_bus.publish("PHASE_1_TEST", {"status": "All systems operational"})
    
    print("\nPhase 1 implementation test completed successfully!")

if __name__ == "__main__":
    test_phase_1()