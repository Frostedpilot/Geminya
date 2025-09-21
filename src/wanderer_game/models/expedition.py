"""
Expedition models for the Wanderer Game

Based on the base_expeditions.json structure.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import random
from .character import Affinity, AffinityType


@dataclass
class AffinityPool:
    """Pool of potential affinities for random selection"""
    elemental: List[str] = field(default_factory=list)
    archetype: List[str] = field(default_factory=list)
    series_id: List[int] = field(default_factory=list)
    genre: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, List]) -> 'AffinityPool':
        """Create AffinityPool from dictionary"""
        return cls(
            elemental=data.get('elemental', []),
            archetype=data.get('archetype', []),
            series_id=data.get('series_id', []),
            genre=data.get('genre', [])
        )
    
    def get_all_affinities(self) -> List[Affinity]:
        """Get all possible affinities from this pool"""
        affinities = []
        
        for elem in self.elemental:
            affinities.append(Affinity(AffinityType.ELEMENTAL, elem))
        
        for arch in self.archetype:
            affinities.append(Affinity(AffinityType.ARCHETYPE, arch))
            
        for series in self.series_id:
            affinities.append(Affinity(AffinityType.SERIES_ID, str(series)))
            
        for genre in self.genre:
            affinities.append(Affinity(AffinityType.GENRE, genre))
        
        return affinities
    
    def select_random_affinities(self, count: int) -> List[Affinity]:
        """Randomly select affinities from this pool"""
        all_affinities = self.get_all_affinities()
        if count >= len(all_affinities):
            return all_affinities
        return random.sample(all_affinities, count)


@dataclass
class ExpeditionTemplate:
    """
    Template for generating expeditions with randomized affinities
    Based on base_expeditions.json structure
    """
    expedition_id: str
    name: str
    duration_hours: int
    difficulty: int
    num_favored_affinities: int
    num_disfavored_affinities: int
    favored_pool: AffinityPool
    disfavored_pool: AffinityPool
    encounter_pool_tags: List[str]
    dominant_stats: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExpeditionTemplate':
        """Create ExpeditionTemplate from dictionary (JSON data)"""
        affinity_pools = data.get('affinity_pools', {})
        dominant_stats = data.get('dominant_stats', [])
        return cls(
            expedition_id=data['expedition_id'],
            name=data['name'],
            duration_hours=data['duration_hours'],
            difficulty=data['difficulty'],
            num_favored_affinities=data['num_favored_affinities'],
            num_disfavored_affinities=data['num_disfavored_affinities'],
            favored_pool=AffinityPool.from_dict(affinity_pools.get('favored', {})),
            disfavored_pool=AffinityPool.from_dict(affinity_pools.get('disfavored', {})),
            encounter_pool_tags=data['encounter_pool_tags'],
            dominant_stats=dominant_stats
        )
    
    def generate_expedition(self, team_series_ids: Optional[List[int]] = None) -> 'Expedition':
        """Generate a specific expedition instance with randomized affinities"""
        # Select random affinities from pools
        favored_affinities = self.favored_pool.select_random_affinities(self.num_favored_affinities)
        disfavored_affinities = self.disfavored_pool.select_random_affinities(self.num_disfavored_affinities)

        # Calculate encounter count based on duration
        # Formula: floor(DurationInHours * (0.5 + random_float_0_to_1 * 1.0))
        random_factor = random.random()  # 0.0 to 1.0
        encounter_count = max(1, int(self.duration_hours * (0.5 + random_factor * 1.0)))  # 0.5x to 1.5x

        # Build dynamic encounter pool tags
        dynamic_tags = self.encounter_pool_tags.copy()
        if team_series_ids:
            # Add series IDs as tags for series-specific content
            dynamic_tags.extend([str(sid) for sid in team_series_ids])

        expedition = Expedition(
            expedition_id=self.expedition_id,
            name=self.name,
            duration_hours=self.duration_hours,
            difficulty=self.difficulty,
            favored_affinities=favored_affinities,
            disfavored_affinities=disfavored_affinities,
            encounter_pool_tags=dynamic_tags,
            encounter_count=encounter_count,
            dominant_stats=self.dominant_stats.copy() if self.dominant_stats else []
        )
        # Attach expected_encounters for downstream display/logic
        setattr(expedition, 'expected_encounters', encounter_count)
        return expedition


@dataclass
class Expedition:
    """
    A specific expedition instance with resolved affinities and parameters
    """
    expedition_id: str
    name: str
    duration_hours: int
    difficulty: int
    favored_affinities: List[Affinity]
    disfavored_affinities: List[Affinity]
    encounter_pool_tags: List[str]
    encounter_count: int
    dominant_stats: List[str] = field(default_factory=list)
    
    # Dynamic modifiers that can be applied during expedition
    dynamic_favored_affinities: List[Affinity] = field(default_factory=list)
    dynamic_disfavored_affinities: List[Affinity] = field(default_factory=list)
    stat_bonuses: Dict[str, int] = field(default_factory=dict)
    difficulty_modifiers: List[float] = field(default_factory=list)
    # Final stat check bonuses (applied after all multipliers, per stat)
    final_stat_check_bonuses: Dict[str, int] = field(default_factory=dict)
    
    # Complex state tracking for encounter-affecting modifiers
    guaranteed_success_encounters: int = 0
    skip_encounters: int = 0
    prevent_mishaps: bool = False
    prevent_failure: bool = False
    loot_multipliers: List[float] = field(default_factory=list)
    encounter_specific_loot_bonus: Dict[str, float] = field(default_factory=dict)  # encounter_type -> bonus
    success_rate_bonus: float = 0.0
    
    def get_all_favored_affinities(self) -> List[Affinity]:
        """Get all favored affinities (base + dynamic)"""
        return self.favored_affinities + self.dynamic_favored_affinities
    
    def get_all_disfavored_affinities(self) -> List[Affinity]:
        """Get all disfavored affinities (base + dynamic)"""
        return self.disfavored_affinities + self.dynamic_disfavored_affinities
    
    def add_dynamic_favored_affinity(self, affinity: Affinity):
        """Add a temporary favored affinity (from BOON encounters)"""
        self.dynamic_favored_affinities.append(affinity)
    
    def add_dynamic_disfavored_affinity(self, affinity: Affinity):
        """Add a temporary disfavored affinity (from HAZARD encounters)"""
        self.dynamic_disfavored_affinities.append(affinity)
    
    def add_stat_bonus(self, stat: str, bonus: int):
        """Add a stat bonus/penalty modifier"""
        current_bonus = self.stat_bonuses.get(stat, 0)
        self.stat_bonuses[stat] = current_bonus + bonus
    
    def add_difficulty_modifier(self, modifier: float):
        """Add a difficulty modifier (multiplicative)"""
        self.difficulty_modifiers.append(modifier)
    
    def get_effective_difficulty(self, base_difficulty: int) -> int:
        """Calculate effective difficulty with all modifiers applied"""
        modified_difficulty = float(base_difficulty)
        for modifier in self.difficulty_modifiers:
            modified_difficulty *= modifier
        return int(modified_difficulty)
    
    def get_effective_stat(self, base_stat: int, stat_name: str) -> int:
        """Get effective stat value with bonuses applied"""
        bonus = self.stat_bonuses.get(stat_name, 0)
        return max(0, base_stat + bonus)  # Don't allow negative stats
    
    def add_loot_multiplier(self, multiplier: float):
        """Add a loot multiplier"""
        self.loot_multipliers.append(multiplier)
    
    def add_encounter_loot_bonus(self, encounter_type: str, bonus: float):
        """Add specific loot bonus for encounter type"""
        current_bonus = self.encounter_specific_loot_bonus.get(encounter_type, 0.0)
        self.encounter_specific_loot_bonus[encounter_type] = current_bonus + bonus
    
    def add_success_rate_bonus(self, bonus: float):
        """Add success rate bonus (additive)"""
        self.success_rate_bonus += bonus
    
    def consume_guaranteed_success(self) -> bool:
        """Use one guaranteed success if available"""
        if self.guaranteed_success_encounters > 0:
            self.guaranteed_success_encounters -= 1
            return True
        return False
    
    def consume_skip_encounter(self) -> bool:
        """Use one skip encounter if available"""
        if self.skip_encounters > 0:
            self.skip_encounters -= 1
            return True
        return False
    
    def get_effective_loot_multiplier(self) -> float:
        """Get combined loot multiplier"""
        multiplier = 1.0
        for mult in self.loot_multipliers:
            multiplier *= mult
        return multiplier


class ExpeditionStatus(Enum):
    """Status of an expedition"""
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class ActiveExpedition:
    """Represents an expedition that has been dispatched and is in progress"""
    expedition: Expedition
    team_character_ids: List[int]
    start_timestamp: float
    end_timestamp: float
    status: ExpeditionStatus = ExpeditionStatus.ACTIVE
    
    def is_complete(self, current_timestamp: float) -> bool:
        """Check if the expedition is complete"""
        return current_timestamp >= self.end_timestamp
    
    def get_time_remaining(self, current_timestamp: float) -> float:
        """Get remaining time in seconds"""
        if self.is_complete(current_timestamp):
            return 0.0
        return self.end_timestamp - current_timestamp