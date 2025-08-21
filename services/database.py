"""Database service for Waifu Academy system."""

import aiosqlite
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path


class DatabaseService:
    """Service for managing the Waifu Academy database."""

    def __init__(self, db_path: str = "data/waifu_academy.db"):
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)

        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Initialize the database with required tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await self._create_tables(db)
            await db.commit()
        self.logger.info("Database initialized successfully")

    async def _create_tables(self, db: aiosqlite.Connection):
        """Create all required tables for the Waifu Academy system."""

        # Users table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT UNIQUE NOT NULL,
                academy_name TEXT,
                collector_rank INTEGER DEFAULT 1,
                sakura_crystals INTEGER DEFAULT 100,
                pity_counter INTEGER DEFAULT 0,
                last_daily_reset INTEGER DEFAULT 0,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """
        )

        # Waifus table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS waifus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                series TEXT NOT NULL,
                genre TEXT NOT NULL,
                element TEXT,
                rarity INTEGER NOT NULL CHECK (rarity >= 1 AND rarity <= 5),
                image_url TEXT,
                mal_id INTEGER,
                personality_profile TEXT,
                base_stats TEXT, -- JSON string
                birthday DATE,
                favorite_gifts TEXT, -- JSON string
                special_dialogue TEXT, -- JSON string
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """
        )

        # User waifus table (collection)
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_waifus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                waifu_id INTEGER NOT NULL,
                bond_level INTEGER DEFAULT 1,
                constellation_level INTEGER DEFAULT 0,
                current_mood TEXT DEFAULT 'neutral',
                last_interaction TIMESTAMP,
                total_conversations INTEGER DEFAULT 0,
                favorite_memory TEXT,
                custom_nickname TEXT,
                room_decorations TEXT, -- JSON string
                obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (waifu_id) REFERENCES waifus (id),
                UNIQUE(user_id, waifu_id, obtained_at) -- Allow duplicates for constellations
            )
        """
        )

        # Conversations table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                waifu_id INTEGER NOT NULL,
                user_message TEXT NOT NULL,
                waifu_response TEXT NOT NULL,
                mood_change INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (waifu_id) REFERENCES waifus (id)
            )
        """
        )

        # Daily missions table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_missions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                type TEXT NOT NULL,
                target_count INTEGER NOT NULL,
                reward_type TEXT NOT NULL,
                reward_amount INTEGER NOT NULL,
                difficulty TEXT DEFAULT 'easy',
                is_active BOOLEAN DEFAULT TRUE
            )
        """
        )

        # User mission progress table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_mission_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                mission_id INTEGER NOT NULL,
                current_progress INTEGER DEFAULT 0,
                completed BOOLEAN DEFAULT FALSE,
                claimed BOOLEAN DEFAULT FALSE,
                date DATE DEFAULT (date('now')),
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (mission_id) REFERENCES daily_missions (id),
                UNIQUE(user_id, mission_id, date)
            )
        """
        )

        # Events table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP NOT NULL,
                event_type TEXT NOT NULL,
                bonus_conditions TEXT, -- JSON string
                is_active BOOLEAN DEFAULT TRUE
            )
        """
        )

        # Create indexes for better performance
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_waifus_user_id ON user_waifus(user_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_user_waifu ON conversations(user_id, waifu_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_waifus_rarity ON waifus(rarity)"
        )

    async def get_or_create_user(self, discord_id: str) -> Dict[str, Any]:
        """Get user from database or create if doesn't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Try to get existing user
            async with db.execute(
                "SELECT * FROM users WHERE discord_id = ?", (discord_id,)
            ) as cursor:
                user = await cursor.fetchone()

            if user:
                return dict(user)

            # Create new user
            await db.execute(
                """INSERT INTO users (discord_id, academy_name, last_daily_reset) 
                   VALUES (?, ?, ?)""",
                (discord_id, f"Academy {discord_id[:6]}", datetime.now()),
            )
            await db.commit()

            # Return the newly created user
            async with db.execute(
                "SELECT * FROM users WHERE discord_id = ?", (discord_id,)
            ) as cursor:
                user = await cursor.fetchone()
                return dict(user)

    async def add_waifu(self, waifu_data: Dict[str, Any]) -> int:
        """Add a new waifu to the database."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO waifus (
                    name, series, genre, element, rarity, image_url, mal_id,
                    personality_profile, base_stats, birthday, favorite_gifts, special_dialogue
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    waifu_data["name"],
                    waifu_data["series"],
                    waifu_data.get("genre", "Unknown"),
                    waifu_data.get("element"),
                    waifu_data["rarity"],
                    waifu_data.get("image_url"),
                    waifu_data.get("mal_id"),
                    waifu_data.get("personality_profile"),
                    json.dumps(waifu_data.get("base_stats", {})),
                    waifu_data.get("birthday"),
                    json.dumps(waifu_data.get("favorite_gifts", [])),
                    json.dumps(waifu_data.get("special_dialogue", {})),
                ),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_waifus_by_rarity(
        self, rarity: int, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get waifus by rarity level."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM waifus WHERE rarity = ? ORDER BY RANDOM() LIMIT ?",
                (rarity, limit),
            ) as cursor:
                waifus = await cursor.fetchall()
                return [dict(w) for w in waifus]

    async def get_user_collection(self, discord_id: str) -> List[Dict[str, Any]]:
        """Get user's waifu collection."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT uw.*, w.name, w.series, w.rarity, w.image_url, w.element
                FROM user_waifus uw
                JOIN waifus w ON uw.waifu_id = w.id
                JOIN users u ON uw.user_id = u.id
                WHERE u.discord_id = ?
                ORDER BY uw.obtained_at DESC
            """,
                (discord_id,),
            ) as cursor:
                collection = await cursor.fetchall()
                return [dict(c) for c in collection]

    async def add_waifu_to_user(self, discord_id: str, waifu_id: int) -> bool:
        """Add a waifu to user's collection."""
        async with aiosqlite.connect(self.db_path) as db:
            # Get user ID
            async with db.execute(
                "SELECT id FROM users WHERE discord_id = ?", (discord_id,)
            ) as cursor:
                user = await cursor.fetchone()
                if not user:
                    return False

            user_id = user[0]

            # Add waifu to collection
            await db.execute(
                """
                INSERT INTO user_waifus (user_id, waifu_id)
                VALUES (?, ?)
            """,
                (user_id, waifu_id),
            )
            await db.commit()
            return True

    async def update_user_crystals(self, discord_id: str, amount: int) -> bool:
        """Update user's Sakura Crystals."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE users SET sakura_crystals = sakura_crystals + ? WHERE discord_id = ?",
                (amount, discord_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def update_pity_counter(self, discord_id: str, reset: bool = False) -> bool:
        """Update user's pity counter."""
        async with aiosqlite.connect(self.db_path) as db:
            if reset:
                cursor = await db.execute(
                    "UPDATE users SET pity_counter = 0 WHERE discord_id = ?",
                    (discord_id,),
                )
            else:
                cursor = await db.execute(
                    "UPDATE users SET pity_counter = pity_counter + 1 WHERE discord_id = ?",
                    (discord_id,),
                )
            await db.commit()
            return cursor.rowcount > 0

    async def get_waifu_by_id(self, waifu_id: int) -> Optional[Dict[str, Any]]:
        """Get waifu by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM waifus WHERE id = ?", (waifu_id,)
            ) as cursor:
                waifu = await cursor.fetchone()
                return dict(waifu) if waifu else None

    async def search_waifus(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search waifus by name or series."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM waifus 
                WHERE name LIKE ? OR series LIKE ?
                ORDER BY rarity DESC, name
                LIMIT ?
            """,
                (f"%{query}%", f"%{query}%", limit),
            ) as cursor:
                waifus = await cursor.fetchall()
                return [dict(w) for w in waifus]

    async def add_conversation(
        self,
        discord_id: str,
        waifu_id: int,
        user_message: str,
        waifu_response: str,
        mood_change: int = 0,
    ) -> bool:
        """Add a conversation record."""
        async with aiosqlite.connect(self.db_path) as db:
            # Get user ID
            async with db.execute(
                "SELECT id FROM users WHERE discord_id = ?", (discord_id,)
            ) as cursor:
                user = await cursor.fetchone()
                if not user:
                    return False

            user_id = user[0]

            # Add conversation
            await db.execute(
                """
                INSERT INTO conversations (user_id, waifu_id, user_message, waifu_response, mood_change)
                VALUES (?, ?, ?, ?, ?)
            """,
                (user_id, waifu_id, user_message, waifu_response, mood_change),
            )

            # Update user waifu interaction stats
            await db.execute(
                """
                UPDATE user_waifus 
                SET total_conversations = total_conversations + 1,
                    last_interaction = CURRENT_TIMESTAMP
                WHERE user_id = ? AND waifu_id = ?
            """,
                (user_id, waifu_id),
            )

            await db.commit()
            return True
