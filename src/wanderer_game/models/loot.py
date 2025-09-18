"""
Loot and reward models for the Wanderer Game
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from enum import Enum
import random


class LootRarity(Enum):
    """Rarity levels for loot items"""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class LootType(Enum):
    """Types of loot that can be obtained"""
    GEMS = "gems"
    EXPERIENCE = "experience"
    ITEM = "item"
    GIFT = "gift"
    MATERIAL = "material"
    QUARTZS = "quartzs"


@dataclass
class LootItem:
    """Represents a single loot item"""
    item_type: LootType
    item_id: str
    quantity: int
    rarity: LootRarity
    value: int  # Base value for calculations
    
    def __str__(self) -> str:
        if self.quantity > 1:
            return f"{self.quantity}x {self.item_id}"
        return self.item_id


@dataclass
class LootTable:
    """
    Weighted loot table for generating random rewards
    """
    name: str
    items: List[Tuple[LootItem, int]]  # (item, weight) pairs
    
    def roll(self, num_rolls: int = 1) -> List[LootItem]:
        """Roll on this loot table"""
        if not self.items:
            return []
        
        results = []
        total_weight = sum(weight for _, weight in self.items)
        
        for _ in range(num_rolls):
            roll = random.randint(1, total_weight)
            current_weight = 0
            
            for item, weight in self.items:
                current_weight += weight
                if roll <= current_weight:
                    results.append(item)
                    break
        
        return results


@dataclass 
class LootPool:
    """Collection of loot items accumulated during an expedition"""
    items: List[LootItem] = field(default_factory=list)
    
    def add_item(self, item: LootItem):
        """Add an item to the loot pool"""
        self.items.append(item)
    
    def add_items(self, items: List[LootItem]):
        """Add multiple items to the loot pool"""
        self.items.extend(items)
    
    def remove_random_item(self) -> bool:
        """Remove a random item (for mishaps). Returns True if item was removed."""
        if not self.items:
            return False
        
        random_item = random.choice(self.items)
        self.items.remove(random_item)
        return True
    
    def apply_multiplier(self, multiplier: float) -> 'LootPool':
        """Apply a final multiplier to the loot pool"""
        if multiplier <= 0:
            return LootPool()  # Empty pool
        
        if multiplier >= 1.0:
            # Positive multiplier - might duplicate items
            target_count = int(len(self.items) * multiplier)
            if target_count <= len(self.items):
                return LootPool(self.items[:target_count])
            else:
                # Need to add more items - duplicate randomly
                new_pool = LootPool(self.items.copy())
                items_to_add = target_count - len(self.items)
                for _ in range(items_to_add):
                    if self.items:  # Safety check
                        new_pool.add_item(random.choice(self.items))
                return new_pool
        else:
            # Negative multiplier - reduce items
            target_count = int(len(self.items) * multiplier)
            if target_count <= 0:
                return LootPool()
            return LootPool(self.items[:target_count])
    
    def get_total_value(self) -> int:
        """Get total value of all items in the pool"""
        return sum(item.value * item.quantity for item in self.items)
    
    def is_empty(self) -> bool:
        """Check if the loot pool is empty"""
        return len(self.items) == 0
    
    def __len__(self) -> int:
        return len(self.items)


class FinalMultiplier(Enum):
    """Final multiplier outcomes"""
    CATASTROPHE = "catastrophe"  # -75%
    SETBACK = "setback"         # -25%
    STANDARD = "standard"       # No change
    JACKPOT = "jackpot"         # +50%