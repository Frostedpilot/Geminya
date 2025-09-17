"""Test script to validate Phase 2 implementation - Complete Battle System."""

from src.game.core.content_loader import ContentLoader
from src.game.core.registries import CharacterDataRegistry
from src.game.core.character_factory import CharacterFactory
from src.game.core.battle_setup import BattleSetup
from src.game.core.event_system import EventBus
from src.game.systems.battle import Battle

def test_phase_2():
    """Test the complete battle loop with two characters fighting."""
    print("Testing Phase 2 Implementation - Complete Battle System...")
    
    # 1. Setup the game infrastructure
    print("\n1. Setting up game infrastructure...")
    content_loader = ContentLoader()
    content = content_loader.load_all_content()
    
    char_registry = CharacterDataRegistry()
    char_registry.load_from_list(content['characters'])
    
    char_factory = CharacterFactory(char_registry)
    battle_setup = BattleSetup(char_factory)
    event_bus = EventBus()
    
    print(f"Loaded {len(char_registry.get_all())} characters")
    
    # 2. Create a battle with two characters
    print("\n2. Creating battle...")
    if len(char_registry.get_all()) < 2:
        print("Error: Need at least 2 characters for battle test")
        return
    
    char_ids = list(char_registry.get_all().keys())[:2]
    char1_id = char_ids[0]
    char2_id = char_ids[1]
    
    # Create battle with one character per team
    battle_context = battle_setup.create_battle([char1_id], [char2_id])
    
    char1 = battle_context.team_one[0]
    char2 = battle_context.team_two[0]
    
    print(f"Team 1: {char1.name} (HP: {char1.components['state'].current_hp}, ATK: {char1.components['stats'].get_stat('atk')}, SPD: {char1.components['stats'].get_stat('spd')})")
    print(f"Team 2: {char2.name} (HP: {char2.components['state'].current_hp}, ATK: {char2.components['stats'].get_stat('atk')}, SPD: {char2.components['stats'].get_stat('spd')})")
    
    # 3. Setup event logging for debugging
    print("\n3. Setting up event logging...")
    events_log = []
    
    def log_event(event_name):
        def handler(data):
            events_log.append(f"{event_name}: {data}")
            if event_name == "HPChanged":
                char = data.get('character')
                old_hp = data.get('old_hp')
                new_hp = data.get('new_hp')
                damage = data.get('damage')
                source = data.get('source')
                print(f"  {char.name}: {old_hp} -> {new_hp} HP (-{damage} from {source.name})")
            elif event_name == "CharacterDefeated":
                char = data.get('character')
                killer = data.get('killer')
                print(f"  {char.name} defeated by {killer.name}!")
        return handler
    
    event_bus.subscribe("HPChanged", log_event("HPChanged"))
    event_bus.subscribe("CharacterDefeated", log_event("CharacterDefeated"))
    event_bus.subscribe("BattleCompleted", log_event("BattleCompleted"))
    
    # 4. Run the battle
    print("\n4. Running battle...")
    battle = Battle(battle_context, event_bus)
    results = battle.run_battle()
    
    # 5. Display results
    print("\n5. Battle Results:")
    print(f"Winner: {results['winner']}")
    print(f"Total ticks: {results['total_ticks']}")
    print(f"Battle finished: {results['battle_finished']}")
    print(f"Team 1 survivors: {results['team_one_survivors']}")
    print(f"Team 2 survivors: {results['team_two_survivors']}")
    
    # 6. Verify final character states
    print("\n6. Final character states:")
    print(f"{char1.name}: HP={char1.components['state'].current_hp}/{char1.components['state'].max_hp}, Alive={char1.components['state'].is_alive}")
    print(f"{char2.name}: HP={char2.components['state'].current_hp}/{char2.components['state'].max_hp}, Alive={char2.components['state'].is_alive}")
    
    # 7. Test validation
    print("\n7. Test validation:")
    if results['battle_finished']:
        print("✓ Battle completed successfully")
    else:
        print("✗ Battle did not complete")
        return
    
    if results['team_one_survivors'] == 0 or results['team_two_survivors'] == 0:
        print("✓ One team was completely defeated")
    else:
        print("✗ Victory condition not properly detected")
        return
    
    if results['winner'] in ['team_one', 'team_two']:
        print("✓ Winner correctly identified")
    else:
        print("✗ Winner not properly determined")
        return
    
    print("\n✓ Phase 2 implementation test completed successfully!")
    print("The battle system is now functional with:")
    print("  - Turn-based action gauge system")
    print("  - AI decision making")
    print("  - Combat resolution with damage")
    print("  - Victory condition detection")
    print("  - Event-driven communication")

def test_action_gauge_system():
    """Test the action gauge system in isolation."""
    print("\n=== Testing Action Gauge System ===")
    
    # Setup
    content_loader = ContentLoader()
    content = content_loader.load_all_content()
    char_registry = CharacterDataRegistry()
    char_registry.load_from_list(content['characters'])
    char_factory = CharacterFactory(char_registry)
    battle_setup = BattleSetup(char_factory)
    event_bus = EventBus()
    
    # Create battle
    char_ids = list(char_registry.get_all().keys())[:2]
    battle_context = battle_setup.create_battle([char_ids[0]], [char_ids[1]])
    
    from src.game.systems.turn_system import TurnSystem
    turn_system = TurnSystem(battle_context, event_bus)
    
    char1 = battle_context.team_one[0]
    char2 = battle_context.team_two[0]
    
    print("Initial action gauges:")
    print(f"  {char1.name}: {char1.components['state'].action_gauge}")
    print(f"  {char2.name}: {char2.components['state'].action_gauge}")
    
    # Simulate several ticks
    for i in range(10):
        turn_system.tick()
        active = turn_system.get_active_character()
        if active:
            print(f"Tick {i+1}: {active.name} ready to act (gauge: {active.components['state'].action_gauge})")
            turn_system.end_turn(active)
        else:
            gauge1 = char1.components['state'].action_gauge
            gauge2 = char2.components['state'].action_gauge
            print(f"Tick {i+1}: No character ready (gauges: {char1.name}={gauge1}, {char2.name}={gauge2})")

if __name__ == "__main__":
    test_phase_2()
    test_action_gauge_system()