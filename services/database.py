
from config.constants import MAX_EQUIPMENT_PER_USER

import asyncpg
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING
from datetime import datetime, timezone

if TYPE_CHECKING:
    from config.config import Config


class DatabaseService:
    async def is_equipment_in_use(self, equipment_id: int) -> bool:
        """Check if the equipment is currently used in any in-progress expedition."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 1 FROM user_expeditions
                WHERE equipped_equipment_id = $1 AND status = 'in_progress'
                LIMIT 1
                """,
                equipment_id
            )
            return row is not None
    async def remove_last_equipment_sub_slot(self, equipment_id: int) -> bool:
        """Remove the last unlocked subslot from an equipment and decrement unlocked_sub_slots atomically."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            async with conn.transaction():
                # Find the highest unlocked subslot for this equipment
                row = await conn.fetchrow(
                    """
                    SELECT id, slot_index FROM equipment_sub_slots
                    WHERE equipment_id = $1 AND is_unlocked = TRUE
                    ORDER BY slot_index DESC LIMIT 1
                    """,
                    equipment_id
                )
                if not row:
                    return False  # No unlocked subslot to remove
                sub_slot_id = row["id"]
                # Delete the subslot
                await conn.execute("DELETE FROM equipment_sub_slots WHERE id = $1", sub_slot_id)
                # Decrement unlocked_sub_slots
                await conn.execute(
                    "UPDATE equipment SET unlocked_sub_slots = GREATEST(unlocked_sub_slots - 1, 0), updated_at = CURRENT_TIMESTAMP WHERE id = $1",
                    equipment_id
                )
                return True
    async def delete_all_equipment_sub_slots(self, equipment_id: int) -> int:
        """Delete all sub slots for a given equipment."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute("DELETE FROM equipment_sub_slots WHERE equipment_id = $1", equipment_id)
            # Returns number of deleted rows as integer
            try:
                return int(result.split()[-1])
            except Exception:
                return 0

    async def unlock_subslot_by_consuming_equipment(self, target_equipment_id: int, consumed_equipment_id: int, effect_json: str) -> tuple[bool, int]:
        """Unlock a new subslot on target equipment by consuming another equipment and add the new subslot with the given effect (atomic). Returns (success, next_slot_index)."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            async with conn.transaction():
                # Get current unlocked_sub_slots
                row = await conn.fetchrow("SELECT unlocked_sub_slots FROM equipment WHERE id = $1 FOR UPDATE", target_equipment_id)
                if not row:
                    return False, 0
                unlocked = row["unlocked_sub_slots"]
                if unlocked >= 5:
                    return False, unlocked
                next_slot_index = unlocked + 1
                # Increment unlocked_sub_slots
                await conn.execute("UPDATE equipment SET unlocked_sub_slots = unlocked_sub_slots + 1, updated_at = CURRENT_TIMESTAMP WHERE id = $1", target_equipment_id)
                # Delete the consumed equipment
                await conn.execute("DELETE FROM equipment WHERE id = $1", consumed_equipment_id)
                # Add the new subslot with the provided effect
                await conn.execute(
                    """
                    INSERT INTO equipment_sub_slots (equipment_id, slot_index, effect, is_unlocked)
                    VALUES ($1, $2, $3, $4)
                    """,
                    target_equipment_id, next_slot_index, effect_json, True
                )
                return True, next_slot_index
    # === EQUIPMENT SYSTEM METHODS ===
    async def add_equipment(self, discord_id: str, main_effect: str, unlocked_sub_slots: int = 0) -> int:
        """Add a new equipment for a user, enforcing the global cap."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        # Enforce equipment cap per user
        user_equipment = await self.get_user_equipment(discord_id)
        if len(user_equipment) >= MAX_EQUIPMENT_PER_USER:
            return -1  # Cap reached
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO equipment (discord_id, main_effect, unlocked_sub_slots)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                discord_id, main_effect, unlocked_sub_slots
            )
            return row["id"] if row else 0

    async def get_equipment_by_id(self, equipment_id: int) -> Optional[Dict[str, Any]]:
        """Get equipment by its id, including sub slots."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM equipment WHERE id = $1", equipment_id)
            if not row:
                return None
            equipment_dict = dict(row)
            # Fetch sub slots
            sub_slots = await conn.fetch("SELECT * FROM equipment_sub_slots WHERE equipment_id = $1 ORDER BY slot_index ASC", equipment_id)
            equipment_dict["sub_slots"] = [dict(sub) for sub in sub_slots]
            return equipment_dict

    async def get_all_user_equipment(self, discord_id: str) -> List[Dict[str, Any]]:
        """Get all equipment for a user, including sub slots for each equipment."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM equipment WHERE discord_id = $1 ORDER BY created_at DESC", discord_id)

            equipment_list = []
            for row in rows:
                equipment_dict = dict(row)
                sub_slots = await conn.fetch("SELECT * FROM equipment_sub_slots WHERE equipment_id = $1 ORDER BY slot_index ASC", row["id"])
                equipment_dict["sub_slots"] = [dict(sub) for sub in sub_slots]
                equipment_list.append(equipment_dict)
            return equipment_list

    async def get_user_equipment(self, discord_id: str) -> List[Dict[str, Any]]:
        """Get all equipment for a user, excluding those used in in_progress expeditions, including sub slots for each equipment."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            # Look up user_id from users table
            user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
            if not user_row:
                return []
            user_id = user_row["id"]

            # Find equipment IDs currently used in in_progress expeditions for this user_id
            in_use_ids = set()
            rows_in_use = await conn.fetch(
                """
                SELECT equipped_equipment_id FROM user_expeditions
                WHERE user_id = $1 AND status = 'in_progress' AND equipped_equipment_id IS NOT NULL
                """,
                user_id
            )
            for row in rows_in_use:
                in_use_ids.add(row["equipped_equipment_id"])

            # Fetch all equipment for user, excluding those in use
            if in_use_ids:
                rows = await conn.fetch(
                    f"SELECT * FROM equipment WHERE discord_id = $1 AND id NOT IN ({', '.join(['$'+str(i+2) for i in range(len(in_use_ids))])}) ORDER BY created_at DESC",
                    discord_id, *in_use_ids
                )
            else:
                rows = await conn.fetch("SELECT * FROM equipment WHERE discord_id = $1 ORDER BY created_at DESC", discord_id)

            equipment_list = []
            for row in rows:
                equipment_dict = dict(row)
                sub_slots = await conn.fetch("SELECT * FROM equipment_sub_slots WHERE equipment_id = $1 ORDER BY slot_index ASC", row["id"])
                equipment_dict["sub_slots"] = [dict(sub) for sub in sub_slots]
                equipment_list.append(equipment_dict)
            return equipment_list

    async def update_equipment(self, equipment_id: int, main_effect: Optional[str] = None, unlocked_sub_slots: Optional[int] = None) -> bool:
        """Update equipment fields."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        set_clauses = []
        values = []
        if main_effect is not None:
            set_clauses.append("main_effect = $%d" % (len(values)+1))
            values.append(main_effect)
        if unlocked_sub_slots is not None:
            set_clauses.append("unlocked_sub_slots = $%d" % (len(values)+1))
            values.append(unlocked_sub_slots)
        if not set_clauses:
            return False
        values.append(equipment_id)
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(
                f"""
                UPDATE equipment SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ${len(values)}
                """,
                *values
            )
            return result.startswith("UPDATE")

    async def delete_equipment(self, equipment_id: int) -> bool:
        """Delete equipment by id."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute("DELETE FROM equipment WHERE id = $1", equipment_id)
            return result.endswith('1')

    async def add_equipment_sub_slot(self, equipment_id: int, slot_index: int, effect: Optional[str] = None, is_unlocked: bool = False) -> int:
        """Add a sub slot to equipment."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO equipment_sub_slots (equipment_id, slot_index, effect, is_unlocked)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                equipment_id, slot_index, effect, is_unlocked
            )
            return row["id"] if row else 0

    async def get_equipment_sub_slots(self, equipment_id: int) -> List[Dict[str, Any]]:
        """Get all sub slots for a given equipment."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM equipment_sub_slots WHERE equipment_id = $1 ORDER BY slot_index ASC", equipment_id)
            return [dict(row) for row in rows]

    async def update_equipment_sub_slot(self, sub_slot_id: int, effect: Optional[str] = None, is_unlocked: Optional[bool] = None) -> bool:
        """Update a sub slot's effect or unlock status."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        set_clauses = []
        values = []
        if effect is not None:
            set_clauses.append("effect = $%d" % (len(values)+1))
            values.append(effect)
        if is_unlocked is not None:
            set_clauses.append("is_unlocked = $%d" % (len(values)+1))
            values.append(is_unlocked)
        if not set_clauses:
            return False
        values.append(sub_slot_id)
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(
                f"""
                UPDATE equipment_sub_slots SET {', '.join(set_clauses)} WHERE id = ${len(values)}
                """,
                *values
            )
            return result.startswith("UPDATE")

    async def delete_equipment_sub_slot(self, sub_slot_id: int) -> bool:
        """Delete a sub slot by id."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute("DELETE FROM equipment_sub_slots WHERE id = $1", sub_slot_id)
            return result.endswith('1')

    async def equip_equipment_for_expedition(self, expedition_id: int, equipment_id: Optional[int]) -> bool:
        """Set the equipped equipment for a user expedition (can be None to unequip)."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE user_expeditions SET equipped_equipment_id = $1 WHERE id = $2",
                equipment_id, expedition_id
            )
            return result.startswith("UPDATE")

    async def get_series_genres(self, series_id: int) -> list:
        """Fetch and parse genres for a given series_id from the series table. Genres are pipe-separated (e.g., 'Comedy|Romance')."""
        if not self.connection_pool:
            return []
        try:
            async with self.connection_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT genres FROM series WHERE series_id = $1", series_id)
                if not row or not row["genres"]:
                    return []
                genres_raw = row["genres"]
                # Always split by '|', strip whitespace, ignore empty
                return [g.strip() for g in genres_raw.split('|') if g.strip()]
        except Exception:
            return []
    async def update_waifu(self, waifu_id: int, waifu_data: Dict[str, Any]) -> bool:
        """Update an existing waifu in the database by waifu_id (PostgreSQL) for new schema."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            # Build update statement dynamically
            fields = []
            values = []
            for key in [
                "name", "series_id", "series", "genre", "rarity", "image_url", "about", "stats", "elemental_type", "archetype", "potency", "elemental_resistances", "birthday", "favorite_gifts", "special_dialogue"
            ]:
                if key in waifu_data:
                    fields.append(f"{key} = ${len(values)+1}")
                    if key in ["stats", "potency", "elemental_resistances"]:
                        values.append(json.dumps(waifu_data.get(key, {})))
                    elif key in ["favorite_gifts", "special_dialogue", "elemental_type"]:
                        values.append(json.dumps(waifu_data.get(key, [])))
                    else:
                        values.append(waifu_data[key])
            if not fields:
                return False
            values.append(waifu_id)
            query = f"""
                UPDATE waifus SET {', '.join(fields)} WHERE waifu_id = ${len(values)}
            """
            result = await conn.execute(query, *values)
            return result.startswith("UPDATE")
    async def get_all_active_daily_missions(self) -> list:
        """Fetch all active daily missions."""
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM daily_missions WHERE is_active = TRUE")
            return [dict(row) for row in rows]

    async def get_all_user_mission_progress_for_date(self, discord_id: str, date) -> list:
        """Fetch all user mission progress for a given date. Date should be a datetime.date object."""
        async with self.connection_pool.acquire() as conn:
            user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
            if not user_row:
                return []
            user_id = user_row["id"]
            rows = await conn.fetch(
                "SELECT * FROM user_mission_progress WHERE user_id = $1 AND date = $2",
                user_id, date
            )
            return [dict(row) for row in rows]
    # --- Daily Mission Helpers ---
    async def get_or_create_mission(self, mission: dict) -> dict:
        """Fetch a mission by type and name, or create it if not present. Mission is a dict with all fields."""
        async with self.connection_pool.acquire() as conn:
            # Try to find by type and name (unique enough for daily missions)
            mission_row = await conn.fetchrow(
                "SELECT * FROM daily_missions WHERE type = $1 AND name = $2 AND is_active = TRUE LIMIT 1",
                mission["type"], mission["name"]
            )
            if mission_row:
                return dict(mission_row)
            # Create the mission if not present
            row = await conn.fetchrow(
                """
                INSERT INTO daily_missions (name, description, type, target_count, reward_type, reward_amount, difficulty, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
                """,
                mission["name"],
                mission["description"],
                mission["type"],
                mission["target_count"],
                mission["reward_type"],
                mission["reward_amount"],
                mission.get("difficulty", "easy"),
                mission.get("is_active", True)
            )
            return dict(row)

    async def get_user_mission_progress(self, discord_id: str, mission_id: int, date) -> Optional[dict]:
        """Fetch the user's mission progress for a given mission and date. Date should be a datetime.date object."""
        async with self.connection_pool.acquire() as conn:
            user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
            if not user_row:
                raise ValueError(f"User {discord_id} not found")
            user_id = user_row["id"]
            progress = await conn.fetchrow(
                "SELECT * FROM user_mission_progress WHERE user_id = $1 AND mission_id = $2 AND date = $3",
                user_id, mission_id, date
            )
            return dict(progress) if progress else None

    async def update_user_mission_progress(self, discord_id: str, mission_id: int, date) -> dict:
        """Increment progress for the user's mission, mark as completed if target met. Date should be a datetime.date object."""
        async with self.connection_pool.acquire() as conn:
            user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
            if not user_row:
                raise ValueError(f"User {discord_id} not found")
            user_id = user_row["id"]
            mission = await conn.fetchrow("SELECT * FROM daily_missions WHERE id = $1", mission_id)
            if not mission:
                raise ValueError(f"Mission {mission_id} not found")
            target_count = mission["target_count"]
            # Upsert progress
            progress = await conn.fetchrow(
                "SELECT * FROM user_mission_progress WHERE user_id = $1 AND mission_id = $2 AND date = $3",
                user_id, mission_id, date
            )
            if not progress:
                # Insert new progress
                completed = True if target_count <= 1 else False
                row = await conn.fetchrow(
                    """
                    INSERT INTO user_mission_progress (user_id, mission_id, current_progress, completed, claimed, date)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING *
                    """,
                    user_id, mission_id, 1, completed, False, date
                )
                return dict(row)
            else:
                # Update progress
                new_progress = progress["current_progress"] + 1
                completed = new_progress >= target_count
                row = await conn.fetchrow(
                    """
                    UPDATE user_mission_progress
                    SET current_progress = $1, completed = $2
                    WHERE id = $3
                    RETURNING *
                    """,
                    new_progress, completed, progress["id"]
                )
                return dict(row)

    async def claim_user_mission_reward(self, discord_id: str, mission_id: int, date) -> bool:
        """Mark the mission as claimed and grant the reward if not already claimed. Date should be a datetime.date object."""
        async with self.connection_pool.acquire() as conn:
            user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
            if not user_row:
                raise ValueError(f"User {discord_id} not found")
            user_id = user_row["id"]
            progress = await conn.fetchrow(
                "SELECT * FROM user_mission_progress WHERE user_id = $1 AND mission_id = $2 AND date = $3",
                user_id, mission_id, date
            )
            if not progress or not progress["completed"] or progress["claimed"]:
                return False
            # Mark as claimed
            await conn.execute(
                "UPDATE user_mission_progress SET claimed = TRUE WHERE id = $1",
                progress["id"]
            )
            # Grant reward
            mission = await conn.fetchrow("SELECT * FROM daily_missions WHERE id = $1", mission_id)
            if mission and mission["reward_type"] == "gems":
                await conn.execute(
                    "UPDATE users SET sakura_crystals = sakura_crystals + $1 WHERE discord_id = $2",
                    mission["reward_amount"], discord_id
                )
            return True
    async def get_gift_code(self, code: str) -> Optional[dict]:
        """Fetch a gift code by code string."""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM gift_codes WHERE code = $1", code)
            return dict(row) if row else None

    async def has_redeemed_gift_code(self, user_id: str, code: str) -> bool:
        """Check if a user has already redeemed a gift code."""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT 1 FROM gift_code_redemptions WHERE user_id = $1 AND code = $2", user_id, code)
            return row is not None

    async def redeem_gift_code(self, user_id: str, code: str) -> str:
        """Attempt to redeem a gift code for a user. Returns a status string."""
        async with self.connection_pool.acquire() as conn:
            async with conn.transaction():
                gift = await conn.fetchrow("SELECT * FROM gift_codes WHERE code = $1 FOR UPDATE", code)
                if not gift or not gift['is_active']:
                    return "invalid"
                # Check usage limit
                if gift['usage_limit'] is not None:
                    count = await conn.fetchval("SELECT COUNT(*) FROM gift_code_redemptions WHERE code = $1", code)
                    if count >= gift['usage_limit']:
                        return "limit"
                # Check if user already redeemed
                already = await conn.fetchrow("SELECT 1 FROM gift_code_redemptions WHERE user_id = $1 AND code = $2", user_id, code)
                if already:
                    return "already"
                # Apply reward
                if gift['reward_type'] == 'quartz':
                    await conn.execute("UPDATE users SET quartzs = quartzs + $1 WHERE discord_id = $2", gift['reward_value'], user_id)
                elif gift['reward_type'] == 'gems':
                    await conn.execute("UPDATE users SET sakura_crystals = sakura_crystals + $1 WHERE discord_id = $2", gift['reward_value'], user_id)
                elif gift['reward_type'] == 'item':
                    # Use purchase_item logic, but free
                    item_id = gift['reward_value']
                    # Add item to inventory (quantity=1)
                    item = await conn.fetchrow("SELECT * FROM shop_items WHERE id = $1 AND is_active = TRUE", item_id)
                    if not item:
                        return "item_missing"
                    existing_item = await conn.fetchrow(
                        "SELECT id, quantity FROM user_inventory WHERE user_id = $1 AND item_name = $2 AND item_type = $3 AND is_active = TRUE",
                        user_id, item['name'], item['item_type'])
                    if existing_item:
                        await conn.execute("UPDATE user_inventory SET quantity = quantity + 1 WHERE id = $1", existing_item['id'])
                    else:
                        await conn.execute(
                            """
                            INSERT INTO user_inventory (user_id, item_name, item_type, quantity, metadata, effects, is_active)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                            """,
                            user_id, item['name'], item['item_type'], 1,
                            item['item_data'] if item['item_data'] else '{}',
                            item['effects'] if item['effects'] else '{}', True
                        )
                elif gift['reward_type'] == 'daphine':
                    await conn.execute("UPDATE users SET daphine = daphine + $1 WHERE discord_id = $2", gift['reward_value'], user_id)
                else:
                    return "unknown_type"
                # Record redemption
                await conn.execute("INSERT INTO gift_code_redemptions (user_id, code, redeemed_at) VALUES ($1, $2, $3)", user_id, code, datetime.utcnow())
                return "success"
    def _parse_waifu_json_fields(self, waifu: dict) -> dict:
        import json
        json_fields = [
            'stats', 'elemental_type', 'potency', 'elemental_resistances', 'favorite_gifts', 'special_dialogue'
        ]
        for field in json_fields:
            if field in waifu and waifu[field] is not None and isinstance(waifu[field], str):
                try:
                    waifu[field] = json.loads(waifu[field])
                except Exception:
                    pass
        return waifu

    async def get_waifus_by_series_id(self, series_id: int) -> List[Dict[str, Any]]:
        """Get all waifus belonging to a given series_id, including series name as 'series'."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT w.*, s.name AS series
                FROM waifus w
                LEFT JOIN series s ON w.series_id = s.series_id
                WHERE w.series_id = $1
                ORDER BY w.rarity DESC, w.name ASC
                """,
                series_id
            )
            return [self._parse_waifu_json_fields(dict(row)) for row in rows]

    async def get_waifus_by_rarity_and_series(self, rarity: int, series_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get waifus by rarity and series (PostgreSQL), including series name as 'series'."""
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT w.*, s.name AS series
                FROM waifus w
                LEFT JOIN series s ON w.series_id = s.series_id
                WHERE w.rarity = $1 AND w.series_id = $2
                ORDER BY RANDOM() LIMIT $3
                """,
                rarity, series_id, limit
            )
            return [self._parse_waifu_json_fields(dict(row)) for row in rows]

    async def get_waifu_by_id_and_rarity(self, waifu_id: int, rarity: int) -> Optional[Dict[str, Any]]:
        """Get a waifu by waifu_id and rarity (PostgreSQL), including series name as 'series'."""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT w.*, s.name AS series
                FROM waifus w
                LEFT JOIN series s ON w.series_id = s.series_id
                WHERE w.waifu_id = $1 AND w.rarity = $2
                """,
                waifu_id, rarity
            )
            return self._parse_waifu_json_fields(dict(row)) if row else None
    async def get_series_by_id(self, series_id: int) -> Optional[Dict[str, Any]]:
        """Get a series by its primary key (series_id)."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM series WHERE series_id = $1", series_id)
            return dict(row) if row else None
    # Banner-related methods
    async def create_banner(self, banner_data: Dict[str, Any]) -> int:
        """Create a new banner and return its id."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO banners (name, type, start_time, end_time, description, is_active, series_ids)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                banner_data["name"],
                banner_data["type"],
                banner_data["start_time"],
                banner_data["end_time"],
                banner_data.get("description", ""),
                banner_data.get("is_active", True),
                banner_data.get("series_ids", "[]"),
            )
            return row["id"] if row else 0

    async def update_banner(self, banner_id: int, update_data: Dict[str, Any]) -> bool:
        """Update a banner by id. Returns True if updated."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        set_clauses = []
        values = []
        for idx, (key, value) in enumerate(update_data.items(), start=1):
            set_clauses.append(f"{key} = ${idx}")
            values.append(value)
        if not set_clauses:
            return False
        values.append(banner_id)
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(
                f"""
                UPDATE banners SET {', '.join(set_clauses)} WHERE id = ${len(values)}
                """,
                *values
            )
            return result.startswith("UPDATE")

    async def get_banner(self, banner_id: int) -> Optional[Dict[str, Any]]:
        """Get a banner by id."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM banners WHERE id = $1", banner_id)
            return dict(row) if row else None

    async def list_banners(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """List all banners, optionally only active ones."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            if active_only:
                rows = await conn.fetch("SELECT * FROM banners WHERE is_active = TRUE")
            else:
                rows = await conn.fetch("SELECT * FROM banners")
            return [dict(row) for row in rows]

    # Banner item methods
    async def add_banner_item(self, banner_id: int, item_id: int, rate_up: bool = False, drop_rate: float = None) -> int:
        """Add an item to a banner. Returns banner_item id."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO banner_items (banner_id, item_id, rate_up, drop_rate)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                banner_id, item_id, rate_up, drop_rate
            )
            return row["id"] if row else 0

    async def get_banner_items(self, banner_id: int) -> List[Dict[str, Any]]:
        """Get all items for a banner."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM banner_items WHERE banner_id = $1", banner_id)
            return [dict(row) for row in rows]

    async def get_banner_item(self, banner_item_id: int) -> Optional[Dict[str, Any]]:
        """Get a banner item by id."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM banner_items WHERE id = $1", banner_item_id)
            return dict(row) if row else None
    async def add_series(self, series_data: dict) -> int:
        """Add a new series to the database. Returns the series_id. series_id must be provided by caller (not serial)."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO series (
                    series_id, name, english_name, image_link, studios, genres, synopsis, favorites, members, score
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (series_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    english_name = EXCLUDED.english_name,
                    image_link = EXCLUDED.image_link,
                    studios = EXCLUDED.studios,
                    genres = EXCLUDED.genres,
                    synopsis = EXCLUDED.synopsis,
                    favorites = EXCLUDED.favorites,
                    members = EXCLUDED.members,
                    score = EXCLUDED.score
                RETURNING series_id
                """,
                series_data['series_id'],
                series_data.get('name', ''),
                series_data.get('english_name', ''),
                series_data.get('image_link', ''),
                series_data.get('studios', ''),
                series_data.get('genres', ''),
                series_data.get('synopsis', ''),
                series_data.get('favorites', None),
                series_data.get('members', None),
                series_data.get('score', None)
            )
            if row and 'series_id' in row:
                return row['series_id']
            raise ValueError("Failed to insert or update series with provided series_id")

    async def get_series_by_name(self, name: str) -> dict:
        """Get a series by name (case-insensitive)."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM series WHERE LOWER(name) = LOWER($1)", name
            )
            return dict(row) if row else None
    async def add_waifus_to_user_batch(self, discord_id: str, waifu_ids: List[int]) -> List[Dict[str, Any]]:
        """Batch add multiple waifus to a user's collection, skipping already-owned waifus. Returns full waifu+user_waifu data for all added. Parses waifu JSON fields."""
        if not waifu_ids:
            return []
        async with self.connection_pool.acquire() as conn:
            user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
            if not user_row:
                raise ValueError(f"User {discord_id} not found")
            user_id = user_row["id"]
            # Find already-owned waifus
            owned_rows = await conn.fetch(
                "SELECT waifu_id FROM user_waifus WHERE user_id = $1 AND waifu_id = ANY($2::int[])",
                user_id, waifu_ids
            )
            owned_ids = {row["waifu_id"] for row in owned_rows}
            to_add = [wid for wid in waifu_ids if wid not in owned_ids]
            results = []
            if to_add:
                # Batch insert new waifus
                now = datetime.now()
                values = [(user_id, wid, now) for wid in to_add]
                await conn.executemany(
                    "INSERT INTO user_waifus (user_id, waifu_id, obtained_at) VALUES ($1, $2, $3)",
                    values
                )
            # Fetch all user_waifu+waifu data for the requested waifu_ids
            all_ids = list(set(waifu_ids))
            rows = await conn.fetch(
                """
                SELECT uw.*, w.name, w.series, w.rarity, w.image_url, w.waifu_id as waifu_id,
                       w.stats, w.elemental_type, w.potency, w.elemental_resistances, w.favorite_gifts, w.special_dialogue
                FROM user_waifus uw
                JOIN waifus w ON uw.waifu_id = w.waifu_id
                WHERE uw.user_id = $1 AND uw.waifu_id = ANY($2::int[])
                """,
                user_id, all_ids
            )
            return [self._parse_waifu_json_fields(dict(row)) for row in rows]
    """Service for managing the Waifu Academy database with PostgreSQL only."""

    def __init__(self, config: "Config"):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.connection_pool = None
        self.pg_config = config.get_postgres_config()

    async def initialize(self):
        """Initialize database connection and create tables."""
        try:
            # Create connection pool for PostgreSQL
            self.connection_pool = await asyncpg.create_pool(
                host=self.pg_config["host"],
                port=self.pg_config["port"],
                user=self.pg_config["user"],
                password=self.pg_config["password"],
                database=self.pg_config["database"],
                min_size=5,
                max_size=20,
            )

            # Create tables
            async with self.connection_pool.acquire() as conn:
                async with conn.transaction():
                    await self._create_tables_postgres(conn)

            self.logger.info("PostgreSQL database initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize PostgreSQL database: {e}")
            raise

    async def close(self):
        """Close database connections."""
        if self.connection_pool:
            await self.connection_pool.close()
            self.logger.info("PostgreSQL database connections closed")


    async def _create_tables_postgres(self, conn):
        # Equipment system tables
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS equipment (
                id SERIAL PRIMARY KEY,
                discord_id VARCHAR(100) NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
                main_effect TEXT NOT NULL,
                unlocked_sub_slots INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_equipment_discord_id ON equipment(discord_id);
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS equipment_sub_slots (
                id SERIAL PRIMARY KEY,
                equipment_id INTEGER NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
                slot_index INTEGER NOT NULL CHECK (slot_index >= 1 AND slot_index <= 5),
                effect TEXT,
                is_unlocked BOOLEAN DEFAULT FALSE
            );
            CREATE INDEX IF NOT EXISTS idx_equipment_id ON equipment_sub_slots(equipment_id);
            """
        )

        """Create all required tables for PostgreSQL."""
        # Users table
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                discord_id VARCHAR(100) UNIQUE NOT NULL,
                academy_name VARCHAR(255),
                collector_rank INTEGER DEFAULT 1,
                sakura_crystals INTEGER DEFAULT 2000,
                quartzs INTEGER DEFAULT 0,
                pity_counter INTEGER DEFAULT 0,
                last_daily_reset BIGINT DEFAULT 0,
                daphine INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_discord_id ON users(discord_id);
            """
        )

        # Series table (series_id is NOT SERIAL, must be provided by caller)
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS series (
                series_id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                english_name VARCHAR(255),
                image_link TEXT,
                studios TEXT,
                genres TEXT,
                synopsis TEXT,
                favorites INTEGER,
                members INTEGER,
                score FLOAT
            );
            CREATE INDEX IF NOT EXISTS idx_series_name ON series(name);
            """
        )

        # Waifus table (waifu_id is now the primary key, series_id is a foreign key, series is denormalized string)
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS waifus (
                waifu_id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                series_id INTEGER REFERENCES series(series_id) ON DELETE SET NULL,
                series VARCHAR(255) NOT NULL,
                genre VARCHAR(100) NOT NULL,
                rarity INTEGER NOT NULL CHECK (rarity >= 1 AND rarity <= 3),
                image_url TEXT,
                about TEXT,
                stats TEXT,
                elemental_type TEXT,
                archetype TEXT,
                potency TEXT,
                elemental_resistances TEXT,
                birthday DATE,
                favorite_gifts TEXT,
                special_dialogue TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_rarity ON waifus(rarity);
            CREATE INDEX IF NOT EXISTS idx_name ON waifus(name);
            CREATE INDEX IF NOT EXISTS idx_series_id ON waifus(series_id);
            CREATE INDEX IF NOT EXISTS idx_series ON waifus(series);
            """
        )

        # User waifus table (collection) - Updated for new star system, references waifu_id
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_waifus (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                waifu_id INTEGER NOT NULL REFERENCES waifus(waifu_id) ON DELETE CASCADE,
                bond_level INTEGER DEFAULT 1,
                constellation_level INTEGER DEFAULT 0,
                current_star_level INTEGER DEFAULT NULL,
                star_shards INTEGER DEFAULT 0,
                character_shards INTEGER DEFAULT 0,
                is_awakened BOOLEAN DEFAULT FALSE,
                current_mood VARCHAR(50) DEFAULT 'neutral',
                last_interaction TIMESTAMP NULL,
                total_conversations INTEGER DEFAULT 0,
                favorite_memory TEXT,
                custom_nickname VARCHAR(100),
                room_decorations TEXT,
                obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_user_id ON user_waifus(user_id);
            CREATE INDEX IF NOT EXISTS idx_waifu_id ON user_waifus(waifu_id);
            """
        )
        # PostgreSQL table creation (no MySQL remnants)
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                waifu_id INTEGER NOT NULL REFERENCES waifus(waifu_id) ON DELETE CASCADE,
                user_message TEXT NOT NULL,
                waifu_response TEXT NOT NULL,
                mood_change INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_user_waifu_id ON conversations(user_id, waifu_id);
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_missions (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                type VARCHAR(50) NOT NULL,
                target_count INTEGER NOT NULL,
                reward_type VARCHAR(50) NOT NULL,
                reward_amount INTEGER NOT NULL,
                difficulty VARCHAR(20) DEFAULT 'easy',
                is_active BOOLEAN DEFAULT TRUE
            );
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_mission_progress (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                mission_id INTEGER NOT NULL REFERENCES daily_missions(id) ON DELETE CASCADE,
                current_progress INTEGER DEFAULT 0,
                completed BOOLEAN DEFAULT FALSE,
                claimed BOOLEAN DEFAULT FALSE,
                date DATE,
                UNIQUE (user_id, mission_id, date)
            );
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                bonus_conditions TEXT,
                is_active BOOLEAN DEFAULT TRUE
            );
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shop_items (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price INTEGER NOT NULL,
                category VARCHAR(50) NOT NULL,
                item_type VARCHAR(50) NOT NULL,
                item_data TEXT,
                effects TEXT,
                stock_limit INTEGER DEFAULT -1,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_category ON shop_items(category);
            CREATE INDEX IF NOT EXISTS idx_active ON shop_items(is_active);
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_purchases (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                shop_item_id INTEGER NOT NULL REFERENCES shop_items(id) ON DELETE CASCADE,
                quantity INTEGER DEFAULT 1,
                total_cost INTEGER NOT NULL,
                currency_type VARCHAR(50) DEFAULT 'quartzs',
                transaction_status VARCHAR(50) DEFAULT 'completed',
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_user_id ON user_purchases(user_id);
            CREATE INDEX IF NOT EXISTS idx_purchased_at ON user_purchases(purchased_at);
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_inventory (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                item_name VARCHAR(255) NOT NULL,
                item_type VARCHAR(50) NOT NULL,
                quantity INTEGER DEFAULT 1,
                metadata TEXT,
                effects TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                expires_at TIMESTAMP NULL,
                acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_user_id ON user_inventory(user_id);
            CREATE INDEX IF NOT EXISTS idx_item_type ON user_inventory(item_type);
            CREATE INDEX IF NOT EXISTS idx_active ON user_inventory(is_active);
            """
        )

        # Banner system tables
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS banners (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                type VARCHAR(50) NOT NULL, -- 'rate-up' or 'limited'
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                series_ids TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_banner_active ON banners(is_active);
            CREATE INDEX IF NOT EXISTS idx_banner_type ON banners(type);
            CREATE INDEX IF NOT EXISTS idx_banner_time ON banners(start_time, end_time);
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS banner_items (
                id SERIAL PRIMARY KEY,
                banner_id INTEGER NOT NULL REFERENCES banners(id) ON DELETE CASCADE,
                item_id INTEGER NOT NULL REFERENCES waifus(waifu_id) ON DELETE CASCADE,
                rate_up BOOLEAN DEFAULT FALSE,
                drop_rate FLOAT DEFAULT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_banner_id ON banner_items(banner_id);
            CREATE INDEX IF NOT EXISTS idx_item_id ON banner_items(item_id);
            """
        )

        # Gift code system tables (add foreign keys)
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS gift_codes (
                code TEXT PRIMARY KEY,
                reward_type TEXT,
                reward_value INT,
                is_active BOOLEAN,
                usage_limit INT,
                created_at TIMESTAMP
            );
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS gift_code_redemptions (
                user_id VARCHAR(100) NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
                code TEXT NOT NULL REFERENCES gift_codes(code) ON DELETE CASCADE,
                redeemed_at TIMESTAMP,
                PRIMARY KEY (user_id, code)
            );
            """
        )

        # Expedition system tables for Wanderer Game integration
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_expeditions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expedition_name VARCHAR(255) NOT NULL,
                location VARCHAR(255) NOT NULL,
                difficulty VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'in_progress',
                duration_hours FLOAT NOT NULL,
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP NULL,
                rewards_claimed BOOLEAN DEFAULT FALSE,
                expedition_data TEXT NOT NULL DEFAULT '{}',
                final_results TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                equipped_equipment_id INTEGER REFERENCES equipment(id)
            );
            CREATE INDEX IF NOT EXISTS idx_user_expeditions_user_id ON user_expeditions(user_id);
            CREATE INDEX IF NOT EXISTS idx_user_expeditions_status ON user_expeditions(status);
            CREATE INDEX IF NOT EXISTS idx_user_expeditions_started_at ON user_expeditions(started_at);
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expedition_participants (
                id SERIAL PRIMARY KEY,
                expedition_id INTEGER NOT NULL REFERENCES user_expeditions(id) ON DELETE CASCADE,
                user_waifu_id INTEGER NOT NULL REFERENCES user_waifus(id) ON DELETE CASCADE,
                position_in_party INTEGER NOT NULL,
                star_level_used INTEGER NOT NULL,
                final_hp INTEGER DEFAULT NULL,
                final_mp INTEGER DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(expedition_id, position_in_party)
            );
            CREATE INDEX IF NOT EXISTS idx_expedition_participants_expedition_id ON expedition_participants(expedition_id);
            CREATE INDEX IF NOT EXISTS idx_expedition_participants_user_waifu_id ON expedition_participants(user_waifu_id);
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expedition_logs (
                id SERIAL PRIMARY KEY,
                expedition_id INTEGER NOT NULL REFERENCES user_expeditions(id) ON DELETE CASCADE,
                log_type VARCHAR(50) NOT NULL,
                encounter_number INTEGER NULL,
                message TEXT NOT NULL,
                data TEXT DEFAULT '{}',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_expedition_logs_expedition_id ON expedition_logs(expedition_id);
            CREATE INDEX IF NOT EXISTS idx_expedition_logs_type ON expedition_logs(log_type);
            """
        )

    # User-related methods
    async def get_or_create_user(self, discord_id: str) -> Dict[str, Any]:
        """Get user from database or create if doesn't exist (PostgreSQL)."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE discord_id = $1", discord_id
            )
            if user:
                return dict(user)
            # Create new user
            old_date = datetime(2022, 1, 1, tzinfo=timezone.utc)
            old_timestamp = int(old_date.timestamp())
            await conn.execute(
                """INSERT INTO users (discord_id, academy_name, last_daily_reset) 
                       VALUES ($1, $2, $3)""",
                discord_id, f"Academy {discord_id[:6]}", old_timestamp
            )
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE discord_id = $1", discord_id
            )
            return dict(user) if user else {}

    async def get_user_fresh(self, discord_id: str) -> Dict[str, Any]:
        """Get user with fresh connection (PostgreSQL)."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
    # ...removed debug logging...
        async with self.connection_pool.acquire() as conn:
            balance_only = await conn.fetchrow(
                "SELECT quartzs FROM users WHERE discord_id = $1", discord_id
            )
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE discord_id = $1", discord_id
            )
            return dict(user) if user else {}

    # Waifu-related methods
    async def add_waifu(self, waifu_data: Dict[str, Any]) -> int:
        """Add a new waifu to the database (PostgreSQL), using new schema fields."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO waifus (
                    name, series_id, series, genre, rarity, image_url, about, waifu_id,
                    stats, elemental_type, archetype, potency, elemental_resistances,
                    birthday, favorite_gifts, special_dialogue
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                RETURNING waifu_id
                """,
                waifu_data["name"],
                waifu_data["series_id"],
                waifu_data["series"],
                waifu_data.get("genre", "Unknown"),
                waifu_data["rarity"],
                waifu_data.get("image_url"),
                waifu_data.get("about", None),
                waifu_data.get("waifu_id"),
                json.dumps(waifu_data.get("stats", {})),
                json.dumps(waifu_data.get("elemental_type", [])),
                waifu_data.get("archetype", None),
                json.dumps(waifu_data.get("potency", {})),
                json.dumps(waifu_data.get("elemental_resistances", {})),
                waifu_data.get("birthday"),
                json.dumps(waifu_data.get("favorite_gifts", [])),
                json.dumps(waifu_data.get("special_dialogue", {})),
            )
            return row["waifu_id"] if row else 0

    async def get_waifu_by_waifu_id(self, waifu_id: int) -> Optional[Dict[str, Any]]:
        """Get a waifu by waifu_id, including series name as 'series' and about field."""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT w.*, s.name AS series
                FROM waifus w
                LEFT JOIN series s ON w.series_id = s.series_id
                WHERE w.waifu_id = $1
                """,
                waifu_id
            )
            if row:
                return self._parse_waifu_json_fields(dict(row))
            return None

    async def test_connection(self) -> bool:
        """Test database connection (PostgreSQL)."""
        try:
            async with self.connection_pool.acquire() as conn:
                await conn.execute("SELECT 1")
                return True
        except Exception:
            return False

    async def get_waifus_by_rarity(self, rarity: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get waifus by rarity level (PostgreSQL), including series name as 'series'."""
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT w.*, s.name AS series
                FROM waifus w
                LEFT JOIN series s ON w.series_id = s.series_id
                WHERE w.rarity = $1
                ORDER BY RANDOM() LIMIT $2
                """,
                rarity, limit
            )
            return [self._parse_waifu_json_fields(dict(row)) for row in rows]

    async def get_user_collection(self, discord_id: str) -> List[Dict[str, Any]]:
        """Get all waifus in a user's collection (PostgreSQL), using waifu_id as identifier. Includes series_id. Parses waifu JSON fields."""
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT uw.*, w.name, w.series, w.series_id, w.rarity, w.image_url, w.waifu_id as waifu_id, u.discord_id,
                       w.stats, w.elemental_type, w.potency, w.elemental_resistances, w.favorite_gifts, w.special_dialogue, w.archetype
                FROM user_waifus uw
                JOIN waifus w ON uw.waifu_id = w.waifu_id
                JOIN users u ON uw.user_id = u.id
                WHERE u.discord_id = $1
                ORDER BY uw.obtained_at DESC
                """,
                discord_id
            )
            return [self._parse_waifu_json_fields(dict(row)) for row in rows]

    async def add_waifu_to_user(self, discord_id: str, waifu_id: int) -> Dict[str, Any]:
        """Add a waifu to a user's collection, handling constellation system (PostgreSQL), using waifu_id as identifier. Parses waifu JSON fields."""
        async with self.connection_pool.acquire() as conn:
            user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
            if not user_row:
                raise ValueError(f"User {discord_id} not found")
            user_id = user_row["id"]
            existing = await conn.fetchrow(
                "SELECT * FROM user_waifus WHERE user_id = $1 AND waifu_id = $2",
                user_id, waifu_id
            )
            if existing:
                row = await conn.fetchrow(
                    """
                    SELECT uw.*, w.name, w.series, w.rarity, w.image_url, w.waifu_id as waifu_id,
                           w.stats, w.elemental_type, w.potency, w.elemental_resistances, w.favorite_gifts, w.special_dialogue
                    FROM user_waifus uw
                    JOIN waifus w ON uw.waifu_id = w.waifu_id
                    WHERE uw.id = $1
                    """,
                    existing["id"]
                )
                return self._parse_waifu_json_fields(dict(row)) if row else {}
            else:
                new_id_row = await conn.fetchrow(
                    """
                    INSERT INTO user_waifus (user_id, waifu_id, obtained_at)
                    VALUES ($1, $2, $3)
                    RETURNING id
                    """,
                    user_id, waifu_id, datetime.now()
                )
                new_id = new_id_row["id"] if new_id_row else None
                row = await conn.fetchrow(
                    """
                    SELECT uw.*, w.name, w.series, w.rarity, w.image_url, w.waifu_id as waifu_id,
                           w.stats, w.elemental_type, w.potency, w.elemental_resistances, w.favorite_gifts, w.special_dialogue
                    FROM user_waifus uw
                    JOIN waifus w ON uw.waifu_id = w.waifu_id
                    WHERE uw.id = $1
                    """,
                    new_id
                )
                return self._parse_waifu_json_fields(dict(row)) if row else {}

    # Currency methods
    async def update_user_crystals(self, discord_id: str, amount: int) -> bool:
        """Update user's sakura crystals (PostgreSQL)."""
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE users SET sakura_crystals = sakura_crystals + $1 WHERE discord_id = $2",
                amount, discord_id
            )
            return result[-1] != '0'

    async def update_user_quartzs(self, discord_id: str, amount: int) -> bool:
        """Update user's quartzs (PostgreSQL)."""
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE users SET quartzs = quartzs + $1 WHERE discord_id = $2",
                amount, discord_id
            )
            return result[-1] != '0'

    async def update_user_rank(self, discord_id: str, new_rank: int) -> bool:
        """Update user's collector rank (PostgreSQL)."""
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE users SET collector_rank = $1 WHERE discord_id = $2",
                new_rank, discord_id
            )
            return result[-1] != '0'

    # Search methods
    async def search_waifus(self, waifu_name: Optional[str] = None, limit: Optional[int] = None, series_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for waifus by name and/or series name (PostgreSQL).
        At least one of waifu_name or series_name must be provided.
        Results are sorted by relevance if waifu_name is provided. Parses waifu JSON fields.
        """
        if not waifu_name and not series_name:
            raise ValueError("At least one of waifu_name or series_name must be provided.")
        async with self.connection_pool.acquire() as conn:
            if waifu_name and series_name:
                query = (
                    "SELECT *, "
                    "LEAST(POSITION(LOWER($1) IN LOWER(name)), POSITION(LOWER($1) IN LOWER(series))) AS relevance "
                    "FROM waifus "
                    "WHERE name ILIKE $2 AND series ILIKE $3 "
                    "ORDER BY relevance, name"
                )
                params = (waifu_name, f"%{waifu_name}%", f"%{series_name}%")
                if limit:
                    query += " LIMIT $4"
                    params = params + (limit,)
            elif waifu_name:
                query = (
                    "SELECT *, "
                    "LEAST(POSITION(LOWER($1) IN LOWER(name)), POSITION(LOWER($1) IN LOWER(series))) AS relevance "
                    "FROM waifus "
                    "WHERE name ILIKE $2 OR series ILIKE $2 "
                    "ORDER BY relevance, name"
                )
                params = (waifu_name, f"%{waifu_name}%")
                if limit:
                    query += " LIMIT $3"
                    params = params + (limit,)
            else:  # Only series_name
                query = (
                    "SELECT *, 0 AS relevance "
                    "FROM waifus "
                    "WHERE series ILIKE $1 "
                    "ORDER BY name"
                )
                params = (f"%{series_name}%",)
                if limit:
                    query += " LIMIT $2"
                    params = params + (limit,)
            rows = await conn.fetch(query, *params)
            return [self._parse_waifu_json_fields(dict(row)) for row in rows]

    # Pity system
    async def update_pity_counter(self, discord_id: str, reset: bool = False) -> bool:
        """Update user's pity counter (PostgreSQL)."""
        async with self.connection_pool.acquire() as conn:
            if reset:
                result = await conn.execute(
                    "UPDATE users SET pity_counter = 0 WHERE discord_id = $1",
                    discord_id
                )
            else:
                result = await conn.execute(
                    "UPDATE users SET pity_counter = pity_counter + 1 WHERE discord_id = $1",
                    discord_id
                )
            return result[-1] != '0'

    # Daily system
    async def update_daily_reset(self, discord_id: str, timestamp: int, login_streak: int = 0) -> bool:
        """Update user's daily reset timestamp (PostgreSQL)."""
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE users SET last_daily_reset = $1 WHERE discord_id = $2",
                timestamp, discord_id
            )
            return result[-1] != '0'

    # Account management
    async def reset_user_account(self, discord_id: str) -> bool:
        """Reset a user's account to default state (PostgreSQL), including inventory and purchases."""
        async with self.connection_pool.acquire() as conn:
            try:
                # Reset user stats
                await conn.execute(
                    """UPDATE users SET 
                       sakura_crystals = 2000, 
                       quartzs = 0,
                       pity_counter = 0, 
                       last_daily_reset = 0,
                       collector_rank = 1
                       WHERE discord_id = $1""",
                    discord_id
                )
                user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
                if user_row:
                    user_id = user_row[0]
                    await conn.execute("DELETE FROM user_waifus WHERE user_id = $1", user_id)
                    await conn.execute("DELETE FROM conversations WHERE user_id = $1", user_id)
                    await conn.execute("DELETE FROM user_mission_progress WHERE user_id = $1", user_id)
                    await conn.execute("DELETE FROM user_inventory WHERE user_id = $1", discord_id)
                    await conn.execute("DELETE FROM user_purchases WHERE user_id = $1", discord_id)
                    await conn.execute("DELETE FROM gift_code_redemptions WHERE user_id = $1", discord_id)
                return True
            except Exception as e:
                self.logger.error(f"Error resetting user account {discord_id}: {e}")
                return False

    async def delete_user_account(self, discord_id: str) -> bool:
        """Permanently delete a user's account (PostgreSQL), including inventory and purchases."""
        async with self.connection_pool.acquire() as conn:
            try:
                user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
                if user_row:
                    user_id = user_row[0]
                    await conn.execute("DELETE FROM user_inventory WHERE user_id = $1", discord_id)
                    await conn.execute("DELETE FROM user_purchases WHERE user_id = $1", discord_id)
                    await conn.execute("DELETE FROM gift_code_redemptions WHERE user_id = $1", discord_id)
                    await conn.execute("DELETE FROM users WHERE id = $1", user_id)
                return True
            except Exception as e:
                self.logger.error(f"Error deleting user account {discord_id}: {e}")
                return False

    # Shop methods - TODO: Implement shop functionality
    async def get_shop_items(self, category: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get shop items with optional filtering (PostgreSQL)."""
        try:
            async with self.connection_pool.acquire() as conn:
                query = "SELECT * FROM shop_items WHERE 1=1"
                params = []
                if active_only:
                    query += " AND is_active = $1"
                    params.append(True)
                if category:
                    query += f" AND category = ${len(params)+1}"
                    params.append(category)
                query += " ORDER BY category, name"
                rows = await conn.fetch(query, *params) if params else await conn.fetch(query)
                result = []
                for row in rows:
                    item_dict = dict(row)
                    if item_dict.get('item_data'):
                        try:
                            item_dict['item_data'] = json.loads(item_dict['item_data'])
                        except:
                            item_dict['item_data'] = {}
                    if item_dict.get('effects'):
                        try:
                            item_dict['effects'] = json.loads(item_dict['effects'])
                        except:
                            item_dict['effects'] = {}
                    result.append(item_dict)
                return result
        except Exception as e:
            self.logger.error(f"Error getting shop items: {e}")
            return []

    async def get_shop_item_by_id(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific shop item by ID (PostgreSQL)."""
        try:
            async with self.connection_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM shop_items WHERE id = $1", item_id)
                if row:
                    item_dict = dict(row)
                    if item_dict.get('item_data'):
                        try:
                            item_dict['item_data'] = json.loads(item_dict['item_data'])
                        except:
                            item_dict['item_data'] = {}
                    if item_dict.get('effects'):
                        try:
                            item_dict['effects'] = json.loads(item_dict['effects'])
                        except:
                            item_dict['effects'] = {}
                    return item_dict
                return None
        except Exception as e:
            self.logger.error(f"Error getting shop item {item_id}: {e}")
            return None

    async def add_shop_item(self, item_data: Dict[str, Any]) -> int:
        """Add a new item to the shop (PostgreSQL)."""
        try:
            async with self.connection_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO shop_items (name, description, price, category, item_type, item_data, effects, stock_limit, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id
                    """,
                    item_data['name'],
                    item_data.get('description', ''),
                    item_data['price'],
                    item_data['category'],
                    item_data['item_type'],
                    json.dumps(item_data.get('item_data', {})),
                    json.dumps(item_data.get('effects', {})),
                    item_data.get('stock_limit', -1),
                    item_data.get('is_active', True)
                )
                return row['id'] if row else 0
        except Exception as e:
            self.logger.error(f"Error adding shop item: {e}")
            return 0

    async def purchase_item(self, user_id: str, item_id: int, quantity: int = 1) -> bool:
        """Purchase an item from the shop (PostgreSQL)."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        try:
            self.logger.info(f"Starting purchase: user={user_id}, item_id={item_id}, qty={quantity}")
            async with self.connection_pool.acquire() as conn:
                async with conn.transaction():
                    # Get item details
                    item = await conn.fetchrow("SELECT * FROM shop_items WHERE id = $1 AND is_active = TRUE", item_id)
                    if not item:
                        self.logger.error(f"Item {item_id} not found")
                        return False
                    self.logger.info(f"Found item: {item['name']}")
                    total_cost = item['price'] * quantity
                    # Check user's quartzs
                    user_result = await conn.fetchrow("SELECT quartzs FROM users WHERE discord_id = $1", user_id)
                    if not user_result or user_result['quartzs'] < total_cost:
                        self.logger.error(f"Insufficient funds: has {user_result['quartzs'] if user_result else 0}, needs {total_cost}")
                        return False
                    current_balance = user_result['quartzs']
                    self.logger.info(f"User has sufficient funds: {current_balance} >= {total_cost}")
                    # Deduct quartzs
                    new_balance = current_balance - total_cost
                    self.logger.info(f"Updating balance: {current_balance} - {total_cost} = {new_balance}")
                    await conn.execute("UPDATE users SET quartzs = $1 WHERE discord_id = $2", new_balance, user_id)
                    # Record purchase
                    await conn.execute(
                        """
                        INSERT INTO user_purchases (user_id, shop_item_id, quantity, total_cost, currency_type)
                        VALUES ($1, $2, $3, $4, $5)
                        """,
                        user_id, item_id, quantity, total_cost, 'quartzs'
                    )
                    self.logger.info(f"Purchase recorded")
                    # Add to inventory - check if item already exists first
                    existing_item = await conn.fetchrow(
                        """
                        SELECT id, quantity FROM user_inventory 
                        WHERE user_id = $1 AND item_name = $2 AND item_type = $3 AND is_active = TRUE
                        """,
                        user_id, item['name'], item['item_type']
                    )
                    if existing_item:
                        new_quantity = existing_item['quantity'] + quantity
                        self.logger.info(f"Updating existing item quantity: {existing_item['quantity']} + {quantity} = {new_quantity}")
                        await conn.execute(
                            "UPDATE user_inventory SET quantity = $1 WHERE id = $2",
                            new_quantity, existing_item['id']
                        )
                    else:
                        self.logger.info(f"Creating new inventory entry for {item['name']}")
                        await conn.execute(
                            """
                            INSERT INTO user_inventory (user_id, item_name, item_type, quantity, metadata, effects, is_active)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                            """,
                            user_id, item['name'], item['item_type'], quantity,
                            item['item_data'] if item['item_data'] else '{}',
                            item['effects'] if item['effects'] else '{}', True
                        )
                    self.logger.info(f"Purchase transaction committed successfully")
                    return True
        except Exception as e:
            self.logger.error(f"Error purchasing item: {e}")
            return False

    async def get_user_inventory(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's inventory (PostgreSQL)."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        try:
            async with self.connection_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM user_inventory 
                    WHERE user_id = $1 AND is_active = TRUE
                    ORDER BY acquired_at DESC
                    """, user_id
                )
                self.logger.info(f"Raw inventory query returned {len(rows)} items for user {user_id}")
                result = []
                for row in rows:
                    try:
                        item_dict = dict(row)
                        if item_dict.get('metadata'):
                            try:
                                item_dict['metadata'] = json.loads(item_dict['metadata'])
                            except Exception as e:
                                self.logger.warning(f"Failed to parse metadata JSON: {e}")
                                item_dict['metadata'] = {}
                        if item_dict.get('effects'):
                            try:
                                item_dict['effects'] = json.loads(item_dict['effects'])
                            except Exception as e:
                                self.logger.warning(f"Failed to parse effects JSON: {e}")
                                item_dict['effects'] = {}
                        result.append(item_dict)
                    except Exception as e:
                        self.logger.error(f"Error processing inventory item: {e}")
                        continue
                self.logger.info(f"Processed inventory returned {len(result)} items")
                return result
        except Exception as e:
            self.logger.error(f"Error getting user inventory: {e}")
            return []

    async def get_user_purchase_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's purchase history (PostgreSQL)."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        try:
            async with self.connection_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT p.*, s.name, s.description 
                    FROM user_purchases p
                    JOIN shop_items s ON p.shop_item_id = s.id
                    WHERE p.user_id = $1 
                    ORDER BY p.purchased_at DESC 
                    LIMIT $2
                    """, user_id, limit
                )
                return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Error getting purchase history: {e}")
            return []

    async def use_inventory_item(self, user_id: str, item_id: int, quantity: int = 1) -> bool:
        """Use an item from user's inventory (PostgreSQL)."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.transaction():
                    item = await conn.fetchrow(
                        """
                        SELECT * FROM user_inventory 
                        WHERE user_id = $1 AND id = $2 AND quantity >= $3 AND is_active = TRUE
                        """, user_id, item_id, quantity
                    )
                    if not item:
                        self.logger.warning(f"Item not found or insufficient quantity: user={user_id}, item_id={item_id}, requested={quantity}")
                        return False
                    current_quantity = item['quantity']
                    new_quantity = current_quantity - quantity
                    self.logger.info(f"Using item: {item['item_name']} qty {current_quantity} -> {new_quantity}")
                    if new_quantity <= 0:
                        self.logger.info(f"Removing item completely (new_quantity={new_quantity})")
                        await conn.execute("DELETE FROM user_inventory WHERE id = $1", item_id)
                    else:
                        self.logger.info(f"Updating quantity to {new_quantity}")
                        await conn.execute("UPDATE user_inventory SET quantity = $1 WHERE id = $2", new_quantity, item_id)
                    self.logger.info(f"Transaction committed successfully")
                    return True
        except Exception as e:
            self.logger.error(f"Error using inventory item: {e}")
            return False

    # Shop-related methods for guarantee tickets only
    # Note: Other item type methods were removed to simplify the codebase

    # === EXPEDITION SYSTEM METHODS ===
    
    async def create_expedition(self, discord_id: str, expedition_data: Dict[str, Any], participants: List[Dict[str, Any]], equipped_equipment_id: Optional[int] = None) -> int:
        """Create a new expedition for a user with participants."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
    # ...removed debug logging...
        
        async with self.connection_pool.acquire() as conn:
            async with conn.transaction():
                # Get user_id
                user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
                if not user_row:
                    self.logger.error(f"[DB_EXPEDITION_CREATE] User {discord_id} not found in database")
                    raise ValueError(f"User {discord_id} not found")
                user_id = user_row["id"]
                
                # Create expedition
                self.logger.debug(f"[DB_EXPEDITION_CREATE] Creating expedition record for user_id {user_id}")
                if equipped_equipment_id is not None:
                    expedition_row = await conn.fetchrow(
                        """
                        INSERT INTO user_expeditions (
                            user_id, expedition_name, location, difficulty, 
                            duration_hours, expedition_data, status, equipped_equipment_id
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        RETURNING id
                        """,
                        user_id,
                        expedition_data["name"],
                        expedition_data["location"],
                        expedition_data["difficulty"],
                        expedition_data["duration_hours"],
                        json.dumps(expedition_data),
                        "in_progress",
                        equipped_equipment_id
                    )
                else:
                    expedition_row = await conn.fetchrow(
                        """
                        INSERT INTO user_expeditions (
                            user_id, expedition_name, location, difficulty, 
                            duration_hours, expedition_data, status
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        RETURNING id
                        """,
                        user_id,
                        expedition_data["name"],
                        expedition_data["location"],
                        expedition_data["difficulty"],
                        expedition_data["duration_hours"],
                        json.dumps(expedition_data),
                        "in_progress"
                    )
                
                expedition_id = expedition_row["id"]
                self.logger.info(f"[DB_EXPEDITION_CREATE] Created expedition {expedition_id} for user {discord_id}")
                
                # Add participants
                self.logger.debug(f"[DB_EXPEDITION_CREATE] Adding {len(participants)} participants to expedition {expedition_id}")
                for i, participant in enumerate(participants):
                    await conn.execute(
                        """
                        INSERT INTO expedition_participants (
                            expedition_id, user_waifu_id, position_in_party, star_level_used
                        ) VALUES ($1, $2, $3, $4)
                        """,
                        expedition_id,
                        participant["user_waifu_id"],
                        i,
                        participant["star_level"]
                    )
                    self.logger.debug(f"[DB_EXPEDITION_CREATE] Added participant {participant['user_waifu_id']} at position {i}")
                
                self.logger.info(f"[DB_EXPEDITION_CREATE] Successfully created expedition {expedition_id} with all participants")
                return expedition_id

    async def get_user_expeditions(self, discord_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all expeditions for a user, optionally filtered by status."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
    # ...removed debug logging...
        
        async with self.connection_pool.acquire() as conn:
            user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
            if not user_row:
                self.logger.warning(f"[DB_EXPEDITION_GET] User {discord_id} not found in database")
                return []
            user_id = user_row["id"]
            
            if status:
                rows = await conn.fetch(
                    "SELECT * FROM user_expeditions WHERE user_id = $1 AND status = $2 ORDER BY started_at DESC",
                    user_id, status
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM user_expeditions WHERE user_id = $1 ORDER BY started_at DESC",
                    user_id
                )
            
            self.logger.debug(f"[DB_EXPEDITION_GET] Found {len(rows)} expeditions for user {discord_id}")
            
            expeditions = []
            for row in rows:
                expedition = dict(row)
                if expedition['expedition_data']:
                    try:
                        expedition['expedition_data'] = json.loads(expedition['expedition_data'])
                    except:
                        expedition['expedition_data'] = {}
                if expedition['final_results']:
                    try:
                        expedition['final_results'] = json.loads(expedition['final_results'])
                    except:
                        expedition['final_results'] = {}
                expeditions.append(expedition)
            
            return expeditions

    async def get_expedition_with_participants(self, expedition_id: int) -> Optional[Dict[str, Any]]:
        """Get expedition with minimal participant details (optimized)."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
        async with self.connection_pool.acquire() as conn:
            # Get expedition
            expedition_row = await conn.fetchrow(
                "SELECT * FROM user_expeditions WHERE id = $1", expedition_id
            )
            if not expedition_row:
                return None
            
            expedition = dict(expedition_row)
            if expedition['expedition_data']:
                try:
                    expedition['expedition_data'] = json.loads(expedition['expedition_data'])
                except:
                    expedition['expedition_data'] = {}
            
            # Get participants with minimal data (no joins to waifus table)
            participant_rows = await conn.fetch(
                """
                SELECT ep.user_waifu_id, ep.position_in_party, ep.star_level_used, uw.waifu_id
                FROM expedition_participants ep
                JOIN user_waifus uw ON ep.user_waifu_id = uw.id
                WHERE ep.expedition_id = $1
                ORDER BY ep.position_in_party
                """,
                expedition_id
            )
            
            participants = []
            for row in participant_rows:
                participant = {
                    "user_waifu_id": row["user_waifu_id"],
                    "waifu_id": row["waifu_id"], 
                    "position_in_party": row["position_in_party"],
                    "star_level_used": row["star_level_used"]
                }
                participants.append(participant)
            
            expedition['participants'] = participants
            return expedition

    async def update_expedition_status(self, expedition_id: int, status: str, final_results: Optional[Dict] = None) -> bool:
        """Update expedition status and optionally set final results."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
        async with self.connection_pool.acquire() as conn:
            if status == "completed" and final_results:
                await conn.execute(
                    """
                    UPDATE user_expeditions 
                    SET status = $1, completed_at = CURRENT_TIMESTAMP, final_results = $2
                    WHERE id = $3
                    """,
                    status, json.dumps(final_results), expedition_id
                )
            else:
                await conn.execute(
                    "UPDATE user_expeditions SET status = $1 WHERE id = $2",
                    status, expedition_id
                )
            return True

    async def claim_expedition_rewards(self, expedition_id: int) -> bool:
        """Mark expedition rewards as claimed."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE user_expeditions SET rewards_claimed = TRUE WHERE id = $1",
                expedition_id
            )
            return result.endswith('1')

    async def add_expedition_log(self, expedition_id: int, log_type: str, message: str, data: Optional[Dict] = None, encounter_number: Optional[int] = None) -> int:
        """Add a log entry to an expedition."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO expedition_logs (expedition_id, log_type, message, data, encounter_number)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                expedition_id, log_type, message, json.dumps(data or {}), encounter_number
            )
            return row["id"] if row else 0

    async def get_expedition_logs(self, expedition_id: int) -> List[Dict[str, Any]]:
        """Get all logs for an expedition."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM expedition_logs WHERE expedition_id = $1 ORDER BY timestamp ASC",
                expedition_id
            )
            
            logs = []
            for row in rows:
                log = dict(row)
                if log['data']:
                    try:
                        log['data'] = json.loads(log['data'])
                    except:
                        log['data'] = {}
                logs.append(log)
            
            return logs

    async def get_user_waifus_for_expedition(self, discord_id: str) -> List[Dict[str, Any]]:
        """Get user's waifus suitable for expeditions with their star levels."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
        async with self.connection_pool.acquire() as conn:
            user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
            if not user_row:
                return []
            user_id = user_row["id"]
            
            rows = await conn.fetch(
                """
                SELECT uw.id as user_waifu_id, uw.waifu_id, uw.current_star_level, uw.bond_level, uw.is_awakened,
                       w.name, w.series, w.rarity, w.image_url, w.stats, w.elemental_type, 
                       w.archetype, w.potency, w.elemental_resistances
                FROM user_waifus uw
                JOIN waifus w ON uw.waifu_id = w.waifu_id
                WHERE uw.user_id = $1
                ORDER BY w.rarity DESC, w.name ASC
                """,
                user_id
            )
            
            waifus = []
            for row in rows:
                waifu = dict(row)
                waifu = self._parse_waifu_json_fields(waifu)
                waifus.append(waifu)
            
            return waifus

    async def get_user_waifus_minimal(self, discord_id: str) -> List[Dict[str, Any]]:
        """Get user's waifus with minimal data (no joins) - optimized for expeditions. Now includes is_awakened."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
        async with self.connection_pool.acquire() as conn:
            user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
            if not user_row:
                return []
            user_id = user_row["id"]
            
            rows = await conn.fetch(
                """
                SELECT id as user_waifu_id, waifu_id, current_star_level, bond_level, is_awakened
                FROM user_waifus
                WHERE user_id = $1
                ORDER BY waifu_id ASC
                """,
                user_id
            )
            
            return [dict(row) for row in rows]

    async def get_user_waifus_available_for_expeditions(self, discord_id: str) -> List[Dict[str, Any]]:
        """Get user's waifus that are NOT currently in active expeditions - for character selection."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
        async with self.connection_pool.acquire() as conn:
            user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
            if not user_row:
                return []
            user_id = user_row["id"]
            
            rows = await conn.fetch(
                """
                SELECT uw.id as user_waifu_id, uw.waifu_id, uw.current_star_level, uw.bond_level, uw.is_awakened
                FROM user_waifus uw
                WHERE uw.user_id = $1
                AND uw.id NOT IN (
                    SELECT DISTINCT ep.user_waifu_id
                    FROM expedition_participants ep
                    JOIN user_expeditions ue ON ep.expedition_id = ue.id
                    WHERE ue.user_id = $1 AND ue.status = 'in_progress'
                )
                ORDER BY uw.waifu_id ASC
                """,
                user_id
            )
            
            return [dict(row) for row in rows]

    async def update_user_waifu_star_level(self, user_waifu_id: int, star_level: int) -> bool:
        """Update a user waifu's star level."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE user_waifus SET current_star_level = $1 WHERE id = $2",
                star_level, user_waifu_id
            )
            return result.endswith('1')

    async def check_expedition_conflicts(self, discord_id: str, participant_ids: List[int]) -> List[int]:
        """Check if any waifus are already in active expeditions."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
        async with self.connection_pool.acquire() as conn:
            user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
            if not user_row:
                return []
            user_id = user_row["id"]
            
            rows = await conn.fetch(
                """
                SELECT DISTINCT ep.user_waifu_id
                FROM expedition_participants ep
                JOIN user_expeditions ue ON ep.expedition_id = ue.id
                WHERE ue.user_id = $1 AND ue.status = 'in_progress'
                AND ep.user_waifu_id = ANY($2::int[])
                """,
                user_id, participant_ids
            )
            
            return [row['user_waifu_id'] for row in rows]

    async def release_expedition_participants(self, expedition_id: int) -> bool:
        """Release participants from an expedition so they can be used in new expeditions."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Simply delete the expedition participants to free them up
                result = await conn.execute(
                    "DELETE FROM expedition_participants WHERE expedition_id = $1",
                    expedition_id
                )
                self.logger.info(f"Released participants for expedition {expedition_id}: {result}")
                return True
            except Exception as e:
                self.logger.error(f"Error releasing expedition participants: {e}")
                return False

    async def distribute_loot_rewards(self, discord_id: str, loot_items: List[Any]) -> Dict[str, Any]:
        """
        Distribute loot rewards to a user
        
        Args:
            discord_id: User's Discord ID
            loot_items: List of loot items from LootGenerator.generate_loot()
                       Each item should have: item_type, item_id, quantity, value
        
        Returns:
            Dictionary with distribution results and summary
        """
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
        async with self.connection_pool.acquire() as conn:
            async with conn.transaction():
                # Get user_id from discord_id
                user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
                if not user_row:
                    raise ValueError(f"User with discord_id {discord_id} not found")
                user_id = user_row["id"]
                # Track rewards for summary
                currency_rewards = {"sakura_crystals": 0, "quartzs": 0}
                item_rewards = []
                for loot_item in loot_items:
                    try:
                        if hasattr(loot_item, 'item_type'):
                            item_type = loot_item.item_type.value if hasattr(loot_item.item_type, 'value') else str(loot_item.item_type)
                            item_id = getattr(loot_item, 'item_id', '')
                            quantity = getattr(loot_item, 'quantity', 0)
                            value = getattr(loot_item, 'value', 0)
                        elif hasattr(loot_item, 'get') and callable(getattr(loot_item, 'get')):
                            item_type = loot_item.get('item_type', '')
                            item_id = loot_item.get('item_id', '')
                            quantity = loot_item.get('quantity', 0)
                            value = loot_item.get('value', 0)
                        else:
                            continue
                        if not item_type or not item_id:
                            continue
                        try:
                            quantity = int(quantity)
                            if quantity <= 0:
                                continue
                        except (ValueError, TypeError):
                            continue
                    except Exception:
                        continue
                    if item_type in ["GEMS", "gems"] and item_id == "sakura_crystals":
                        await conn.execute(
                            "UPDATE users SET sakura_crystals = sakura_crystals + $1 WHERE id = $2",
                            quantity, user_id
                        )
                        currency_rewards["sakura_crystals"] += quantity
                    elif item_type in ["QUARTZS", "quartzs"] and item_id == "quartzs":
                        await conn.execute(
                            "UPDATE users SET quartzs = quartzs + $1 WHERE id = $2",
                            quantity, user_id
                        )
                        currency_rewards["quartzs"] += quantity
                    elif item_type in ["ITEM", "item"]:
                        await self._add_item_to_inventory(conn, discord_id, item_id, quantity)
                        item_rewards.append({
                            "item_id": item_id,
                            "quantity": quantity,
                            "value": value
                        })
                    else:
                        continue
                return {
                    "success": True,
                    "currency_rewards": currency_rewards,
                    "item_rewards": item_rewards,
                    "total_items": len(loot_items)
                }

    async def _add_item_to_inventory(self, conn, discord_id: str, item_id: str, quantity: int):
        """
        Add an item to user inventory, stacking if it already exists.
        Uses shop_items table for item details if item_id follows format "item_X" where X is shop_items.id
        
        Args:
            conn: Database connection
            discord_id: User's Discord ID (string)
            item_id: Item identifier (e.g., "item_1", "item_2") where number is shop_items.id
            quantity: Quantity to add
        """
        # Extract shop_item_id from item_id (e.g., "item_1" -> 1)
        shop_item_id = None
        item_name = item_id
        item_type = "expedition_reward"
        metadata = '{}'
        effects = '{}'
        
        if item_id.startswith("item_") and len(item_id) > 5:
            try:
                shop_item_id = int(item_id[5:])  # Extract number after "item_"
                
                # Fetch item details from shop_items table including item_data and effects
                shop_item = await conn.fetchrow(
                    "SELECT name, description, category, item_type, item_data, effects FROM shop_items WHERE id = $1",
                    shop_item_id
                )
                
                if shop_item:
                    item_name = shop_item["name"]
                    item_type = shop_item.get("item_type", "expedition_reward")
                    metadata = shop_item.get("item_data") if shop_item.get("item_data") else '{}'
                    effects = shop_item.get("effects") if shop_item.get("effects") else '{}'
                else:
                    self.logger.warning(f"Shop item with ID {shop_item_id} not found, using fallback item_id: {item_id}")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid item_id format: {item_id}, expected 'item_X' where X is a number")
        
        # Check if item already exists in inventory (by item_name)
        existing_item = await conn.fetchrow(
            """
            SELECT id, quantity FROM user_inventory 
            WHERE user_id = $1 AND item_name = $2
            """,
            discord_id, item_name
        )
        
        if existing_item:
            # Update existing item quantity
            await conn.execute(
                "UPDATE user_inventory SET quantity = quantity + $1 WHERE id = $2",
                quantity, existing_item["id"]
            )
        else:
            # Create new inventory entry with copied metadata and effects
            await conn.execute(
                """
                INSERT INTO user_inventory (user_id, item_name, item_type, quantity, metadata, effects, is_active, acquired_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                """,
                discord_id, item_name, item_type, quantity, metadata, effects, True
            )

    async def get_user_currency(self, discord_id: str) -> Dict[str, int]:
        """
        Get user's current currency amounts
        
        Args:
            discord_id: User's Discord ID
            
        Returns:
            Dictionary with sakura_crystals and quartzs amounts
        """
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
        async with self.connection_pool.acquire() as conn:
            user_row = await conn.fetchrow(
                "SELECT sakura_crystals, quartzs FROM users WHERE discord_id = $1", 
                discord_id
            )
            
            if not user_row:
                return {"sakura_crystals": 0, "quartzs": 0}
            
            return {
                "sakura_crystals": user_row["sakura_crystals"] or 0,
                "quartzs": user_row["quartzs"] or 0
            }

    async def get_user_inventory_items(self, discord_id: str, item_type: str = None) -> List[Dict[str, Any]]:
        """
        Get user's inventory items
        
        Args:
            discord_id: User's Discord ID
            item_type: Optional filter by item type
            
        Returns:
            List of inventory items
        """
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
        async with self.connection_pool.acquire() as conn:
            # Get user_id from discord_id
            user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
            if not user_row:
                return []
            
            user_id = str(user_row["id"])
            
            if item_type:
                items = await conn.fetch(
                    """
                    SELECT * FROM user_inventory 
                    WHERE user_id = $1 AND item_type = $2 
                    ORDER BY acquired_at DESC
                    """,
                    user_id, item_type
                )
            else:
                items = await conn.fetch(
                    """
                    SELECT * FROM user_inventory 
                    WHERE user_id = $1 
                    ORDER BY acquired_at DESC
                    """,
                    user_id
                )
            
            return [dict(item) for item in items]

    async def get_expedition_by_id(self, expedition_id: int) -> Optional[Dict[str, Any]]:
        """Get expedition details by ID with creator information"""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        
        async with self.connection_pool.acquire() as conn:
            expedition_row = await conn.fetchrow(
                """
                SELECT e.*, u.discord_id as creator_discord_id 
                FROM user_expeditions e
                JOIN users u ON e.user_id = u.id
                WHERE e.id = $1
                """,
                expedition_id
            )
            
            if not expedition_row:
                return None
            
            expedition = dict(expedition_row)
            if expedition['expedition_data']:
                try:
                    expedition['expedition_data'] = json.loads(expedition['expedition_data'])
                except:
                    expedition['expedition_data'] = {}
            
            return expedition
