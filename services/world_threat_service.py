"""
World Threat Service - Manages the server-wide cooperative boss battle game mode

This service handles:
- Boss state management and evolution
- Player action processing (Research and Fight)
- Point calculation and reward distribution
- Checkpoint reward tracking
- Character availability filtering
"""

import json
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

from .database import DatabaseService
from src.wanderer_game.models.world_threat import WorldThreatBoss, WorldThreatPlayerStatus
from src.wanderer_game.models.character import Character, CharacterStats, Affinity, AffinityType
from src.wanderer_game.registries.data_manager import DataManager


class WorldThreatService:
    """Service for managing World Threat game mode operations."""
    
    # Game balance constants
    RESEARCH_ADAPTATION_THRESHOLD_1 = 5
    RESEARCH_ADAPTATION_THRESHOLD_2 = 10
    ADAPTATION_DAMAGE_MULTIPLIER = 0.9
    SERIES_MULTIPLIER = 1.5
    AWAKENED_REWARD_MULTIPLIER = 1.2  # Per awakened character (stacks exponentially)
    MAX_RESEARCH_STACKS = 2
    
    # Reward tiers - Immediate rewards based on points scored in single action
    # Format: (min_points, {crystals, quartzs, daphine, items: [(item_id, quantity)]})
    IMMEDIATE_REWARD_TIERS = [
        (30000, {"quartzs": 1000, "daphine": 10, "items": [{"item_type": "ITEM", "item_id": "item_7", "quantity": 10}]}),
        (20000, {"quartzs": 500, "daphine": 1, "items": [{"item_type": "ITEM", "item_id": "item_7", "quantity": 1}]}),
        (17500, {"quartzs": 300, "daphine": 1, "items": [{"item_type": "ITEM", "item_id": "item_7", "quantity": 1}]}),
        (15000, {"quartzs": 200, "daphine": 1, "items": [{"item_type": "ITEM", "item_id": "item_7", "quantity": 1}]}),
        (12500, {"quartzs": 100, "daphine": 1, "items": [{"item_type": "ITEM", "item_id": "item_7", "quantity": 1}]}),
        (10000, {"quartzs": 50, "daphine": 1, "items": [{"item_type": "ITEM", "item_id": "item_6", "quantity": 2}]}),
        (9000, {"quartzs": 20, "daphine": 0, "items": [{"item_type": "ITEM", "item_id": "item_6", "quantity": 2}]}),
        (8000, {"quartzs": 20, "daphine": 0, "items": [{"item_type": "ITEM", "item_id": "item_6", "quantity": 1}]}),
        (7000, {"quartzs": 20, "daphine": 0, "items": [{"item_type": "ITEM", "item_id": "item_6", "quantity": 1}]}),
        (6000, {"quartzs": 10, "daphine": 0, "items": [{"item_type": "ITEM", "item_id": "item_6", "quantity": 1}]}),
        (5000, {"quartzs": 10, "daphine": 1, "items": [{"item_type": "ITEM", "item_id": "item_3", "quantity": 2}]}),
        (4500, {"quartzs": 10, "daphine": 0, "items": [{"item_type": "ITEM", "item_id": "item_3", "quantity": 1}]}),
        (4000, {"quartzs": 10, "daphine": 0, "items": [{"item_type": "ITEM", "item_id": "item_1", "quantity": 2}]}),
        (3500, {"quartzs": 10, "daphine": 0, "items": [{"item_type": "ITEM", "item_id": "item_1", "quantity": 1}]}),
        (3000, {"quartzs": 10, "daphine": 0, "items": [{"item_type": "ITEM", "item_id": "item_5", "quantity": 5}]}),
        (2500, {"quartzs": 5, "daphine": 0, "items": [{"item_type": "ITEM", "item_id": "item_5", "quantity": 3}]}),
        (2000, {"quartzs": 5, "daphine": 0, "items": [{"item_type": "ITEM", "item_id": "item_5", "quantity": 1}]}),
        (1750, {"quartzs": 5, "daphine": 0, "items": [{"item_type": "ITEM", "item_id": "item_2", "quantity": 5}]}),
        (1500, {"quartzs": 5, "daphine": 0, "items": [{"item_type": "ITEM", "item_id": "item_2", "quantity": 3}]}),
        (1000, {"quartzs": 5, "daphine": 1, "items": [{"item_type": "ITEM", "item_id": "item_2", "quantity": 2}]}),
        (750, {"quartzs": 5, "daphine": 0, "items": [{"item_type": "ITEM", "item_id": "item_2", "quantity": 1}]}),
        (500, {"quartzs": 5, "daphine": 0, "items": [{"item_type": "ITEM", "item_id": "item_4", "quantity": 5}]}),
        (250, {"quartzs": 5, "daphine": 0, "items": [{"item_type": "ITEM", "item_id": "item_4", "quantity": 3}]}),
        (100, {"quartzs": 5, "daphine": 0, "items": [{"item_type": "ITEM", "item_id": "item_4", "quantity": 1}]})
    ]
    
    # Personal checkpoint rewards - Based on cumulative points
    # Format: points: {crystals, quartzs, daphine, items: [(item_id, quantity)]}
    PERSONAL_CHECKPOINT_REWARDS = {
        200000: {"crystals": 10000, "quartzs": 1000, "daphine": 10, "items": [{"item_type": "ITEM", "item_id": "item_7", "quantity": 1}]},
        100000: {"crystals": 5000, "quartzs": 500, "daphine": 5, "items": [{"item_type": "ITEM", "item_id": "item_6", "quantity": 3}]},
        75000: {"crystals": 3000, "quartzs": 250, "daphine": 3, "items": [{"item_type": "ITEM", "item_id": "item_3", "quantity": 5}]},
        50000: {"crystals": 2000, "quartzs": 100, "daphine": 2, "items": [{"item_type": "ITEM", "item_id": "item_5", "quantity": 3}]},
        25000: {"crystals": 1000, "quartzs": 50, "daphine": 1, "items": [{"item_type": "ITEM", "item_id": "item_2", "quantity": 5}]},
        10000: {"crystals": 500, "quartzs": 20, "daphine": 1, "items": [{"item_type": "ITEM", "item_id": "item_4", "quantity": 10}]}
    }
    
    # Server checkpoint rewards - Based on server total points
    # Format: points: {crystals, quartzs, daphine, items: [(item_id, quantity)]}
    SERVER_CHECKPOINT_REWARDS = {
        1000000: {"crystals": 10000, "quartzs": 1000, "daphine": 10, "items": [{"item_type": "ITEM", "item_id": "item_7", "quantity": 3}]},
        800000: {"crystals": 5000, "quartzs": 500, "daphine": 5, "items": [{"item_type": "ITEM", "item_id": "item_6", "quantity": 10}]},
        600000: {"crystals": 3000, "quartzs": 250, "daphine": 3, "items": [{"item_type": "ITEM", "item_id": "item_3", "quantity": 10}]},
        400000: {"crystals": 2000, "quartzs": 100, "daphine": 2, "items": [{"item_type": "ITEM", "item_id": "item_5", "quantity": 10}]},
        200000: {"crystals": 1000, "quartzs": 50, "daphine": 1, "items": [{"item_type": "ITEM", "item_id": "item_2", "quantity": 10}]},
        100000: {"crystals": 500, "quartzs": 20, "daphine": 1, "items": [{"item_type": "ITEM", "item_id": "item_4", "quantity": 20}]}
    }
    
    # Checkpoint point thresholds (for easier reference)
    PERSONAL_CHECKPOINTS = list(PERSONAL_CHECKPOINT_REWARDS.keys())
    SERVER_CHECKPOINTS = list(SERVER_CHECKPOINT_REWARDS.keys())
    
    # Stat pool for random selection
    ALL_STATS = ["atk","mag","vit","spr","int","spd","lck"]
    
    def __init__(self, database_service: DatabaseService):
        self.db = database_service
        self.logger = logging.getLogger(__name__)
        
        # Initialize wanderer game data manager for character data
        self.data_manager = DataManager()
        try:
            success = self.data_manager.load_all_data()
            if success:
                self.logger.info("Loaded character and game data successfully")
            else:
                self.logger.error("Failed to load character data")
                raise RuntimeError("Failed to load character data")
        except Exception as e:
            self.logger.error(f"Failed to load character data: {e}")
            raise
        
        # Initialize WaifuService for daphine distribution
        from services.waifu_service import WaifuService
        self.waifu_service = WaifuService(database_service)
        
        # Get affinity pools from data manager (loaded once at startup)
        self.affinity_pools = self.data_manager.get_affinity_pools()
        if not self.affinity_pools:
            self.logger.error("Failed to load affinity pools")
            raise RuntimeError("Affinity pools not available")
        
        self.logger.info(f"Affinity pools loaded: {', '.join(self.affinity_pools.keys())}")
    
    # === DATA ACCESS METHODS ===
    
    async def get_boss(self) -> Optional[WorldThreatBoss]:
        """Fetch the current World Threat boss from database and return as Pydantic model."""
        try:
            boss_data = await self.db.get_world_threat_boss()
            if not boss_data:
                return None
            
            # Deserialize JSON fields
            boss_data['dominant_stats'] = json.loads(boss_data['dominant_stats'])
            # cursed_stat is stored as plain string, not JSON
            boss_data['buffs'] = json.loads(boss_data['buffs'])
            boss_data['curses'] = json.loads(boss_data['curses'])
            
            return WorldThreatBoss(**boss_data)
        except Exception as e:
            self.logger.error(f"Error getting boss: {e}")
            return None
    
    async def get_player_status(self, discord_id: str) -> WorldThreatPlayerStatus:
        """Fetch player status from database, creating default if doesn't exist."""
        try:
            player_data = await self.db.get_world_threat_player_status(discord_id)
            
            if player_data:
                # Deserialize JSON fields
                player_data['claimed_personal_checkpoints'] = json.loads(player_data.get('claimed_personal_checkpoints', '[]'))
                player_data['claimed_server_checkpoints'] = json.loads(player_data.get('claimed_server_checkpoints', '[]'))
                return WorldThreatPlayerStatus(**player_data)
            else:
                # Create new player status
                new_status = WorldThreatPlayerStatus(discord_id=discord_id)
                await self._update_player_status(new_status)
                return new_status
        except Exception as e:
            self.logger.error(f"Error getting player status for {discord_id}: {e}")
            # Return default status on error
            return WorldThreatPlayerStatus(discord_id=discord_id)
    
    async def _update_boss(self, boss: WorldThreatBoss) -> bool:
        """Write updated boss model back to database."""
        try:
            await self.db.update_world_threat_boss(
                boss_name=boss.boss_name,
                dominant_stats=json.dumps(boss.dominant_stats),
                cursed_stat=boss.cursed_stat,  # Plain string, no JSON encoding
                buffs=json.dumps(boss.buffs),
                curses=json.dumps(boss.curses),
                buff_cap=boss.buff_cap,
                curse_cap=boss.curse_cap,
                server_total_points=boss.server_total_points,
                total_research_actions=boss.total_research_actions,
                adaptation_level=boss.adaptation_level
            )
            return True
        except Exception as e:
            self.logger.error(f"Error updating boss: {e}")
            return False
    
    async def _update_player_status(self, player_status: WorldThreatPlayerStatus) -> bool:
        """Write updated player status back to database."""
        try:
            # Check if player exists
            existing = await self.db.get_world_threat_player_status(player_status.discord_id)
            
            if existing:
                await self.db.update_world_threat_player_status(
                    discord_id=player_status.discord_id,
                    cumulative_points=player_status.cumulative_points,
                    last_action_timestamp=player_status.last_action_timestamp,
                    research_stacks=player_status.research_stacks,
                    claimed_personal_checkpoints=json.dumps(player_status.claimed_personal_checkpoints),
                    claimed_server_checkpoints=json.dumps(player_status.claimed_server_checkpoints)
                )
            else:
                await self.db.create_world_threat_player_status(
                    discord_id=player_status.discord_id,
                    cumulative_points=player_status.cumulative_points,
                    last_action_timestamp=player_status.last_action_timestamp,
                    research_stacks=player_status.research_stacks,
                    claimed_personal_checkpoints=json.dumps(player_status.claimed_personal_checkpoints),
                    claimed_server_checkpoints=json.dumps(player_status.claimed_server_checkpoints)
                )
            return True
        except Exception as e:
            self.logger.error(f"Error updating player status for {player_status.discord_id}: {e}")
            return False
    
    # === COOLDOWN AND ACTION VALIDATION ===
    
    async def can_perform_action(self, discord_id: str) -> Dict[str, Any]:
        """Check if player can perform an action. Actions reset daily at midnight UTC+7."""
        player_status = await self.get_player_status(discord_id)
        
        # # DEBUG
        # return {"can_act": True, "time_remaining": 0}
        
        if not player_status.last_action_timestamp:
            return {"can_act": True, "time_remaining": 0}
        
        # Check if it's a new day in UTC+7
        utc7_offset = timedelta(hours=7)
        now_utc = datetime.now(timezone.utc)
        last_action_utc = player_status.last_action_timestamp
        
        # Ensure timezone awareness
        if last_action_utc.tzinfo is None:
            last_action_utc = last_action_utc.replace(tzinfo=timezone.utc)
        
        # Work with UTC times, then convert to UTC+7 for date comparison
        now_utc7 = now_utc + utc7_offset
        last_action_utc7 = last_action_utc + utc7_offset
        
        # Check if dates are different (new day in UTC+7)
        if now_utc7.date() > last_action_utc7.date():
            return {"can_act": True, "time_remaining": 0}
        
        # Calculate time until next midnight UTC+7
        # Create naive datetime for next midnight in UTC+7, then convert to UTC
        next_midnight_utc7_naive = datetime.combine(
            now_utc7.date() + timedelta(days=1),
            datetime.min.time()
        )
        # Convert back to UTC by subtracting the offset
        next_midnight_utc = next_midnight_utc7_naive.replace(tzinfo=timezone.utc) - utc7_offset
        
        time_remaining = int((next_midnight_utc - now_utc).total_seconds())
        
        return {"can_act": False, "time_remaining": time_remaining}
    
    # === RESEARCH ACTION ===
    
    async def perform_research(self, discord_id: str) -> Dict[str, Any]:
        """
        Handle the Research action.
        - Checks cooldown
        - Increments research stacks (max 2 for x4 multiplier)
        - Updates timestamp
        - Triggers boss evolution
        """
        self.logger.info(f"[WORLD_THREAT] User {discord_id} performing Research action")
        
        try:
            # Check cooldown
            action_check = await self.can_perform_action(discord_id)
            if not action_check["can_act"]:
                return {
                    "success": False,
                    "error": "Action on cooldown",
                    "time_remaining": action_check["time_remaining"]
                }
            
            # Get player status and boss
            player_status = await self.get_player_status(discord_id)
            boss = await self.get_boss()
            
            if not boss:
                return {"success": False, "error": "No active World Threat boss"}
            
            # Increment research stacks (max 2)
            player_status.research_stacks = min(player_status.research_stacks + 1, self.MAX_RESEARCH_STACKS)
            player_status.last_action_timestamp = datetime.now(timezone.utc)
            
            # Update boss research counter
            boss.total_research_actions += 1
            
            # Save changes
            await self._update_player_status(player_status)
            
            # Evolve boss
            await self._evolve_boss(boss, is_research_action=True)
            
            research_multiplier = 2 ** player_status.research_stacks
            
            self.logger.info(f"[WORLD_THREAT] User {discord_id} completed Research (stacks: {player_status.research_stacks}, multiplier: x{research_multiplier})")
            
            return {
                "success": True,
                "new_stacks": player_status.research_stacks,
                "research_multiplier": research_multiplier,
                "message": f"Research complete! Next fight will have x{research_multiplier} multiplier."
            }
            
        except Exception as e:
            self.logger.error(f"[WORLD_THREAT] Error in perform_research for {discord_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    # === FIGHT ACTION ===
    
    async def perform_fight(self, discord_id: str, team_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Handle the Fight action.
        - Validates team (6 characters, no cursed affinities)
        - Calculates points based on formula
        - Applies research multiplier
        - Grants immediate rewards
        - Checks and grants checkpoint rewards
        - Resets research stacks
        - Triggers boss evolution
        """
        self.logger.info(f"[WORLD_THREAT] User {discord_id} performing Fight action with {len(team_data)} characters")
        
        try:
            # Check cooldown
            action_check = await self.can_perform_action(discord_id)
            if not action_check["can_act"]:
                return {
                    "success": False,
                    "error": "Action on cooldown",
                    "time_remaining": action_check["time_remaining"]
                }
            
            # Get player status and boss (fetch LATEST boss state to handle race conditions)
            player_status = await self.get_player_status(discord_id)
            boss = await self.get_boss()
            
            if not boss:
                return {"success": False, "error": "No active World Threat boss"}
            
            # Validate team size
            if len(team_data) != 6:
                return {"success": False, "error": "Team must have exactly 6 characters"}
            
            # Build character objects and validate against CURRENT boss curses
            # (Boss may have evolved between team selection and fight execution)
            character_registry = self.data_manager.get_character_registry()
            team_characters = []
            series_ids = []
            awakened_count = 0
            cursed_characters = []  # Track any newly cursed characters
            
            # Get user's waifu data to check awakened status
            user_waifus = await self.db.get_user_collection(discord_id)
            user_waifu_map = {w["waifu_id"]: w for w in user_waifus}
            
            for char_data in team_data:
                waifu_id = char_data.get("waifu_id")
                character = character_registry.get_character(waifu_id)
                
                if not character:
                    return {"success": False, "error": f"Character {waifu_id} not found"}
                
                # CRITICAL: Check if character has any cursed affinities with CURRENT boss state
                # This handles race condition where boss evolved after team selection
                if self._is_character_cursed(character, boss):
                    cursed_characters.append(character.name)
            
            # If any characters are now cursed, reject the fight
            if cursed_characters:
                cursed_list = ", ".join(cursed_characters)
                return {
                    "success": False,
                    "error": f"Boss evolved! These characters are now cursed: {cursed_list}. Please select a new team."
                }
            
            # All characters are valid, build the team
            for char_data in team_data:
                waifu_id = char_data.get("waifu_id")
                character = character_registry.get_character(waifu_id)
                
                team_characters.append({
                    "character": character,
                    "star_level": char_data.get("star_level", 1)
                })
                series_ids.append(character.series_id)
                
                # Check if character is awakened
                user_waifu = user_waifu_map.get(waifu_id)
                if user_waifu and user_waifu.get("is_awakened", False):
                    awakened_count += 1
            
            # Calculate points
            points_result = self._calculate_fight_points(team_characters, boss, player_status.research_stacks, series_ids)
            final_points = points_result["final_points"]
            
            # Update player status
            player_status.cumulative_points += final_points
            player_status.last_action_timestamp = datetime.now(timezone.utc)
            player_status.research_stacks = 0  # Reset research stacks
            
            # Update boss server total
            boss.server_total_points += final_points
            
            # Grant immediate rewards
            immediate_rewards = await self._grant_immediate_rewards(discord_id, final_points, awakened_count)
            
            # Check and grant checkpoint rewards
            checkpoint_rewards = await self._check_and_grant_checkpoint_rewards(discord_id, player_status, boss)
            
            # Save changes
            await self._update_player_status(player_status)
            
            # Evolve boss
            await self._evolve_boss(boss, is_research_action=False)
            
            self.logger.info(f"[WORLD_THREAT] User {discord_id} completed Fight (points: {final_points}, total: {player_status.cumulative_points})")
            
            return {
                "success": True,
                "points_scored": final_points,
                "total_points": player_status.cumulative_points,
                "calculation_breakdown": points_result,
                "immediate_rewards": immediate_rewards,
                "checkpoint_rewards": checkpoint_rewards,
                "awakened_count": awakened_count,
                "awakened_multiplier": 1.2 ** awakened_count if awakened_count > 0 else 1.0,
                "message": f"Fight complete! Scored {final_points:,} points."
            }
            
        except Exception as e:
            self.logger.error(f"[WORLD_THREAT] Error in perform_fight for {discord_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    # === CHARACTER FILTERING ===
    
    async def get_available_characters(self, discord_id: str) -> List[Dict[str, Any]]:
        """
        Get user's characters that can be used (not cursed by current boss).
        Filters out characters whose affinities match boss curses.
        """
        try:
            boss = await self.get_boss()
            if not boss:
                return []
            
            # Get user's collection
            user_waifus = await self.db.get_user_collection(discord_id)
            character_registry = self.data_manager.get_character_registry()
            
            available = []
            
            for user_waifu in user_waifus:
                waifu_id = user_waifu["waifu_id"]
                character = character_registry.get_character(waifu_id)
                
                if not character:
                    continue
                
                # Check if character is cursed
                if not self._is_character_cursed(character, boss):
                    available.append({
                        "user_waifu_id": user_waifu.get("id"),
                        "waifu_id": waifu_id,
                        "name": character.name,
                        "series": character.series,
                        "series_id": character.series_id,
                        "rarity": user_waifu.get("rarity", 1),
                        "star_level": user_waifu.get("current_star_level", 1),
                        "stats": character.base_stats.to_dict(),
                        "elemental_types": character.elemental_types,
                        "archetype": character.archetype,
                        "anime_genres": character.anime_genres
                    })
            
            self.logger.info(f"[WORLD_THREAT] User {discord_id} has {len(available)} available characters (filtered from {len(user_waifus)})")
            return available
            
        except Exception as e:
            self.logger.error(f"[WORLD_THREAT] Error getting available characters for {discord_id}: {e}", exc_info=True)
            return []
    
    def _is_character_cursed(self, character: Character, boss: WorldThreatBoss) -> bool:
        """Check if a character has any cursed affinity."""
        # Check elemental curses
        if "elemental" in boss.curses:
            for elemental_curse in boss.curses["elemental"]:
                if character.has_elemental_type(elemental_curse):
                    return True
        
        # Check archetype curses
        if "archetype" in boss.curses:
            for archetype_curse in boss.curses["archetype"]:
                if character.has_archetype(archetype_curse):
                    return True
        
        # Check series curses
        if "series" in boss.curses:
            if str(character.series_id) in boss.curses["series"]:
                return True
        
        # Check genre curses
        if "genre" in boss.curses:
            for genre_curse in boss.curses["genre"]:
                if character.has_genre(genre_curse):
                    return True
        
        return False
    
    # === POINT CALCULATION ===
    
    def _calculate_fight_points(
        self,
        team_characters: List[Dict[str, Any]],
        boss: WorldThreatBoss,
        research_stacks: int,
        series_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Calculate points for a fight based on the formula:
        Points = (Base_Power * Affinity_Multiplier * Series_Multiplier) * Research_Multiplier * Adaptation_Multiplier
        """
        base_power = 0
        total_buff_count = 0
        
        # Calculate base power and count total buff matches
        for char_entry in team_characters:
            character = char_entry["character"]
            star_level = char_entry["star_level"]
            
            # Base power: (sum of dominant stats - cursed stat) * (1 + 0.1*(star-1))
            char_base = 0
            
            if character.base_stats:
                stats_dict = character.base_stats.to_dict()
                
                # Sum dominant stats
                dominant_sum = sum(stats_dict.get(stat, 0) for stat in boss.dominant_stats)
                
                # Subtract cursed stat
                cursed_value = stats_dict.get(boss.cursed_stat, 0)
                
                # Apply star level multiplier: 1 + 0.1 * (star - 1)
                star_multiplier = 1 + 0.1 * (star_level - 1)
                
                # Apply formula: (dominant - cursed) * star_multiplier
                char_base = (dominant_sum - cursed_value) * star_multiplier
            
            base_power += max(0, char_base)  # Don't allow negative contributions
            
            # Count buffed affinities for this character (max 3 per character)
            char_buff_count = 0
            
            if "elemental" in boss.buffs:
                for elemental_buff in boss.buffs["elemental"]:
                    if character.has_elemental_type(elemental_buff):
                        char_buff_count += 1
                        break  # Only count once per category
            
            if "archetype" in boss.buffs:
                for archetype_buff in boss.buffs["archetype"]:
                    if character.has_archetype(archetype_buff):
                        char_buff_count += 1
                        break  # Only count once per category
            
            # Check series buffs
            if "series" in boss.buffs:
                if str(character.series_id) in boss.buffs["series"]:
                    char_buff_count += 1
            
            # Check genre buffs
            if "genre" in boss.buffs:
                for genre_buff in boss.buffs["genre"]:
                    if character.has_genre(genre_buff):
                        char_buff_count += 1
                        break  # Only count once per category
            
            # Cap buff count at 3 per character
            char_buff_count = min(char_buff_count, 3)
            
            # Add to total buff count (each buff match adds 0.2 to multiplier)
            total_buff_count += char_buff_count
        
        # Affinity multiplier: 1.0 + (buff_count * 0.2)
        affinity_multiplier = 1.0 + (total_buff_count * 0.2)
        
        # Series multiplier (1.5x if all from same series)
        series_multiplier = 1.0
        if len(set(series_ids)) == 1:
            series_multiplier = self.SERIES_MULTIPLIER
        
        # Research multiplier (2^stacks)
        research_multiplier = 2 ** research_stacks
        
        # Adaptation multiplier (damage reduction based on adaptation level)
        adaptation_multiplier = self.ADAPTATION_DAMAGE_MULTIPLIER ** boss.adaptation_level
        
        # Final calculation
        final_points = int(
            base_power * affinity_multiplier * series_multiplier * research_multiplier * adaptation_multiplier
        )
        
        return {
            "base_power": base_power,
            "affinity_multiplier": affinity_multiplier,
            "series_multiplier": series_multiplier,
            "research_multiplier": research_multiplier,
            "adaptation_multiplier": adaptation_multiplier,
            "final_points": final_points
        }
    
    # === REWARD SYSTEM ===
    
    async def _grant_immediate_rewards(
        self, 
        discord_id: str,  # Using str to match database service 
        points: int, 
        awakened_count: int
    ) -> Dict[str, Any]:
        """
        Grant immediate rewards based on points scored.
        Crystals are calculated as points/10 with awakened multiplier.
        Other rewards from tiers are cumulative - player receives ALL rewards from tiers they qualify for.
        Awakened characters apply 1.2^count multiplier to crystal rewards.
        Returns info about granted rewards.
        """
        # Calculate base crystal reward from score
        awakened_multiplier = 1.2 ** awakened_count if awakened_count > 0 else 1.0
        total_crystals = int((points / 10) * awakened_multiplier)
        
        # Collect tier-based rewards (quartzs, daphine, items) from all qualified tiers
        total_quartzs = 0
        total_daphine = 0
        all_items = []
        
        # Add rewards from all tiers the player qualifies for
        qualified_tiers = []
        for min_points, rewards in self.IMMEDIATE_REWARD_TIERS:
            if points >= min_points:
                qualified_tiers.append((min_points, rewards))
                total_quartzs += rewards.get("quartzs", 0)
                total_daphine += rewards.get("daphine", 0)
                all_items.extend(rewards.get("items", []))
        
        # Distribute rewards
        try:
            # Add crystals (sakura_crystals in DB)
            if total_crystals > 0:
                await self.db.update_user_crystals(discord_id, total_crystals)
            
            # Add quartzs
            if total_quartzs > 0:
                await self.db.update_user_quartzs(discord_id, total_quartzs)
            
            # Add daphine
            if total_daphine > 0:
                await self.waifu_service.add_daphine(discord_id, total_daphine)
            
            # Add items if any
            if all_items:
                await self.db.distribute_loot_rewards(discord_id, all_items)
            
            self.logger.info(
                f"Granted immediate rewards to {discord_id}: "
                f"{total_crystals} crystals, {total_quartzs} quartzs, {total_daphine} daphine"
            )
            
            return {
                "granted": True,
                "crystals": total_crystals,
                "quartzs": total_quartzs,
                "daphine": total_daphine,
                "items": all_items,
                "awakened_count": awakened_count,
                "awakened_multiplier": awakened_multiplier
            }
        except Exception as e:
            self.logger.error(f"Failed to grant immediate rewards: {e}")
            return {"granted": False, "error": str(e)}
    
    async def _check_and_grant_checkpoint_rewards(
        self,
        discord_id: str,  # Using str to match database service
        player_status: WorldThreatPlayerStatus,
        boss: WorldThreatBoss
    ) -> Dict[str, Any]:
        """
        Check if player has reached new checkpoints and grant rewards.
        Returns info about newly claimed checkpoints.
        """
        granted_rewards = {
            "personal": [],
            "server": []
        }
        
        # Check personal checkpoints
        for checkpoint in sorted(self.PERSONAL_CHECKPOINTS):
            if (player_status.cumulative_points >= checkpoint and 
                checkpoint not in player_status.claimed_personal_checkpoints):
                
                # Get reward definition
                reward_def = self.PERSONAL_CHECKPOINT_REWARDS.get(checkpoint)
                if not reward_def:
                    continue
                
                # Distribute rewards
                try:
                    if reward_def["crystals"] > 0:
                        await self.db.update_user_crystals(discord_id, reward_def["crystals"])
                    
                    if reward_def["quartzs"] > 0:
                        await self.db.update_user_quartzs(discord_id, reward_def["quartzs"])
                    
                    if reward_def["daphine"] > 0:
                        await self.waifu_service.add_daphine(discord_id, reward_def["daphine"])
                    
                    if reward_def["items"]:
                        await self.db.distribute_loot_rewards(discord_id, reward_def["items"])
                    
                    granted_rewards["personal"].append({
                        "checkpoint": checkpoint,
                        "reward": reward_def
                    })
                    player_status.claimed_personal_checkpoints.append(checkpoint)
                    
                    self.logger.info(
                        f"Granted personal checkpoint {checkpoint} to {discord_id}: "
                        f"{reward_def['crystals']} crystals, {reward_def['quartzs']} quartzs, "
                        f"{reward_def['daphine']} daphine"
                    )
                except Exception as e:
                    self.logger.error(f"Failed to grant personal checkpoint {checkpoint}: {e}")
        
        # Check server checkpoints
        for checkpoint in sorted(self.SERVER_CHECKPOINTS):
            if (boss.server_total_points >= checkpoint and 
                checkpoint not in player_status.claimed_server_checkpoints):
                
                # Get reward definition
                reward_def = self.SERVER_CHECKPOINT_REWARDS.get(checkpoint)
                if not reward_def:
                    continue
                
                # Distribute rewards
                try:
                    if reward_def["crystals"] > 0:
                        await self.db.update_user_crystals(discord_id, reward_def["crystals"])
                    
                    if reward_def["quartzs"] > 0:
                        await self.db.update_user_quartzs(discord_id, reward_def["quartzs"])
                    
                    if reward_def["daphine"] > 0:
                        await self.waifu_service.add_daphine(discord_id, reward_def["daphine"])
                    
                    if reward_def["items"]:
                        await self.db.distribute_loot_rewards(discord_id, reward_def["items"])
                    
                    granted_rewards["server"].append({
                        "checkpoint": checkpoint,
                        "reward": reward_def
                    })
                    player_status.claimed_server_checkpoints.append(checkpoint)
                    
                    self.logger.info(
                        f"Granted server checkpoint {checkpoint} to {discord_id}: "
                        f"{reward_def['crystals']} crystals, {reward_def['quartzs']} quartzs, "
                        f"{reward_def['daphine']} daphine"
                    )
                except Exception as e:
                    self.logger.error(f"Failed to grant server checkpoint {checkpoint}: {e}")
        
        return granted_rewards
    
    # === BOSS EVOLUTION ===
    
    async def _evolve_boss(self, boss: WorldThreatBoss, is_research_action: bool) -> bool:
        """
        Update boss stats and affinities after each action.
        - Re-rolls dominant stats (2) and cursed stat (1)
        - Adds/replaces buffs and curses
        - Checks adaptation thresholds
        """
        try:
            # Re-roll stats
            available_stats = self.ALL_STATS.copy()
            
            # Select 2 dominant stats
            boss.dominant_stats = random.sample(available_stats, 2)
            
            # Select 1 cursed stat (different from dominant)
            remaining_stats = [s for s in available_stats if s not in boss.dominant_stats]
            boss.cursed_stat = random.choice(remaining_stats)  # String, not list
            
            # Add/replace buff
            self._add_random_affinity(boss.buffs, boss.buff_cap)
            
            # Add/replace curse
            self._add_random_affinity(boss.curses, boss.curse_cap)
            
            # Check adaptation thresholds
            if is_research_action:
                if (boss.total_research_actions == self.RESEARCH_ADAPTATION_THRESHOLD_1 and 
                    boss.adaptation_level == 0):
                    boss.adaptation_level = 1
                    boss.buff_cap += 1  # Gain extra buff slot
                    self.logger.info(f"[WORLD_THREAT] Boss adapted to level 1 (extra buff slot)")
                
                elif (boss.total_research_actions == self.RESEARCH_ADAPTATION_THRESHOLD_2 and 
                      boss.adaptation_level == 1):
                    boss.adaptation_level = 2
                    boss.buff_cap += 1  # Gain another buff slot
                    self.logger.info(f"[WORLD_THREAT] Boss adapted to level 2 (extra buff slot)")
            
            # Save updated boss
            await self._update_boss(boss)
            
            self.logger.info(f"[WORLD_THREAT] Boss evolved - Dominant: {boss.dominant_stats}, Cursed: {boss.cursed_stat}")
            return True
            
        except Exception as e:
            self.logger.error(f"[WORLD_THREAT] Error evolving boss: {e}", exc_info=True)
            return False
    
    def _add_random_affinity(self, affinity_dict: Dict[str, List[str]], cap: int):
        """Add or replace a random affinity (total cap across all categories).
        
        Categories with fewer affinities are more likely to receive new ones.
        Categories with more affinities are more likely to have one removed when at cap.
        """
        # Use affinity pools loaded from DataManager (real game data)
        # Format: { 'series_id': [...], 'archetype': [...], 'elemental': [...], 'genre': [...] }
        
        # Map category names to pool keys
        category_map = {
            "elemental": "elemental",
            "archetype": "archetype", 
            "genre": "genre",
            "series": "series_id"  # series maps to series_id pool
        }
        
        # Count total affinities across all categories
        total_count = sum(len(values) for values in affinity_dict.values())
        
        # Initialize all categories
        for cat in category_map.keys():
            if cat not in affinity_dict:
                affinity_dict[cat] = []
        
        # Calculate weights for category selection (inverse of count - fewer items = higher weight)
        category_counts = {cat: len(affinity_dict.get(cat, [])) for cat in category_map.keys()}
        max_count = max(category_counts.values()) if category_counts.values() else 1
        
        # Weight calculation: categories with fewer items get higher weight
        # Add 1 to avoid zero weight, use (max_count + 1 - count) for inverse weighting
        category_weights = {cat: (max_count + 1 - count) for cat, count in category_counts.items()}
        
        # Pick a weighted random category (favoring those with fewer affinities)
        categories = list(category_weights.keys())
        weights = [category_weights[cat] for cat in categories]
        category = random.choices(categories, weights=weights, k=1)[0]
        pool_key = category_map[category]
        
        # Get available values from pool
        available_values = self.affinity_pools.get(pool_key, [])
        if not available_values:
            self.logger.warning(f"No values available for affinity category {category} (pool: {pool_key})")
            return
        
        # Pick a random value from the pool
        affinity_value = random.choice(available_values)
        
        # For series_id, convert to string if it's an int
        if category == "series":
            affinity_value = str(affinity_value)
        
        # If already in this category, don't add duplicate
        if affinity_value in affinity_dict[category]:
            return
        
        # Add if not at total cap, otherwise remove one from a weighted random category first
        if total_count < cap:
            affinity_dict[category].append(affinity_value)
        else:
            # We're at cap - remove from a category (weighted toward those with MORE items)
            all_categories = [cat for cat, vals in affinity_dict.items() if vals]
            if all_categories:
                # Weight for removal: categories with more items get higher weight
                removal_weights = [len(affinity_dict[cat]) for cat in all_categories]
                remove_category = random.choices(all_categories, weights=removal_weights, k=1)[0]
                remove_idx = random.randint(0, len(affinity_dict[remove_category]) - 1)
                affinity_dict[remove_category].pop(remove_idx)
                
                # Add new value to its proper category
                affinity_dict[category].append(affinity_value)
