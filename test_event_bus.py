"""Test harness for validating EventBus functionality."""

from src.game.core.event_system import EventBus
from src.game.core.battle_context import BattleContext

def test_event_bus():
    """Test the EventBus system to ensure it works correctly."""
    print("Testing EventBus system...")
    
    # Create EventBus and BattleContext
    event_bus = EventBus()
    battle_context = BattleContext()
    
    # Test data storage
    received_events = []
    
    # Create test handler functions
    def on_test_event(data):
        print(f"Event received: {data}")
        received_events.append(data)
    
    def on_battle_start(data):
        print(f"Battle started with data: {data}")
        received_events.append(f"battle_start_{data}")
    
    # Subscribe handlers to events
    event_bus.subscribe("TEST_EVENT", on_test_event)
    event_bus.subscribe("BATTLE_START", on_battle_start)
    
    # Test publishing events
    print("\n1. Publishing TEST_EVENT...")
    event_bus.publish("TEST_EVENT", {"message": "Hello World"})
    
    print("\n2. Publishing BATTLE_START...")
    event_bus.publish("BATTLE_START", "team_composition")
    
    print("\n3. Publishing event with no subscribers...")
    event_bus.publish("NON_EXISTENT_EVENT", "should_not_crash")
    
    print("\n4. Publishing event with no data...")
    event_bus.publish("TEST_EVENT")
    
    # Verify results
    print(f"\nReceived events: {received_events}")
    
    # Test multiple subscribers to same event
    def second_handler(data):
        received_events.append(f"second_handler_{data}")
    
    event_bus.subscribe("TEST_EVENT", second_handler)
    
    print("\n5. Publishing TEST_EVENT with multiple subscribers...")
    event_bus.publish("TEST_EVENT", "multiple_test")
    
    print(f"Final received events: {received_events}")
    print("EventBus test completed successfully!")

if __name__ == "__main__":
    test_event_bus()