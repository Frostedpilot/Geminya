"""Waifu service for managing gacha mechanics and character data."""

import random
import logging
from typing import Dict, List, Any
from services.database import DatabaseService


class WaifuService:
    """Service for managing waifu gacha system."""

    # Gacha rates (percentages)
    GACHA_RATES = {
        5: 0.6,  # 5-star: 0.6%
        4: 2.0,  # 4-star: 2.0%
        3: 25.0,  # 3-star: 25.0%
        2: 35.0,  # 2-star: 35.0%
        1: 37.4,  # 1-star: 37.4%
    }

    # Pity system
    PITY_5_STAR = 90  # Guaranteed 5-star every 90 pulls

    # Elements for diversity
    ELEMENTS = ["Fire", "Water", "Earth", "Air", "Light", "Dark"]

    # Cost per summon
    SUMMON_COST = 10

    def __init__(self, database: DatabaseService):
        self.db = database
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize the waifu service."""
        await self.db.initialize()
        self.logger.info("Waifu service initialized")

    async def close(self):
        """Close the waifu service and its database connection."""
        await self.db.close()
        self.logger.info("Waifu service closed")

    async def perform_summon(
        self, discord_id: str
    ) -> Dict[str, Any]:
        """Perform a waifu summon."""
        user = await self.db.get_or_create_user(discord_id)

        # Check if user has enough crystals
        if user["sakura_crystals"] < self.SUMMON_COST:
            return {
                "success": False,
                "message": f"Not enough Sakura Crystals! You need {self.SUMMON_COST} but have {user['sakura_crystals']}.",
            }

        # Determine rarity with pity system
        rarity = await self._determine_summon_rarity(user)

        # Get available waifus of that rarity
        available_waifus = await self.db.get_waifus_by_rarity(rarity, 50)

        if not available_waifus:
            return {
                "success": False,
                "message": f"No waifus available for rarity {rarity}. Please contact an administrator.",
            }

        # Select random waifu
        selected_waifu = random.choice(available_waifus)

        # Add to user's collection
        await self.db.add_waifu_to_user(discord_id, selected_waifu["id"])

        # Update user's crystals and pity counter
        await self.db.update_user_crystals(discord_id, -self.SUMMON_COST)

        # Only reset pity on 5* pulls now
        if rarity >= 5:
            await self.db.update_pity_counter(discord_id, reset=True)
        else:
            await self.db.update_pity_counter(discord_id)

        # Check if this is a new waifu or constellation
        user_collection = await self.db.get_user_collection(discord_id)
        waifu_count = sum(
            1 for w in user_collection if w["waifu_id"] == selected_waifu["id"]
        )

        is_new = waifu_count == 1
        constellation_level = waifu_count - 1

        return {
            "success": True,
            "waifu": selected_waifu,
            "is_new": is_new,
            "constellation_level": constellation_level,
            "crystals_remaining": user["sakura_crystals"] - self.SUMMON_COST,
            "rarity": rarity,
        }

    async def perform_multi_summon(
        self, discord_id: str
    ) -> Dict[str, Any]:
        """Perform multiple waifu summons - always 10 rolls."""
        count = 10  # Fixed to always be 10 rolls
        user = await self.db.get_or_create_user(discord_id)

        # Calculate cost (no discount)
        total_cost = self.SUMMON_COST * count

        # Check if user has enough crystals
        if user["sakura_crystals"] < total_cost:
            return {
                "success": False,
                "message": f"Not enough Sakura Crystals! You need {total_cost} but have {user['sakura_crystals']}.",
            }

        # Deduct the total cost upfront
        await self.db.update_user_crystals(discord_id, -total_cost)

        # Perform individual summons
        results = []
        rarity_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        new_waifus = []
        constellation_upgrades = []

        for i in range(count):
            # Get fresh user data for each summon (for pity system)
            current_user = await self.db.get_or_create_user(discord_id)

            # Special logic for 10th roll - guarantee 4* minimum
            if i == 9:  # 10th roll (0-indexed)
                # Check if we already got a 4* or 5* in this multi-summon
                has_4_star_or_higher = any(r["rarity"] >= 4 for r in results)
                if not has_4_star_or_higher:
                    # Force 4* minimum on 10th roll
                    rarity = max(4, await self._determine_summon_rarity(current_user))
                else:
                    rarity = await self._determine_summon_rarity(current_user)
            else:
                # Normal rarity determination
                rarity = await self._determine_summon_rarity(current_user)

            # Get available waifus of that rarity
            available_waifus = await self.db.get_waifus_by_rarity(rarity, 50)

            if not available_waifus:
                # Skip this summon if no waifus available
                continue

            # Select random waifu
            selected_waifu = random.choice(available_waifus)

            # Add to user's collection
            await self.db.add_waifu_to_user(discord_id, selected_waifu["id"])

            # Update pity counter (no crystal deduction here since it's done upfront)
            # Only reset pity on 5* pulls now
            if rarity >= 5:
                await self.db.update_pity_counter(discord_id, reset=True)
            else:
                await self.db.update_pity_counter(discord_id)

            # Check if this is a new waifu or constellation
            user_collection = await self.db.get_user_collection(discord_id)
            waifu_count = sum(
                1 for w in user_collection if w["waifu_id"] == selected_waifu["id"]
            )

            is_new = waifu_count == 1
            constellation_level = waifu_count - 1

            # Track results
            rarity_counts[rarity] += 1

            if is_new:
                new_waifus.append(selected_waifu)
            else:
                constellation_upgrades.append(
                    {
                        "waifu": selected_waifu,
                        "constellation_level": constellation_level,
                    }
                )

            results.append(
                {
                    "waifu": selected_waifu,
                    "rarity": rarity,
                    "is_new": is_new,
                    "constellation_level": constellation_level,
                }
            )

        # Get final user state
        final_user = await self.db.get_or_create_user(discord_id)

        return {
            "success": True,
            "results": results,
            "count": len(results),
            "total_cost": total_cost,
            "crystals_remaining": final_user["sakura_crystals"],
            "rarity_counts": rarity_counts,
            "new_waifus": new_waifus,
            "constellation_upgrades": constellation_upgrades,
        }

    async def _determine_summon_rarity(self, user: Dict[str, Any]) -> int:
        """Determine summon rarity using gacha rates and pity system."""
        pity_count = user["pity_counter"]

        # Pity system check - only 5* pity
        if pity_count >= self.PITY_5_STAR:
            return 5

        # Normal rates with pity soft increase
        rates = self.GACHA_RATES.copy()

        # Soft pity - increase 5-star rate after 75 pulls
        if pity_count >= 75:
            increase = (pity_count - 74) * 0.6
            rates[5] = min(rates[5] + increase, 100)

        # Generate random number and determine rarity
        roll = random.random() * 100
        
        # Build proper cumulative ranges from lowest to highest rarity
        cumulative = 0
        for rarity in sorted(rates.keys()):  # Process 1, 2, 3, 4, 5
            cumulative += rates[rarity]
            if roll <= cumulative:
                return rarity

        return 1  # Fallback

    async def get_user_stats(self, discord_id: str) -> Dict[str, Any]:
        """Get user's academy stats."""
        user = await self.db.get_or_create_user(discord_id)
        collection = await self.db.get_user_collection(discord_id)

        # Calculate collection stats
        total_waifus = len(collection)
        unique_waifus = len(set(w["waifu_id"] for w in collection))
        rarity_counts = {}

        for waifu in collection:
            rarity = waifu["rarity"]
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1

        return {
            "user": user,
            "total_waifus": total_waifus,
            "unique_waifus": unique_waifus,
            "rarity_distribution": rarity_counts,
            "collection_power": sum(w["rarity"] * w["bond_level"] for w in collection),
        }
