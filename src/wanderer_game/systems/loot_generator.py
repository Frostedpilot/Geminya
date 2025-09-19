"""
Two-stage LootGenerator system for the Wanderer Game

Stage 1: Choose loot type (gems/quartzs/items) based on difficulty
Stage 2: Generate amount using normal distribution or item selection
"""

import math
import random
from typing import Dict, List, Tuple
from ..models import LootTable, LootItem, LootType, LootRarity


class LootGenerator:
    """
    Two-stage loot generation system
    
    Stage 1: Dynamic type selection based on difficulty
    Stage 2: Amount generation via normal distribution or item selection
    """
    
    def __init__(self):
        self.item_configs = self._initialize_item_configs()
    
    def _initialize_item_configs(self) -> List[Tuple[str, int, LootRarity, int]]:
        """Initialize item configurations for the item selection stage"""
        # Items only (for stage 2 when item type is selected)
        item_configs = [
            ("item_4", 1, LootRarity.COMMON, 80),
            ("item_4", 2, LootRarity.COMMON, 120),
            ("item_4", 3, LootRarity.COMMON, 200),
            ("item_4", 4, LootRarity.UNCOMMON, 280),
            ("item_4", 5, LootRarity.UNCOMMON, 320),
            ("item_4", 6, LootRarity.RARE, 400),
            ("item_4", 30, LootRarity.LEGENDARY, 1600),
            ("item_4", 100, LootRarity.LEGENDARY, 2000),
            ("item_2", 1, LootRarity.COMMON, 200),
            ("item_2", 2, LootRarity.UNCOMMON, 300),
            ("item_2", 3, LootRarity.UNCOMMON, 400),
            ("item_2", 4, LootRarity.RARE, 500),
            ("item_2", 5, LootRarity.RARE, 600),
            ("item_5", 1, LootRarity.UNCOMMON, 300),
            ("item_5", 2, LootRarity.RARE, 450),
            ("item_5", 3, LootRarity.RARE, 600),
            ("item_5", 4, LootRarity.EPIC, 750),
            ("item_5", 5, LootRarity.LEGENDARY, 900),
            ("item_5", 27, LootRarity.LEGENDARY, 2000),
            ("item_1", 1, LootRarity.RARE, 400),
            ("item_1", 2, LootRarity.EPIC, 700),
            ("item_1", 3, LootRarity.LEGENDARY, 900),
            ("item_3", 1, LootRarity.RARE, 600),
            ("item_3", 2, LootRarity.EPIC, 900),
            ("item_3", 3, LootRarity.LEGENDARY, 1200),
            ("item_6", 1, LootRarity.EPIC, 700),
            ("item_6", 2, LootRarity.LEGENDARY, 1200),
            ("item_6", 7, LootRarity.LEGENDARY, 2500),
            ("item_7", 1, LootRarity.LEGENDARY, 1400),
        ]
        
        return item_configs
    
    def _calculate_type_probabilities(self, difficulty: int) -> Dict[str, float]:
        """
        Calculate probabilities for each loot type based on difficulty
        
        Args:
            difficulty: The difficulty value (encounter + effective loot)
            
        Returns:
            Dictionary with probabilities for 'gems', 'quartzs', 'items'
        """
        # Clamp difficulty to reasonable range
        diff = max(1, min(1000, difficulty))
        
        # Item probability: 1% below diff 500, scaling to 20% at diff 1000
        if diff <= 500:
            item_prob = 0.01  # 1%
        else:
            # Scale from 1% to 20% between diff 500-1000
            item_prob = 0.01 + (0.19 * (diff - 500) / 500)
        
        # Quartzs probability: Scale from ~2% to 10% across diff 1-1000
        quartzs_prob = 0.02 + (0.08 * (diff - 1) / 999)
        
        # Gems probability: Takes the remainder (always the most common)
        gems_prob = 1.0 - item_prob - quartzs_prob
        
        return {
            'gems': gems_prob,
            'quartzs': quartzs_prob,
            'items': item_prob
        }
    
    def _select_loot_type(self, difficulty: int) -> str:
        """Select loot type using weighted random selection"""
        probs = self._calculate_type_probabilities(difficulty)
        
        roll = random.random()
        if roll < probs['items']:
            return 'items'
        elif roll < probs['items'] + probs['quartzs']:
            return 'quartzs'
        else:
            return 'gems'
    
    def _generate_gems_amount(self, difficulty: int) -> int:
        """Generate sakura crystals amount using normal distribution"""
        # Base amount scales with difficulty
        base_amount = max(5, difficulty // 10)  # 5 at diff 50, 10 at diff 100, etc.
        
        # Add some randomness using normal distribution
        # Standard deviation is 20% of base amount
        std_dev = max(1, base_amount * 0.2)
        amount = int(random.gauss(base_amount, std_dev))
        
        # Ensure minimum of 1
        return max(1, amount)
    
    def _generate_quartzs_amount(self, difficulty: int) -> int:
        """Generate quartzs amount using normal distribution"""
        # Base amount scales with difficulty (quartzs are more valuable, so fewer)
        base_amount = max(1, difficulty // 50)  # 1 at diff 50, 2 at diff 100, etc.
        
        # Add some randomness using normal distribution
        # Standard deviation is 30% of base amount (more variance for rare currency)
        std_dev = max(0.5, base_amount * 0.3)
        amount = int(random.gauss(base_amount, std_dev))
        
        # Ensure minimum of 1
        return max(1, amount)
    
    def _select_item(self, difficulty: int) -> Tuple[str, int, LootRarity]:
        """Select a specific item using the existing value-based system"""
        # Use the old probability weight system for items
        valid_items = []
        for item_id, amount, rarity, target_value in self.item_configs:
            weight = self._calculate_item_probability_weight(target_value, difficulty)
            if weight > 0:
                valid_items.append((item_id, amount, rarity, weight))
        
        if not valid_items:
            # Fallback to basic item
            return ("item_basic_1", 1, LootRarity.COMMON)
        
        # Select using weighted random
        total_weight = sum(weight for _, _, _, weight in valid_items)
        roll = random.uniform(0, total_weight)
        current_weight = 0
        
        for item_id, amount, rarity, weight in valid_items:
            current_weight += weight
            if roll <= current_weight:
                return (item_id, amount, rarity)
        
        # Fallback
        return valid_items[0][:3]
    
    def _calculate_item_probability_weight(self, target_value: int, difficulty: int) -> float:
        """Calculate probability weight for item selection (more forgiving range)"""
        distance = abs(target_value - difficulty)
        
        if distance == 0:
            return 1.0
        
        # Much more forgiving k value: 1000 distance = 0.01% (0.0001)
        # Using formula: weight = exp(-k * distance)
        # At distance 1000: should be 0.0001 (0.01%)
        k = -math.log(0.0001) / 1000  # ≈ 0.00921
        weight = math.exp(-k * distance)
        
        return max(weight, 0.000001)  # Very small minimum threshold
    
    def generate_loot(self, loot_value: int, num_rolls: int = 1) -> List[LootItem]:
        """
        Generate loot using two-stage system
        
        Args:
            loot_value: Combined value (encounter difficulty + effective_loot_value)
            num_rolls: Number of items to generate (default 1)
            
        Returns:
            List of generated loot items
        """
        results = []
        
        for _ in range(num_rolls):
            # Stage 1: Select loot type
            loot_type = self._select_loot_type(loot_value)
            
            # Stage 2: Generate amount/item based on type
            if loot_type == 'gems':
                amount = self._generate_gems_amount(loot_value)
                rarity = self._determine_rarity_by_difficulty(loot_value)
                item = LootItem(LootType.GEMS, "sakura_crystals", amount, rarity, amount)
                results.append(item)
                
            elif loot_type == 'quartzs':
                amount = self._generate_quartzs_amount(loot_value)
                rarity = self._determine_rarity_by_difficulty(loot_value)
                item = LootItem(LootType.QUARTZS, "quartzs", amount, rarity, amount * 10)
                results.append(item)
                
            else:  # items
                item_id, amount, rarity = self._select_item(loot_value)
                item_value = loot_value // 10  # Derived value
                item = LootItem(LootType.ITEM, item_id, amount, rarity, item_value)
                results.append(item)
        
        return results
    
    def _determine_rarity_by_difficulty(self, difficulty: int) -> LootRarity:
        """Determine rarity based on difficulty level"""
        if difficulty >= 800:
            return LootRarity.LEGENDARY
        elif difficulty >= 500:
            return LootRarity.EPIC
        elif difficulty >= 300:
            return LootRarity.RARE
        elif difficulty >= 150:
            return LootRarity.UNCOMMON
        else:
            return LootRarity.COMMON
    
    def get_loot_info(self, loot_value: int) -> Dict:
        """Get information about loot generation for a specific loot value"""
        type_probs = self._calculate_type_probabilities(loot_value)
        
        # Calculate expected amounts
        gems_amount = self._generate_gems_amount(loot_value)
        quartzs_amount = self._generate_quartzs_amount(loot_value)
        
        # Get available items
        available_items = []
        for item_id, amount, rarity, target_value in self.item_configs:
            weight = self._calculate_item_probability_weight(target_value, loot_value)
            if weight > 0:
                available_items.append({
                    "item_id": item_id,
                    "quantity": amount,
                    "rarity": rarity.value,
                    "target_value": target_value,
                    "probability_weight": weight,
                    "distance": abs(target_value - loot_value)
                })
        
        # Sort by probability weight (highest first)
        available_items.sort(key=lambda x: x["probability_weight"], reverse=True)
        
        return {
            "loot_value": loot_value,
            "type_probabilities": {
                "gems": f"{type_probs['gems']*100:.1f}%",
                "quartzs": f"{type_probs['quartzs']*100:.1f}%", 
                "items": f"{type_probs['items']*100:.1f}%"
            },
            "expected_amounts": {
                "gems": gems_amount,
                "quartzs": quartzs_amount
            },
            "available_items": len(available_items),
            "top_items": available_items[:5]
        }
    
    def get_all_loot_info(self) -> List[Dict]:
        """Get information about all item configurations"""
        items_info = []
        for item_id, amount, rarity, target_value in self.item_configs:
            items_info.append({
                "item_id": item_id,
                "quantity": amount,
                "rarity": rarity.value,
                "target_value": target_value
            })
        
        # Sort by target value
        items_info.sort(key=lambda x: x["target_value"])
        
        return items_info
    
    def simulate_loot_generation(self, loot_value: int, num_simulations: int = 1000) -> Dict:
        """
        Simulate loot generation for balancing purposes
        
        Args:
            loot_value: The loot value to simulate
            num_simulations: Number of simulations to run
            
        Returns:
            Dictionary with simulation statistics
        """
        type_counts = {"gems": 0, "quartzs": 0, "items": 0}
        item_counts = {}
        total_value = 0
        total_gems = 0
        total_quartzs = 0
        
        for _ in range(num_simulations):
            loot_items = self.generate_loot(loot_value, 1)
            for item in loot_items:
                # Count by type
                if item.item_type == LootType.GEMS:
                    type_counts["gems"] += 1
                    total_gems += item.quantity
                elif item.item_type == LootType.QUARTZS:
                    type_counts["quartzs"] += 1
                    total_quartzs += item.quantity
                else:
                    type_counts["items"] += 1
                    if item.item_id not in item_counts:
                        item_counts[item.item_id] = 0
                    item_counts[item.item_id] += 1
                
                total_value += item.value
        
        # Convert counts to percentages
        type_percentages = {type_name: (count / num_simulations) * 100 
                           for type_name, count in type_counts.items()}
        
        item_percentages = {item_id: (count / num_simulations) * 100 
                           for item_id, count in item_counts.items()}
        
        return {
            "loot_value": loot_value,
            "simulations": num_simulations,
            "average_value": total_value / num_simulations,
            "type_distribution": type_percentages,
            "average_gems": total_gems / max(1, type_counts["gems"]) if type_counts["gems"] > 0 else 0,
            "average_quartzs": total_quartzs / max(1, type_counts["quartzs"]) if type_counts["quartzs"] > 0 else 0,
            "item_probabilities": item_percentages
        }