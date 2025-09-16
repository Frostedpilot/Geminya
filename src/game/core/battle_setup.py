"""Battle setup and initialization."""

from src.game.core.battle_context import BattleContext
from src.game.core.character_factory import CharacterFactory

class BattleSetup:
    """Handles battle initialization and character setup."""
    
    def __init__(self, character_factory):
        self.character_factory = character_factory
    
    def create_battle(self, team_one_ids, team_two_ids):
        """Create a battle with two teams of characters.
        
        Args:
            team_one_ids: List of character IDs for team one
            team_two_ids: List of character IDs for team two
            
        Returns:
            BattleContext with populated teams
        """
        battle_context = BattleContext()
        
        # Create team one characters
        for i, char_id in enumerate(team_one_ids):
            character = self.character_factory.create_character(char_id, team=1, position=i)
            battle_context.team_one.append(character)
        
        # Create team two characters
        for i, char_id in enumerate(team_two_ids):
            character = self.character_factory.create_character(char_id, team=2, position=i)
            battle_context.team_two.append(character)
        
        return battle_context