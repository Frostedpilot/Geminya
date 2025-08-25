"""Enhanced Waifu Service with shard-based upgrade system.

This service manages the waifu gacha system where:
- Gacha pulls give 1⭐, 2⭐, or 3⭐ characters only
- 4⭐ and 5⭐ are achieved through duplicate upgrades using shards
- Duplicate pulls give shards which auto-upgrade characters when enough are collected
"""


import random
import logging
from typing import Dict, List, Any, Optional
from services.database import DatabaseService
from services.banner_manager import BannerManager


class WaifuService:
    # ... existing code ...
    """Service for managing waifu gacha system with star upgrades."""

    # NEW GACHA RATES (1-3 stars only)
    GACHA_RATES = {
        3: 5.0,   # 3-star: 5%
        2: 20.0,  # 2-star: 20% 
        1: 75.0,  # 1-star: 75%
    }

    # NEW PITY SYSTEM
    PITY_3_STAR = 50   # Guaranteed 3-star every 50 pulls

    # SHARD REWARDS (based on current star level of pulled character)
    SHARD_REWARDS = {
        3: 90,  # 3-star dupe = 90 shards
        2: 20,  # 2-star dupe = 20 shards
        1: 5,   # 1-star dupe = 5 shards
    }

    # UPGRADE COSTS (shards required to upgrade) - FIXED
    UPGRADE_COSTS = {
        2: 50,   # 1→2 star: 50 shards
        3: 100,  # 2→3 star: 100 shards
        4: 150,  # 3→4 star: 150 shards
        5: 200,  # 4→5 star: 200 shards
    }

    # Maximum star level
    MAX_STAR_LEVEL = 5

    # Elements for diversity
    ELEMENTS = ["Fire", "Water", "Earth", "Air", "Light", "Dark"]

    # Cost per summon
    SUMMON_COST = 10

    def __init__(self, database: DatabaseService):
        self.db = database
        self.logger = logging.getLogger(__name__)
        self._waifu_list = []  # In-memory waifu list from CSV
        self.banner_manager = BannerManager()

    def _load_waifus_from_csv(self, csv_path: str):
        import csv
        waifus = []
        try:
            with open(csv_path, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    valid = True
                    if 'waifu_id' in row and row['waifu_id'] != '':
                        try:
                            row['waifu_id'] = int(row['waifu_id'])
                        except Exception as e:
                            row['waifu_id'] = None
                            valid = False
                            self.logger.warning("Invalid waifu_id in row: %s", row)
                    else:
                        row['waifu_id'] = None
                        valid = False
                    if 'rarity' in row and row['rarity'] != '':
                        try:
                            row['rarity'] = int(row['rarity'])
                        except Exception as e:
                            row['rarity'] = None
                            self.logger.warning("Invalid rarity in row: %s", row)
                    else:
                        row['rarity'] = None
                    if valid and row['waifu_id'] is not None:
                        waifus.append(row)
                    else:
                        self.logger.info("Skipping invalid waifu row (missing or invalid waifu_id): %s", row)
        except Exception as e:
            self.logger.error("Failed to load waifus from CSV: %s", e)
        return waifus

    async def initialize(self):
        """Initialize the waifu service and load waifus from CSV."""
        await self.db.initialize()
        self._waifu_list = self._load_waifus_from_csv('data/character_final.csv')
        self.logger.info("Waifu service initialized with new star system. Loaded %d waifus from CSV.", len(self._waifu_list))

    async def close(self):
        """Close the waifu service and its database connection. Release waifu list."""
        await self.db.close()
        self._waifu_list = []
        self.logger.info("Waifu service closed and waifu list released.")

    async def _check_and_perform_auto_upgrades(self, discord_id: str, waifu_id: int, current_shards: int, current_star: int) -> Dict[str, Any]:
        """
        Automatically upgrade character stars if sufficient shards are available.
        Returns upgrade results including final star level and any quartz gained.
        """
        upgrades_performed = []
        total_quartz_gained = 0
        remaining_shards = current_shards
        final_star_level = current_star
        
        # Keep upgrading while possible
        while final_star_level < self.MAX_STAR_LEVEL:
            target_star_level = final_star_level + 1
            required_shards = self.UPGRADE_COSTS.get(target_star_level)
            if required_shards is None or remaining_shards < required_shards:
                break
            # Perform the upgrade
            remaining_shards -= required_shards
            final_star_level += 1
            # Log the upgrade
            upgrades_performed.append({
                "from_star": final_star_level - 1,
                "to_star": final_star_level,
                "shards_used": required_shards
            })
            self.logger.info("Auto-upgraded character %s from %d* to %d* for user %s", waifu_id, final_star_level - 1, final_star_level, discord_id)
        # If character reached max star level, convert excess shards to quartz
        if final_star_level >= self.MAX_STAR_LEVEL and remaining_shards > 0:
            total_quartz_gained = await self.convert_excess_shards_to_quartz(discord_id, waifu_id, remaining_shards)
            remaining_shards = 0  # All excess shards converted
        # Update database with final values
        user = await self.db.get_or_create_user(discord_id)
        if not self.db.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await waifu_service.initialize()' first.")
        async with self.db.connection_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE user_waifus 
                SET current_star_level = $1, star_shards = $2 
                WHERE user_id = $3 AND waifu_id = $4
                """,
                final_star_level, remaining_shards, user["id"], waifu_id
            )
        return {
            "final_star_level": final_star_level,
            "remaining_shards": remaining_shards,
            "upgrades_performed": upgrades_performed,
            "quartz_gained": total_quartz_gained
        }

    # ==================== STAR UPGRADE METHODS ====================

    async def get_character_shards(self, discord_id: str, waifu_id: int) -> int:
        """Get current shard count for a specific character."""
        try:
            user = await self.db.get_or_create_user(discord_id)
            
            if not self.db.connection_pool:
                raise RuntimeError("Database connection pool is not initialized. Call 'await waifu_service.initialize()' first.")
            async with self.db.connection_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT star_shards 
                    FROM user_waifus 
                    WHERE user_id = $1 AND waifu_id = $2
                    """,
                    user["id"], waifu_id
                )
                return row["star_shards"] if row else 0
                    
        except Exception as e:
            self.logger.error("Error getting character shards: %s", e)
            return 0

    async def add_character_shards(self, discord_id: str, waifu_id: int, amount: int) -> int:
        """Add shards for a specific character. Returns new total."""
        try:
            user = await self.db.get_or_create_user(discord_id)
            
            if not self.db.connection_pool:
                raise RuntimeError("Database connection pool is not initialized. Call 'await waifu_service.initialize()' first.")
            async with self.db.connection_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE user_waifus 
                    SET star_shards = star_shards + $1 
                    WHERE user_id = $2 AND waifu_id = $3
                    """,
                    amount, user["id"], waifu_id
                )
                row = await conn.fetchrow(
                    """
                    SELECT star_shards 
                    FROM user_waifus 
                    WHERE user_id = $1 AND waifu_id = $2
                    """,
                    user["id"], waifu_id
                )
                new_total = row["star_shards"] if row else 0
                return new_total
                    
        except Exception as e:
            self.logger.error("Error adding character shards: %s", e)
            return 0

    async def get_character_star_level(self, discord_id: str, waifu_id: int) -> int:
        """Get current star level of a character in user's collection."""
        try:
            if not self.db.connection_pool:
                raise RuntimeError("Database connection pool is not initialized. Call 'await waifu_service.initialize()' first.")
            async with self.db.connection_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT uw.current_star_level, w.rarity as base_rarity
                    FROM user_waifus uw
                    JOIN waifus w ON uw.waifu_id = w.waifu_id
                    JOIN users u ON uw.user_id = u.id
                    WHERE u.discord_id = $1 AND uw.waifu_id = $2
                    LIMIT 1
                    """,
                    discord_id, waifu_id
                )
                if row:
                    return row["current_star_level"] if row["current_star_level"] is not None else row["base_rarity"]
                waifu_row = await conn.fetchrow("SELECT rarity FROM waifus WHERE waifu_id = $1", waifu_id)
                return waifu_row["rarity"] if waifu_row else 1
                    
        except Exception as e:
            self.logger.error("Error getting character star level: %s", e)
            return 1

    async def upgrade_character_star(self, discord_id: str, waifu_id: int) -> Dict[str, Any]:
        """Upgrade a character's star level using shards."""
        try:
            # Get current star level
            current_star = await self.get_character_star_level(discord_id, waifu_id)
            
            if current_star >= self.MAX_STAR_LEVEL:
                return {
                    "success": False,
                    "message": f"Character is already at maximum star level ({self.MAX_STAR_LEVEL}★)"
                }
            
            next_star = current_star + 1
            required_shards = self.UPGRADE_COSTS.get(next_star)
            
            if not required_shards:
                return {
                    "success": False,
                    "message": f"Invalid upgrade path from {current_star}★ to {next_star}★"
                }
            
            # Check current shards
            current_shards = await self.get_character_shards(discord_id, waifu_id)
            
            if current_shards < required_shards:
                return {
                    "success": False,
                    "message": f"Not enough shards! Need {required_shards}, have {current_shards}",
                    "required": required_shards,
                    "current": current_shards
                }
            
            # Perform upgrade
            user = await self.db.get_or_create_user(discord_id)
            if not self.db.connection_pool:
                raise RuntimeError("Database connection pool is not initialized. Call 'await waifu_service.initialize()' first.")
            async with self.db.connection_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE user_waifus 
                    SET current_star_level = $1, star_shards = star_shards - $2 
                    WHERE user_id = $3 AND waifu_id = $4
                    """,
                    next_star, required_shards, user["id"], waifu_id
                )
                waifu_data = await conn.fetchrow("SELECT name, series FROM waifus WHERE waifu_id = $1", waifu_id)
                remaining_shards = current_shards - required_shards
                return {
                    "success": True,
                    "character_name": waifu_data["name"] if waifu_data else "Unknown",
                    "character_series": waifu_data["series"] if waifu_data else "Unknown",
                    "from_star": current_star,
                    "to_star": next_star,
                    "shards_used": required_shards,
                    "remaining_shards": remaining_shards
                }
                    
        except Exception as e:
            self.logger.error("Error upgrading character star: %s", e)
            return {
                "success": False,
                "message": f"Upgrade failed: {str(e)}"
            }

    async def convert_excess_shards_to_quartz(self, discord_id: str, waifu_id: int, excess_shards: int) -> int:
        """Convert excess shards to quartz for max-star characters."""
        try:
            if excess_shards <= 0:
                return 0
            
            # Add quartz (1 shard = 1 quartz)
            await self.db.update_user_quartzs(discord_id, excess_shards)
            
            self.logger.info(f"Converted {excess_shards} excess shards to quartz for user {discord_id}")
            return excess_shards
            
        except Exception as e:
            self.logger.error("Error converting excess shards to quartz: %s", e)
            return 0

    # ==================== UPDATED GACHA METHODS ====================

    async def perform_summon(self, discord_id: str) -> Dict[str, Any]:
        """Perform a waifu summon using server-side banner/waifu pool logic."""
        user = await self.db.get_or_create_user(discord_id)
        if user["sakura_crystals"] < self.SUMMON_COST:
            return {
                "success": False,
                "message": f"Not enough Sakura Crystals! You need {self.SUMMON_COST} but have {user['sakura_crystals']}.",
            }
        # Get user's selected banner (or fallback to default)
        selected_banner_id = await self.db.get_user_selected_banner(discord_id)
        if not isinstance(selected_banner_id, int):
            banners = self.banner_manager.get_all_banners()
            selected_banner_id = banners[0]["id"] if banners else None
        banner = self.banner_manager.get_banner_by_id(selected_banner_id) if selected_banner_id is not None else None
        if not banner:
            return {"success": False, "message": "Selected banner not found."}
        rarity = await self._determine_summon_rarity(user)
        waifu_ids = self.banner_manager.get_waifu_ids_for_banner(banner)
        waifus_of_rarity = [w for w in self._waifu_list if w.get('rarity') == rarity and w.get('waifu_id') in waifu_ids]
        if not waifus_of_rarity:
            return {"success": False, "message": f"No waifus available for rarity {rarity} in this banner. Please contact an administrator."}
        selected_waifu = random.choice(waifus_of_rarity)
        summon_result = await self._handle_summon_result(discord_id, selected_waifu, rarity)
        await self.db.update_user_crystals(discord_id, -self.SUMMON_COST)
        if rarity >= 3:
            await self.db.update_pity_counter(discord_id, reset=True)
        else:
            await self.db.update_pity_counter(discord_id)
        await self.check_and_update_rank(discord_id)
        await self.db.update_user_quartzs(discord_id, 1)
        return {"success": True, "waifu": selected_waifu, "rarity": rarity, **summon_result}

    async def _handle_summon_result(self, discord_id: str, waifu: Dict[str, Any], pulled_rarity: int) -> Dict[str, Any]:
        """Handle summon result with new shard system and automatic upgrades."""
        if not self.db.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await waifu_service.initialize()' first.")
        waifu_id = waifu["waifu_id"]
        # Check if user already owns this character
        user_collection = await self.db.get_user_collection(discord_id)
        existing_waifu = next((w for w in user_collection if w["waifu_id"] == waifu_id), None)
        if existing_waifu:
            # DUPLICATE: Give shards based on pulled rarity (not current star level)
            current_star = existing_waifu.get("current_star_level") or pulled_rarity
            shard_reward = self.SHARD_REWARDS.get(pulled_rarity, 5)  # Based on pulled rarity
            # Check if character is already at max star level
            if current_star >= self.MAX_STAR_LEVEL:
                # Character is already 5⭐, convert all shards directly to quartz
                quartz_gained = await self.convert_excess_shards_to_quartz(discord_id, waifu_id, shard_reward)
                return {
                    "is_new": False,
                    "is_duplicate": True,
                    "current_star_level": current_star,
                    "shards_gained": 0,  # No shards gained, converted to quartz
                    "total_shards": 0,   # No shards remaining
                    "quartz_gained": quartz_gained,
                    "upgrades_performed": []  # No upgrades possible
                }
            else:
                # Character can still be upgraded, add shards and check for upgrades
                current_shards = await self.get_character_shards(discord_id, waifu_id)
                new_shard_total = current_shards + shard_reward
                await self.add_character_shards(discord_id, waifu_id, shard_reward)
                # Perform automatic upgrades after adding shards
                upgrade_result = await self._check_and_perform_auto_upgrades(discord_id, waifu_id, new_shard_total, current_star)
                return {
                    "is_new": False,
                    "is_duplicate": True,
                    "current_star_level": upgrade_result["final_star_level"],
                    "shards_gained": shard_reward,
                    "total_shards": upgrade_result["remaining_shards"],
                    "quartz_gained": upgrade_result["quartz_gained"],
                    "upgrades_performed": upgrade_result["upgrades_performed"]
                }
        else:
            # NEW CHARACTER: Add to collection
            await self.db.add_waifu_to_user(discord_id, waifu_id)
            # Set initial star level to pulled rarity
            user = await self.db.get_or_create_user(discord_id)
            async with self.db.connection_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE user_waifus 
                    SET current_star_level = $1 
                    WHERE user_id = $2 AND waifu_id = $3
                    """,
                    pulled_rarity, user["id"], waifu_id
                )
            return {
                "is_new": True,
                "is_duplicate": False,
                "current_star_level": pulled_rarity,
                "shards_gained": 0,
                "total_shards": 0,
                "quartz_gained": 0,
                "upgrades_performed": []
            }

    async def _determine_summon_rarity(self, user: Dict[str, Any]) -> int:
        """Determine summon rarity using NEW gacha rates and pity system."""
        pity_count = user["pity_counter"]

        # NEW Pity system check - 3* pity at 50 pulls
        if pity_count >= self.PITY_3_STAR:
            return 3

        # Normal rates with pity soft increase
        rates = self.GACHA_RATES.copy()

        # # Soft pity - increase 3-star rate after 75 pulls
        # if pity_count >= 75:
        #     increase = (pity_count - 74) * 0.6
        #     rates[3] = min(rates[3] + increase, 100)

        # Generate random number and determine rarity
        roll = random.random() * 100
        
        # Build proper cumulative ranges from lowest to highest rarity
        cumulative = 0
        for rarity in sorted(rates.keys()):  # Process 1, 2, 3
            cumulative += rates[rarity]
            if roll <= cumulative:
                return rarity

        return 1  # Fallback

    # ==================== MULTI-SUMMON WITH NEW SYSTEM ====================

    async def perform_multi_summon(self, discord_id: str) -> Dict[str, Any]:
        """Perform multiple waifu summons using server-side banner/waifu pool logic - always 10 rolls."""
        count = 10
        user = await self.db.get_or_create_user(discord_id)
        total_cost = self.SUMMON_COST * count
        if user["sakura_crystals"] < total_cost:
            return {"success": False, "message": f"Not enough Sakura Crystals! You need {total_cost} but have {user['sakura_crystals']}.",}
        await self.db.update_user_crystals(discord_id, -total_cost)
        selected_banner_id = await self.db.get_user_selected_banner(discord_id)
        if not isinstance(selected_banner_id, int):
            banners = self.banner_manager.get_all_banners()
            selected_banner_id = banners[0]["id"] if banners else None
        banner = self.banner_manager.get_banner_by_id(selected_banner_id) if selected_banner_id is not None else None
        if not banner:
            return {"success": False, "message": "Selected banner not found."}
        pity_count = user.get("pity_counter", 0)
        pity_active = pity_count >= self.PITY_3_STAR
        pity_consumed = False
        results = []
        rarity_counts = {1: 0, 2: 0, 3: 0}
        waifu_ids = self.banner_manager.get_waifu_ids_for_banner(banner)
        for _ in range(count):
            current_user = await self.db.get_or_create_user(discord_id)
            if pity_active and not pity_consumed:
                natural_rarity = await self._determine_summon_rarity(current_user)
                if natural_rarity == 3:
                    rarity = 3
                    pity_consumed = True
                    await self.db.update_pity_counter(discord_id, reset=True)
                else:
                    rarity = natural_rarity
            else:
                rarity = await self._determine_summon_rarity(current_user)
            waifus_of_rarity = [w for w in self._waifu_list if w.get('rarity') == rarity and w.get('waifu_id') in waifu_ids]
            if not waifus_of_rarity:
                continue
            selected_waifu = random.choice(waifus_of_rarity)
            summon_result = await self._handle_summon_result(discord_id, selected_waifu, rarity)
            results.append({"waifu": selected_waifu, "rarity": rarity, **summon_result})
            rarity_counts[rarity] += 1
        await self.db.update_user_quartzs(discord_id, 10)
        crystals_remaining = user["sakura_crystals"] - self.SUMMON_COST * 10
        return {"success": True, "results": results, "rarity_counts": rarity_counts, "total_cost": self.SUMMON_COST * 10, "crystals_remaining": crystals_remaining}

    # ==================== UTILITY METHODS ====================

    async def get_user_collection_with_stars(self, discord_id: str) -> List[Dict[str, Any]]:
        """Get user's collection with star levels and shard information."""
        try:
            collection = await self.db.get_user_collection(discord_id)
            
            # Enhance each entry with shard information
            enhanced_collection = []
            for waifu in collection:
                waifu_id = waifu["waifu_id"]
                current_star = waifu.get("current_star_level") or waifu["rarity"]
                shards = await self.get_character_shards(discord_id, waifu_id)
                # Calculate upgrade info
                next_star = current_star + 1 if current_star < self.MAX_STAR_LEVEL else None
                shards_needed = self.UPGRADE_COSTS.get(next_star, 0) if next_star else 0
                enhanced_waifu = {
                    **waifu,
                    "current_star_level": current_star,
                    "character_shards": shards,
                    "next_star_level": next_star,
                    "shards_needed_for_upgrade": shards_needed,
                    "can_upgrade": shards >= shards_needed if shards_needed > 0 else False,
                    "is_max_star": current_star >= self.MAX_STAR_LEVEL
                }
                enhanced_collection.append(enhanced_waifu)
            
            return enhanced_collection
            
        except Exception as e:
            self.logger.error("Error getting enhanced collection: %s", e)
            return []

    async def get_user_stats(self, discord_id: str) -> Dict[str, Any]:
        """Get comprehensive user statistics for academy status display."""
        try:
            # Get user data
            user = await self.db.get_or_create_user(discord_id)
            # Get user's collection
            collection = await self.db.get_user_collection(discord_id)
            # Calculate stats
            total_waifus = len(collection)
            unique_waifus = len(set(waifu['waifu_id'] for waifu in collection))
            # Calculate collection power and star distribution
            collection_power = 0
            star_distribution = {}
            for waifu in collection:
                waifu_id = waifu['waifu_id']
                # Get current star level for this waifu
                star_level = await self.get_character_star_level(discord_id, waifu_id)
                # Ensure minimum star level is 1
                if star_level == 0:
                    star_level = 1
                # Calculate power based on star level (exponential growth)
                # 1* = 100, 2* = 250, 3* = 500, 4* = 1000, 5* = 2000, etc.
                if star_level == 1:
                    power = 100
                elif star_level == 2:
                    power = 250
                elif star_level == 3:
                    power = 500
                elif star_level == 4:
                    power = 1000
                elif star_level == 5:
                    power = 2000
                else:
                    power = 0
                collection_power += power
                star_distribution[star_level] = star_distribution.get(star_level, 0) + 1
            return {
                "user": user,
                "total_waifus": total_waifus,
                "unique_waifus": unique_waifus,
                "collection_power": collection_power,
                "rarity_distribution": star_distribution
            }
        except Exception as e:
            self.logger.error("Error getting user stats: %s", e)
            # Return default stats structure
            user = await self.db.get_or_create_user(discord_id)
            return {
                "user": user,
                "total_waifus": 0,
                "unique_waifus": 0,
                "collection_power": 0,
                "rarity_distribution": {}
            }

    async def check_and_update_rank(self, discord_id: str) -> int:
        """Check if user qualifies for rank up and automatically update their rank.
        Returns the new rank level."""
        try:
            # Get current stats
            stats = await self.get_user_stats(discord_id)
            user = stats["user"]
            current_rank = user["collector_rank"]
            current_power = stats["collection_power"]
            current_waifus = stats["total_waifus"]
            # Calculate what rank the user should actually be based on their power
            # Rank 1: 0 power, Rank 2: 2000 power, Rank 3: 6000 power (2000+4000), etc.
            actual_rank_by_power = 1
            total_power_needed = 0
            # Keep checking if user has enough power for next rank
            while True:
                next_rank = actual_rank_by_power + 1
                power_needed_for_next_rank = 1000 * (2 ** actual_rank_by_power)  # 2000, 4000, 8000, etc.
                if current_power >= total_power_needed + power_needed_for_next_rank:
                    total_power_needed += power_needed_for_next_rank
                    actual_rank_by_power = next_rank
                else:
                    break
            # Calculate what rank by waifus (5 waifus per rank: rank 1 = 0-4 waifus, rank 2 = 5-9, etc.)
            actual_rank_by_waifus = (current_waifus // 5) + 1
            # True rank should be minimum of both (both requirements must be met)
            suggested_rank = min(actual_rank_by_power, actual_rank_by_waifus)
            # If user should be higher rank, update their rank
            if suggested_rank > current_rank:
                await self.db.update_user_rank(discord_id, suggested_rank)
                self.logger.info("Auto-ranked up user %s from %d to %d", discord_id, current_rank, suggested_rank)
                return suggested_rank
            else:
                # Debug logging to see why no rank up occurred
                self.logger.info("No rank up for %s: Current=%d, Power rank=%d (power=%d), Waifu rank=%d (waifus=%d), Suggested=%d", discord_id, current_rank, actual_rank_by_power, current_power, actual_rank_by_waifus, current_waifus, suggested_rank)
            return current_rank
        except Exception as e:
            self.logger.error("Error checking/updating rank for %s: %s", discord_id, e)
            # Return current rank as fallback
            user = await self.db.get_or_create_user(discord_id)
            return user["collector_rank"]
