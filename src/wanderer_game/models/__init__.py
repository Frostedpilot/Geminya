"""
Models package for the Wanderer Game

Contains data classes and schemas for:
- Expeditions and expedition templates
- Encounters and encounter types
- Characters and their stats/affinities
- Loot and rewards
- Results and logging
"""

from .expedition import Expedition, ExpeditionTemplate, AffinityPool, ActiveExpedition, ExpeditionStatus
from .encounter import Encounter, EncounterType, EncounterCondition, EncounterResult, EncounterOutcome, EncounterModifier, ModifierType
from .character import Character, CharacterStats, Affinity, AffinityType, Team
from .loot import LootTable, LootItem, LootPool, FinalMultiplier, LootType, LootRarity
from .result import ExpeditionResult

__all__ = [
    'Expedition',
    'ExpeditionTemplate',
    'AffinityPool',
    'ActiveExpedition', 
    'ExpeditionStatus',
    'Encounter',
    'EncounterType',
    'EncounterCondition',
    'EncounterResult',
    'EncounterOutcome',
    'EncounterModifier',
    'ModifierType',
    'Character',
    'CharacterStats',
    'Affinity',
    'AffinityType',
    'Team',
    'LootTable',
    'LootItem', 
    'LootPool',
    'FinalMultiplier',
    'LootType',
    'LootRarity',
    'ExpeditionResult'
]