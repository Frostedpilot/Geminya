from config.constants import MAX_EQUIPMENT_PER_USER
from src.wanderer_game.utils.equipment_utils import random_sub_stat_modifier
"""
Expedition Service - Bridge between Discord Bot, Database, and Wanderer Game

This service handles:
- Creating expeditions from database user data
- Managing offline expedition state
- Processing expedition completion
- Integrating with the wanderer game system
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from dataclasses import asdict
from enum import Enum

from .database import DatabaseService
from src.wanderer_game.models.character import Character, CharacterStats, Team
from src.wanderer_game.models.expedition import Expedition, ActiveExpedition
from src.wanderer_game.systems.expedition_resolver import ExpeditionResolver
from src.wanderer_game.registries.data_manager import DataManager


def serialize_for_json(obj):
    """Custom serializer that handles enums and other non-JSON types"""
    if isinstance(obj, Enum):
        return obj.value
    elif hasattr(obj, '__dict__'):
        # Convert object to dict and recursively serialize
        result = {}
        for key, value in obj.__dict__.items():
            result[key] = serialize_for_json(value)
        return result
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: serialize_for_json(value) for key, value in obj.items()}
    else:
        return obj


class ExpeditionService:
    async def remove_last_subslot(self, equipment_id: int) -> bool:
        """Remove the last unlocked subslot from an equipment and decrement unlocked_sub_slots."""
        return await self.db.remove_last_equipment_sub_slot(equipment_id)

    async def remove_all_subslots(self, equipment_id: int) -> int:
        """Remove all subslots from an equipment and reset unlocked_sub_slots to 0."""
        # Remove all subslots
        deleted = await self.db.delete_all_equipment_sub_slots(equipment_id)
        # Reset unlocked_sub_slots to 0
        await self.db.update_equipment(equipment_id, unlocked_sub_slots=0)
        return deleted

    async def unlock_subslot_by_consuming_equipment(self, target_equipment_id: int, consumed_equipment_id: int) -> bool:
        """Unlock a new subslot on target equipment by consuming another equipment, and roll the effect for that slot (all DB logic atomic)."""
        effect = random_sub_stat_modifier()
        effect_json = json.dumps(serialize_for_json(effect))
        success, _ = await self.db.unlock_subslot_by_consuming_equipment(target_equipment_id, consumed_equipment_id, effect_json)
        return success

    def __init__(self, database_service: DatabaseService):
        self.db = database_service
        self.logger = logging.getLogger(__name__)
        # Initialize wanderer game data manager
        self.data_manager = DataManager()
        
        # Load expedition templates and encounters
        try:
            success = self.data_manager.load_all_data()
            if success:
                self.logger.info("Loaded expedition and encounter data successfully")
                # Initialize expedition resolver with loaded data
                encounters_data = self.data_manager.get_encounters_as_dict()
                self.expedition_resolver = ExpeditionResolver(encounters_data, self.data_manager.get_loot_generator())
            else:
                self.logger.error("Failed to load expedition/encounter data")
                raise RuntimeError("Failed to load expedition/encounter data")
        except Exception as e:
            self.logger.error("Failed to load expedition/encounter data: %s", e)
            raise

    def _get_multiplier_value(self, multiplier_name: str) -> float:
        """Convert final multiplier name to numeric value."""
        multiplier_values = {
            "catastrophe": 0.25,  # -75%
            "setback": 0.75,      # -25%
            "standard": 1.0,      # No change
            "jackpot": 1.5        # +50%
        }
        return multiplier_values.get(multiplier_name, 1.0)

    async def get_available_expeditions(self) -> List[Dict[str, Any]]:
        """Get all available expedition templates (simplified lifecycle - no daily refresh needed)"""
        templates = []
        for template in self.data_manager.get_expedition_templates():
            # Keep original difficulty value, but calculate tier for rewards logic
            difficulty_tier = max(1, min(5, (template.difficulty + 50) // 100))
            
            # Calculate encounter count based on duration (0.5-1.5 x hours)
            # Use a more dynamic range: minimum 0.5x hours, maximum 1.5x hours
            import random
            expected_encounters = max(1, int(template.duration_hours * 1.0 * 0.75))
            
            # Convert AffinityPool objects to dictionary format for Discord display
            affinity_pools = {}
            
            # Extract favored affinities from the favored_pool
            if hasattr(template, 'favored_pool') and template.favored_pool:
                favored_data = {}
                if template.favored_pool.elemental:
                    favored_data['elemental'] = template.favored_pool.elemental
                if template.favored_pool.archetype:
                    favored_data['archetype'] = template.favored_pool.archetype
                if template.favored_pool.series_id:
                    # Convert series IDs to names using character registry
                    series_names = []
                    char_registry = self.data_manager.get_character_registry()
                    for series_id in template.favored_pool.series_id:
                        # Get characters from this series to get the series name
                        characters_in_series = char_registry.get_characters_by_series(series_id)
                        if characters_in_series:
                            series_name = characters_in_series[0].series  # All characters in series have same series name
                            series_names.append(series_name)
                    if series_names:
                        favored_data['series'] = series_names
                if template.favored_pool.genre:
                    favored_data['genre'] = template.favored_pool.genre
                
                if favored_data:
                    affinity_pools['favored'] = favored_data
            
            # Extract disfavored affinities from the disfavored_pool  
            if hasattr(template, 'disfavored_pool') and template.disfavored_pool:
                disfavored_data = {}
                if template.disfavored_pool.elemental:
                    disfavored_data['elemental'] = template.disfavored_pool.elemental
                if template.disfavored_pool.archetype:
                    disfavored_data['archetype'] = template.disfavored_pool.archetype
                if template.disfavored_pool.series_id:
                    # Convert series IDs to names using character registry
                    series_names = []
                    char_registry = self.data_manager.get_character_registry()
                    for series_id in template.disfavored_pool.series_id:
                        # Get characters from this series to get the series name
                        characters_in_series = char_registry.get_characters_by_series(series_id)
                        if characters_in_series:
                            series_name = characters_in_series[0].series  # All characters in series have same series name
                            series_names.append(series_name)
                    if series_names:
                        disfavored_data['series'] = series_names
                if template.disfavored_pool.genre:
                    disfavored_data['genre'] = template.disfavored_pool.genre
                
                if disfavored_data:
                    affinity_pools['disfavored'] = disfavored_data
            
            templates.append({
                "expedition_id": template.expedition_id,
                "name": template.name,
                "duration_hours": template.duration_hours,
                "difficulty": template.difficulty,  # Keep original raw difficulty
                "difficulty_tier": difficulty_tier,  # Keep tier for rewards logic
                "expected_encounters": expected_encounters,  # Add calculated encounters
                "num_favored_affinities": template.num_favored_affinities,
                "num_disfavored_affinities": template.num_disfavored_affinities,
                "affinity_pools": affinity_pools,  # Properly formatted affinity pools
                "encounter_pool_tags": template.encounter_pool_tags,
                "dominant_stats": getattr(template, "dominant_stats", []),
                "description": f"Duration: {template.duration_hours}h, Difficulty: {template.difficulty}, Buffs/Debuffs: {template.num_favored_affinities}/{template.num_disfavored_affinities}"
            })
        return templates

    async def get_user_expeditions(self, discord_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get user's expeditions with status information"""
        self.logger.debug(f"[EXPEDITION_GET] Loading expeditions for user {discord_id} with status filter: {status}")
        
        expeditions = await self.db.get_user_expeditions(discord_id, status)
        self.logger.debug(f"[EXPEDITION_GET] Found {len(expeditions)} expeditions for user {discord_id}")
        
        # Add completion status and time remaining for active expeditions
        current_time = datetime.now(timezone.utc)
        in_progress_count = 0
        ready_to_complete = 0
        
        for expedition in expeditions:
            if expedition['status'] == 'in_progress':
                in_progress_count += 1
                start_time = expedition['started_at']
                
                # Ensure timezone awareness - database timestamps are UTC
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                
                duration = timedelta(hours=expedition['duration_hours'])
                end_time = start_time + duration
                
                expedition['end_time'] = end_time
                expedition['is_complete'] = current_time >= end_time
                expedition['time_remaining'] = max(0, (end_time - current_time).total_seconds())
                
                if expedition['is_complete']:
                    ready_to_complete += 1
            else:
                expedition['is_complete'] = True
                expedition['time_remaining'] = 0
        
        if status == 'in_progress':
            self.logger.info(f"[EXPEDITION_GET] User {discord_id} has {in_progress_count} in_progress expeditions, {ready_to_complete} ready to complete")
                
        return expeditions

    async def get_user_characters_for_expedition(self, discord_id: str) -> List[Dict[str, Any]]:
        """Get user's characters suitable for expeditions"""
        db_waifus = await self.db.get_user_waifus_for_expedition(discord_id)
        
        characters = []
        for db_waifu in db_waifus:
            # Convert database waifu to character format
            character_data = {
                "user_waifu_id": db_waifu["user_waifu_id"],
                "waifu_id": db_waifu["waifu_id"],
                "name": db_waifu["name"],
                "series": db_waifu["series"],
                "rarity": db_waifu["rarity"],
                "current_star_level": db_waifu["current_star_level"] or 1,
                "bond_level": db_waifu["bond_level"],
                "stats": db_waifu.get("stats", {}),
                "elemental_type": db_waifu.get("elemental_type", []),
                "archetype": db_waifu.get("archetype", ""),
                "potency": db_waifu.get("potency", {}),
                "elemental_resistances": db_waifu.get("elemental_resistances", {})
            }
            characters.append(character_data)
            
        return characters

    async def start_expedition(self, discord_id: str, expedition_id: str, participant_data: List[Dict[str, Any]], equipped_equipment_id: Optional[int] = None) -> Dict[str, Any]:
        """Start a new expedition with the given participants - simplified lifecycle"""
        self.logger.info(f"[EXPEDITION_START] User {discord_id} attempting to start expedition {expedition_id} with {len(participant_data)} participants")
        
        try:
            # Check expedition limit - each player can only have up to MAX_EXPEDITION_SLOTS ongoing expeditions
            self.logger.debug(f"[EXPEDITION_START] Checking expedition limit for user {discord_id}")
            active_expeditions = await self.get_user_expeditions(discord_id, status='in_progress')
            self.logger.debug(f"[EXPEDITION_START] User {discord_id} has {len(active_expeditions)} active expeditions")
            
            from cogs.commands.expeditions import MAX_EXPEDITION_SLOTS
            if len(active_expeditions) >= MAX_EXPEDITION_SLOTS:
                self.logger.warning(f"[EXPEDITION_START] User {discord_id} at expedition limit ({len(active_expeditions)}/{MAX_EXPEDITION_SLOTS})")
                return {
                    "success": False,
                    "error": f"You can only have up to {MAX_EXPEDITION_SLOTS} ongoing expeditions at a time. Complete some expeditions first."
                }
            
            # Validate expedition template exists
            self.logger.debug(f"[EXPEDITION_START] Validating expedition template {expedition_id}")
            template = None
            for exp_template in self.data_manager.get_expedition_templates():
                if exp_template.expedition_id == expedition_id:
                    template = exp_template
                    break
            
            if not template:
                self.logger.error(f"[EXPEDITION_START] Expedition template {expedition_id} not found")
                return {"success": False, "error": f"Expedition template {expedition_id} not found"}
            
            self.logger.info(f"[EXPEDITION_START] Using template: {template.name} (Duration: {template.duration_hours}h, Difficulty: {template.difficulty})")
            
            # Validate participants
            self.logger.debug(f"[EXPEDITION_START] Validating {len(participant_data)} participants")
            if not participant_data or len(participant_data) == 0:
                self.logger.error(f"[EXPEDITION_START] No participants provided")
                return {"success": False, "error": "At least one participant is required"}
            
            # Check for conflicts (characters already in expeditions)
            participant_ids = [p["user_waifu_id"] for p in participant_data]
            self.logger.debug(f"[EXPEDITION_START] Checking conflicts for characters: {participant_ids}")
            conflicts = await self.db.check_expedition_conflicts(discord_id, participant_ids)
            if conflicts:
                self.logger.warning(f"[EXPEDITION_START] Character conflicts found: {conflicts}")
                return {"success": False, "error": f"Characters with IDs {conflicts} are already in expeditions"}
            
            # Get participant details - optimized approach
            self.logger.debug(f"[EXPEDITION_START] Loading participant details")
            db_participants = []
            team_series_ids = []
            
            # Get minimal user waifu data once (no database joins)
            user_waifus = await self.db.get_user_waifus_minimal(discord_id)
            user_waifu_lookup = {uw["user_waifu_id"]: uw for uw in user_waifus}
            self.logger.debug(f"[EXPEDITION_START] Loaded {len(user_waifus)} user waifus")
            
            # Get character registry for local character data
            character_registry = self.data_manager.get_character_registry()
            
            for participant in participant_data:
                user_waifu = user_waifu_lookup.get(participant["user_waifu_id"])
                if not user_waifu:
                    self.logger.error(f"[EXPEDITION_START] Character {participant['user_waifu_id']} not found in user's waifus")
                    return {"success": False, "error": f"Character {participant['user_waifu_id']} not found"}
                
                # Get character details from local CSV data
                character = character_registry.get_character(user_waifu["waifu_id"])
                if not character:
                    self.logger.error(f"[EXPEDITION_START] Character data not found for waifu_id {user_waifu['waifu_id']}")
                    return {"success": False, "error": f"Character data not found for waifu_id {user_waifu['waifu_id']}"}
                
                star_level = participant.get("star_level", user_waifu.get("current_star_level", 1) or 1)
                self.logger.debug(f"[EXPEDITION_START] Adding participant: {character.name} (waifu_id: {user_waifu['waifu_id']}, star_level: {star_level})")
                
                db_participants.append({
                    "user_waifu_id": participant["user_waifu_id"],
                    "star_level": star_level
                })
                
                # Collect team series IDs for dynamic encounter tags
                if character.series_id:
                    team_series_ids.append(character.series_id)
            
            self.logger.info(f"[EXPEDITION_START] Team composition: {len(db_participants)} characters from {len(set(team_series_ids))} different series")
            
            # NEW APPROACH: Store base template data and team info, roll buffs/debuffs at completion time
            # No need to generate expedition instance here - just store template reference and team data
            
            # Calculate estimated encounter count for display (actual count will be rolled at completion)
            # Use the midpoint of the 0.5-1.5x range for estimate: 1.0x
            estimated_encounter_count = max(1, int(template.duration_hours * 0.75))  # Midpoint estimate, minimum 1
            self.logger.debug(f"[EXPEDITION_START] Estimated encounter count: {estimated_encounter_count}")
            
            # Prepare simplified expedition data for database
            expedition_data = {
                "name": template.name,
                "location": template.expedition_id,  # Use template ID as location
                "difficulty": str(template.difficulty),
                "duration_hours": template.duration_hours,
                "template_data": {
                    "expedition_id": template.expedition_id,
                    "name": template.name,
                    "duration_hours": template.duration_hours,
                    "difficulty": template.difficulty,
                    "encounter_pool_tags": template.encounter_pool_tags,
                    "num_favored_affinities": template.num_favored_affinities,
                    "num_disfavored_affinities": template.num_disfavored_affinities,
                    "favored_pool": serialize_for_json(template.favored_pool),
                    "disfavored_pool": serialize_for_json(template.disfavored_pool),
                    "team_series_ids": team_series_ids,  # Store for runtime encounter tag generation
                    "dominant_stats": getattr(template, "dominant_stats", [])
                }
            }
            
            # Create expedition in database
            self.logger.info(f"[EXPEDITION_START] Creating expedition in database for user {discord_id}")
            # Pass equipped_equipment_id to DB if provided
            expedition_db_id = await self.db.create_expedition(
                discord_id,
                expedition_data,
                db_participants,
                equipped_equipment_id=equipped_equipment_id
            )
            
            if expedition_db_id:
                self.logger.info(f"[EXPEDITION_START] Successfully created expedition {expedition_db_id} for user {discord_id}")
            else:
                self.logger.error(f"[EXPEDITION_START] Failed to create expedition in database for user {discord_id}")
                return {"success": False, "error": "Failed to create expedition in database"}
            
            return {
                "success": True,
                "expedition_id": expedition_db_id,
                "name": template.name,
                "duration_hours": template.duration_hours,
                "estimated_encounters": estimated_encounter_count,
                "message": "Expedition started! Complete it manually when ready to resolve results."
            }
            
        except Exception as e:
            self.logger.error(f"[EXPEDITION_START] Error starting expedition for user {discord_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # REMOVED: Auto-processing methods - New lifecycle is MANUAL COMPLETION ONLY
    # Users must explicitly complete expeditions using complete_expedition()
    # This removes the complexity of background processing and daily lifecycles

    def _generate_expedition_at_completion(self, template_data: Dict[str, Any]) -> Expedition:
        """
        Generate expedition instance at completion time with RUNTIME RANDOMIZATION
        
        This implements the "scummy" approach - no pre-generated buffs/debuffs,
        all randomization happens at completion time for maximum variance.
        """
        import random
        from src.wanderer_game.models.character import Affinity, AffinityType
        
        # Reconstruct affinity pools from stored data
        favored_pool_data = template_data.get("favored_pool", {})
        disfavored_pool_data = template_data.get("disfavored_pool", {})
        
        # Helper function to create affinities from pool data
        def create_affinities_from_pool(pool_data: Dict, count: int) -> List[Affinity]:
            all_affinities = []
            
            # Add elemental affinities
            for elem in pool_data.get("elemental", []):
                all_affinities.append(Affinity(AffinityType.ELEMENTAL, elem))
            
            # Add archetype affinities  
            for arch in pool_data.get("archetype", []):
                all_affinities.append(Affinity(AffinityType.ARCHETYPE, arch))
                
            # Add series ID affinities
            for series in pool_data.get("series_id", []):
                all_affinities.append(Affinity(AffinityType.SERIES_ID, str(series)))
                
            # Add genre affinities
            for genre in pool_data.get("genre", []):
                all_affinities.append(Affinity(AffinityType.GENRE, genre))
            
            # Randomly select the requested count
            if len(all_affinities) >= count:
                return random.sample(all_affinities, count)
            else:
                return all_affinities  # Return all if not enough available
        
        # RUNTIME RANDOMIZATION: Roll for buffs/debuffs NOW
        num_favored = template_data.get("num_favored_affinities", 0)
        num_disfavored = template_data.get("num_disfavored_affinities", 0)
        
        favored_affinities = create_affinities_from_pool(favored_pool_data, num_favored)
        disfavored_affinities = create_affinities_from_pool(disfavored_pool_data, num_disfavored)

        # RUNTIME ENCOUNTER COUNT: Roll for encounter count NOW
        duration_hours = template_data.get("duration_hours", 1)
        random_factor = random.random()  # 0.0 to 1.0
        encounter_count = max(1, int(duration_hours * (0.5 + random_factor * 1.0) * 0.75))  # 0.5x to 1.5x

        # Build dynamic encounter pool tags
        base_tags = template_data.get("encounter_pool_tags", [])
        team_series_ids = template_data.get("team_series_ids", [])
        dynamic_tags = base_tags.copy()
        dynamic_tags.extend([str(sid) for sid in team_series_ids])

        # Create expedition instance with runtime-rolled values
        expedition = Expedition(
            expedition_id=template_data["expedition_id"],
            name=template_data["name"],
            duration_hours=duration_hours,
            difficulty=template_data["difficulty"],
            favored_affinities=favored_affinities,
            disfavored_affinities=disfavored_affinities,
            encounter_pool_tags=dynamic_tags,
            encounter_count=encounter_count,
            dominant_stats=template_data.get("dominant_stats", [])
        )

        self.logger.info(f"Generated expedition at completion: {encounter_count} encounters, {len(favored_affinities)} favored, {len(disfavored_affinities)} disfavored affinities")
        return expedition

    async def get_expedition_details(self, expedition_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about an expedition"""
        expedition = await self.db.get_expedition_with_participants(expedition_id)
        if not expedition:
            return None
        
        # Add completion status
        current_time = datetime.now(timezone.utc)
        if expedition['status'] == 'in_progress':
            start_time = expedition['started_at']
            
            # Ensure timezone awareness - database timestamps are UTC
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            
            duration = timedelta(hours=expedition['duration_hours'])
            end_time = start_time + duration
            
            expedition['end_time'] = end_time
            expedition['is_complete'] = current_time >= end_time
            expedition['time_remaining'] = max(0, (end_time - current_time).total_seconds())
        else:
            expedition['is_complete'] = True
            expedition['time_remaining'] = 0
        
        # Get logs
        expedition['logs'] = await self.db.get_expedition_logs(expedition_id)
        
        return expedition

    async def claim_expedition_rewards(self, discord_id: str, expedition_id: int) -> Dict[str, Any]:
        """Claim rewards from a completed expedition"""
        try:
            # Get expedition details
            expedition = await self.db.get_expedition_with_participants(expedition_id)
            if not expedition:
                return {"success": False, "error": "Expedition not found"}
            
            # Verify expedition belongs to user
            user_data = await self.db.get_or_create_user(discord_id)
            if expedition["user_id"] != user_data["id"]:
                return {"success": False, "error": "Not your expedition"}
            
            # Check if expedition is completed
            if expedition["status"] != "completed":
                return {"success": False, "error": "Expedition not completed"}
            
            # Check if rewards already claimed
            if expedition["rewards_claimed"]:
                return {"success": False, "error": "Rewards already claimed"}
            
            # Process rewards (implement reward logic based on final_results)
            final_results = expedition.get("final_results", {})
            
            # For now, just mark as claimed
            # TODO: Implement actual reward processing (gems, items, etc.)
            success = await self.db.claim_expedition_rewards(expedition_id)
            
            if success:
                return {
                    "success": True,
                    "rewards": final_results.get("total_loot", []),
                    "expedition_success": final_results.get("expedition_success", False)
                }
            else:
                return {"success": False, "error": "Failed to claim rewards"}
                
        except Exception as e:
            self.logger.error("Error claiming expedition rewards: %s", e)
            return {"success": False, "error": str(e)}

    async def cancel_expedition(self, discord_id: str, expedition_id: int) -> Dict[str, Any]:
        """Cancel an active expedition"""
        try:
            # Get expedition details
            expedition = await self.db.get_expedition_with_participants(expedition_id)
            if not expedition:
                return {"success": False, "error": "Expedition not found"}
            
            # Verify expedition belongs to user
            user_data = await self.db.get_or_create_user(discord_id)
            if expedition["user_id"] != user_data["id"]:
                return {"success": False, "error": "Not your expedition"}
            
            # Check if expedition can be cancelled
            if expedition["status"] != "in_progress":
                return {"success": False, "error": "Expedition cannot be cancelled"}
            
            # Update status
            await self.db.update_expedition_status(expedition_id, "cancelled")
            
            # Add log entry
            await self.db.add_expedition_log(
                expedition_id,
                "cancellation",
                "Expedition cancelled by user"
            )
            
            return {"success": True, "message": "Expedition cancelled"}
            
        except Exception as e:
            self.logger.error("Error cancelling expedition: %s", e)
            return {"success": False, "error": str(e)}

    async def complete_expedition(self, expedition_id: int, discord_id: str) -> Dict[str, Any]:
        """
        MANUAL COMPLETION: Complete an expedition with full resolution and loot distribution
        
        This method implements the new simplified lifecycle:
        1. Load base template and participants
        2. Generate expedition instance with runtime randomization (buffs/debuffs)
        3. Resolve encounters using the wanderer game engine
        4. Distribute loot rewards
        5. Mark expedition as completed
        
        Args:
            expedition_id: ID of the expedition to complete
            discord_id: Discord ID of the user completing the expedition
            
        Returns:
            Dictionary with complete expedition results and loot rewards
        """
        self.logger.info(f"[EXPEDITION_COMPLETE] User {discord_id} attempting to complete expedition {expedition_id}")
        
        try:
            # Get expedition with participants from database
            self.logger.debug(f"[EXPEDITION_COMPLETE] Loading expedition {expedition_id} data")
            expedition = await self.db.get_expedition_with_participants(expedition_id)
            if not expedition:
                self.logger.error(f"[EXPEDITION_COMPLETE] Expedition {expedition_id} not found in database")
                return {"success": False, "error": f"Expedition {expedition_id} not found"}
            
            # Verify expedition belongs to user
            user_data = await self.db.get_or_create_user(discord_id)
            if expedition["user_id"] != user_data["id"]:
                self.logger.warning(f"[EXPEDITION_COMPLETE] User {discord_id} attempted to complete expedition {expedition_id} belonging to user_id {expedition['user_id']}")
                return {"success": False, "error": "You can only complete your own expeditions"}
            
            # Check expedition status
            if expedition["status"] != "in_progress":
                self.logger.warning(f"[EXPEDITION_COMPLETE] Expedition {expedition_id} status is '{expedition['status']}', cannot complete")
                return {"success": False, "error": f"Expedition is {expedition['status']}, cannot complete"}
            
            self.logger.info(f"[EXPEDITION_COMPLETE] Expedition {expedition_id} validation passed - proceeding with completion")
            
            # Get template data that was stored at expedition start
            template_data = expedition["expedition_data"].get("template_data", {})
            if not template_data:
                self.logger.error(f"[EXPEDITION_COMPLETE] Expedition {expedition_id} missing template data")
                return {"success": False, "error": "Invalid expedition data - missing template information"}
            
            # Step 1: Reconstruct template and generate expedition instance with RUNTIME RANDOMIZATION
            # This is where we roll for buffs/debuffs at completion time!
            expedition_instance = self._generate_expedition_at_completion(template_data)
            
            # Step 2: Convert participants to Character objects using local CSV data
            team_characters = []
            character_registry = self.data_manager.get_character_registry()
            
            for participant in expedition["participants"]:
                # Get character details from local CSV data
                character = character_registry.get_character(participant["waifu_id"])
                if not character:
                    return {"success": False, "error": f"Character data not found for waifu_id {participant['waifu_id']}"}
                # Apply star level used in expedition
                character.star_level = participant["star_level_used"]
                team_characters.append(character)
            team = Team(team_characters)

            # Step 3: Fetch equipped equipment and sub slots, parse EncounterModifier effects
            equipped_equipment_id = expedition.get('equipped_equipment_id')
            equipment_obj = None
            if equipped_equipment_id:
                equipment_row = await self.db.get_equipment_by_id(equipped_equipment_id)
                if equipment_row:
                    from src.wanderer_game.models.equipment import Equipment, EquipmentSubSlot
                    from src.wanderer_game.models.encounter import EncounterModifier
                    import json
                    # Parse main_effect as EncounterModifier
                    main_effect_data = json.loads(equipment_row['main_effect']) if isinstance(equipment_row['main_effect'], str) else equipment_row['main_effect']
                    main_effect = EncounterModifier.from_dict(main_effect_data) if main_effect_data else None
                    # Use sub_slots from equipment_row dict
                    sub_slots = []
                    for slot_row in equipment_row.get('sub_slots', []):
                        effect_data = json.loads(slot_row['effect']) if slot_row.get('effect') else None
                        effect = EncounterModifier.from_dict(effect_data) if effect_data else None
                        sub_slots.append(EquipmentSubSlot(
                            slot_index=slot_row['slot_index'],
                            effect=effect,
                            is_unlocked=slot_row['is_unlocked']
                        ))
                    equipment_obj = Equipment(
                        id=equipment_row['id'],
                        discord_id=equipment_row['discord_id'],
                        main_effect=main_effect,
                        unlocked_sub_slots=equipment_row.get('unlocked_sub_slots', 0),
                        sub_slots=sub_slots,
                        created_at=str(equipment_row.get('created_at')) if equipment_row.get('created_at') else None,
                        updated_at=str(equipment_row.get('updated_at')) if equipment_row.get('updated_at') else None
                    )

            # Step 3.5: Award equipment after each encounter
            from src.wanderer_game.models.equipment import random_equipment_no_subslots
            awarded_equipment = []

            # Step 4: Create ActiveExpedition object for resolution
            import time
            current_time = time.time()
            active_expedition = ActiveExpedition(
                expedition=expedition_instance,
                team_character_ids=[char.waifu_id for char in team_characters],
                start_timestamp=current_time,
                end_timestamp=current_time  # Immediately complete for resolution
            )

            # Step 5: Resolve expedition through wanderer game engine, passing equipment_obj
            self.logger.info(f"Resolving expedition {expedition_id} with {expedition_instance.encounter_count} encounters")
            expedition_result = self.expedition_resolver.resolve(active_expedition, team, equipment_obj)

            # Award only one equipment per expedition, enforcing the global cap
            user_equipment = await self.db.get_user_equipment(discord_id)
            if len(user_equipment) < MAX_EQUIPMENT_PER_USER:
                new_equipment = random_equipment_no_subslots(discord_id)
                if new_equipment.main_effect is None:
                    self.logger.warning("Skipping equipment award: generated equipment has no main_effect (discord_id=%s)", discord_id)
                else:
                    import json as _json
                    main_effect_json = _json.dumps({
                        "type": getattr(new_equipment.main_effect.type, 'value', None),
                        "affinity": getattr(new_equipment.main_effect, 'affinity', None),
                        "category": getattr(new_equipment.main_effect, 'category', None),
                        "value": getattr(new_equipment.main_effect, 'value', None),
                        "stat": getattr(new_equipment.main_effect, 'stat', None)
                    })
                    equipment_id = await self.db.add_equipment(discord_id, main_effect_json, unlocked_sub_slots=0)
                    new_equipment.id = equipment_id
                    awarded_equipment.append(new_equipment)
            else:
                self.logger.info("User %s has reached the equipment cap (%d). No equipment awarded.", discord_id, MAX_EQUIPMENT_PER_USER)

            # Step 5: Distribute loot rewards to user
            self.logger.info(f"Expedition result - Loot pool exists: {expedition_result.loot_pool is not None}")
            if expedition_result.loot_pool:
                self.logger.info(f"Loot pool items count: {len(expedition_result.loot_pool.items) if expedition_result.loot_pool.items else 0}")
                self.logger.info(f"Loot pool total value: {expedition_result.loot_pool.get_total_value()}")
                # Log details of each loot item for debugging
                if expedition_result.loot_pool.items:
                    for i, item in enumerate(expedition_result.loot_pool.items):
                        self.logger.info(f"Loot item {i}: type={item.item_type.value if hasattr(item.item_type, 'value') else item.item_type}, id={item.item_id}, quantity={item.quantity}, rarity={item.rarity.value if hasattr(item.rarity, 'value') else item.rarity}, value={item.value}")
            if expedition_result.loot_pool and expedition_result.loot_pool.items:
                loot_result = await self.db.distribute_loot_rewards(discord_id, expedition_result.loot_pool.items)
                self.logger.info(f"Distributed loot - Currency: {loot_result.get('currency_rewards', {})}")
            else:
                loot_result = {"success": True, "total_items": 0, "currency_rewards": {"sakura_crystals": 0, "quartzs": 0}}
                self.logger.info("No loot pool or no items - no rewards distributed")
            
            # Step 6: Prepare complete expedition results
            expedition_success = expedition_result.great_successes + expedition_result.successes > expedition_result.failures + expedition_result.mishaps
            
            # Determine outcome string based on results
            if expedition_result.great_successes >= expedition_result.successes and expedition_result.great_successes > 0 and expedition_result.failures == 0 and expedition_result.mishaps == 0:
                outcome_string = "perfect"
            elif expedition_success and expedition_result.great_successes > 0:
                outcome_string = "great_success"
            elif expedition_success:
                outcome_string = "success"
            else:
                outcome_string = "failure"
            
            final_results = {
                "expedition_success": expedition_success,
                "encounters_completed": len(expedition_result.encounter_results),
                "great_successes": expedition_result.great_successes,
                "successes": expedition_result.successes,
                "failures": expedition_result.failures,
                "mishaps": expedition_result.mishaps,
                "final_multiplier": expedition_result.final_multiplier.value,
                "final_luck_score": expedition_result.final_luck_score,
                "expedition_log": expedition_result.generate_log(),
                "outcome": outcome_string,
                "loot_summary": {
                    "total_items": len(expedition_result.loot_pool.items) if expedition_result.loot_pool.items else 0,
                    "total_value": expedition_result.loot_pool.get_total_value() if expedition_result.loot_pool else 0
                }
            }
            
            # Step 7: Update expedition status in database and mark rewards as claimed
            await self.db.update_expedition_status(expedition_id, "completed", final_results)
            
            # Step 8: Release expedition participants so they can be used in new expeditions
            await self.db.release_expedition_participants(expedition_id)
            
            # Mark rewards as claimed since they are automatically distributed
            await self.db.claim_expedition_rewards(expedition_id)
            
            # Step 9: Add completion log
            await self.db.add_expedition_log(
                expedition_id,
                "completion",
                f"Expedition manually completed with {'SUCCESS' if expedition_success else 'FAILURE'} - {expedition_result.great_successes}⭐ {expedition_result.successes}✓ {expedition_result.failures}✗ {expedition_result.mishaps}💥"
            )
            
            return {
                "success": True,
                "expedition_id": expedition_id,
                "expedition_name": expedition_instance.name,
                "expedition_success": expedition_success,
                "outcome": outcome_string,
                "result_summary": {
                    "encounters": len(expedition_result.encounter_results),
                    "great_successes": expedition_result.great_successes,
                    "successes": expedition_result.successes,
                    "failures": expedition_result.failures,
                    "mishaps": expedition_result.mishaps,
                    "final_multiplier": expedition_result.final_multiplier.value,
                    "final_multiplier_numeric": self._get_multiplier_value(expedition_result.final_multiplier.value)
                },
                "encounter_results": expedition_result.encounter_results,  # Add raw encounter results for difficulty access
                "loot_result": loot_result,
                "loot_items": expedition_result.loot_pool.items if expedition_result.loot_pool else [],
                "loot_currency": loot_result.get("currency_rewards", {}),
                "expedition_log": expedition_result.generate_log(),  # Full log for detailed view
                "completion_time": datetime.now(timezone.utc).isoformat(),
                "awarded_equipment": [
                    {
                        "id": eq.id,
                        "discord_id": eq.discord_id,
                        "main_effect": {
                            "type": eq.main_effect.type.value,
                            "affinity": eq.main_effect.affinity,
                            "category": eq.main_effect.category,
                            "value": eq.main_effect.value,
                            "stat": eq.main_effect.stat
                        },
                        "created_at": eq.created_at,
                        "updated_at": eq.updated_at
                    }
                    for eq in awarded_equipment
                ]
            }
            
        except Exception as e:
            self.logger.error("Error completing expedition: %s", e)
            return {"success": False, "error": str(e)}

    async def get_user_expedition_summary(self, discord_id: str) -> Dict[str, Any]:
        """
        Get summary of user's expeditions and current resources
        
        Args:
            discord_id: User's Discord ID
            
        Returns:
            Dictionary with expedition history and current resources
        """
        try:
            # Get user's expeditions
            expeditions = await self.db.get_user_expeditions(discord_id)
            
            # Get current currency
            currency = await self.db.get_user_currency(discord_id)
            
            # Get inventory items
            inventory = await self.db.get_user_inventory_items(discord_id)
            
            return {
                "success": True,
                "expeditions": {
                    "total": len(expeditions),
                    "active": len([e for e in expeditions if e.get('status') == 'active']),
                    "completed": len([e for e in expeditions if e.get('status') == 'completed']),
                    "list": expeditions
                },
                "resources": {
                    "currency": currency,
                    "inventory_items": len(inventory),
                    "recent_items": inventory[:5]  # Show 5 most recent items
                }
            }
            
        except Exception as e:
            self.logger.error("Error getting expedition summary: %s", e)
            return {"success": False, "error": str(e)}

    async def get_expedition_participants(self, expedition_id: int) -> List[Dict[str, Any]]:
        """Get participants of a specific expedition."""
        try:
            if not self.db.connection_pool:
                self.logger.error("Database connection pool not initialized")
                return []
                
            query = """
                SELECT ep.*, uw.waifu_id, uw.current_star_level, uw.bond_level
                FROM expedition_participants ep
                JOIN user_waifus uw ON ep.user_waifu_id = uw.id
                WHERE ep.expedition_id = $1
                ORDER BY ep.id
            """
            
            async with self.db.connection_pool.acquire() as conn:
                participants = await conn.fetch(query, expedition_id)
                return [dict(participant) for participant in participants]
                
        except Exception as e:
            self.logger.error(f"Error getting expedition participants: {e}")
            return []

    async def complete_user_expeditions(self, discord_id: str) -> List[Dict[str, Any]]:
        """Complete all ready expeditions for a user and return results, including awarded equipment."""
        try:
            # Get user's in-progress expeditions
            expeditions = await self.get_user_expeditions(discord_id, status='in_progress')
            completed_expeditions = []

            from datetime import datetime, timedelta

            for expedition in expeditions:
                try:
                    # Check if expedition is ready to complete
                    start_time = expedition.get('started_at')
                    duration_hours = expedition.get('duration_hours', 4)

                    if start_time:
                        # Ensure timezone awareness - database timestamps are UTC
                        if start_time.tzinfo is None:
                            start_time = start_time.replace(tzinfo=timezone.utc)

                        end_time = start_time + timedelta(hours=duration_hours)
                        now = datetime.now(timezone.utc)

                        if now >= end_time:
                            # Complete this expedition
                            result = await self.complete_expedition(expedition['id'], discord_id)
                            if result.get('success'):
                                # Properly structure the loot data
                                loot_data = {
                                    'sakura_crystals': result.get('loot_currency', {}).get('sakura_crystals', 0),
                                    'quartzs': result.get('loot_currency', {}).get('quartzs', 0),
                                    'items': result.get('loot_items', [])
                                }

                                # Include awarded_equipment in the result if present
                                awarded_equipment = result.get('awarded_equipment', [])

                                completed_expeditions.append({
                                    **expedition,
                                    'loot': loot_data,
                                    'outcome': result.get('outcome', 'success'),
                                    'completion_time': now,
                                    'expedition_log': result.get('expedition_log', []),
                                    'result_summary': result.get('result_summary', {}),
                                    'encounter_results': result.get('encounter_results', []),  # Add encounter results
                                    'loot_result': result.get('loot_result', {}),
                                    'expedition_name': result.get('expedition_name', expedition.get('expedition_name', 'Unknown Expedition')),
                                    'awarded_equipment': awarded_equipment
                                })

                except Exception as e:
                    self.logger.error(f"Error completing expedition {expedition.get('id')}: {e}")
                    continue

            return completed_expeditions

        except Exception as e:
            self.logger.error(f"Error completing user expeditions: {e}")
            return []

    async def get_expedition_history(self, discord_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's expedition history."""
        try:
            if not self.db.connection_pool:
                self.logger.error("Database connection pool not initialized")
                return []
                
            query = """
                SELECT ue.*, el.loot_data, el.outcome, el.completion_time, et.name, et.description,
                       et.duration_hours, et.difficulty_tier, et.expected_encounters
                FROM user_expeditions ue
                LEFT JOIN expedition_logs el ON ue.id = el.expedition_id
                LEFT JOIN expedition_templates et ON ue.expedition_template_id = et.id
                WHERE ue.discord_id = $1 
                AND ue.status = 'completed'
                ORDER BY ue.completion_time DESC
                LIMIT $2
            """
            
            async with self.db.connection_pool.acquire() as conn:
                history = await conn.fetch(query, discord_id, limit)
                
                result = []
                for record in history:
                    expedition_data = dict(record)
                    
                    # Parse loot data if it exists
                    if expedition_data.get('loot_data'):
                        import json
                        try:
                            expedition_data['loot'] = json.loads(expedition_data['loot_data'])
                        except (json.JSONDecodeError, TypeError):
                            expedition_data['loot'] = {}
                    else:
                        expedition_data['loot'] = {}
                    
                    result.append(expedition_data)
                
                return result
                
        except Exception as e:
            self.logger.error(f"Error getting expedition history: {e}")
            return []