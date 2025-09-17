"""Test script for the new effects system."""

from src.game.core.content_loader import ContentLoader
from src.game.core.registries import CharacterDataRegistry
from src.game.core.character_factory import CharacterFactory
from src.game.core.battle_setup import BattleSetup
from src.game.core.event_system import EventBus
from src.game.effects.stat_modifier import StatModifierEffect
from src.game.effects.damage_over_time import DamageOverTimeEffect

def test_effects_system():
    """Test the new effects system with stat modifiers and DoTs."""
    print("Testing Effects System...")
    
    # Setup
    content_loader = ContentLoader()
    content = content_loader.load_all_content()
    
    char_registry = CharacterDataRegistry()
    char_registry.load_from_list(content['characters'])
    
    event_bus = EventBus()
    char_factory = CharacterFactory(char_registry, event_bus)
    battle_setup = BattleSetup(char_factory)
    
    # Create test characters
    char_ids = list(char_registry.get_all().keys())[:2]
    battle_context = battle_setup.create_battle([char_ids[0]], [char_ids[1]])
    
    char1 = battle_context.team_one[0]
    char2 = battle_context.team_two[0]
    
    print(f"\nInitial stats for {char1.name}:")
    stats = char1.components['stats']
    print(f"ATK: {stats.get_stat('atk')}")
    print(f"VIT: {stats.get_stat('vit')}")
    print(f"HP: {char1.components['state'].current_hp}")
    
    # Test stat modifier effect
    print(f"\nApplying +20% ATK buff to {char1.name}...")
    atk_buff = StatModifierEffect(
        source_character=char2,
        target_character=char1,
        duration=3,
        stat_name="atk",
        modifier_value=20,
        modifier_type="percentage"
    )
    
    effects_comp = char1.components['effects']
    effects_comp.add_effect(atk_buff)
    
    print(f"ATK after buff: {stats.get_stat('atk')}")
    
    # Test damage over time effect
    print(f"\nApplying Bleed (5 damage/turn) to {char1.name}...")
    bleed_effect = DamageOverTimeEffect(
        source_character=char2,
        target_character=char1,
        duration=3,
        damage_per_turn=5,
        damage_type="physical"
    )
    
    effects_comp.add_effect(bleed_effect)
    
    # Simulate turn processing
    print(f"\nSimulating turns...")
    for turn in range(4):
        print(f"\nTurn {turn + 1}:")
        print(f"HP before turn: {char1.components['state'].current_hp}")
        
        # Simulate turn start (DoT processing)
        event_bus.publish("OnTurnStart", {"character": char1})
        
        print(f"HP after DoT: {char1.components['state'].current_hp}")
        print(f"ATK with buff: {stats.get_stat('atk')}")
        
        # Simulate turn end (duration countdown)
        event_bus.publish("OnTurnEnded", {"character": char1})
        
        # Show active effects
        active_effects = effects_comp.get_all_active_effects()
        print(f"Active effects: {len(active_effects)}")
        for effect in active_effects:
            print(f"  - {effect.get_description()}")
    
    print(f"\nFinal state:")
    print(f"HP: {char1.components['state'].current_hp}")
    print(f"ATK: {stats.get_stat('atk')} (should be back to base)")
    print(f"Active effects: {len(effects_comp.get_all_active_effects())}")

if __name__ == "__main__":
    test_effects_system()