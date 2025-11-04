# Geminya Database Technical Documentation

## Table of Contents
1. [Overview](#overview)
2. [Database Architecture](#database-architecture)
3. [Core Database Schema](#core-database-schema)
4. [Database Service Implementation](#database-service-implementation)
5. [Connection Management](#connection-management)
6. [Table Structure and Relationships](#table-structure-and-relationships)
7. [Data Models and Business Logic](#data-models-and-business-logic)
8. [Performance Considerations](#performance-considerations)
9. [Migration and Maintenance](#migration-and-maintenance)
10. [Development and Deployment](#development-and-deployment)

## Overview

The Geminya Discord bot uses a **PostgreSQL database** as its primary data store, designed to support a comprehensive waifu collection and expedition game system. The database handles user management, character collections, equipment systems, expeditions, shop transactions, and social features.

### Key Features
- **PostgreSQL-only implementation** with asyncpg for high-performance async operations
- **Connection pooling** for efficient database resource management
- **Transactional integrity** for complex operations
- **Comprehensive indexing** for optimized query performance
- **Modular schema design** supporting multiple game systems

### Technology Stack
- **Database**: PostgreSQL 12+
- **Python ORM**: asyncpg (direct SQL with connection pooling)
- **Connection Pool**: asyncpg built-in pooling (5-20 connections)
- **Migration Tool**: Custom schema creation in `_create_tables_postgres()`

## Database Architecture

### Connection Strategy
```python
# Connection pool configuration
self.connection_pool = await asyncpg.create_pool(
    host=self.pg_config["host"],
    port=self.pg_config["port"],
    user=self.pg_config["user"],
    password=self.pg_config["password"],
    database=self.pg_config["database"],
    min_size=5,
    max_size=20,
)
```

### Service Architecture
The database is managed through a single `DatabaseService` class that:
- Initializes connection pools
- Creates and manages all tables
- Provides high-level business logic methods
- Handles transactions and error management
- Supports concurrent operations through async/await

## Core Database Schema

### 1. User Management System

#### `users` Table
```sql
CREATE TABLE users (
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
```

**Purpose**: Core user profile and game currency management
- `discord_id`: Unique Discord user identifier
- `sakura_crystals`: Primary game currency for gacha pulls
- `quartzs`: Secondary currency for shop purchases
- `daphine`: Premium currency for character awakening
- `pity_counter`: Gacha pity system tracking

### 2. Character and Collection System

#### `series` Table
```sql
CREATE TABLE series (
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
```

**Purpose**: Anime/manga series metadata imported from external sources

#### `waifus` Table
```sql
CREATE TABLE waifus (
    waifu_id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    series_id INTEGER REFERENCES series(series_id),
    series VARCHAR(255) NOT NULL,
    genre VARCHAR(100) NOT NULL,
    rarity INTEGER NOT NULL CHECK (rarity >= 1 AND rarity <= 3),
    image_url TEXT,
    about TEXT,
    stats TEXT,                    -- JSON: battle statistics
    elemental_type TEXT,           -- JSON: elemental affinities
    archetype TEXT,                -- Character role/class
    potency TEXT,                  -- JSON: ability potency
    elemental_resistances TEXT,    -- JSON: damage resistances
    birthday DATE,
    favorite_gifts TEXT,           -- JSON: gift preferences
    special_dialogue TEXT,         -- JSON: character interactions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Character definitions with game mechanics and metadata
- Supports rarities 1-3 (★, ★★, ★★★)
- JSON fields store complex game data
- Denormalized `series` field for query optimization

#### `user_waifus` Table
```sql
CREATE TABLE user_waifus (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    waifu_id INTEGER REFERENCES waifus(waifu_id) ON DELETE CASCADE,
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
```

**Purpose**: User's character collection with progression tracking
- **Star System**: Character power progression (1-6 stars)
- **Constellation**: Duplicate character bonuses
- **Social Features**: Mood, conversations, customization
- **Awakening**: Premium character enhancement

### 3. Equipment System

#### `equipment` Table
```sql
CREATE TABLE equipment (
    id SERIAL PRIMARY KEY,
    discord_id VARCHAR(100) REFERENCES users(discord_id) ON DELETE CASCADE,
    main_effect TEXT NOT NULL,          -- JSON: primary equipment effect
    unlocked_sub_slots INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `equipment_sub_slots` Table
```sql
CREATE TABLE equipment_sub_slots (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER REFERENCES equipment(id) ON DELETE CASCADE,
    slot_index INTEGER CHECK (slot_index >= 1 AND slot_index <= 5),
    effect TEXT,                        -- JSON: slot effect
    is_unlocked BOOLEAN DEFAULT FALSE
);
```

**Purpose**: Equipment system with main effects and unlockable sub-slots
- Up to 5 sub-slots per equipment piece
- Equipment can be consumed to unlock new slots on other equipment
- User limit: 20 equipment pieces per user (`MAX_EQUIPMENT_PER_USER`)

### 4. Expedition System

#### `user_expeditions` Table
```sql
CREATE TABLE user_expeditions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    expedition_name VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    difficulty VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'in_progress',
    duration_hours FLOAT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    rewards_claimed BOOLEAN DEFAULT FALSE,
    expedition_data TEXT DEFAULT '{}',   -- JSON: expedition configuration
    final_results TEXT NULL,            -- JSON: completion results
    equipped_equipment_id INTEGER REFERENCES equipment(id)
);
```

#### `expedition_participants` Table
```sql
CREATE TABLE expedition_participants (
    id SERIAL PRIMARY KEY,
    expedition_id INTEGER REFERENCES user_expeditions(id) ON DELETE CASCADE,
    user_waifu_id INTEGER REFERENCES user_waifus(id) ON DELETE CASCADE,
    position_in_party INTEGER NOT NULL,
    star_level_used INTEGER NOT NULL,
    final_hp INTEGER DEFAULT NULL,
    final_mp INTEGER DEFAULT NULL,
    UNIQUE(expedition_id, position_in_party)
);
```

#### `expedition_logs` Table
```sql
CREATE TABLE expedition_logs (
    id SERIAL PRIMARY KEY,
    expedition_id INTEGER REFERENCES user_expeditions(id) ON DELETE CASCADE,
    log_type VARCHAR(50) NOT NULL,
    encounter_number INTEGER NULL,
    message TEXT NOT NULL,
    data TEXT DEFAULT '{}',             -- JSON: log metadata
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Complete expedition/adventure system
- **Party Management**: Multiple characters per expedition
- **Equipment Integration**: Equipment effects during expeditions
- **Detailed Logging**: Battle encounters and events
- **Resource Management**: Characters locked during expeditions

### 5. Economy and Shop System

#### `shop_items` Table
```sql
CREATE TABLE shop_items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price INTEGER NOT NULL,
    category VARCHAR(50) NOT NULL,
    item_type VARCHAR(50) NOT NULL,
    item_data TEXT,                     -- JSON: item configuration
    effects TEXT,                       -- JSON: item effects
    stock_limit INTEGER DEFAULT -1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `user_purchases` Table
```sql
CREATE TABLE user_purchases (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    shop_item_id INTEGER REFERENCES shop_items(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 1,
    total_cost INTEGER NOT NULL,
    currency_type VARCHAR(50) DEFAULT 'quartzs',
    transaction_status VARCHAR(50) DEFAULT 'completed',
    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `user_inventory` Table
```sql
CREATE TABLE user_inventory (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    item_type VARCHAR(50) NOT NULL,
    quantity INTEGER DEFAULT 1,
    metadata TEXT,                      -- JSON: item metadata
    effects TEXT,                       -- JSON: item effects
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP NULL,
    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6. Gacha and Banner System

#### `banners` Table
```sql
CREATE TABLE banners (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,          -- 'rate-up' or 'limited'
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    series_ids TEXT                     -- JSON: featured series
);
```

#### `banner_items` Table
```sql
CREATE TABLE banner_items (
    id SERIAL PRIMARY KEY,
    banner_id INTEGER REFERENCES banners(id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES waifus(waifu_id) ON DELETE CASCADE,
    rate_up BOOLEAN DEFAULT FALSE,
    drop_rate FLOAT DEFAULT NULL
);
```

### 7. Daily Missions and Events

#### `daily_missions` Table
```sql
CREATE TABLE daily_missions (
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
```

#### `user_mission_progress` Table
```sql
CREATE TABLE user_mission_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    mission_id INTEGER REFERENCES daily_missions(id) ON DELETE CASCADE,
    current_progress INTEGER DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    claimed BOOLEAN DEFAULT FALSE,
    date DATE,
    UNIQUE (user_id, mission_id, date)
);
```

### 8. Gift Code System

#### `gift_codes` Table
```sql
CREATE TABLE gift_codes (
    code TEXT PRIMARY KEY,
    reward_type TEXT,
    reward_value INT,
    is_active BOOLEAN,
    usage_limit INT,
    created_at TIMESTAMP
);
```

#### `gift_code_redemptions` Table
```sql
CREATE TABLE gift_code_redemptions (
    user_id VARCHAR(100) REFERENCES users(discord_id) ON DELETE CASCADE,
    code TEXT REFERENCES gift_codes(code) ON DELETE CASCADE,
    redeemed_at TIMESTAMP,
    PRIMARY KEY (user_id, code)
);
```

### 9. Social Features

#### `conversations` Table
```sql
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    waifu_id INTEGER REFERENCES waifus(waifu_id) ON DELETE CASCADE,
    user_message TEXT NOT NULL,
    waifu_response TEXT NOT NULL,
    mood_change INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Database Service Implementation

### Core Service Class
```python
class DatabaseService:
    def __init__(self, config: "Config"):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.connection_pool = None
        self.pg_config = config.get_postgres_config()
```

### Key Design Patterns

#### 1. Connection Pool Management
```python
async def initialize(self):
    self.connection_pool = await asyncpg.create_pool(
        host=self.pg_config["host"],
        port=self.pg_config["port"],
        user=self.pg_config["user"],
        password=self.pg_config["password"],
        database=self.pg_config["database"],
        min_size=5,
        max_size=20,
    )
```

#### 2. Transaction Safety
```python
async with self.connection_pool.acquire() as conn:
    async with conn.transaction():
        # Atomic operations here
        result = await conn.execute(query, *params)
        return result
```

#### 3. JSON Field Parsing
```python
def _parse_waifu_json_fields(self, waifu: dict) -> dict:
    json_fields = [
        'stats', 'elemental_type', 'potency', 'elemental_resistances', 
        'favorite_gifts', 'special_dialogue'
    ]
    for field in json_fields:
        if field in waifu and isinstance(waifu[field], str):
            try:
                waifu[field] = json.loads(waifu[field])
            except json.JSONDecodeError:
                waifu[field] = {}
    return waifu
```

### Critical Operations

#### User Management
- `get_or_create_user()`: Atomic user creation
- `update_user_crystals()`: Currency transactions
- `awaken_user_waifu()`: Complex character upgrades

#### Collection Management
- `add_waifu_to_user()`: Handles constellation system
- `batch_update_new_waifus_star_and_shards()`: Bulk operations
- `upgrade_character_star_transaction()`: Star level progression

#### Expedition System
- `create_expedition()`: Party setup with conflict checking
- `update_expedition_status()`: Status transitions
- `distribute_loot_rewards()`: Complex reward distribution

## Performance Considerations

### Indexing Strategy
```sql
-- User lookups
CREATE INDEX idx_discord_id ON users(discord_id);

-- Collection queries
CREATE INDEX idx_user_id ON user_waifus(user_id);
CREATE INDEX idx_waifu_id ON user_waifus(waifu_id);

-- Expedition performance
CREATE INDEX idx_user_expeditions_user_id ON user_expeditions(user_id);
CREATE INDEX idx_user_expeditions_status ON user_expeditions(status);

-- Equipment queries
CREATE INDEX idx_equipment_discord_id ON equipment(discord_id);
```

### Query Optimization Patterns

#### 1. Bulk Operations
```python
async def add_waifus_to_user_batch(self, discord_id: str, waifu_ids: List[int]):
    # Single query for multiple insertions
    query = """
        INSERT INTO user_waifus (user_id, waifu_id, current_star_level, character_shards)
        SELECT $1, unnest($2::int[]), unnest($3::int[]), unnest($4::int[])
        ON CONFLICT (user_id, waifu_id) DO UPDATE SET 
            constellation_level = user_waifus.constellation_level + 1,
            character_shards = user_waifus.character_shards + EXCLUDED.character_shards
    """
```

#### 2. Efficient Joins
```python
# Optimized user collection query with series information
query = """
    SELECT uw.*, w.name, w.series, w.rarity, w.image_url, w.stats
    FROM user_waifus uw
    JOIN waifus w ON uw.waifu_id = w.waifu_id
    WHERE uw.user_id = $1
    ORDER BY w.rarity DESC, w.name ASC
"""
```

#### 3. Conflict Resolution
```python
# Equipment availability checking
query = """
    SELECT user_waifu_id FROM expedition_participants ep
    JOIN user_expeditions ue ON ep.expedition_id = ue.id
    WHERE ue.user_id = $1 AND ue.status = 'in_progress'
    AND ep.user_waifu_id = ANY($2)
"""
```

## Migration and Maintenance

### Schema Initialization
The database schema is created through the `_create_tables_postgres()` method:

```python
async def _create_tables_postgres(self, conn):
    # Creates all tables with proper foreign keys and constraints
    # Includes all indexes for optimal performance
    # Handles cascading deletes appropriately
```

### Database Reset Utilities
```python
# Complete database reset (reset_database_star_system.py)
async def run_database_reset():
    # Drops all tables and recreates schema
    # Used for development and major migrations
```

### Data Import Tools
```python
# Character data import (upload_to_postgres.py)
class PostgresUploader:
    async def upload_series_and_characters(self):
        # Imports anime series and character data
        # Handles JSON field parsing and validation
```

## Development and Deployment

### Configuration Management
Database connection configured through:
- `secrets.json`: Database credentials
- `config.yml`: Application settings
- Environment variables: Docker/production overrides

```python
pg_config = {
    'host': secrets.get('POSTGRES_HOST', 'localhost'),
    'port': int(secrets.get('POSTGRES_PORT', 5432)),
    'user': secrets.get('POSTGRES_USER'),
    'password': secrets.get('POSTGRES_PASSWORD'),
    'database': secrets.get('POSTGRES_DATABASE'),
}
```

### Testing and Quality Assurance

#### Connection Testing
```python
async def test_connection(self) -> bool:
    try:
        async with self.connection_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception:
        return False
```

#### Transaction Rollback
All critical operations use transactions to ensure data consistency:
```python
async with conn.transaction():
    # Multiple related operations
    # Automatic rollback on any exception
```

### Deployment Considerations

1. **Connection Limits**: Pool size (5-20) configured for expected load
2. **Memory Usage**: JSON field parsing balanced with query efficiency  
3. **Backup Strategy**: Regular PostgreSQL dumps recommended
4. **Monitoring**: Connection pool utilization and query performance
5. **Scaling**: Read replicas can be added for read-heavy operations

### Security Features

1. **SQL Injection Prevention**: Parameterized queries throughout
2. **Cascade Deletes**: Proper cleanup of related data
3. **Constraint Validation**: Database-level data integrity
4. **Connection Security**: SSL and credential management

## Conclusion

The Geminya database represents a comprehensive PostgreSQL implementation supporting a complex multi-feature Discord bot. The design emphasizes:

- **Performance**: Connection pooling, efficient indexing, bulk operations
- **Reliability**: Transaction safety, constraint validation, error handling
- **Scalability**: Modular design, optimized queries, connection management
- **Maintainability**: Clear schema design, comprehensive documentation, migration tools

The system successfully handles the complex requirements of a gaming bot with user management, character collection, equipment systems, expeditions, and social features while maintaining high performance and data integrity.