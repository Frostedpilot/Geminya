from typing import Dict, List, Any, Optional, Set, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import copy
import logging

if TYPE_CHECKING:
    from ..components.character import Character

from .team_formation import FormationManager, Position

logger = logging.getLogger(__name__)

class BattlePhase(Enum):
    """Battle phases for different mechanics"""
    SETUP = "setup"
    PRE_BATTLE = "pre_battle"
    BATTLE = "battle"
    POST_BATTLE = "post_battle"
    CLEANUP = "cleanup"

class TurnPhase(Enum):
    """Turn phases within battle"""
    TURN_START = "turn_start"
    ACTION_SELECTION = "action_selection"
    ACTION_EXECUTION = "action_execution"
    TURN_END = "turn_end"

@dataclass
class BattleSnapshot:
    """Snapshot of battle state at a specific point in time"""
    battle_id: str
    turn_number: int
    phase: BattlePhase
    turn_phase: TurnPhase
    active_character_id: Optional[str]
    character_states: Dict[str, Dict[str, Any]]
    global_effects: Dict[str, Any]
    timestamp: float = field(default_factory=lambda: __import__('time').time())

@dataclass
class BattleRules:
    """Configuration for battle mechanics"""
    max_turns: int = 100
    turn_timeout: float = 30.0
    auto_resolve_timeout: bool = True
    friendly_fire: bool = False
    max_characters_per_team: int = 6
    enable_snapshots: bool = True
    snapshot_frequency: int = 5  # Every N turns

