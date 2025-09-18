"""
Systems package for the Wanderer Game

Contains core game logic systems:
- ExpeditionManager: Handles expedition lifecycle and state
- ExpeditionResolver: Processes expedition encounters and outcomes  
- LootGenerator: Generates rewards based on expedition results
- ChanceTable: Probability calculations for encounter outcomes
"""

from .expedition_manager import ExpeditionManager, ExpeditionSlot
from .expedition_resolver import ExpeditionResolver
from .loot_generator import LootGenerator
from .chance_table import ChanceTable, FinalMultiplierTable

__all__ = [
    'ExpeditionManager',
    'ExpeditionSlot',
    'ExpeditionResolver', 
    'LootGenerator',
    'ChanceTable',
    'FinalMultiplierTable'
]