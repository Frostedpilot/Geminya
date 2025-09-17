"""Main battle orchestration class."""

from .turn_system import TurnSystem
from .combat_system import CombatSystem
from .ai_system import AI_System
from .victory_system import VictorySystem

class Battle:
    """Main battle orchestrator that manages the battle loop."""
    
    def __init__(self, battle_context, event_bus, skill_registry=None):
        """Initialize the battle with context and event bus.
        
        Args:
            battle_context: BattleContext containing teams and state
            event_bus: EventBus for system communication
            skill_registry: SkillRegistry for skill lookup (optional)
        """
        self.battle_context = battle_context
        self.event_bus = event_bus
        self.skill_registry = skill_registry
        
        # Initialize all battle systems
        self.turn_system = TurnSystem(battle_context, event_bus)
        self.combat_system = CombatSystem(battle_context, event_bus, skill_registry)
        self.ai_system = AI_System(battle_context, event_bus)  # TODO: Add skill_registry support
        self.victory_system = VictorySystem(battle_context, event_bus)
        
        # Battle state
        self.tick_count = 0
        self.max_ticks = 10000  # Safety limit to prevent infinite loops
        
        # Subscribe to battle completion
        self.event_bus.subscribe("BattleCompleted", self._on_battle_completed)
        
    def run_battle(self):
        """Run the complete battle loop until completion.
        
        Returns:
            Battle result dict with winner and statistics
        """
        print("Battle starting...")
        
        # Publish battle start event
        self.event_bus.publish("BattleStarted", {
            "team_one_size": len(self.battle_context.team_one),
            "team_two_size": len(self.battle_context.team_two)
        })
        
        # Main battle loop
        while not self.victory_system.is_battle_finished() and self.tick_count < self.max_ticks:
            self._battle_tick()
        
        # Return battle results
        return self._get_battle_results()
    
    def _battle_tick(self):
        """Execute one tick of the battle loop."""
        self.tick_count += 1
        
        # 1. Advance action gauges
        self.turn_system.tick()
        
        # 2. Check for ready character
        active_character = self.turn_system.get_active_character()
        if not active_character:
            return  # No character ready to act
        
        print(f"Turn {self.tick_count}: {active_character.name} is acting")
        
        # 3. AI chooses action
        action_command = self.ai_system.choose_action(active_character)
        if not action_command:
            # Character can't act, end turn
            self.turn_system.end_turn(active_character)
            return
        
        print(f"  Action: {action_command.skill_name} targeting {len(action_command.targets)} enemies")
        
        # 4. Resolve action
        self.combat_system.resolve_action(action_command)
        
        # 5. End turn
        self.turn_system.end_turn(active_character)
        
        # 6. Check victory conditions (handled by VictorySystem via events)
    
    def _on_battle_completed(self, event_data):
        """Handle battle completion event."""
        print(f"Battle completed! Winner: {event_data.get('winner')}")
        print(f"Reason: {event_data.get('reason')}")
    
    def _get_battle_results(self):
        """Get the final battle results.
        
        Returns:
            Dict containing battle statistics
        """
        return {
            "winner": self.victory_system.get_winner(),
            "total_ticks": self.tick_count,
            "battle_finished": self.victory_system.is_battle_finished(),
            "team_one_survivors": self._count_survivors(self.battle_context.team_one),
            "team_two_survivors": self._count_survivors(self.battle_context.team_two)
        }
    
    def _count_survivors(self, team):
        """Count surviving characters in a team.
        
        Args:
            team: List of characters
            
        Returns:
            Number of alive characters
        """
        survivors = 0
        for character in team:
            state_component = character.components.get('state')
            if state_component and state_component.is_alive:
                survivors += 1
        return survivors