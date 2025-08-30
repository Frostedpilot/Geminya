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


class WaifuService:
    async def clamp_pity_counter(self, discord_id: str):
        """Ensure the user's pity counter never exceeds the 3★ pity cap."""
        user = await self.db.get_or_create_user(discord_id)
        pity = user.get("pity_counter", 0)
        if pity > self.PITY_3_STAR:
            if self.db.connection_pool:
                async with self.db.connection_pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE users SET pity_counter = $1 WHERE discord_id = $2
                        """,
                        self.PITY_3_STAR, discord_id
                    )
            else:
                await self.db.update_pity_counter(discord_id, reset=True)
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
        3: 50,  # 3-star dupe = 50 shards
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

    def _load_waifus_from_csv(self, csv_path: str):
        import csv
        waifus = []
        try:
            with open(csv_path, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert numeric fields
                    valid = True
                    # Only waifu_id is required as unique identifier
                    if 'waifu_id' in row and row['waifu_id'] != '':
                        try:
                            row['waifu_id'] = int(row['waifu_id'])
                        except Exception:
                            row['waifu_id'] = None
                            valid = False
                    else:
                        row['waifu_id'] = None
                        valid = False
                    # Parse rarity if present
                    if 'rarity' in row and row['rarity'] != '':
                        try:
                            row['rarity'] = int(row['rarity'])
                        except Exception:
                            row['rarity'] = None
                    else:
                        row['rarity'] = None
                    # Only add waifu if waifu_id is valid
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
            self.logger.info(f"Auto-upgraded character {waifu_id} from {final_star_level - 1}* to {final_star_level}* for user {discord_id}")
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
            self.logger.error(f"Error getting character shards: {e}")
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
            self.logger.error(f"Error adding character shards: {e}")
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
            self.logger.error(f"Error getting character star level: {e}")
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
            self.logger.error(f"Error upgrading character star: {e}")
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
            self.logger.error(f"Error converting excess shards to quartz: {e}")
            return 0

    # ==================== UPDATED GACHA METHODS ====================


    async def perform_summon(self, discord_id: str, banner_id: Optional[int] = None) -> Dict[str, Any]:
        """Perform a waifu summon with new star system, optionally from a banner pool or normal pool."""
        user = await self.db.get_or_create_user(discord_id)

        # Check if user has enough crystals
        if user["sakura_crystals"] < self.SUMMON_COST:
            return {
                "success": False,
                "message": f"Not enough Sakura Crystals! You need {self.SUMMON_COST} but have {user['sakura_crystals']}.",
            }

        # Determine rarity using new gacha rates
        rarity = await self._determine_summon_rarity(user)

        available_waifus = []
        weights = []
        # Banner gacha
        if banner_id is not None:
            banner = await self.db.get_banner(banner_id)
            if not banner:
                return {"success": False, "message": f"Banner not found."}
            banner_type = banner.get("type", "standard")
            banner_items = await self.db.get_banner_items(banner_id)
            waifu_ids = [item["item_id"] for item in banner_items]
            # For rate-up banners, pool is ALL waifus of the pulled rarity
            if banner_type == "rate-up":
                waifus = [w for w in self._waifu_list if w.get("rarity") == rarity]
                rate_up_ids = set(item["item_id"] for item in banner_items if item.get("rate_up"))
                n = sum(1 for w in waifus if w["waifu_id"] in rate_up_ids)
                m = sum(1 for w in waifus if w["waifu_id"] not in rate_up_ids)
                if n > 0 and m > 0:
                    for w in waifus:
                        if w["waifu_id"] in rate_up_ids:
                            available_waifus.append(w)
                            weights.append(m/2)
                        else:
                            available_waifus.append(w)
                            weights.append(n*1.5)
                else:
                    # All rate-up or all non-rate-up, fallback to uniform
                    available_waifus = waifus
                    weights = [1] * len(available_waifus)
            else:
                # For limited banners, always include all 1★ waifus in the 1★ pool
                if banner_type == "limited" and rarity == 1:
                    waifus = [w for w in self._waifu_list if w["waifu_id"] in waifu_ids and w.get("rarity") == 1]
                    all_one_star_waifus = [w for w in self._waifu_list if w.get("rarity") == 1]
                    waifu_ids_in_banner = set(w["waifu_id"] for w in waifus)
                    waifus += [w for w in all_one_star_waifus if w["waifu_id"] not in waifu_ids_in_banner]
                else:
                    waifus = [w for w in self._waifu_list if w["waifu_id"] in waifu_ids and w.get("rarity") == rarity]
                available_waifus = waifus
                weights = [1] * len(available_waifus)
        else:
            # Normal gacha: all waifus of the pulled rarity
            available_waifus = [w for w in self._waifu_list if w.get('rarity') == rarity]
            weights = [1] * len(available_waifus)

        if not available_waifus:
            return {
                "success": False,
                "message": f"No waifus available for rarity {rarity}. Please contact an administrator.",
            }

        # Select random waifu using weights
        selected_waifu = random.choices(available_waifus, weights=weights, k=1)[0]

        # Handle duplicate/new character logic with new shard system
        summon_result = await self._handle_summon_result(discord_id, selected_waifu, rarity)

        # Update user's crystals and pity counter
        await self.db.update_user_crystals(discord_id, -self.SUMMON_COST)

        # Update pity system (only reset on 3* pulls now)
        if rarity >= 3:
            await self.db.update_pity_counter(discord_id, reset=True)
        else:
            await self.db.update_pity_counter(discord_id)
        # Clamp pity counter after update
        await self.clamp_pity_counter(discord_id)

        # Check for automatic rank up after summon
        await self.check_and_update_rank(discord_id)

        # Add 1 quartz for every single roll (not a guaranteed ticket)
        await self.db.update_user_quartzs(discord_id, 1)

        # Get updated user state for crystals_remaining
        updated_user = await self.db.get_or_create_user(discord_id)
        return {
            "success": True,
            "waifu": selected_waifu,
            "rarity": rarity,
            "crystals_remaining": updated_user.get("sakura_crystals", 0),
            **summon_result
        }

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

    async def perform_multi_summon(self, discord_id: str, banner_id: Optional[int] = None) -> Dict[str, Any]:
        """Perform multiple waifu summons with new star system - always 10 rolls. Guarantees at least one 2★ or higher per multi. Optionally use a banner pool."""
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

        # --- Improved Pity logic: pity is consumed as soon as a 3★ is pulled (naturally or via pity) ---
        pity_count = user.get("pity_counter", 0)
        pity_active = pity_count >= self.PITY_3_STAR
        pity_consumed = False
        results = []
        rarity_counts = {1: 0, 2: 0, 3: 0}
        waifu_rarity_pairs = []

        # Prepare waifu pool for this banner or default
        if banner_id is not None:
            banner = await self.db.get_banner(banner_id)
            if not banner:
                return {"success": False, "message": f"Banner not found."}
            banner_type = banner.get("type", "standard")
            banner_items = await self.db.get_banner_items(banner_id)
            if not banner_items:
                return {"success": False, "message": f"No waifus in this banner pool."}
            waifu_ids = [item["item_id"] for item in banner_items]
            # Always use the global pool for guarantee logic
            waifus_by_rarity = {
                r: [w for w in self._waifu_list if w.get("rarity") == r]
                for r in [1, 2, 3]
            }
            rate_up_map = {item["item_id"]: item.get("rate_up") for item in banner_items}
        else:
            banner_type = None
            banner_items = []
            waifu_ids = []
            waifus_by_rarity = {
                r: [w for w in self._waifu_list if w.get("rarity") == r]
                for r in [1, 2, 3]
            }
            rate_up_map = {}



        for i in range(count):
            current_user = await self.db.get_or_create_user(discord_id)
            # Determine rarity
            pity_reset_this_roll = False
            if pity_active and not pity_consumed:
                natural_rarity = await self._determine_summon_rarity(current_user)
                if natural_rarity == 3:
                    rarity = 3
                    pity_consumed = True
                    pity_reset_this_roll = True
                    await self.db.update_pity_counter(discord_id, reset=True)
                elif i == count - 1 or (i < count - 1 and (count - i) == (self.PITY_3_STAR - pity_count)):
                    rarity = 3
                    pity_consumed = True
                    pity_reset_this_roll = True
                    await self.db.update_pity_counter(discord_id, reset=True)
                else:
                    rarity = natural_rarity
            else:
                rarity = await self._determine_summon_rarity(current_user)
                if rarity == 3 and pity_active and not pity_consumed:
                    pity_consumed = True
                    pity_reset_this_roll = True
                    await self.db.update_pity_counter(discord_id, reset=True)
            # Only increment pity if not reset this roll
            if not pity_reset_this_roll:
                await self.db.update_pity_counter(discord_id)
            # Clamp pity counter after update
            await self.clamp_pity_counter(discord_id)

            # Banner pool selection logic
            weights = []
            available_waifus = []
            if banner_id is not None:
                if banner_type == "rate-up":
                    pool = [w for w in self._waifu_list if w.get("rarity") == rarity]
                    rate_up_ids = set(item["item_id"] for item in banner_items if item.get("rate_up"))
                    n = sum(1 for w in pool if w["waifu_id"] in rate_up_ids)
                    m = sum(1 for w in pool if w["waifu_id"] not in rate_up_ids)
                    if n > 0 and m > 0:
                        for w in pool:
                            if w["waifu_id"] in rate_up_ids:
                                available_waifus.append(w)
                                weights.append(m/2)
                            else:
                                available_waifus.append(w)
                                weights.append(n*1.5)
                    else:
                        available_waifus = pool
                        weights = [1] * len(available_waifus)
                else:
                    # For limited banners, always include all 1★ waifus in the 1★ pool
                    if banner_type == "limited" and rarity == 1:
                        pool = [w for w in self._waifu_list if w["waifu_id"] in waifu_ids and w.get("rarity") == 1]
                        all_one_star_waifus = [w for w in self._waifu_list if w.get("rarity") == 1]
                        waifu_ids_in_banner = set(w["waifu_id"] for w in pool)
                        pool += [w for w in all_one_star_waifus if w["waifu_id"] not in waifu_ids_in_banner]
                    else:
                        pool = [w for w in self._waifu_list if w["waifu_id"] in waifu_ids and w.get("rarity") == rarity]
                    available_waifus = pool
                    weights = [1] * len(available_waifus)
            else:
                pool = [w for w in self._waifu_list if w.get("rarity") == rarity]
                available_waifus = pool
                weights = [1] * len(available_waifus)

            if not available_waifus:
                continue
            selected_waifu = random.choices(available_waifus, weights=weights, k=1)[0]
            waifu_rarity_pairs.append((selected_waifu, rarity))
            rarity_counts[rarity] += 1

        # --- 2★ Guarantee: If no 2★ or 3★ was pulled, upgrade a random 1★ to 2★ ---
        if rarity_counts[2] == 0 and rarity_counts[3] == 0:
            one_star_indices = [i for i, (_, rarity) in enumerate(waifu_rarity_pairs) if rarity == 1]
            if one_star_indices:
                idx_to_upgrade = random.choice(one_star_indices)
                if banner_id is not None:
                    two_star_waifus = waifus_by_rarity[2]
                else:
                    two_star_waifus = waifus_by_rarity[2]
                if two_star_waifus:
                    waifu_rarity_pairs[idx_to_upgrade] = (random.choice(two_star_waifus), 2)
                    rarity_counts[1] -= 1
                    rarity_counts[2] += 1

        # Get user's collection before the summon
        user_collection = await self.db.get_user_collection(discord_id)
        owned_ids = {w["waifu_id"] for w in user_collection}

        new_this_session = set()
        new_waifu_ids = []
        session_new_star_level = {}  # waifu_id -> rarity of first pull this session
        session_new_shards = {}      # waifu_id -> shards accumulated in-session
        session_new_upgrades = {}    # waifu_id -> list of upgrades performed in-session
        session_new_quartz = {}      # waifu_id -> quartz gained in-session
        summon_results = []
        shard_summary = {}
        upgrade_summary = []

        for (waifu, rarity) in waifu_rarity_pairs:
            waifu_id = waifu["waifu_id"]
            if waifu_id not in owned_ids and waifu_id not in session_new_star_level:
                # First time pulled in this session, treat as new
                new_this_session.add(waifu_id)
                new_waifu_ids.append(waifu_id)
                session_new_star_level[waifu_id] = rarity
                session_new_shards[waifu_id] = 0
                session_new_upgrades[waifu_id] = []
                session_new_quartz[waifu_id] = 0
                summon_result = {
                    "is_new": True,
                    "is_duplicate": False,
                    "current_star_level": rarity,
                    "shards_gained": 0,
                    "total_shards": 0,
                    "quartz_gained": 0,
                    "upgrades_performed": []
                }
            elif waifu_id in owned_ids:
                # Already owned in DB, treat as dupe
                user_collection_entry = next((w for w in user_collection if w["waifu_id"] == waifu_id), None)
                current_star = user_collection_entry.get("current_star_level") if user_collection_entry else rarity
                if current_star is None:
                    current_star = rarity
                shard_reward = self.SHARD_REWARDS.get(rarity, 5)
                if current_star >= self.MAX_STAR_LEVEL:
                    quartz_gained = await self.convert_excess_shards_to_quartz(discord_id, waifu_id, shard_reward)
                    summon_result = {
                        "is_new": False,
                        "is_duplicate": True,
                        "current_star_level": current_star,
                        "shards_gained": 0,
                        "total_shards": 0,
                        "quartz_gained": quartz_gained,
                        "upgrades_performed": []
                    }
                else:
                    current_shards = await self.get_character_shards(discord_id, waifu_id)
                    new_shard_total = current_shards + shard_reward
                    await self.add_character_shards(discord_id, waifu_id, shard_reward)
                    upgrade_result = await self._check_and_perform_auto_upgrades(discord_id, waifu_id, new_shard_total, int(current_star))
                    summon_result = {
                        "is_new": False,
                        "is_duplicate": True,
                        "current_star_level": upgrade_result["final_star_level"],
                        "shards_gained": shard_reward,
                        "total_shards": upgrade_result["remaining_shards"],
                        "quartz_gained": upgrade_result["quartz_gained"],
                        "upgrades_performed": upgrade_result["upgrades_performed"]
                    }
            else:
                # Session-duplicate: pulled as new earlier in this session
                current_star = session_new_star_level[waifu_id]
                shard_reward = self.SHARD_REWARDS.get(rarity, 5)
                # Simulate in-memory shard and upgrade logic
                prev_shards = session_new_shards[waifu_id]
                new_shard_total = prev_shards + shard_reward
                upgrades_performed = []
                final_star_level = current_star
                remaining_shards = new_shard_total
                quartz_gained = 0
                # Simulate upgrades in-memory
                while final_star_level < self.MAX_STAR_LEVEL:
                    target_star_level = final_star_level + 1
                    required_shards = self.UPGRADE_COSTS.get(target_star_level)
                    if required_shards is None or remaining_shards < required_shards:
                        break
                    remaining_shards -= required_shards
                    upgrades_performed.append({
                        "from_star": final_star_level,
                        "to_star": final_star_level + 1,
                        "shards_used": required_shards
                    })
                    final_star_level += 1
                # If max star reached, convert excess shards to quartz (simulate)
                if final_star_level >= self.MAX_STAR_LEVEL and remaining_shards > 0:
                    quartz_gained = remaining_shards
                    remaining_shards = 0
                # Update session tracking
                session_new_shards[waifu_id] = remaining_shards
                session_new_upgrades[waifu_id].extend(upgrades_performed)
                session_new_star_level[waifu_id] = final_star_level
                session_new_quartz[waifu_id] += quartz_gained
                summon_result = {
                    "is_new": False,
                    "is_duplicate": True,
                    "current_star_level": final_star_level,
                    "shards_gained": shard_reward,
                    "total_shards": remaining_shards,
                    "quartz_gained": quartz_gained,
                    "upgrades_performed": upgrades_performed
                }
            # Pity counter already updated and clamped above per roll
            # Track shard gains and upgrades
            if summon_result["shards_gained"] > 0:
                char_name = waifu["name"]
                if char_name not in shard_summary:
                    shard_summary[char_name] = 0
                shard_summary[char_name] += summon_result["shards_gained"]
            if summon_result.get("upgrades_performed"):
                for upgrade in summon_result["upgrades_performed"]:
                    char_name = waifu["name"]
                    upgrade_info = f"{char_name}: {upgrade['from_star']}★ → {upgrade['to_star']}★"
                    upgrade_summary.append(upgrade_info)
            summon_results.append({
                "waifu": waifu,
                "rarity": rarity,
                **summon_result
            })


        # Batch add new waifus at the end
        if new_waifu_ids:
            await self.db.add_waifus_to_user_batch(discord_id, new_waifu_ids)
            # Set initial star level and shards for all new waifus
            user = await self.db.get_or_create_user(discord_id)
            if not self.db.connection_pool:
                raise RuntimeError("Database connection pool is not initialized. Call 'await waifu_service.initialize()' first.")
            async with self.db.connection_pool.acquire() as conn:
                for waifu_id in new_waifu_ids:
                    rarity = session_new_star_level[waifu_id]
                    shards = session_new_shards[waifu_id]
                    upgrades = session_new_upgrades[waifu_id]
                    quartz_gained = session_new_quartz[waifu_id]
                    # Set star level and shards
                    await conn.execute(
                        """
                        UPDATE user_waifus 
                        SET current_star_level = $1, star_shards = $2 
                        WHERE user_id = $3 AND waifu_id = $4
                        """,
                        rarity, shards, user["id"], waifu_id
                    )
                    # If any quartz was gained (from excess shards), add to user
                    if quartz_gained > 0:
                        await self.db.update_user_quartzs(discord_id, quartz_gained)

        new_waifus = [w for (w, _) in waifu_rarity_pairs if w["waifu_id"] in new_waifu_ids]
        results = summon_results

        # Get final user state
        final_user = await self.db.get_or_create_user(discord_id)

        # Check for automatic rank up after multi-summon
        await self.check_and_update_rank(discord_id)

        # Add 10 quartz for every multi roll (not a guaranteed ticket)
        await self.db.update_user_quartzs(discord_id, 10)

        return {
            "success": True,
            "results": results,
            "count": len(results),
            "total_cost": total_cost,
            "crystals_remaining": final_user["sakura_crystals"],
            "rarity_counts": rarity_counts,
            "new_waifus": new_waifus,
            "shard_summary": shard_summary,
            "upgrade_summary": upgrade_summary,
        }

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
            self.logger.error(f"Error getting enhanced collection: {e}")
            return []

    async def get_user_stats(self, discord_id: str) -> Dict[str, Any]:
        """Get comprehensive user statistics for academy status display (optimized, no N+1 queries)."""
        try:
            # Get user data
            user = await self.db.get_or_create_user(discord_id)

            # Get user's collection (already includes current_star_level and rarity)
            collection = await self.db.get_user_collection(discord_id)

            # Calculate stats
            total_waifus = len(collection)
            unique_waifus = len(set(waifu['waifu_id'] for waifu in collection))

            # Calculate collection power and star distribution
            collection_power = 0
            star_distribution = {}

            for waifu in collection:
                # Use current_star_level if present, else fallback to rarity
                star_level = waifu.get('current_star_level')
                if star_level is None:
                    star_level = waifu.get('rarity', 1)
                if star_level == 0:
                    star_level = 1

                # Calculate power based on star level (exponential growth)
                if star_level == 1:
                    power = 100
                elif star_level == 2:
                    power = 250
                elif star_level == 3:
                    power = 500
                elif star_level == 4:
                    power = 1000
                elif star_level >= 5:
                    power = 2000 * (2 ** (star_level - 5))
                else:
                    power = 100

                collection_power += power

                # Count star distribution
                if star_level in star_distribution:
                    star_distribution[star_level] += 1
                else:
                    star_distribution[star_level] = 1

            return {
                "user": user,
                "total_waifus": total_waifus,
                "unique_waifus": unique_waifus,
                "collection_power": collection_power,
                "rarity_distribution": star_distribution
            }

        except Exception as e:
            self.logger.error(f"Error getting user stats: {e}")
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
            
            # Calculate what rank the user should actually be based on their power (non-cumulative, matches docs)
            actual_rank_by_power = 1
            while True:
                next_rank = actual_rank_by_power + 1
                power_needed_for_next_rank = 1000 * (2 ** (next_rank - 1))
                if current_power >= power_needed_for_next_rank:
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
                self.logger.info(f"Auto-ranked up user {discord_id} from {current_rank} to {suggested_rank}")
                return suggested_rank
            else:
                # Debug logging to see why no rank up occurred
                self.logger.info(f"No rank up for {discord_id}: Current={current_rank}, Power rank={actual_rank_by_power} (power={current_power}), Waifu rank={actual_rank_by_waifus} (waifus={current_waifus}), Suggested={suggested_rank}")
            
            return current_rank
            
        except Exception as e:
            self.logger.error(f"Error checking/updating rank for {discord_id}: {e}")
            # Return current rank as fallback
            user = await self.db.get_or_create_user(discord_id)
            return user["collector_rank"]
