"""Database service for Waifu Academy system with MySQL support only."""

import aiomysql
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from config.config import Config


class DatabaseService:
    """Service for managing the Waifu Academy database with MySQL only."""

    def __init__(self, config: "Config"):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.connection_pool = None
        self.mysql_config = config.get_mysql_config()

    async def initialize(self):
        """Initialize database connection and create tables."""
        try:
            # Create connection pool for MySQL
            self.connection_pool = await aiomysql.create_pool(
                host=self.mysql_config["host"],
                port=self.mysql_config["port"],
                user=self.mysql_config["user"],
                password=self.mysql_config["password"],
                db=self.mysql_config["database"],
                minsize=5,
                maxsize=20,
                autocommit=False,
            )

            # Create tables
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await self._create_tables_mysql(cursor)

            self.logger.info("MySQL database initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize MySQL database: {e}")
            raise

    async def close(self):
        """Close database connections."""
        if self.connection_pool:
            self.connection_pool.close()
            await self.connection_pool.wait_closed()
            self.logger.info("MySQL database connections closed")

    async def _create_tables_mysql(self, cursor):
        """Create all required tables for MySQL."""
        # Users table
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                discord_id VARCHAR(100) UNIQUE NOT NULL,
                academy_name VARCHAR(255),
                collector_rank INT DEFAULT 1,
                sakura_crystals INT DEFAULT 2000,
                quartzs INT DEFAULT 0,
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
                genre VARCHAR(100) NOT NULL,
                element VARCHAR(50),
                rarity INT NOT NULL CHECK (rarity >= 1 AND rarity <= 3),
                image_url TEXT,
                mal_id INT,
                base_stats TEXT,
                birthday DATE,
                favorite_gifts TEXT,
                special_dialogue TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_rarity (rarity),
                INDEX idx_name (name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        )

        # User waifus table (collection) - Updated for new star system
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_waifus (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                waifu_id INT NOT NULL,
                bond_level INT DEFAULT 1,
                constellation_level INT DEFAULT 0,
                current_star_level INT DEFAULT NULL,
                star_shards INT DEFAULT 0,
                character_shards INT DEFAULT 0,
                current_mood VARCHAR(50) DEFAULT 'neutral',
                last_interaction TIMESTAMP NULL,
                total_conversations INT DEFAULT 0,
                favorite_memory TEXT,
                custom_nickname VARCHAR(100),
                room_decorations TEXT,
                obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (waifu_id) REFERENCES waifus (id) ON DELETE CASCADE,
                INDEX idx_user_id (user_id),
                INDEX idx_waifu_id (waifu_id)
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
                type VARCHAR(50) NOT NULL,
                target_count INT NOT NULL,
                reward_type VARCHAR(50) NOT NULL,
                reward_amount INT NOT NULL,
                difficulty VARCHAR(20) DEFAULT 'easy',
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
                date DATE,
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
                event_type VARCHAR(50) NOT NULL,
                bonus_conditions TEXT,
                is_active BOOLEAN DEFAULT TRUE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        )

        # Shop items table
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS shop_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price INT NOT NULL,
                category VARCHAR(50) NOT NULL,
                item_type VARCHAR(50) NOT NULL,
                item_data TEXT,
                effects TEXT,
                stock_limit INT DEFAULT -1,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_category (category),
                INDEX idx_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        )

        # User purchases table
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_purchases (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                shop_item_id INT NOT NULL,
                quantity INT DEFAULT 1,
                total_cost INT NOT NULL,
                currency_type VARCHAR(50) DEFAULT 'quartzs',
                transaction_status VARCHAR(50) DEFAULT 'completed',
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_purchased_at (purchased_at),
                FOREIGN KEY (shop_item_id) REFERENCES shop_items (id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        )

        # User inventory table
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_inventory (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                item_name VARCHAR(255) NOT NULL,
                item_type VARCHAR(50) NOT NULL,
                quantity INT DEFAULT 1,
                metadata TEXT,
                effects TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                expires_at TIMESTAMP NULL,
                acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_item_type (item_type),
                INDEX idx_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        )

        # User character shards table (for new star system)
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_character_shards (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                waifu_id INT NOT NULL,
                shard_count INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (waifu_id) REFERENCES waifus(id) ON DELETE CASCADE,
                UNIQUE KEY unique_user_waifu (user_id, waifu_id),
                INDEX idx_user_shards (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        )

    # User-related methods
    async def get_or_create_user(self, discord_id: str) -> Dict[str, Any]:
        """Get user from database or create if doesn't exist."""
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

    # Waifu-related methods
    async def add_waifu(self, waifu_data: Dict[str, Any]) -> int:
        """Add a new waifu to the database."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO waifus (
                        name, series, genre, element, rarity, image_url, mal_id,
                        base_stats, birthday, favorite_gifts, special_dialogue
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        waifu_data["name"],
                        waifu_data["series"],
                        waifu_data.get("genre", "Unknown"),
                        waifu_data.get("element"),
                        waifu_data["rarity"],
                        waifu_data.get("image_url"),
                        waifu_data.get("mal_id"),
                        json.dumps(waifu_data.get("base_stats", {})),
                        waifu_data.get("birthday"),
                        json.dumps(waifu_data.get("favorite_gifts", [])),
                        json.dumps(waifu_data.get("special_dialogue", {})),
                    ),
                )
                await conn.commit()
                return cursor.lastrowid or 0

    async def get_waifu_by_mal_id(self, mal_id: int) -> Optional[Dict[str, Any]]:
        """Get a waifu by MAL ID."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM waifus WHERE mal_id = %s", (mal_id,)
                )
                row = await cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "name": row[1],
                        "series": row[2],
                        "genre": row[3],
                        "element": row[4],
                        "rarity": row[5],
                        "image_url": row[6],
                        "mal_id": row[7],
                        "base_stats": json.loads(row[8]) if row[8] else {},
                        "birthday": row[9],
                        "favorite_gifts": json.loads(row[10]) if row[10] else [],
                        "special_dialogue": json.loads(row[11]) if row[11] else {},
                        "created_at": row[12],
                    }
                return None

    async def test_connection(self) -> bool:
        """Test database connection."""
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    return True
        except Exception:
            return False

    async def get_waifus_by_rarity(self, rarity: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get waifus by rarity level."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    "SELECT * FROM waifus WHERE rarity = %s ORDER BY RAND() LIMIT %s",
                    (rarity, limit),
                )
                return await cursor.fetchall()

    async def get_user_collection(self, discord_id: str) -> List[Dict[str, Any]]:
        """Get all waifus in a user's collection."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT uw.*, w.name, w.series, w.rarity, w.image_url, u.discord_id
                    FROM user_waifus uw
                    JOIN waifus w ON uw.waifu_id = w.id
                    JOIN users u ON uw.user_id = u.id
                    WHERE u.discord_id = %s
                    ORDER BY uw.obtained_at DESC
                """,
                    (discord_id,),
                )
                return await cursor.fetchall()

    async def add_waifu_to_user(self, discord_id: str, waifu_id: int) -> Dict[str, Any]:
        """Add a waifu to a user's collection, handling constellation system."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # Get user ID
                await cursor.execute("SELECT id FROM users WHERE discord_id = %s", (discord_id,))
                user_row = await cursor.fetchone()
                if not user_row:
                    raise ValueError(f"User {discord_id} not found")
                user_id = user_row["id"]

                # Check if user already has this waifu
                await cursor.execute(
                    "SELECT * FROM user_waifus WHERE user_id = %s AND waifu_id = %s",
                    (user_id, waifu_id),
                )
                existing = await cursor.fetchone()

                if existing:
                    # For backwards compatibility with old constellation system
                    # But we don't update constellation_level anymore with new star system
                    # The star system handles duplicates via shards in WaifuService
                    
                    # Get waifu details for quartzs calculation (legacy system)
                    await cursor.execute("SELECT rarity FROM waifus WHERE id = %s", (waifu_id,))
                    waifu_row = await cursor.fetchone()
                    if waifu_row and waifu_row["rarity"] >= 3:  # 3★+ gives quartzs (legacy)
                        quartzs_reward = (waifu_row["rarity"] - 2) * 5  # 3★=5, 4★=10, 5★=15 (for upgraded chars)
                        await self.update_user_quartzs(discord_id, quartzs_reward)

                    # Return existing entry without constellation update
                    await cursor.execute(
                        """
                        SELECT uw.*, w.name, w.series, w.rarity, w.image_url
                        FROM user_waifus uw
                        JOIN waifus w ON uw.waifu_id = w.id
                        WHERE uw.id = %s
                    """,
                        (existing["id"],),
                    )
                    return await cursor.fetchone()
                else:
                    # Add new waifu
                    await cursor.execute(
                        """
                        INSERT INTO user_waifus (user_id, waifu_id, obtained_at)
                        VALUES (%s, %s, %s)
                    """,
                        (user_id, waifu_id, datetime.now()),
                    )
                    await conn.commit()
                    new_id = cursor.lastrowid

                    # Return new entry
                    await cursor.execute(
                        """
                        SELECT uw.*, w.name, w.series, w.rarity, w.image_url
                        FROM user_waifus uw
                        JOIN waifus w ON uw.waifu_id = w.id
                        WHERE uw.id = %s
                    """,
                        (new_id,),
                    )
                    return await cursor.fetchone()

    # Currency methods
    async def update_user_crystals(self, discord_id: str, amount: int) -> bool:
        """Update user's sakura crystals."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE users SET sakura_crystals = sakura_crystals + %s WHERE discord_id = %s",
                    (amount, discord_id),
                )
                await conn.commit()
                return cursor.rowcount > 0

    async def update_user_quartzs(self, discord_id: str, amount: int) -> bool:
        """Update user's quartzs."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE users SET quartzs = quartzs + %s WHERE discord_id = %s",
                    (amount, discord_id),
                )
                await conn.commit()
                return cursor.rowcount > 0

    # Search methods
    async def search_waifus(self, name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for waifus by name."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = "SELECT * FROM waifus WHERE name LIKE %s OR series LIKE %s"
                params = (f"%{name}%", f"%{name}%")
                
                if limit:
                    query += " LIMIT %s"
                    params = params + (limit,)
                
                await cursor.execute(query, params)
                return await cursor.fetchall()

    # Pity system
    async def update_pity_counter(self, discord_id: str, reset: bool = False) -> bool:
        """Update user's pity counter."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if reset:
                    await cursor.execute(
                        "UPDATE users SET pity_counter = 0 WHERE discord_id = %s",
                        (discord_id,),
                    )
                else:
                    await cursor.execute(
                        "UPDATE users SET pity_counter = pity_counter + 1 WHERE discord_id = %s",
                        (discord_id,),
                    )
                await conn.commit()
                return cursor.rowcount > 0

    # Daily system
    async def update_daily_reset(self, discord_id: str, timestamp: int, login_streak: int = 0) -> bool:
        """Update user's daily reset timestamp."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE users SET last_daily_reset = %s WHERE discord_id = %s",
                    (timestamp, discord_id),
                )
                await conn.commit()
                return cursor.rowcount > 0

    # Account management
    async def reset_user_account(self, discord_id: str) -> bool:
        """Reset a user's account to default state."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    # Reset user stats
                    await cursor.execute(
                        """UPDATE users SET 
                           sakura_crystals = 2000, 
                           quartzs = 0,
                           pity_counter = 0, 
                           last_daily_reset = 0,
                           collector_rank = 1
                           WHERE discord_id = %s""",
                        (discord_id,)
                    )

                    # Get user ID
                    await cursor.execute("SELECT id FROM users WHERE discord_id = %s", (discord_id,))
                    user_row = await cursor.fetchone()
                    if user_row:
                        user_id = user_row[0]
                        
                        # Clear collections
                        await cursor.execute("DELETE FROM user_waifus WHERE user_id = %s", (user_id,))
                        await cursor.execute("DELETE FROM conversations WHERE user_id = %s", (user_id,))
                        await cursor.execute("DELETE FROM user_mission_progress WHERE user_id = %s", (user_id,))
                        # Shop related deletions - TODO: Restore when shop is re-implemented
                        # await cursor.execute("DELETE FROM user_purchases WHERE user_id = %s", (user_id,))
                        # await cursor.execute("DELETE FROM user_inventory WHERE user_id = %s", (user_id,))

                    await conn.commit()
                    return True
                except Exception as e:
                    await conn.rollback()
                    self.logger.error(f"Error resetting user account {discord_id}: {e}")
                    return False

    async def delete_user_account(self, discord_id: str) -> bool:
        """Permanently delete a user's account."""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    # Get user ID first
                    await cursor.execute("SELECT id FROM users WHERE discord_id = %s", (discord_id,))
                    user_row = await cursor.fetchone()
                    if user_row:
                        user_id = user_row[0]
                        
                        # Delete all related data (foreign keys will cascade)
                        await cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))

                    await conn.commit()
                    return True
                except Exception as e:
                    await conn.rollback()
                    self.logger.error(f"Error deleting user account {discord_id}: {e}")
                    return False

    # Shop methods - TODO: Implement shop functionality
    async def get_shop_items(self, category: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get shop items with optional filtering."""
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    query = "SELECT * FROM shop_items WHERE 1=1"
                    params = []
                    
                    if active_only:
                        query += " AND is_active = %s"
                        params.append(True)
                    
                    if category:
                        query += " AND category = %s"
                        params.append(category)
                    
                    query += " ORDER BY category, name"
                    
                    await cursor.execute(query, params)
                    items = await cursor.fetchall()
                    
                    # Convert items to proper format
                    result = []
                    for item in items:
                        item_dict = dict(item)
                        # Parse JSON fields
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
        """Get a specific shop item by ID."""
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("SELECT * FROM shop_items WHERE id = %s", (item_id,))
                    item = await cursor.fetchone()
                    
                    if item:
                        item_dict = dict(item)
                        # Parse JSON fields
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
        """Add a new item to the shop."""
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    query = """
                    INSERT INTO shop_items (name, description, price, category, item_type, item_data, effects, stock_limit, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    params = (
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
                    
                    await cursor.execute(query, params)
                    await conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Error adding shop item: {e}")
            return 0

    async def purchase_item(self, user_id: str, item_id: int, quantity: int = 1) -> bool:
        """Purchase an item from the shop."""
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Start transaction
                    await conn.begin()
                    
                    try:
                        # Get item details
                        await cursor.execute("SELECT * FROM shop_items WHERE id = %s AND is_active = TRUE", (item_id,))
                        item = await cursor.fetchone()
                        
                        if not item:
                            await conn.rollback()
                            return False
                        
                        # Calculate total cost (shop uses quartzs)
                        total_cost = item[3] * quantity  # price is at index 3
                        
                        # Check user's quartzs
                        await cursor.execute("SELECT quartzs FROM users WHERE discord_id = %s", (user_id,))
                        user_result = await cursor.fetchone()
                        
                        if not user_result or user_result[0] < total_cost:
                            await conn.rollback()
                            return False
                        
                        # Deduct quartzs
                        new_balance = user_result[0] - total_cost
                        await cursor.execute("UPDATE users SET quartzs = %s WHERE discord_id = %s", (new_balance, user_id))
                        
                        # Record purchase
                        await cursor.execute("""
                            INSERT INTO user_purchases (user_id, shop_item_id, quantity, total_cost, currency_type)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (user_id, item_id, quantity, total_cost, 'quartzs'))
                        
                        # Add to inventory
                        await cursor.execute("""
                            INSERT INTO user_inventory (user_id, item_name, item_type, quantity, metadata, effects)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (user_id, item[1], item[5], quantity, item[6], item[7]))  # name, item_type, item_data, effects
                        
                        await conn.commit()
                        return True
                        
                    except Exception as e:
                        await conn.rollback()
                        self.logger.error(f"Error in purchase transaction: {e}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error purchasing item: {e}")
            return False

    async def get_user_inventory(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's inventory."""
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("""
                        SELECT * FROM user_inventory 
                        WHERE user_id = %s 
                        ORDER BY acquired_at DESC
                    """, (user_id,))
                    
                    items = await cursor.fetchall()
                    
                    # Convert items to proper format
                    result = []
                    for item in items:
                        item_dict = dict(item)
                        # Parse JSON fields
                        if item_dict.get('metadata'):
                            try:
                                item_dict['metadata'] = json.loads(item_dict['metadata'])
                            except:
                                item_dict['metadata'] = {}
                        if item_dict.get('effects'):
                            try:
                                item_dict['effects'] = json.loads(item_dict['effects'])
                            except:
                                item_dict['effects'] = {}
                        result.append(item_dict)
                    
                    return result
                    
        except Exception as e:
            self.logger.error(f"Error getting user inventory: {e}")
            return []

    async def get_user_purchase_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's purchase history."""
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("""
                        SELECT p.*, s.name, s.description 
                        FROM user_purchases p
                        JOIN shop_items s ON p.shop_item_id = s.id
                        WHERE p.user_id = %s 
                        ORDER BY p.purchased_at DESC 
                        LIMIT %s
                    """, (user_id, limit))
                    
                    purchases = await cursor.fetchall()
                    return [dict(purchase) for purchase in purchases]
                    
        except Exception as e:
            self.logger.error(f"Error getting purchase history: {e}")
            return []

    async def use_inventory_item(self, user_id: str, item_id: int, quantity: int = 1) -> bool:
        """Use an item from user's inventory."""
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Start transaction
                    await conn.begin()
                    
                    try:
                        # Check if user has the item
                        await cursor.execute("""
                            SELECT * FROM user_inventory 
                            WHERE user_id = %s AND id = %s AND quantity >= %s AND is_active = TRUE
                        """, (user_id, item_id, quantity))
                        
                        item = await cursor.fetchone()
                        if not item:
                            await conn.rollback()
                            return False
                        
                        # Reduce quantity or remove item
                        new_quantity = item[5] - quantity  # quantity is at index 5
                        
                        if new_quantity <= 0:
                            # Remove item completely
                            await cursor.execute("DELETE FROM user_inventory WHERE id = %s", (item_id,))
                        else:
                            # Update quantity
                            await cursor.execute("UPDATE user_inventory SET quantity = %s WHERE id = %s", (new_quantity, item_id))
                        
                        await conn.commit()
                        return True
                        
                    except Exception as e:
                        await conn.rollback()
                        self.logger.error(f"Error in use item transaction: {e}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error using inventory item: {e}")
            return False

    async def add_crystals(self, user_id: str, amount: int) -> bool:
        """Add crystals to user account."""
        return await self.update_user_crystals(user_id, amount)

    async def unlock_feature(self, user_id: str, feature: str) -> bool:
        """Unlock a feature for a user."""
        # TODO: Implement feature unlocking system
        self.logger.info(f"Unlocking feature '{feature}' for user {user_id}")
        return True

    async def increase_collection_limit(self, user_id: str, increase: int) -> bool:
        """Increase user's collection limit."""
        # TODO: Implement collection limit system
        self.logger.info(f"Increasing collection limit by {increase} for user {user_id}")
        return True

    async def apply_user_boost(self, user_id: str, boost_type: str, multiplier: float, duration_hours: int) -> bool:
        """Apply a temporary boost to user."""
        # TODO: Implement boost system
        self.logger.info(f"Applying {boost_type} boost ({multiplier}x) for {duration_hours}h to user {user_id}")
        return True

    async def unlock_cosmetic(self, user_id: str, cosmetic_type: str, effects: dict) -> bool:
        """Unlock a cosmetic item for user."""
        # TODO: Implement cosmetic system
        self.logger.info(f"Unlocking {cosmetic_type} cosmetic for user {user_id}: {effects}")
        return True
