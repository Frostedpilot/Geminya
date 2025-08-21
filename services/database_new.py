"""Database service for Waifu Academy system with MySQL and SQLite support."""

import aiosqlite
import aiomysql
import json
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from config.config import Config


class DatabaseService:
    """Service for managing the Waifu Academy database."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.db_type = config.get_database_type()
        self.connection_pool = None
        
        if self.db_type == "sqlite":
            self.db_path = Path(config.get_sqlite_path())
            # Ensure data directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        elif self.db_type == "mysql":
            self.mysql_config = config.get_mysql_config()

    async def initialize(self):
        """Initialize the database with required tables."""
        if self.db_type == "mysql":
            # Create connection pool for MySQL
            self.connection_pool = await aiomysql.create_pool(
                host=self.mysql_config["host"],
                port=self.mysql_config["port"],
                user=self.mysql_config["user"],
                password=self.mysql_config["password"],
                db=self.mysql_config["database"],
                charset=self.mysql_config.get("charset", "utf8mb4"),
                autocommit=self.mysql_config.get("autocommit", True),
                minsize=1,
                maxsize=10
            )
            
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await self._create_tables_mysql(cursor)
                    await conn.commit()
        else:
            async with aiosqlite.connect(self.db_path) as db:
                await self._create_tables_sqlite(db)
                await db.commit()
                
        self.logger.info("Database (%s) initialized successfully", self.db_type)

    async def close(self):
        """Close database connections."""
        if self.db_type == "mysql" and self.connection_pool:
            self.connection_pool.close()
            await self.connection_pool.wait_closed()
            self.logger.info("MySQL connection pool closed")

    async def _create_tables_sqlite(self, db: aiosqlite.Connection):
        """Create all required tables for SQLite."""
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

    async def _create_tables_mysql(self, cursor):
        """Create all required tables for MySQL."""
        # Users table
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                discord_id VARCHAR(255) UNIQUE NOT NULL,
                academy_name VARCHAR(255),
                collector_rank INT DEFAULT 1,
                sakura_crystals INT DEFAULT 100,
                pity_counter INT DEFAULT 0,
                last_daily_reset BIGINT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_discord_id (discord_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        )

        # Waifus table
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS waifus (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                series VARCHAR(255) NOT NULL,
                genre VARCHAR(255) NOT NULL,
                element VARCHAR(50),
                rarity INT NOT NULL CHECK (rarity >= 1 AND rarity <= 5),
                image_url TEXT,
                mal_id INT,
                personality_profile TEXT,
                base_stats JSON,
                birthday DATE,
                favorite_gifts JSON,
                special_dialogue JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_rarity (rarity)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        )

        # User waifus table (collection)
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_waifus (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                waifu_id INT NOT NULL,
                bond_level INT DEFAULT 1,
                constellation_level INT DEFAULT 0,
                current_mood VARCHAR(50) DEFAULT 'neutral',
                last_interaction TIMESTAMP NULL,
                total_conversations INT DEFAULT 0,
                favorite_memory TEXT,
                custom_nickname VARCHAR(255),
                room_decorations JSON,
                obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (waifu_id) REFERENCES waifus (id) ON DELETE CASCADE,
                INDEX idx_user_id (user_id),
                INDEX idx_user_waifu (user_id, waifu_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        )

        # Conversations table
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                waifu_id INT NOT NULL,
                user_message TEXT NOT NULL,
                waifu_response TEXT NOT NULL,
                mood_change INT DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (waifu_id) REFERENCES waifus (id) ON DELETE CASCADE,
                INDEX idx_user_waifu (user_id, waifu_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        )

        # Daily missions table
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_missions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                type VARCHAR(100) NOT NULL,
                target_count INT NOT NULL,
                reward_type VARCHAR(100) NOT NULL,
                reward_amount INT NOT NULL,
                difficulty VARCHAR(50) DEFAULT 'easy',
                is_active BOOLEAN DEFAULT TRUE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        )

        # User mission progress table
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_mission_progress (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                mission_id INT NOT NULL,
                current_progress INT DEFAULT 0,
                completed BOOLEAN DEFAULT FALSE,
                claimed BOOLEAN DEFAULT FALSE,
                date DATE DEFAULT (CURDATE()),
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (mission_id) REFERENCES daily_missions (id) ON DELETE CASCADE,
                UNIQUE KEY unique_user_mission_date (user_id, mission_id, date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        )

        # Events table
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP NOT NULL,
                event_type VARCHAR(100) NOT NULL,
                bonus_conditions JSON,
                is_active BOOLEAN DEFAULT TRUE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        )

    async def get_or_create_user(self, discord_id: str) -> Dict[str, Any]:
        """Get user from database or create if doesn't exist."""
        if self.db_type == "mysql":
            return await self._get_or_create_user_mysql(discord_id)
        else:
            return await self._get_or_create_user_sqlite(discord_id)

    async def _get_or_create_user_sqlite(self, discord_id: str) -> Dict[str, Any]:
        """SQLite implementation of get_or_create_user."""
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
                (discord_id, f"Academy {discord_id[:6]}", datetime.now().timestamp()),
            )
            await db.commit()

            # Return the newly created user
            async with db.execute(
                "SELECT * FROM users WHERE discord_id = ?", (discord_id,)
            ) as cursor:
                user = await cursor.fetchone()
                return dict(user) if user else {}

    async def _get_or_create_user_mysql(self, discord_id: str) -> Dict[str, Any]:
        """MySQL implementation of get_or_create_user."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # Try to get existing user
                await cursor.execute(
                    "SELECT * FROM users WHERE discord_id = %s", (discord_id,)
                )
                user = await cursor.fetchone()

                if user:
                    return user

                # Create new user
                await cursor.execute(
                    """INSERT INTO users (discord_id, academy_name, last_daily_reset) 
                       VALUES (%s, %s, %s)""",
                    (discord_id, f"Academy {discord_id[:6]}", int(datetime.now().timestamp())),
                )
                await conn.commit()

                # Return the newly created user
                await cursor.execute(
                    "SELECT * FROM users WHERE discord_id = %s", (discord_id,)
                )
                user = await cursor.fetchone()
                return user if user else {}

    async def add_waifu(self, waifu_data: Dict[str, Any]) -> int:
        """Add a new waifu to the database."""
        if self.db_type == "mysql":
            return await self._add_waifu_mysql(waifu_data)
        else:
            return await self._add_waifu_sqlite(waifu_data)

    async def _add_waifu_sqlite(self, waifu_data: Dict[str, Any]) -> int:
        """SQLite implementation of add_waifu."""
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
            return cursor.lastrowid or 0

    async def _add_waifu_mysql(self, waifu_data: Dict[str, Any]) -> int:
        """MySQL implementation of add_waifu."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO waifus (
                        name, series, genre, element, rarity, image_url, mal_id,
                        personality_profile, base_stats, birthday, favorite_gifts, special_dialogue
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                await conn.commit()
                return cursor.lastrowid or 0

    async def get_waifus_by_rarity(
        self, rarity: int, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get waifus by rarity level."""
        if self.db_type == "mysql":
            return await self._get_waifus_by_rarity_mysql(rarity, limit)
        else:
            return await self._get_waifus_by_rarity_sqlite(rarity, limit)

    async def _get_waifus_by_rarity_sqlite(
        self, rarity: int, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """SQLite implementation of get_waifus_by_rarity."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM waifus WHERE rarity = ? ORDER BY RANDOM() LIMIT ?",
                (rarity, limit),
            ) as cursor:
                waifus = await cursor.fetchall()
                return [dict(w) for w in waifus]

    async def _get_waifus_by_rarity_mysql(
        self, rarity: int, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """MySQL implementation of get_waifus_by_rarity."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    "SELECT * FROM waifus WHERE rarity = %s ORDER BY RAND() LIMIT %s",
                    (rarity, limit),
                )
                waifus = await cursor.fetchall()
                return list(waifus)

    async def get_user_collection(self, discord_id: str) -> List[Dict[str, Any]]:
        """Get user's waifu collection."""
        if self.db_type == "mysql":
            return await self._get_user_collection_mysql(discord_id)
        else:
            return await self._get_user_collection_sqlite(discord_id)

    async def _get_user_collection_sqlite(self, discord_id: str) -> List[Dict[str, Any]]:
        """SQLite implementation of get_user_collection."""
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

    async def _get_user_collection_mysql(self, discord_id: str) -> List[Dict[str, Any]]:
        """MySQL implementation of get_user_collection."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT uw.*, w.name, w.series, w.rarity, w.image_url, w.element
                    FROM user_waifus uw
                    JOIN waifus w ON uw.waifu_id = w.id
                    JOIN users u ON uw.user_id = u.id
                    WHERE u.discord_id = %s
                    ORDER BY uw.obtained_at DESC
                """,
                    (discord_id,),
                )
                collection = await cursor.fetchall()
                return list(collection)

    async def add_waifu_to_user(self, discord_id: str, waifu_id: int) -> bool:
        """Add a waifu to user's collection."""
        if self.db_type == "mysql":
            return await self._add_waifu_to_user_mysql(discord_id, waifu_id)
        else:
            return await self._add_waifu_to_user_sqlite(discord_id, waifu_id)

    async def _add_waifu_to_user_sqlite(self, discord_id: str, waifu_id: int) -> bool:
        """SQLite implementation of add_waifu_to_user."""
        async with aiosqlite.connect(self.db_path) as db:
            # Get user ID
            async with db.execute(
                "SELECT id FROM users WHERE discord_id = ?", (discord_id,)
            ) as cursor:
                user = await cursor.fetchone()
                if not user:
                    return False

            user_id = user[0]

            # Add waifu to collection with a unique timestamp to handle rapid summons
            import time
            unique_timestamp = (
                f"{datetime.now().isoformat()}.{int(time.time_ns() % 1000000)}"
            )

            await db.execute(
                """
                INSERT INTO user_waifus (user_id, waifu_id, obtained_at)
                VALUES (?, ?, ?)
            """,
                (user_id, waifu_id, unique_timestamp),
            )
            await db.commit()
            return True

    async def _add_waifu_to_user_mysql(self, discord_id: str, waifu_id: int) -> bool:
        """MySQL implementation of add_waifu_to_user."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Get user ID
                await cursor.execute(
                    "SELECT id FROM users WHERE discord_id = %s", (discord_id,)
                )
                user = await cursor.fetchone()
                if not user:
                    return False

                user_id = user[0]

                # Add waifu to collection
                await cursor.execute(
                    """
                    INSERT INTO user_waifus (user_id, waifu_id, obtained_at)
                    VALUES (%s, %s, NOW())
                """,
                    (user_id, waifu_id),
                )
                await conn.commit()
                return True

    async def update_user_crystals(self, discord_id: str, amount: int) -> bool:
        """Update user's Sakura Crystals."""
        if self.db_type == "mysql":
            return await self._update_user_crystals_mysql(discord_id, amount)
        else:
            return await self._update_user_crystals_sqlite(discord_id, amount)

    async def _update_user_crystals_sqlite(self, discord_id: str, amount: int) -> bool:
        """SQLite implementation of update_user_crystals."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE users SET sakura_crystals = sakura_crystals + ? WHERE discord_id = ?",
                (amount, discord_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def _update_user_crystals_mysql(self, discord_id: str, amount: int) -> bool:
        """MySQL implementation of update_user_crystals."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE users SET sakura_crystals = sakura_crystals + %s WHERE discord_id = %s",
                    (amount, discord_id),
                )
                await conn.commit()
                return cursor.rowcount > 0

    # Add other methods with similar patterns...
    # For brevity, I'll implement the core methods needed for the waifu system
