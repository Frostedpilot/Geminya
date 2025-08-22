"""Enhanced Waifu Service wit    # UPGRADE COSTS (shards required to upgrade)
    UPGRADE_COSTS = {
        2: 50,   # 1→2 star: 50 shards
        3: 100,  # 2→3 star: 100 shards
    }

    # Maximum star level (NEW SYSTEM: 1-3★ direct gacha, no 4-5★)
    MAX_STAR_LEVEL = 3-based upgrade system."""

import random
import logging
from typing import Dict, List, Any, Optional
from services.database import DatabaseService


class WaifuService:
    """Service for managing waifu gacha system with star upgrades."""

    # NEW GACHA RATES (1-3 stars only)
    GACHA_RATES = {
        3: 5.0,   # 3-star: 5%
        2: 20.0,  # 2-star: 20% 
        1: 75.0,  # 1-star: 75%
    }

    # NEW PITY SYSTEM
    PITY_3_STAR = 90   # Guaranteed 3-star every 90 pulls
    PITY_2_STAR = 10   # Guaranteed 2-star every 10 pulls

    # SHARD REWARDS (based on current star level of pulled character)
    SHARD_REWARDS = {
        3: 90,  # 3-star dupe = 90 shards
        2: 20,  # 2-star dupe = 20 shards
        1: 5,   # 1-star dupe = 5 shards
    }

    # UPGRADE COSTS (shards required to upgrade)
    UPGRADE_COSTS = {
        2: 50,   # 1→2 star: 50 shards
        3: 100,  # 2→3 star: 100 shards
        4: 200,  # 3→4 star: 200 shards
        5: 300,  # 4→5 star: 300 shards
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

    async def initialize(self):
        """Initialize the waifu service."""
        await self.db.initialize()
        self.logger.info("Waifu service initialized with new star system")

    async def close(self):
        """Close the waifu service and its database connection."""
        await self.db.close()
        self.logger.info("Waifu service closed")

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
            required_shards = self.UPGRADE_COSTS.get(final_star_level)
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
        async with self.db.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    UPDATE user_waifus 
                    SET current_star_level = %s, star_shards = %s 
                    WHERE user_id = %s AND waifu_id = %s
                """, (final_star_level, remaining_shards, user["id"], waifu_id))
                await conn.commit()
        
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
            
            async with self.db.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        SELECT shard_count 
                        FROM user_character_shards 
                        WHERE user_id = %s AND waifu_id = %s
                    """, (user["id"], waifu_id))
                    
                    result = await cursor.fetchone()
                    return result[0] if result else 0
                    
        except Exception as e:
            self.logger.error(f"Error getting character shards: {e}")
            return 0

    async def add_character_shards(self, discord_id: str, waifu_id: int, amount: int) -> int:
        """Add shards for a specific character. Returns new total."""
        try:
            user = await self.db.get_or_create_user(discord_id)
            
            async with self.db.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Insert or update shard count
                    await cursor.execute("""
                        INSERT INTO user_character_shards (user_id, waifu_id, shard_count, updated_at)
                        VALUES (%s, %s, %s, NOW())
                        ON DUPLICATE KEY UPDATE 
                        shard_count = shard_count + %s,
                        updated_at = NOW()
                    """, (user["id"], waifu_id, amount, amount))
                    
                    # Get new total
                    await cursor.execute("""
                        SELECT shard_count 
                        FROM user_character_shards 
                        WHERE user_id = %s AND waifu_id = %s
                    """, (user["id"], waifu_id))
                    
                    result = await cursor.fetchone()
                    new_total = result[0] if result else 0
                    
                    await conn.commit()
                    return new_total
                    
        except Exception as e:
            self.logger.error(f"Error adding character shards: {e}")
            return 0

    async def get_character_star_level(self, discord_id: str, waifu_id: int) -> int:
        """Get current star level of a character in user's collection."""
        try:
            async with self.db.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        SELECT uw.current_star_level, w.rarity as base_rarity
                        FROM user_waifus uw
                        JOIN waifus w ON uw.waifu_id = w.id
                        JOIN users u ON uw.user_id = u.id
                        WHERE u.discord_id = %s AND uw.waifu_id = %s
                        LIMIT 1
                    """, (discord_id, waifu_id))
                    
                    result = await cursor.fetchone()
                    if result:
                        # Use current_star_level if set, otherwise fall back to base rarity
                        return result[0] if result[0] is not None else result[1]
                    
                    # Character not owned, return base rarity
                    await cursor.execute("SELECT rarity FROM waifus WHERE id = %s", (waifu_id,))
                    waifu_result = await cursor.fetchone()
                    return waifu_result[0] if waifu_result else 1
                    
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
            
            async with self.db.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Update star level
                    await cursor.execute("""
                        UPDATE user_waifus 
                        SET current_star_level = %s 
                        WHERE user_id = %s AND waifu_id = %s
                    """, (next_star, user["id"], waifu_id))
                    
                    # Deduct shards
                    await cursor.execute("""
                        UPDATE user_character_shards 
                        SET shard_count = shard_count - %s,
                            updated_at = NOW()
                        WHERE user_id = %s AND waifu_id = %s
                    """, (required_shards, user["id"], waifu_id))
                    
                    await conn.commit()
                    
                    # Get character name for response
                    await cursor.execute("SELECT name, series FROM waifus WHERE id = %s", (waifu_id,))
                    waifu_data = await cursor.fetchone()
                    
                    remaining_shards = current_shards - required_shards
                    
                    return {
                        "success": True,
                        "character_name": waifu_data[0] if waifu_data else "Unknown",
                        "character_series": waifu_data[1] if waifu_data else "Unknown",
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

    async def perform_summon(self, discord_id: str) -> Dict[str, Any]:
        """Perform a waifu summon with new star system."""
        user = await self.db.get_or_create_user(discord_id)

        # Check if user has enough crystals
        if user["sakura_crystals"] < self.SUMMON_COST:
            return {
                "success": False,
                "message": f"Not enough Sakura Crystals! You need {self.SUMMON_COST} but have {user['sakura_crystals']}.",
            }

        # Determine rarity using new gacha rates
        rarity = await self._determine_summon_rarity(user)

        # Get available waifus of that rarity (only 1-3 stars available in gacha)
        available_waifus = await self.db.get_waifus_by_rarity(rarity, 50)

        if not available_waifus:
            return {
                "success": False,
                "message": f"No waifus available for rarity {rarity}. Please contact an administrator.",
            }

        # Select random waifu
        selected_waifu = random.choice(available_waifus)

        # Handle duplicate/new character logic with new shard system
        summon_result = await self._handle_summon_result(discord_id, selected_waifu, rarity)

        # Update user's crystals and pity counter
        await self.db.update_user_crystals(discord_id, -self.SUMMON_COST)

        # Update pity system (only reset on 3* pulls now)
        if rarity >= 3:
            await self.db.update_pity_counter(discord_id, reset=True)
        else:
            await self.db.update_pity_counter(discord_id)

        return {
            "success": True,
            "waifu": selected_waifu,
            "rarity": rarity,
            **summon_result
        }

    async def _handle_summon_result(self, discord_id: str, waifu: Dict[str, Any], pulled_rarity: int) -> Dict[str, Any]:
        """Handle summon result with new shard system and automatic upgrades."""
        waifu_id = waifu["id"]
        
        # Check if user already owns this character
        user_collection = await self.db.get_user_collection(discord_id)
        existing_waifu = next((w for w in user_collection if w["waifu_id"] == waifu_id), None)
        
        if existing_waifu:
            # DUPLICATE: Give shards based on pulled rarity (not current star level)
            current_star = existing_waifu.get("current_star_level") or pulled_rarity
            shard_reward = self.SHARD_REWARDS.get(pulled_rarity, 5)  # Based on pulled rarity
            
            # Add shards first
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
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        UPDATE user_waifus 
                        SET current_star_level = %s 
                        WHERE user_id = %s AND waifu_id = %s
                    """, (pulled_rarity, user["id"], waifu_id))
                    await conn.commit()
            
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

        # NEW Pity system check - 3* pity at 90 pulls
        if pity_count >= self.PITY_3_STAR:
            return 3

        # Normal rates with pity soft increase
        rates = self.GACHA_RATES.copy()

        # Soft pity - increase 3-star rate after 75 pulls
        if pity_count >= 75:
            increase = (pity_count - 74) * 0.6
            rates[3] = min(rates[3] + increase, 100)

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
        """Perform multiple waifu summons with new star system - always 10 rolls."""
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
        rarity_counts = {1: 0, 2: 0, 3: 0}
        new_waifus = []
        shard_summary = {}
        upgrade_summary = []

        for i in range(count):
            # Get fresh user data for each summon (for pity system)
            current_user = await self.db.get_or_create_user(discord_id)

            # Special logic for 10th roll - guarantee 2* minimum
            if i == 9:  # 10th roll (0-indexed)
                # Check if we already got a 2* or 3* in this multi-summon
                has_2_star_or_higher = any(r["rarity"] >= 2 for r in results)
                if not has_2_star_or_higher:
                    # Force 2* minimum on 10th roll
                    rarity = max(2, await self._determine_summon_rarity(current_user))
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

            # Handle summon result with new shard system
            summon_result = await self._handle_summon_result(discord_id, selected_waifu, rarity)

            # Update pity counter (no crystal deduction here since it's done upfront)
            if rarity >= 3:
                await self.db.update_pity_counter(discord_id, reset=True)
            else:
                await self.db.update_pity_counter(discord_id)

            # Track results
            rarity_counts[rarity] += 1

            if summon_result["is_new"]:
                new_waifus.append(selected_waifu)

            # Track shard gains and upgrades
            if summon_result["shards_gained"] > 0:
                char_name = selected_waifu["name"]
                if char_name not in shard_summary:
                    shard_summary[char_name] = 0
                shard_summary[char_name] += summon_result["shards_gained"]

            # Track upgrades performed
            if summon_result.get("upgrades_performed"):
                for upgrade in summon_result["upgrades_performed"]:
                    char_name = selected_waifu["name"]
                    upgrade_info = f"{char_name}: {upgrade['from_star']}★ → {upgrade['to_star']}★"
                    upgrade_summary.append(upgrade_info)

            results.append({
                "waifu": selected_waifu,
                "rarity": rarity,
                **summon_result
            })

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
