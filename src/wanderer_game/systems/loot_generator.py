"""
Tier-based LootGenerator system for the Wanderer Game

Uses 20 comprehensive tiers with simplified loot types.
Each tier contains balanced distributions of sakura_crystals, quartzs, and items.
"""

from typing import Dict, List, Union
from ..models import LootTable, LootItem, LootType, LootRarity


class LootGenerator:
    """
    20-tier loot generation system with simplified loot types
    
    Each tier defines complete loot tables with (loot_type, amount, weight) format.
    Supports sakura_crystals, quartzs, and item_id based rewards.
    """
    
    def __init__(self):
        self.tier_tables = self._initialize_tier_tables()
    
    def _initialize_tier_tables(self) -> Dict[int, LootTable]:
        """Initialize all 20 tier tables with static, balanced loot distributions"""
        tier_tables = {}
        
        # Static loot table definitions for each tier
        tier_configs = {
            1: [
                ("sakura_crystals", 10, 50),    # Basic crystals
                ("quartzs", 1, 30),             # Valuable currency (10x sakura value)
                ("item_1", 1, 20)             # Basic item
            ],
            2: [
                ("sakura_crystals", 15, 50),
                ("quartzs", 1, 30),
                ("item_1", 1, 20)
            ],
            3: [
                ("sakura_crystals", 20, 50),
                ("quartzs", 2, 30),
                ("item_1", 1, 20)
            ],
            4: [
                ("sakura_crystals", 25, 50),
                ("quartzs", 2, 30),
                ("item_1", 1, 20)
            ],
            5: [
                ("sakura_crystals", 35, 50),
                ("quartzs", 3, 30),
                ("item_5", 1, 20)
            ],
            6: [
                ("sakura_crystals", 45, 50),
                ("quartzs", 4, 30),
                ("item_6", 1, 20)
            ],
            7: [
                ("sakura_crystals", 55, 50),
                ("quartzs", 5, 30),
                ("item_7", 1, 20)
            ],
            8: [
                ("sakura_crystals", 70, 50),
                ("quartzs", 6, 30),
                ("item_1", 1, 20)
            ],
            9: [
                ("sakura_crystals", 85, 50),
                ("quartzs", 8, 30),
                ("item_1", 1, 20)
            ],
            10: [
                ("sakura_crystals", 100, 50),
                ("quartzs", 10, 30),
                ("item_1", 1, 20)
            ],
            11: [
                ("sakura_crystals", 120, 50),
                ("quartzs", 12, 30),
                ("item_1", 1, 20)
            ],
            12: [
                ("sakura_crystals", 140, 50),
                ("quartzs", 14, 30),
                ("item_2", 1, 20)
            ],
            13: [
                ("sakura_crystals", 165, 50),
                ("quartzs", 16, 30),
                ("item_3", 1, 20)
            ],
            14: [
                ("sakura_crystals", 190, 50),
                ("quartzs", 19, 30),
                ("item_4", 1, 20)
            ],
            15: [
                ("sakura_crystals", 220, 50),
                ("quartzs", 22, 30),
                ("item_5", 1, 20)
            ],
            16: [
                ("sakura_crystals", 250, 50),
                ("quartzs", 25, 30),
                ("item_6", 1, 20)
            ],
            17: [
                ("sakura_crystals", 285, 50),
                ("quartzs", 28, 30),
                ("item_7", 1, 20)
            ],
            18: [
                ("sakura_crystals", 325, 50),
                ("quartzs", 32, 30),
                ("item_1", 1, 20)
            ],
            19: [
                ("sakura_crystals", 370, 50),
                ("quartzs", 37, 30),
                ("item_1", 1, 20)
            ],
            20: [
                ("sakura_crystals", 420, 50),
                ("quartzs", 42, 30),
                ("item_1", 1, 20)
            ]
        }
        
        # Create LootTables from static configurations
        for tier, config in tier_configs.items():
            loot_items = []
            for item_id, amount, weight in config:
                # Determine loot type and create appropriate item
                if item_id == "sakura_crystals":
                    item = LootItem(LootType.GEMS, item_id, amount, self._get_rarity(tier), amount)
                elif item_id == "quartzs":
                    # Quartzs are 10x more valuable than sakura crystals
                    item = LootItem(LootType.QUARTZS, item_id, amount, self._get_rarity(tier), amount * 10)
                else:  # item_xxx
                    item_value = int(item_id.split('_')[1]) * 5  # item_101 = 505 value
                    item = LootItem(LootType.ITEM, item_id, amount, self._get_rarity(tier), item_value)
                
                loot_items.append((item, weight))
            
            tier_tables[tier] = LootTable(f"Tier {tier} Static", loot_items)
        
        return tier_tables
    
    def get_available_tables(self) -> List[str]:
        """Get list of all available tier table names for compatibility"""
        return [f"Tier {tier} Static" for tier in range(1, 21)]
    
    def _get_rarity(self, tier: int) -> LootRarity:
        """Determine rarity based on tier"""
        if tier >= 18:
            return LootRarity.LEGENDARY
        elif tier >= 14:
            return LootRarity.EPIC
        elif tier >= 10:
            return LootRarity.RARE
        elif tier >= 6:
            return LootRarity.UNCOMMON
        else:
            return LootRarity.COMMON
    
    def generate_loot(self, difficulty: int, success_level: str) -> List[LootItem]:
        """
        Generate loot based on difficulty and success level
        
        Args:
            difficulty: Expedition difficulty
            success_level: "common" or "great"
            
        Returns:
            List of generated loot items
        """
        # Calculate tier from difficulty (0-49 = tier 1, 50-99 = tier 2, etc.)
        tier = min(20, max(1, (difficulty // 50) + 1))
        
        # Determine number of rolls
        num_rolls = 2 if success_level == "great" else 1
        
        # Get tier table and roll for loot
        if tier in self.tier_tables:
            table = self.tier_tables[tier]
            return table.roll(num_rolls)
        
        # Fallback (shouldn't happen)
        return [LootItem(LootType.GEMS, "sakura_crystals", 5, LootRarity.COMMON, 5)]
    
    def get_tier_info(self, tier: int) -> Dict:
        """Get information about a specific tier"""
        if tier < 1 or tier > 20:
            return {"error": "Tier must be between 1 and 20"}
        
        # Get the loot table for this tier
        table = self.tier_tables.get(tier)
        if not table:
            return {"error": f"No table found for tier {tier}"}
        
        # Extract info from the static table
        tier_info = {
            "tier": tier,
            "rarity": self._get_rarity(tier).value,
            "difficulty_range": f"{(tier-1)*50}-{tier*50-1}",
            "loot_items": []
        }
        
        for item, weight in table.items:
            tier_info["loot_items"].append({
                "item_id": item.item_id,
                "amount": item.quantity,
                "weight": weight,
                "value": item.value
            })
        
        return tier_info
    
    def get_all_tiers_info(self) -> List[Dict]:
        """Get information about all tiers"""
        return [self.get_tier_info(tier) for tier in range(1, 21)]
    
    def simulate_loot_generation(self, difficulty: int, success_level: str, 
                                num_simulations: int = 1000) -> Dict:
        """
        Simulate loot generation for balancing purposes
        
        Args:
            difficulty: Expedition difficulty
            success_level: "common" or "great"
            num_simulations: Number of simulations to run
            
        Returns:
            Dictionary with average values and statistics
        """
        total_sakura = 0
        total_quartzs = 0
        total_items = 0
        total_value = 0
        
        for _ in range(num_simulations):
            loot_items = self.generate_loot(difficulty, success_level)
            for item in loot_items:
                if item.item_type == LootType.GEMS:
                    total_sakura += item.quantity
                elif item.item_type == LootType.QUARTZS:
                    total_quartzs += item.quantity
                elif item.item_type == LootType.ITEM:
                    total_items += item.quantity
                
                total_value += item.value * item.quantity
        
        tier = min(20, max(1, (difficulty // 50) + 1))
        
        return {
            "tier": tier,
            "difficulty": difficulty,
            "success_level": success_level,
            "average_sakura_crystals": total_sakura / num_simulations,
            "average_quartzs": total_quartzs / num_simulations,
            "average_items": total_items / num_simulations,
            "average_total_value": total_value / num_simulations,
            "simulations": num_simulations
        }