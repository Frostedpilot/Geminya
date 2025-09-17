"""Base system class for all game systems."""

class BaseSystem:
    """Abstract base class for all game systems."""
    
    def __init__(self, battle_context, event_bus):
        """Initialize the system with battle context and event bus.
        
        Args:
            battle_context: The BattleContext instance
            event_bus: The EventBus instance for communication
        """
        self.battle_context = battle_context
        self.event_bus = event_bus
        self.initialize()
    
    def initialize(self):
        """Initialize the system. Override in subclasses."""
        # Subclasses can override this method for custom initialization
        return