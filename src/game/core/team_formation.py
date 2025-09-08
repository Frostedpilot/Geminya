"""
Team Formation System

Handles team composition, positioning, and formation-based mechanics
including front/back row positioning and leader designation.
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

class Position(Enum):
    """Character position in battle formation"""
    FRONT_LEFT = "front_left"
    FRONT_CENTER = "front_center"  
    FRONT_RIGHT = "front_right"
    BACK_LEFT = "back_left"
    BACK_CENTER = "back_center"
    BACK_RIGHT = "back_right"

class Row(Enum):
    """Battle formation rows"""
    FRONT = "front"
    BACK = "back"

@dataclass
class TeamSlot:
    """A single slot in team formation"""
    position: Position
    character_id: Optional[str] = None
    is_leader: bool = False
    
    @property
    def row(self) -> Row:
        """Get the row this position belongs to"""
        if self.position.value.startswith("front"):
            return Row.FRONT
        return Row.BACK
    
    @property
    def is_occupied(self) -> bool:
        """Check if this slot has a character"""
        return self.character_id is not None

class TeamFormation:
    """Manages team formation and positioning"""
    
    def __init__(self, team_id: str):
        self.team_id = team_id
        self.slots: Dict[Position, TeamSlot] = {}
        self.leader_id: Optional[str] = None
        
        # Initialize all positions
        for position in Position:
            self.slots[position] = TeamSlot(position)
    
    def add_character(self, character_id: str, position: Position, is_leader: bool = False) -> bool:
        """Add a character to a specific position"""
        if self.slots[position].is_occupied:
            logger.warning("Position %s is already occupied", position.value)
            return False
        
        # Remove character from any existing position
        self.remove_character(character_id)
        
        # Add to new position
        self.slots[position].character_id = character_id
        
        # Handle leader designation
        if is_leader:
            self.set_leader(character_id)
        
        logger.info("Added character %s to %s (leader: %s)", character_id, position.value, is_leader)
        return True
    
    def remove_character(self, character_id: str) -> bool:
        """Remove a character from the formation"""
        for position, slot in self.slots.items():
            if slot.character_id == character_id:
                slot.character_id = None
                if self.leader_id == character_id:
                    self.leader_id = None
                    slot.is_leader = False
                logger.info("Removed character %s from %s", character_id, position.value)
                return True
        return False
    
    def set_leader(self, character_id: str) -> bool:
        """Designate a character as team leader"""
        # Check if character is in formation
        character_position = self.get_character_position(character_id)
        if not character_position:
            logger.warning("Cannot set leader: character %s not in formation", character_id)
            return False
        
        # Remove previous leader status
        if self.leader_id:
            old_leader_pos = self.get_character_position(self.leader_id)
            if old_leader_pos:
                self.slots[old_leader_pos].is_leader = False
        
        # Set new leader
        self.leader_id = character_id
        self.slots[character_position].is_leader = True
        
        logger.info("Set %s as team leader", character_id)
        return True
    
    def get_character_position(self, character_id: str) -> Optional[Position]:
        """Get the position of a character"""
        for position, slot in self.slots.items():
            if slot.character_id == character_id:
                return position
        return None
    
    def get_characters_in_row(self, row: Row) -> List[str]:
        """Get all character IDs in a specific row"""
        characters = []
        for slot in self.slots.values():
            if slot.row == row and slot.is_occupied:
                characters.append(slot.character_id)
        return characters
    
    def get_front_row_characters(self) -> List[str]:
        """Get all characters in front row"""
        return self.get_characters_in_row(Row.FRONT)
    
    def get_back_row_characters(self) -> List[str]:
        """Get all characters in back row"""
        return self.get_characters_in_row(Row.BACK)
    
    def is_front_row_empty(self) -> bool:
        """Check if front row is completely empty"""
        return len(self.get_front_row_characters()) == 0
    
    def get_all_characters(self) -> List[str]:
        """Get all character IDs in formation"""
        return [slot.character_id for slot in self.slots.values() if slot.is_occupied and slot.character_id is not None]
    
    def get_valid_targets(self, can_target_back_row: bool = False) -> List[str]:
        """Get valid targets based on targeting rules"""
        front_row = self.get_front_row_characters()
        
        # If front row exists and skill can't target back row, only front row is valid
        if front_row and not can_target_back_row:
            return front_row
        
        # If front row is empty or skill can target back row, all characters are valid
        return self.get_all_characters()
    
    def get_adjacent_positions(self, position: Position) -> List[Position]:
        """Get positions adjacent to the given position"""
        
        # Define adjacency rules
        adjacency_map = {
            Position.FRONT_LEFT: [Position.FRONT_CENTER],
            Position.FRONT_CENTER: [Position.FRONT_LEFT, Position.FRONT_RIGHT],
            Position.FRONT_RIGHT: [Position.FRONT_CENTER],
            Position.BACK_LEFT: [Position.BACK_CENTER],
            Position.BACK_CENTER: [Position.BACK_LEFT, Position.BACK_RIGHT],
            Position.BACK_RIGHT: [Position.BACK_CENTER],
        }
        
        return adjacency_map.get(position, [])
    
    def get_characters_adjacent_to(self, character_id: str) -> List[str]:
        """Get characters adjacent to the specified character"""
        position = self.get_character_position(character_id)
        if not position:
            return []
        
        adjacent_chars = []
        for adj_pos in self.get_adjacent_positions(position):
            slot = self.slots[adj_pos]
            if slot.is_occupied:
                adjacent_chars.append(slot.character_id)
        
        return adjacent_chars
    
    def get_formation_summary(self) -> Dict:
        """Get a summary of the current formation"""
        return {
            "team_id": self.team_id,
            "leader_id": self.leader_id,
            "front_row": self.get_front_row_characters(),
            "back_row": self.get_back_row_characters(),
            "total_characters": len(self.get_all_characters()),
            "positions": {
                pos.value: slot.character_id for pos, slot in self.slots.items() 
                if slot.is_occupied
            }
        }

class FormationManager:
    """Manages formations for all teams in a battle"""
    
    def __init__(self):
        self.formations: Dict[str, TeamFormation] = {}
        logger.info("Initialized Formation Manager")
    
    def create_team_formation(self, team_id: str) -> TeamFormation:
        """Create a new team formation"""
        formation = TeamFormation(team_id)
        self.formations[team_id] = formation
        logger.info("Created formation for team %s", team_id)
        return formation
    
    def get_formation(self, team_id: str) -> Optional[TeamFormation]:
        """Get formation for a team"""
        return self.formations.get(team_id)
    
    def get_character_formation(self, character_id: str) -> Optional[TeamFormation]:
        """Find which formation a character belongs to"""
        for formation in self.formations.values():
            if character_id in formation.get_all_characters():
                return formation
        return None
    
    def get_character_position(self, character_id: str) -> Optional[Position]:
        """Get the position of a character across all formations"""
        formation = self.get_character_formation(character_id)
        if formation:
            return formation.get_character_position(character_id)
        return None
    
    def is_character_leader(self, character_id: str) -> bool:
        """Check if a character is a team leader"""
        formation = self.get_character_formation(character_id)
        return formation is not None and formation.leader_id == character_id
    
    def get_valid_targets_for_character(self, attacker_id: str, can_target_back_row: bool = False) -> List[str]:
        """Get valid targets for an attacking character"""
        attacker_formation = self.get_character_formation(attacker_id)
        if not attacker_formation:
            return []
        
        # Get all enemy formations
        valid_targets = []
        for formation in self.formations.values():
            if formation.team_id != attacker_formation.team_id:
                valid_targets.extend(formation.get_valid_targets(can_target_back_row))
        
        return valid_targets
    
    def get_all_formations_summary(self) -> Dict:
        """Get summary of all formations"""
        return {
            team_id: formation.get_formation_summary() 
            for team_id, formation in self.formations.items()
        }