class BattleContext:
    """
    Central battle state management and context provider.
    Handles battle flow, state tracking, and provides context for events.
    """
    
    def __init__(self, battle_id: str, rules: Optional[BattleRules] = None):
        self.battle_id = battle_id
        self.rules = rules or BattleRules()
        
        # Battle state
        self.phase = BattlePhase.SETUP
        self.turn_phase = TurnPhase.TURN_START
        self.turn_number = 0
        self.active_character_id: Optional[str] = None
        
        # Characters and teams
        self.characters: Dict[str, 'Character'] = {}
        self.teams: Dict[str, Set[str]] = {}  # team_id -> character_ids
        self.character_teams: Dict[str, str] = {}  # character_id -> team_id
        
        # Team formation system
        self.formation_manager = FormationManager()
        
        # Battle state tracking
        self.global_effects: Dict[str, Any] = {}
        self.turn_order: List[str] = []
        self.battle_log: List[Dict[str, Any]] = []
        
        # Snapshots for rollback/debugging
        self.snapshots: List[BattleSnapshot] = []
        self.max_snapshots = 20
        
        # Battle results
        self.winners: Set[str] = set()
        self.is_complete = False
        self.completion_reason = ""
        
        logger.info("Created battle context for battle %s", battle_id)
    
    def add_character(self, character: 'Character', team_id: str, position: Optional[Position] = None, is_leader: bool = False) -> bool:
        """Add a character to the battle with optional formation position"""
        if character.character_id in self.characters:
            logger.warning("Character %s already in battle", character.character_id)
            return False
        
        if team_id not in self.teams:
            self.teams[team_id] = set()
            # Create formation for new team
            self.formation_manager.create_team_formation(team_id)
        
        if len(self.teams[team_id]) >= self.rules.max_characters_per_team:
            logger.warning("Team %s already has maximum characters", team_id)
            return False
        
        self.characters[character.character_id] = character
        self.teams[team_id].add(character.character_id)
        self.character_teams[character.character_id] = team_id
        
        # Add to formation if position specified
        if position:
            formation = self.formation_manager.get_formation(team_id)
            if formation:
                formation.add_character(character.character_id, position, is_leader)
        
        logger.debug("Added character %s to team %s", 
                    character.character_id, team_id)
        return True
    
    def remove_character(self, character_id: str) -> bool:
        """Remove a character from battle"""
        if character_id not in self.characters:
            return False
        
        team_id = self.character_teams.get(character_id)
        if team_id and character_id in self.teams[team_id]:
            self.teams[team_id].remove(character_id)
        
        del self.characters[character_id]
        if character_id in self.character_teams:
            del self.character_teams[character_id]
        
        # Remove from turn order if present
        if character_id in self.turn_order:
            self.turn_order.remove(character_id)
        
        # Update active character if needed
        if self.active_character_id == character_id:
            self.active_character_id = None
        
        logger.debug("Removed character %s from battle", character_id)
        return True
    
    def get_character(self, character_id: str) -> Optional['Character']:
        """Get a character by ID"""
        return self.characters.get(character_id)
    
    def get_team_characters(self, team_id: str) -> List['Character']:
        """Get all characters in a team"""
        if team_id not in self.teams:
            return []
        return [self.characters[char_id] for char_id in self.teams[team_id] 
                if char_id in self.characters]
    
    def get_enemy_characters(self, character_id: str) -> List['Character']:
        """Get all enemy characters for a given character"""
        character_team = self.character_teams.get(character_id)
        if not character_team:
            return []
        
        enemies = []
        for team_id, char_ids in self.teams.items():
            if team_id != character_team:
                enemies.extend([self.characters[char_id] for char_id in char_ids
                              if char_id in self.characters])
        return enemies
    
    def get_ally_characters(self, character_id: str) -> List['Character']:
        """Get all ally characters for a given character"""
        character_team = self.character_teams.get(character_id)
        if not character_team:
            return []
        
        return [self.characters[char_id] for char_id in self.teams[character_team]
                if char_id in self.characters and char_id != character_id]
    
    def set_phase(self, phase: BattlePhase):
        """Set the current battle phase"""
        old_phase = self.phase
        self.phase = phase
        logger.debug("Battle %s phase changed from %s to %s", 
                    self.battle_id, old_phase, phase)
    
    def set_turn_phase(self, turn_phase: TurnPhase):
        """Set the current turn phase"""
        old_phase = self.turn_phase
        self.turn_phase = turn_phase
        logger.debug("Battle %s turn phase changed from %s to %s", 
                    self.battle_id, old_phase, turn_phase)
    
    def advance_turn(self) -> bool:
        """Advance to the next turn"""
        self.turn_number += 1
        self.set_turn_phase(TurnPhase.TURN_START)
        
        # Check for turn limit
        if self.turn_number >= self.rules.max_turns:
            self.complete_battle("Turn limit reached")
            return False
        
        # Create snapshot if configured
        if (self.rules.enable_snapshots and 
            self.turn_number % self.rules.snapshot_frequency == 0):
            self.create_snapshot()
        
        logger.debug("Battle %s advanced to turn %d", 
                    self.battle_id, self.turn_number)
        return True
    
    def set_active_character(self, character_id: Optional[str]):
        """Set the currently active character"""
        if character_id and character_id not in self.characters:
            logger.warning("Trying to set inactive character %s as active", 
                         character_id)
            return False
        
        old_active = self.active_character_id
        self.active_character_id = character_id
        logger.debug("Active character changed from %s to %s", 
                    old_active, character_id)
        return True
    
    def add_global_effect(self, effect_id: str, effect_data: Dict[str, Any]):
        """Add a global battle effect"""
        self.global_effects[effect_id] = effect_data
        logger.debug("Added global effect %s", effect_id)
    
    def remove_global_effect(self, effect_id: str) -> bool:
        """Remove a global battle effect"""
        if effect_id in self.global_effects:
            del self.global_effects[effect_id]
            logger.debug("Removed global effect %s", effect_id)
            return True
        return False
    
    def log_action(self, action_type: str, data: Dict[str, Any]):
        """Log a battle action"""
        log_entry = {
            'turn': self.turn_number,
            'phase': self.phase.value,
            'turn_phase': self.turn_phase.value,
            'action_type': action_type,
            'timestamp': __import__('time').time(),
            'data': data
        }
        self.battle_log.append(log_entry)
        
        # Limit log size
        if len(self.battle_log) > 1000:
            self.battle_log.pop(0)
    
    def create_snapshot(self) -> BattleSnapshot:
        """Create a snapshot of current battle state"""
        character_states = {}
        for char_id, character in self.characters.items():
            # Serialize character state (implementation depends on character structure)
            character_states[char_id] = self._serialize_character_state(character)
        
        snapshot = BattleSnapshot(
            battle_id=self.battle_id,
            turn_number=self.turn_number,
            phase=self.phase,
            turn_phase=self.turn_phase,
            active_character_id=self.active_character_id,
            character_states=character_states,
            global_effects=copy.deepcopy(self.global_effects)
        )
        
        self.snapshots.append(snapshot)
        
        # Limit snapshot count
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots.pop(0)
        
        logger.debug("Created snapshot for turn %d", self.turn_number)
        return snapshot
    
    def restore_snapshot(self, snapshot: BattleSnapshot) -> bool:
        """Restore battle state from a snapshot"""
        try:
            self.turn_number = snapshot.turn_number
            self.phase = snapshot.phase
            self.turn_phase = snapshot.turn_phase
            self.active_character_id = snapshot.active_character_id
            self.global_effects = copy.deepcopy(snapshot.global_effects)
            
            # Restore character states
            for char_id, state in snapshot.character_states.items():
                if char_id in self.characters:
                    self._restore_character_state(self.characters[char_id], state)
            
            logger.info("Restored battle state from snapshot at turn %d", 
                       snapshot.turn_number)
            return True
        except (ValueError, TypeError, AttributeError) as e:
            logger.error("Failed to restore snapshot: %s", e)
            return False
    
    def check_victory_conditions(self) -> bool:
        """Check if any team has won the battle"""
        active_teams = set()
        
        for team_id, char_ids in self.teams.items():
            team_has_active = False
            for char_id in char_ids:
                character = self.characters.get(char_id)
                if character and self._is_character_active(character):
                    team_has_active = True
                    break
            
            if team_has_active:
                active_teams.add(team_id)
        
        # Check victory conditions
        if len(active_teams) <= 1:
            self.winners = active_teams
            reason = "Enemy team eliminated" if active_teams else "All teams eliminated"
            self.complete_battle(reason)
            return True
        
        return False
    
    def complete_battle(self, reason: str):
        """Mark the battle as complete"""
        self.is_complete = True
        self.completion_reason = reason
        self.set_phase(BattlePhase.POST_BATTLE)
        
        logger.info("Battle %s completed: %s. Winners: %s", 
                   self.battle_id, reason, self.winners)
    
    def get_battle_summary(self) -> Dict[str, Any]:
        """Get a summary of the current battle state"""
        return {
            'battle_id': self.battle_id,
            'phase': self.phase.value,
            'turn_phase': self.turn_phase.value,
            'turn_number': self.turn_number,
            'active_character': self.active_character_id,
            'is_complete': self.is_complete,
            'completion_reason': self.completion_reason,
            'winners': list(self.winners),
            'teams': {team_id: list(char_ids) for team_id, char_ids in self.teams.items()},
            'character_count': len(self.characters),
            'global_effects_count': len(self.global_effects),
            'turn_order': self.turn_order.copy()
        }
    
    # Formation-related methods
    def get_character_position(self, character_id: str) -> Optional[Position]:
        """Get the formation position of a character"""
        return self.formation_manager.get_character_position(character_id)
    
    def is_character_leader(self, character_id: str) -> bool:
        """Check if a character is a team leader"""
        return self.formation_manager.is_character_leader(character_id)
    
    def get_valid_targets_for_attack(self, attacker_id: str, can_target_back_row: bool = False) -> List[str]:
        """Get valid targets for an attack based on formation rules"""
        return self.formation_manager.get_valid_targets_for_character(attacker_id, can_target_back_row)
    
    def get_characters_in_position_range(self, character_id: str, include_adjacent: bool = False) -> List[str]:
        """Get characters in the same position or adjacent positions"""
        formation = self.formation_manager.get_character_formation(character_id)
        if not formation:
            return []
        
        targets = [character_id]
        if include_adjacent:
            targets.extend(formation.get_characters_adjacent_to(character_id))
        
        return targets
    
    def apply_leader_bonuses(self):
        """Apply leader bonuses to designated leaders"""
        for formation in self.formation_manager.formations.values():
            if formation.leader_id and formation.leader_id in self.characters:
                leader = self.characters[formation.leader_id]
                # Apply +10% bonus to all base stats
                leader.stats.apply_leader_bonus()
                logger.debug("Applied leader bonus to %s", formation.leader_id)
    
    def get_formation_summary(self) -> Dict:
        """Get summary of all team formations"""
        return self.formation_manager.get_all_formations_summary()
    
    def _serialize_character_state(self, character: 'Character') -> Dict[str, Any]:
        """Serialize character state for snapshots"""
        try:
            return {
                'character_id': character.character_id,
                'name': character.name,
                'current_hp': character.current_hp,
                'max_hp': character.max_hp,
                'stats': character.stats.to_dict() if hasattr(character.stats, 'to_dict') else {},
                'status_effects': [
                    {
                        'effect_type': effect.effect_type,
                        'duration': effect.duration,
                        'value': getattr(effect, 'value', 0),
                        'stacks': getattr(effect, 'stacks', 1)
                    } for effect in character.effects.active_effects
                ] if hasattr(character, 'effects') and character.effects else [],
                'skill_cooldowns': {
                    skill_id: cooldown for skill_id, cooldown in character.skill_cooldowns.items()
                } if hasattr(character, 'skill_cooldowns') else {},
                'position': character.position if hasattr(character, 'position') else {'x': 0, 'y': 0},
                'team_id': character.team_id,
                'is_alive': character.is_alive()
            }
        except Exception as e:
            logger.warning(f"Failed to serialize character {character.character_id}: {e}")
            return {
                'character_id': character.character_id,
                'error': f'Serialization failed: {str(e)}'
            }
    
    def _restore_character_state(self, character: 'Character', state: Dict[str, Any]):  # pylint: disable=unused-argument
        """Restore character state from snapshot data"""
        try:
            if 'error' in state:
                logger.warning(f"Cannot restore character {character.character_id}: {state['error']}")
                return
            
            # Restore HP
            if 'current_hp' in state:
                character.current_hp = state['current_hp']
            
            # Restore status effects
            if 'status_effects' in state and hasattr(character, 'effects'):
                character.effects.clear_all_effects()
                for effect_data in state['status_effects']:
                    try:
                        # Reconstruct effect (simplified)
                        character.effects.add_effect(
                            effect_type=effect_data.get('effect_type', 'unknown'),
                            duration=effect_data.get('duration', 1),
                            value=effect_data.get('value', 0),
                            stacks=effect_data.get('stacks', 1)
                        )
                    except Exception as e:
                        logger.warning(f"Failed to restore effect {effect_data}: {e}")
            
            # Restore skill cooldowns
            if 'skill_cooldowns' in state and hasattr(character, 'skill_cooldowns'):
                character.skill_cooldowns.update(state['skill_cooldowns'])
            
            # Restore position
            if 'position' in state and hasattr(character, 'position'):
                character.position = state['position']
                
            logger.debug(f"Successfully restored character {character.character_id} state")
            
        except Exception as e:
            logger.error(f"Failed to restore character {character.character_id} state: {e}")
    
    def _is_character_active(self, character: 'Character') -> bool:  # pylint: disable=unused-argument
        """Check if a character is still active in battle"""
        # This would need to be implemented based on the character structure
        # For now, assume characters are always active
        return True
