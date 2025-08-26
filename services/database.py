"""Database service for Waifu Academy system with PostgreSQL support only."""

import asyncpg
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING
from datetime import datetime, timezone

if TYPE_CHECKING:
    from config.config import Config


class DatabaseService:
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
            return [dict(row) for row in rows]

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
            return [dict(row) for row in rows]

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
            return dict(row) if row else None
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
        """Batch add multiple waifus to a user's collection, skipping already-owned waifus. Returns full waifu+user_waifu data for all added."""
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
                SELECT uw.*, w.name, w.series, w.rarity, w.image_url, w.waifu_id as waifu_id
                FROM user_waifus uw
                JOIN waifus w ON uw.waifu_id = w.waifu_id
                WHERE uw.user_id = $1 AND uw.waifu_id = ANY($2::int[])
                """,
                user_id, all_ids
            )
            return [dict(row) for row in rows]
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
                element VARCHAR(50),
                rarity INTEGER NOT NULL CHECK (rarity >= 1 AND rarity <= 3),
                image_url TEXT,
                about TEXT,
                base_stats TEXT,
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
        self.logger.info(f"get_user_fresh: Starting query for user {discord_id}")
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
        """Add a new waifu to the database (PostgreSQL), including series_id as a foreign key and about field."""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool is not initialized. Call 'await initialize()' first.")
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO waifus (
                    name, series_id, series, genre, element, rarity, image_url, about, waifu_id,
                    base_stats, birthday, favorite_gifts, special_dialogue
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING waifu_id
                """,
                waifu_data["name"],
                waifu_data["series_id"],
                waifu_data["series"],
                waifu_data.get("genre", "Unknown"),
                waifu_data.get("element"),
                waifu_data["rarity"],
                waifu_data.get("image_url"),
                waifu_data.get("about", None),
                waifu_data.get("waifu_id"),
                json.dumps(waifu_data.get("base_stats", {})),
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
                return dict(row)
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
            return [dict(row) for row in rows]

    async def get_user_collection(self, discord_id: str) -> List[Dict[str, Any]]:
        """Get all waifus in a user's collection (PostgreSQL), using waifu_id as identifier."""
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT uw.*, w.name, w.series, w.rarity, w.image_url, w.waifu_id as waifu_id, u.discord_id
                FROM user_waifus uw
                JOIN waifus w ON uw.waifu_id = w.waifu_id
                JOIN users u ON uw.user_id = u.id
                WHERE u.discord_id = $1
                ORDER BY uw.obtained_at DESC
                """,
                discord_id
            )
            return [dict(row) for row in rows]

    async def add_waifu_to_user(self, discord_id: str, waifu_id: int) -> Dict[str, Any]:
        """Add a waifu to a user's collection, handling constellation system (PostgreSQL), using waifu_id as identifier."""
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
                    SELECT uw.*, w.name, w.series, w.rarity, w.image_url, w.waifu_id as waifu_id
                    FROM user_waifus uw
                    JOIN waifus w ON uw.waifu_id = w.waifu_id
                    WHERE uw.id = $1
                    """,
                    existing["id"]
                )
                return dict(row) if row else {}
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
                    SELECT uw.*, w.name, w.series, w.rarity, w.image_url, w.waifu_id as waifu_id
                    FROM user_waifus uw
                    JOIN waifus w ON uw.waifu_id = w.waifu_id
                    WHERE uw.id = $1
                    """,
                    new_id
                )
                return dict(row) if row else {}

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
    async def search_waifus(self, name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for waifus by name (PostgreSQL)."""
        async with self.connection_pool.acquire() as conn:
            query = "SELECT * FROM waifus WHERE name ILIKE $1 OR series ILIKE $2"
            params = (f"%{name}%", f"%{name}%")
            if limit:
                query += " LIMIT $3"
                params = params + (limit,)
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

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
        """Reset a user's account to default state (PostgreSQL)."""
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
                return True
            except Exception as e:
                self.logger.error(f"Error resetting user account {discord_id}: {e}")
                return False

    async def delete_user_account(self, discord_id: str) -> bool:
        """Permanently delete a user's account (PostgreSQL)."""
        async with self.connection_pool.acquire() as conn:
            try:
                user_row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
                if user_row:
                    user_id = user_row[0]
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
                            json.dumps(item['item_data']) if item['item_data'] else '{}',
                            json.dumps(item['effects']) if item['effects'] else '{}', True
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
