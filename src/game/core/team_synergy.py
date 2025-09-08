"""
Team Synergy System

Implements series-based team bonuses when multiple characters from the same
anime series are on the same team, as described in the design document.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

from ..components.stats_component import StatModifier, StatType, ModifierType

logger = logging.getLogger(__name__)

class SynergyTier(Enum):
    """Synergy bonus tiers based on character count"""
    TIER_1 = "tier_1"  # 2 characters
    TIER_2 = "tier_2"  # 4 characters  
    TIER_3 = "tier_3"  # 6 characters

@dataclass
class SynergyBonus:
    """Individual synergy bonus effect"""
    bonus_type: str             # "stat_modifier", "status_effect", "special_ability"
    target_stat: Optional[str] = None
    value: float = 0.0
    effect_name: Optional[str] = None
    description: str = ""
    duration: Optional[int] = None  # None = permanent

@dataclass
class SeriesSynergy:
    """Complete synergy definition for an anime series"""
    series_id: str
    series_name: str
    tier_1_bonus: SynergyBonus  # 2 characters
    tier_2_bonus: SynergyBonus  # 4 characters
    tier_3_bonus: SynergyBonus  # 6 characters
    required_characters: Dict[SynergyTier, int]

class TeamSynergySystem:
    """Manages team synergy bonuses and series effects"""
    
    def __init__(self):
        self.series_synergies: Dict[str, SeriesSynergy] = {}
        self._initialize_series_synergies()
        logger.info("Initialized team synergy system with %d series", len(self.series_synergies))
    
    def _initialize_series_synergies(self):
        """Initialize all series synergies from the design document"""
        
        synergies = [
            # K-On! Series
            SeriesSynergy(
                series_id="k_on",
                series_name="K-On!",
                tier_1_bonus=SynergyBonus(
                    bonus_type="stat_modifier",
                    target_stat="spd",
                    value=0.10,
                    description="+10% SPD for all allies."
                ),
                tier_2_bonus=SynergyBonus(
                    bonus_type="stat_modifier",
                    target_stat="mag",
                    value=0.10,
                    description="+10% MAG for all allies."
                ),
                tier_3_bonus=SynergyBonus(
                    bonus_type="status_effect",
                    effect_name="regen",
                    duration=2,
                    description="All allies gain a small 'Regen' effect for the first 2 rounds."
                ),
                required_characters={
                    SynergyTier.TIER_1: 2,
                    SynergyTier.TIER_2: 4,
                    SynergyTier.TIER_3: 6
                }
            ),
            
            # Re:Zero Series
            SeriesSynergy(
                series_id="re_zero",
                series_name="Re:Zero",
                tier_1_bonus=SynergyBonus(
                    bonus_type="stat_modifier",
                    target_stat="spr",
                    value=0.15,
                    description="+15% SPR for all allies."
                ),
                tier_2_bonus=SynergyBonus(
                    bonus_type="special_ability",
                    effect_name="death_prevention",
                    description="The first time an ally would be defeated, their HP is set to 1 instead (once per battle)."
                ),
                tier_3_bonus=SynergyBonus(
                    bonus_type="stat_modifier",
                    target_stat="lck",
                    value=0.10,
                    description="+10% LCK for all allies."
                ),
                required_characters={
                    SynergyTier.TIER_1: 2,
                    SynergyTier.TIER_2: 4,
                    SynergyTier.TIER_3: 6
                }
            ),
            
            # Konosuba Series
            SeriesSynergy(
                series_id="konosuba",
                series_name="Konosuba",
                tier_1_bonus=SynergyBonus(
                    bonus_type="stat_modifier",
                    target_stat="lck",
                    value=0.20,
                    description="+20% LCK for all allies."
                ),
                tier_2_bonus=SynergyBonus(
                    bonus_type="special_ability",
                    effect_name="cooldown_chance",
                    value=0.05,
                    description="All skills have a 5% chance to not go on cooldown."
                ),
                tier_3_bonus=SynergyBonus(
                    bonus_type="special_ability",
                    effect_name="random_battle_effects",
                    description="At the start of the battle, apply one random buff to all allies and one random debuff to all enemies."
                ),
                required_characters={
                    SynergyTier.TIER_1: 2,
                    SynergyTier.TIER_2: 4,
                    SynergyTier.TIER_3: 6
                }
            ),
            
            # Attack on Titan Series
            SeriesSynergy(
                series_id="attack_on_titan",
                series_name="Attack on Titan",
                tier_1_bonus=SynergyBonus(
                    bonus_type="stat_modifier",
                    target_stat="atk",
                    value=0.15,
                    description="+15% ATK for all allies."
                ),
                tier_2_bonus=SynergyBonus(
                    bonus_type="stat_modifier",
                    target_stat="vit",
                    value=0.10,
                    description="+10% VIT for all allies."
                ),
                tier_3_bonus=SynergyBonus(
                    bonus_type="special_ability",
                    effect_name="titan_transformation",
                    description="When an ally drops below 25% HP, they gain +25% ATK and +25% SPD for 3 turns."
                ),
                required_characters={
                    SynergyTier.TIER_1: 2,
                    SynergyTier.TIER_2: 4,
                    SynergyTier.TIER_3: 6
                }
            ),
            
            # Demon Slayer Series
            SeriesSynergy(
                series_id="demon_slayer",
                series_name="Demon Slayer",
                tier_1_bonus=SynergyBonus(
                    bonus_type="stat_modifier",
                    target_stat="spd",
                    value=0.12,
                    description="+12% SPD for all allies."
                ),
                tier_2_bonus=SynergyBonus(
                    bonus_type="special_ability",
                    effect_name="breathing_technique",
                    description="Critical hits restore 5% HP to the attacker."
                ),
                tier_3_bonus=SynergyBonus(
                    bonus_type="special_ability",
                    effect_name="demon_slayer_mark",
                    description="All allies immune to poison and burn effects."
                ),
                required_characters={
                    SynergyTier.TIER_1: 2,
                    SynergyTier.TIER_2: 4,
                    SynergyTier.TIER_3: 6
                }
            ),
            
            # Jujutsu Kaisen Series
            SeriesSynergy(
                series_id="jujutsu_kaisen",
                series_name="Jujutsu Kaisen",
                tier_1_bonus=SynergyBonus(
                    bonus_type="stat_modifier",
                    target_stat="mag",
                    value=0.15,
                    description="+15% MAG for all allies."
                ),
                tier_2_bonus=SynergyBonus(
                    bonus_type="special_ability",
                    effect_name="cursed_energy",
                    description="Magical attacks have a 10% chance to apply 'Curse' debuff."
                ),
                tier_3_bonus=SynergyBonus(
                    bonus_type="special_ability",
                    effect_name="domain_expansion",
                    description="Once per battle, all allies can act twice in a single turn."
                ),
                required_characters={
                    SynergyTier.TIER_1: 2,
                    SynergyTier.TIER_2: 4,
                    SynergyTier.TIER_3: 6
                }
            )
        ]
        
        for synergy in synergies:
            self.series_synergies[synergy.series_id] = synergy
    
    def calculate_team_synergies(self, team_characters: List[Dict[str, Any]]) -> Dict[str, List[SynergyBonus]]:
        """Calculate active synergy bonuses for a team"""
        # Count characters by series
        series_counts: Dict[str, int] = {}
        
        for character in team_characters:
            series = character.get("series", "").lower().replace(" ", "_").replace(":", "").replace("!", "")
            if series:
                series_counts[series] = series_counts.get(series, 0) + 1
        
        # Determine active synergies
        active_synergies: Dict[str, List[SynergyBonus]] = {}
        
        for series_id, count in series_counts.items():
            if series_id in self.series_synergies:
                synergy = self.series_synergies[series_id]
                bonuses = []
                
                # Check tier requirements
                if count >= synergy.required_characters[SynergyTier.TIER_1]:
                    bonuses.append(synergy.tier_1_bonus)
                
                if count >= synergy.required_characters[SynergyTier.TIER_2]:
                    bonuses.append(synergy.tier_2_bonus)
                
                if count >= synergy.required_characters[SynergyTier.TIER_3]:
                    bonuses.append(synergy.tier_3_bonus)
                
                if bonuses:
                    active_synergies[series_id] = bonuses
                    logger.info("Activated %d synergy bonuses for series %s with %d characters", 
                               len(bonuses), synergy.series_name, count)
        
        return active_synergies
    
    def apply_synergy_bonuses(self, team_characters: List, active_synergies: Dict[str, List[SynergyBonus]]):
        """Apply synergy bonuses to team characters"""
        
        for series_id, bonuses in active_synergies.items():
            series_synergy = self.series_synergies[series_id]
            
            for bonus in bonuses:
                if bonus.bonus_type == "stat_modifier":
                    self._apply_stat_modifier_synergy(team_characters, bonus, series_id)
                elif bonus.bonus_type == "status_effect":
                    self._apply_status_effect_synergy(team_characters, bonus, series_id)
                elif bonus.bonus_type == "special_ability":
                    self._apply_special_ability_synergy(team_characters, bonus, series_id)
                
                logger.info("Applied synergy bonus '%s' to team (series: %s)", 
                           bonus.description, series_synergy.series_name)
    
    def _apply_stat_modifier_synergy(self, team_characters: List, bonus: SynergyBonus, series_id: str):
        """Apply stat modifier synergy to all team members"""
        for character in team_characters:
            if hasattr(character, 'stats') and bonus.target_stat:
                modifier = StatModifier(
                    modifier_id=f"synergy_{series_id}_{bonus.target_stat}",
                    stat_type=getattr(StatType, bonus.target_stat.upper()),
                    modifier_type=ModifierType.PERCENTAGE,
                    value=bonus.value,
                    source=f"synergy_{series_id}",
                    layer=2,  # Synergy bonuses apply after archetypes
                    duration=bonus.duration
                )
                character.stats.add_modifier(modifier)
                logger.debug("Added synergy stat modifier %s to character %s", 
                           bonus.target_stat, character.character_id)
    
    def _apply_status_effect_synergy(self, team_characters: List, bonus: SynergyBonus, series_id: str):
        """Apply status effect synergy to all team members"""
        # This would integrate with the status effect system
        for character in team_characters:
            logger.debug("Applied synergy status effect %s to character %s (series: %s)", 
                        bonus.effect_name, character.character_id, series_id)
            # In a full implementation, we'd apply the actual status effect here
    
    def _apply_special_ability_synergy(self, team_characters: List, bonus: SynergyBonus, series_id: str):
        """Apply special ability synergy to team"""
        # This would integrate with the special abilities system
        logger.debug("Applied synergy special ability %s to team (series: %s, %d characters)", 
                    bonus.effect_name, series_id, len(team_characters))
        # In a full implementation, we'd register event handlers for special abilities
    
    def get_series_synergy(self, series_id: str) -> Optional[SeriesSynergy]:
        """Get synergy definition for a series"""
        return self.series_synergies.get(series_id)
    
    def get_all_series(self) -> List[str]:
        """Get all available series IDs"""
        return list(self.series_synergies.keys())
    
    def get_synergy_preview(self, series_id: str) -> Dict[str, str]:
        """Get a preview of synergy bonuses for a series"""
        synergy = self.get_series_synergy(series_id)
        if not synergy:
            return {}
        
        return {
            "series_name": synergy.series_name,
            "tier_1": f"({synergy.required_characters[SynergyTier.TIER_1]} chars) {synergy.tier_1_bonus.description}",
            "tier_2": f"({synergy.required_characters[SynergyTier.TIER_2]} chars) {synergy.tier_2_bonus.description}",
            "tier_3": f"({synergy.required_characters[SynergyTier.TIER_3]} chars) {synergy.tier_3_bonus.description}"
        }

# Global team synergy system instance
team_synergy_system = TeamSynergySystem()
