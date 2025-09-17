"""Turn system for managing action gauges and turn order."""

import random
from .base_system import BaseSystem

class TurnSystem(BaseSystem):
    """Manages the action gauge system and turn ordering."""
    
    def initialize(self):
        """Initialize action gauges for all characters."""
        self.active_character = None
        self.initialize_action_gauges()
    
    def initialize_action_gauges(self):
        """Set initial action gauge values for all characters."""
        all_characters = self.battle_context.team_one + self.battle_context.team_two
        
        for character in all_characters:
            state_component = character.components.get('state')
            if state_component and state_component.is_alive:
                # First turn normalization: random value between 400-600
                state_component.action_gauge = random.randint(400, 600)
    
    def tick(self):
        """Advance action gauges for all living characters."""
        all_characters = self.battle_context.team_one + self.battle_context.team_two
        
        for character in all_characters:
            state_component = character.components.get('state')
            stats_component = character.components.get('stats')
            
            if state_component and stats_component and state_component.is_alive:
                spd = stats_component.get_stat('spd')
                state_component.action_gauge += spd
    
    def get_active_character(self):
        """Get the character ready to act (action gauge >= 1000).
        
        Returns:
            Character ready to act, or None if no character is ready
        """
        all_characters = self.battle_context.team_one + self.battle_context.team_two
        ready_characters = []
        
        for character in all_characters:
            state_component = character.components.get('state')
            if state_component and state_component.is_alive and state_component.action_gauge >= 1000:
                ready_characters.append((character, state_component.action_gauge))
        
        if not ready_characters:
            return None
        
        # Sort by action gauge (highest first), then by random for ties
        ready_characters.sort(key=lambda x: (-x[1], random.random()))
        active_character = ready_characters[0][0]
        
        # Publish OnTurnStart event
        self.event_bus.publish("OnTurnStart", {"character": active_character})
        self.active_character = active_character
        
        return active_character
    
    def end_turn(self, character):
        """End the turn for the specified character."""
        state_component = character.components.get('state')
        if state_component:
            # Reset action gauge, keeping overflow
            overflow = state_component.action_gauge - 1000
            state_component.action_gauge = max(0, overflow)
            
            # Increment turn counter and tick cooldowns
            state_component.turn_count += 1
            state_component.tick_cooldowns()
        
        # Publish OnTurnEnded event
        self.event_bus.publish("OnTurnEnded", {"character": character})
        self.active_character = None