"""Test script for the skill system."""

from src.game.core.content_loader import ContentLoader
from src.game.core.registries import CharacterDataRegistry
from src.game.core.character_factory import CharacterFactory
from src.game.core.battle_setup import BattleSetup
from src.game.core.event_system import EventBus
from src.game.core.skill_system import SkillRegistry
from src.game.systems.battle import Battle

def test_skill_system():
    """Test the skill system with skill loading and cooldowns."""
    print("Testing Skill System...")
    
    # Setup
    content_loader = ContentLoader()
    content = content_loader.load_all_content()
    
    char_registry = CharacterDataRegistry()
    char_registry.load_from_list(content['characters'])
    
    skill_registry = SkillRegistry()
    skill_registry.load_from_dict(content['skills'])
    
    event_bus = EventBus()
    char_factory = CharacterFactory(char_registry, event_bus)
    battle_setup = BattleSetup(char_factory)
    
    print(f"Loaded {len(skill_registry.get_all())} skills")
    for skill_id, skill in skill_registry.get_all().items():
        print(f"  - {skill.name} ({skill_id}): {skill.description}")
    
    # Create test characters
    char_ids = list(char_registry.get_all().keys())[:2]
    battle_context = battle_setup.create_battle([char_ids[0]], [char_ids[1]])
    
    char1 = battle_context.team_one[0]
    char2 = battle_context.team_two[0]
    
    print(f"\nTest Characters:")
    print(f"  {char1.name}: HP={char1.components['state'].current_hp}, ATK={char1.components['stats'].get_stat('atk')}")
    print(f"  {char2.name}: HP={char2.components['state'].current_hp}, ATK={char2.components['stats'].get_stat('atk')}")
    
    # Test skill cooldowns
    state1 = char1.components['state']
    
    print(f"\nTesting skill cooldowns...")
    print(f"Power Strike ready: {state1.is_skill_ready('power_strike')}")
    
    # Set a cooldown
    state1.set_skill_cooldown('power_strike', 3)
    print(f"Power Strike ready after cooldown: {state1.is_skill_ready('power_strike')}")
    print(f"Power Strike cooldown: {state1.get_skill_cooldown('power_strike')} turns")
    
    # Test cooldown countdown
    for turn in range(4):
        print(f"\nTurn {turn + 1}:")
        print(f"  Power Strike cooldown: {state1.get_skill_cooldown('power_strike')}")
        state1.tick_cooldowns()
        print(f"  After tick: {state1.get_skill_cooldown('power_strike')}")
        print(f"  Skill ready: {state1.is_skill_ready('power_strike')}")
    
    # Create a battle with skill registry
    print(f"\nCreating battle with skill system...")
    battle = Battle(battle_context, event_bus, skill_registry)
    
    # Test a few turns to see skill usage
    print(f"\nRunning battle with skills...")
    result = battle.run_battle()
    
    print(f"\nBattle completed!")
    print(f"Winner: {result.get('winner', 'Unknown')}")
    print(f"Total ticks: {result.get('total_ticks', 0)}")

if __name__ == "__main__":
    test_skill_system()