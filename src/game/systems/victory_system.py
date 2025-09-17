"""Victory system for checking win/loss conditions."""

from .base_system import BaseSystem

class VictorySystem(BaseSystem):
    """Handles victory condition checking and battle end state."""
    
    def initialize(self):
        """Subscribe to relevant events."""
        self.battle_finished = False
        self.winner = None
        self.event_bus.subscribe("CharacterDefeated", self._on_character_defeated)
    
    def _on_character_defeated(self, event_data):
        """Handle character defeated events and check for victory.
        
        Args:
            event_data: Event data containing defeated character info
        """
        if self.battle_finished:
            return
        
        # Check if entire team is defeated
        team_one_alive = self._count_alive_characters(self.battle_context.team_one)
        team_two_alive = self._count_alive_characters(self.battle_context.team_two)
        
        if team_one_alive == 0:
            # Team two wins
            self._end_battle(winner="team_two", reason="team_one_eliminated")
        elif team_two_alive == 0:
            # Team one wins
            self._end_battle(winner="team_one", reason="team_two_eliminated")
    
    def _count_alive_characters(self, team):
        """Count the number of alive characters in a team.
        
        Args:
            team: List of characters in the team
            
        Returns:
            Number of alive characters
        """
        alive_count = 0
        for character in team:
            state_component = character.components.get('state')
            if state_component and state_component.is_alive:
                alive_count += 1
        return alive_count
    
    def _end_battle(self, winner, reason):
        """End the battle and announce the winner.
        
        Args:
            winner: The winning team identifier
            reason: Reason for the victory
        """
        self.battle_finished = True
        self.winner = winner
        
        # Publish battle completed event
        self.event_bus.publish("BattleCompleted", {
            "winner": winner,
            "reason": reason,
            "team_one_alive": self._count_alive_characters(self.battle_context.team_one),
            "team_two_alive": self._count_alive_characters(self.battle_context.team_two)
        })
    
    def is_battle_finished(self):
        """Check if the battle has finished.
        
        Returns:
            True if battle is finished, False otherwise
        """
        return self.battle_finished
    
    def get_winner(self):
        """Get the winner of the battle.
        
        Returns:
            Winner identifier or None if battle not finished
        """
        return self.winner if self.battle_finished else None