"""
Validation utilities for the Wanderer Game

Helper functions for data validation and integrity checks.
"""

from typing import List
from ..models import Team, Expedition


class DataValidator:
    """Utility class for validating game data"""
    
    @staticmethod
    def validate_expedition_data(expedition_dict: dict) -> bool:
        """Validate expedition data dictionary"""
        required_fields = [
            'expedition_id', 'name', 'duration_hours', 'difficulty',
            'num_favored_affinities', 'num_disfavored_affinities',
            'affinity_pools', 'encounter_pool_tags'
        ]
        
        for field in required_fields:
            if field not in expedition_dict:
                return False
        
        # Validate types
        if not isinstance(expedition_dict['duration_hours'], int):
            return False
        if not isinstance(expedition_dict['difficulty'], int):
            return False
        
        return True
    
    @staticmethod
    def validate_encounter_data(encounter_dict: dict) -> bool:
        """Validate encounter data dictionary"""
        required_fields = ['encounter_id', 'name', 'type', 'tags']
        
        for field in required_fields:
            if field not in encounter_dict:
                return False
        
        # Type-specific validation
        encounter_type = encounter_dict.get('type')
        if encounter_type == 'STANDARD':
            if 'check_stat' not in encounter_dict or 'difficulty' not in encounter_dict:
                return False
        elif encounter_type == 'GATED':
            if 'condition' not in encounter_dict:
                return False
        
        return True
    
    @staticmethod
    def validate_character_data(character_dict: dict) -> bool:
        """Validate character data dictionary"""
        required_fields = [
            'waifu_id', 'name', 'series', 'series_id', 'genre',
            'stats', 'elemental_type', 'archetype'
        ]
        
        for field in required_fields:
            if field not in character_dict:
                return False
        
        return True


class TeamValidator:
    """Utility class for validating team compositions"""
    
    @staticmethod
    def validate_team_size(team: Team) -> bool:
        """Validate team has correct number of members"""
        return 1 <= len(team.characters) <= 4
    
    @staticmethod
    def validate_unique_characters(team: Team) -> bool:
        """Validate team has no duplicate characters"""
        character_ids = [char.waifu_id for char in team.characters]
        return len(character_ids) == len(set(character_ids))
    
    @staticmethod
    def validate_team_for_expedition(team: Team, expedition: Expedition) -> List[str]:
        """
        Validate team for expedition and return list of warnings/issues
        
        Returns:
            List of warning strings (empty if no issues)
        """
        warnings = []
        
        if not TeamValidator.validate_team_size(team):
            warnings.append("Team must have 1-4 characters")
        
        if not TeamValidator.validate_unique_characters(team):
            warnings.append("Team cannot have duplicate characters")
        
        # Check for obvious mismatches
        favored_count = team.count_affinity_matches(expedition.favored_affinities)
        disfavored_count = team.count_affinity_matches(expedition.disfavored_affinities)
        
        if favored_count == 0 and len(expedition.favored_affinities) > 0:
            warnings.append("Team has no characters matching favored affinities")
        
        if disfavored_count > favored_count:
            warnings.append("Team has more disfavored than favored affinity matches")
        
        return warnings