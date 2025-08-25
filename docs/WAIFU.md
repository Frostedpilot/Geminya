# 🌸 No Waifu No Laifu (NWNL) Academy: Complete System Documentation 🌸

Welcome to **NWNL Academy** - a comprehensive waifu collection system with gacha mechanics, automatic star progression, and academy management built for Discord!

## 📋 **Table of Contents**

1. [System Overview](#system-overview)
2. [Architecture & Services](#architecture--services)
3. [Database Schema](#database-schema)
4. [Star System & Gacha Mechanics](#star-system--gacha-mechanics)
5. [Currency System](#currency-system)
6. [Academy System](#academy-system)
7. [Shop System](#shop-system)
8. [Command Reference](#command-reference)
9. [Service Layer Documentation](#service-layer-documentation)
10. [Development Guide](#development-guide)

---

## 🎯 **System Overview**

NWNL Academy is a Discord bot-based gacha collection system where users can:
- **Summon waifus** using Sakura Crystals through a 1★-3★ gacha system
- **Automatically upgrade** characters to 4★ and 5★ using shards from duplicates
- **Manage their academy** with ranks, daily rewards, and guarantee tickets
- **Track collection progress** with detailed statistics and power calculations
- **Purchase guarantee tickets** from the shop using premium currency

### **Core Design Philosophy**
- **Simplified gacha pulls:** Only 1★-3★ from direct summons
- **Shard-based progression:** 4★ and 5★ achieved through duplicate collection
- **Automatic upgrades:** No manual star upgrade actions needed
- **Premium progression:** Excess shards convert to premium currency
- **Focused shop:** Only essential items (guarantee tickets)

---

## 🏗️ **Architecture & Services**

### **Service Container Pattern**
The system uses dependency injection through `ServiceContainer` (`services/container.py`):

```python
class ServiceContainer:
    """Container for managing all bot services and dependencies."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger_manager = setup_logging(config)
        self.error_handler = ErrorHandler(config, self.logger_manager.get_error_logger())
        self.state_manager = StateManager(config, self.logger_manager.get_logger("state"))
        self.llm_manager = LLMManager(config, self.state_manager, self.logger_manager.get_ai_logger())
        self.mcp_client = MCPClientManager(config, self.state_manager, self.llm_manager)
        
        # Core NWNL services
        self.database = DatabaseService(config)
        self.waifu_service = WaifuService(self.database)
        self.command_queue = CommandQueueService()
```

### **Command Architecture**
All NWNL commands inherit from `BaseCommand` (`cogs/base_command.py`):

```python
class BaseCommand(commands.Cog):
    """Base class for all command cogs with service dependencies."""
    
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        self.bot = bot
        self.services = services
        self.config = services.config
        self.state_manager = services.state_manager
        self.ai_service = services.ai_service
        self.logger = services.get_logger(self.__class__.__name__)
    
    async def queue_command(self, ctx: commands.Context, command_impl, *args, **kwargs):
        """Queue a command for sequential execution per user."""
        command_queue = self.services.get_command_queue()
        return await command_queue.enqueue_command(
            str(ctx.author.id), command_impl, ctx, *args, **kwargs
        )
```

### **Command Cogs Structure**
1. **WaifuSummonCog** (`cogs/commands/waifu_summon.py`)
   - Single and multi-summons
   - Collection viewing
   - Character profiles
   
2. **WaifuAcademyCog** (`cogs/commands/waifu_academy.py`)
   - Academy status and stats
   - Daily rewards
   - Account management
   
3. **ShopCog** (`cogs/commands/shop.py`)
   - Shop browsing and purchases
   - Inventory management
   - Item usage (guarantee tickets)

---

## 🗄️ **Database Schema**

### **Core Tables (PostgreSQL)**

#### `banners` - Gacha Banners
```sql
CREATE TABLE IF NOT EXISTS banners (
    id SERIAL PRIMARY KEY,
    mal_id INTEGER,
    title VARCHAR(255) NOT NULL,
    title_english VARCHAR(255),
    image_url TEXT
);
```

#### `users` - User Accounts
```sql
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    discord_id VARCHAR(100) UNIQUE NOT NULL,
    academy_name VARCHAR(255),
    collector_rank INTEGER DEFAULT 1,
    sakura_crystals INTEGER DEFAULT 2000,
    quartzs INTEGER DEFAULT 0,
    pity_counter INTEGER DEFAULT 0,
    last_daily_reset BIGINT DEFAULT 0,
    selected_banner_id INTEGER REFERENCES banners(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_discord_id ON users(discord_id);
```

#### `waifus` - Character Database
```sql
CREATE TABLE IF NOT EXISTS waifus (
    waifu_id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    series VARCHAR(255) NOT NULL,
    banner_id INTEGER REFERENCES banners(id) ON DELETE SET NULL,
    genre VARCHAR(100) NOT NULL,
    element VARCHAR(50),
    rarity INTEGER NOT NULL CHECK (rarity >= 1 AND rarity <= 3),
    image_url TEXT,
    base_stats TEXT,
    birthday DATE,
    favorite_gifts TEXT,
    special_dialogue TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rarity ON waifus(rarity);
CREATE INDEX IF NOT EXISTS idx_name ON waifus(name);
CREATE INDEX IF NOT EXISTS idx_banner_id ON waifus(banner_id);
```

#### `user_waifus` - User Collections
```sql
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
```

#### `conversations` - Conversation Logs
```sql
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
```

#### `daily_missions` - Daily Missions
```sql
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
```

#### `user_mission_progress` - User Mission Progress
```sql
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
```

#### `events` - Events Table
```sql
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
```

#### `shop_items` - Shop Inventory
```sql
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
```

#### `user_purchases` - Purchase History
```sql
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
```

#### `user_inventory` - User Item Storage
```sql
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
```

---


## ⭐ **Star System & Gacha Mechanics**

### **Banner System (Server-Driven, In-Memory)**

**Banner System:**

All banners are managed server-side in memory by the `BannerManager` service. Banners are no longer stored in the database. Instead, the server defines and manages all available banners and their waifu pools at runtime.

**Banner Types:**

- **Series Banner:** The waifu pool is constructed from all characters belonging to a specific anime/series (using `series_id`).
- **Character-List Banner:** The waifu pool is a custom list of specific waifu IDs, allowing for special or event banners.

**Banner Selection:**

Each user can select their active banner (persisted in `users.selected_banner_id`). All summons use the waifu pool from the user's selected banner.

**Waifu Pools:**

- For **series banners**, the pool is dynamically built from all waifus with the matching `series_id`.
- For **character-list banners**, the pool is the explicit list of waifu IDs defined for that banner.
- All banner logic, including rate-up and pool management, is handled in memory by the server.

**BannerManager:**

- Responsible for defining, updating, and providing waifu pools for all banners.
- Supports both banner types and exposes APIs for listing banners, retrieving waifu pools, and handling rate-up logic.
- No banner data is stored in the database; only series, waifus, and user-selected banner IDs are persisted.

**Gacha Rates:**

- **Rate-up waifus:**
  - 3★: 3.5% (rate-up), 1.5% (rest)
  - 2★: 10% (rate-up), 10% (rest)
  - 1★: 35% (rate-up), 30% (rest)
- **Total per rarity:**
  - 3★: 5%
  - 2★: 20%
  - 1★: 75%
- Banner selection and rates are enforced in all summon commands via the BannerManager and WaifuService.

```python
GACHA_RATES = {
    3: {"rate_up": 3.5, "rest": 1.5},
    2: {"rate_up": 10.0, "rest": 10.0},
    1: {"rate_up": 35.0, "rest": 30.0},
}
```

### **Multi-Summon Guarantees**
- **2★ Guarantee:** Every 10x multi-summon (including those performed via `/nwnl_super_multiple_summon`) always guarantees at least one 2★ or higher. If all 10 rolls would be 1★, one is upgraded to 2★ automatically.
- **3★ Pity:** Every 50 pulls (across all banners), a 3★ is guaranteed. The pity counter resets as soon as a 3★ is pulled (naturally or via pity).

> **Technical Note:**
> The 2★ guarantee is enforced in the service layer (`WaifuService.perform_multi_summon`). This means all multi-summon commands, including super multi, always benefit from this guarantee. No additional logic is needed in command handlers.

### **Pity System**
```python
PITY_3_STAR = 50   # Guaranteed 3-star every 50 pulls
```


### **Banner Selection & Waifu Pools**

- Users can select their active banner using `/nwnl_banner_select` and view all available banners with `/nwnl_banner_list`.
- All banners are managed by the server in memory (see BannerManager). No banner data is stored in the database.
- Each banner defines its waifu pool:
  - **Series banner:** Pool is all waifus with the matching `series_id`.
  - **Character-list banner:** Pool is the explicit list of waifu IDs defined for the banner.
- Summons always use the waifu pool from the user's selected banner, with all rate-up and rarity logic enforced by the BannerManager and WaifuService.

### **Shard Rewards (From Duplicates)**
```python
SHARD_REWARDS = {
  3: 90,  # 3-star dupe = 90 shards
  2: 20,  # 2-star dupe = 20 shards
  1: 5,   # 1-star dupe = 5 shards
}
```

### **Upgrade Costs (Automatic)**
```python
UPGRADE_COSTS = {
  2: 50,   # 1→2 star: 50 shards
  3: 100,  # 2→3 star: 100 shards
  4: 150,  # 3→4 star: 150 shards
  5: 200,  # 4→5 star: 200 shards
}
```

### **Star Level Progression Flow**
1. **Initial Pull:** Character received at 1★, 2★, or 3★ rarity
2. **Duplicate Detection:** System checks if user already owns character
3. **Shard Award:** If duplicate, award shards based on original rarity
4. **Automatic Upgrade:** Check if enough shards exist for upgrades
5. **Multiple Upgrades:** Can chain multiple upgrades in single pull
6. **Quartz Conversion:** Excess shards from 5★ characters become quartz

### **Power Calculation**
Each character contributes to user power based on current star level:
```python
if current_star == 1:
  power = 100
elif current_star == 2:
  power = 250
elif current_star == 3:
  power = 500
elif current_star == 4:
  power = 1000
elif current_star >= 5:
  power = 2000 * (2 ** (current_star - 5))
```

---

## 💎 **Currency System**

### **Sakura Crystals (Primary Currency)**
- **Purpose:** Main summoning currency
- **Single summon:** 10 crystals
- **Multi-summon (10x):** 100 crystals
- **Starting amount:** 2000 crystals for new users
- **Daily rewards:** Primary source of income
- **Storage:** `users.sakura_crystals` field

### **Quartz (Premium Currency)**
- **Purpose:** Purchase guarantee tickets and premium items
- **Source:** Converting excess shards from maxed (5★) characters
- **Conversion rate:** Varies based on character rarity
- **High value:** Difficult to obtain, used for guaranteed outcomes
- **Storage:** `users.quartzs` field

### **Currency Transaction Safety**
All currency operations use PostgreSQL transactions:
```python
async with self.connection_pool.acquire() as conn:
    async with conn.transaction():
        # All currency operations here
        # Automatic rollback on error
        # Automatic commit on success
```

---

## 🏫 **Academy System**

### **Collector Ranks**
Automatic progression based on collection power and waifu count:

#### **Rank Calculation Formula**
```python
# Power requirement: 1000 × 2^(rank-1)
# Waifu requirement: 5 × rank
def get_rank_requirements(rank):
    power_required = 1000 * (2 ** (rank - 1))
    waifus_required = 5 * rank
    return power_required, waifus_required
```

#### **Rank Progression Examples**
- **Rank 1:** 1000 power, 5 waifus
- **Rank 2:** 2000 power, 10 waifus  
- **Rank 3:** 4000 power, 15 waifus
- **Rank 4:** 8000 power, 20 waifus
- **Rank 5:** 16000 power, 25 waifus

### **Daily Rewards System**
- **Cooldown:** 24-hour reset using `users.last_daily_reset` timestamp
- **Rewards:** Fixed amount of Sakura Crystals + potential bonuses
- **Streak tracking:** Consecutive claim tracking (future feature)
- **Automatic rank check:** Triggers rank-up evaluation on daily claim

### **Academy Management Features**
- **Academy naming:** Custom academy names (`users.academy_name`)
- **Statistics tracking:** Power, collection size, rank progress
- **Account reset:** Complete data wipe with confirmation
- **Account deletion:** Permanent removal with cascade delete

---

## 🛒 **Shop System**

### **Current Implementation: Guarantee Tickets Only**
The shop system is intentionally simplified to focus on the core mechanic:

#### **Guarantee Ticket Properties**
```json
{
  "item_type": "guarantee_ticket",
  "effects": {
    "guarantee_rarity": 3  // Guarantees 3★ pull
  },
  "currency_type": "quartzs",
  "price": 500  // Example price
}
```

#### **Shop Item Structure**
```python
{
    "id": int,                    # Unique item ID
    "name": str,                  # Display name
    "description": str,           # Item description
    "price": int,                 # Cost in specified currency
    "category": str,              # Item category
    "item_type": str,             # Type (guarantee_ticket)
    "item_data": json,            # Additional metadata
    "effects": json,              # Item effects definition
    "is_active": bool             # Whether item is purchasable
}
```

#### **Purchase Flow**
1. **Validation:** Check item exists and is active
2. **Requirements:** Verify user rank and currency requirements
3. **Transaction:** Deduct currency, add to inventory
4. **Logging:** Record purchase in `user_purchases` table
5. **Inventory:** Add item to `user_inventory` table

#### **Inventory Management**
- **Stacking:** Same items stack quantities
- **Expiration:** Optional expiration dates
- **Usage tracking:** Active/inactive status
- **Metadata storage:** JSON fields for flexibility

### **Guarantee Ticket Usage**
When used from inventory:
1. **Validation:** Check item exists and is active
2. **Guaranteed roll:** Perform roll with specified rarity guarantee
3. **Processing:** Use normal summon flow with guaranteed outcome
4. **Consumption:** Remove one item from inventory
5. **Result display:** Same embed format as regular summons

---

## 📋 **Command Reference**

### **Summoning & Collection Commands**

#### `/nwnl_summon` - Single Summon
- **Cost:** 10 Sakura Crystals
- **Implementation:** `WaifuSummonCog._nwnl_summon_impl()`
- **Features:**
  - Single character pull
  - Automatic star upgrades
  - Shard calculation
  - Embed result display
  - Error handling for insufficient currency

#### `/nwnl_multi_summon` - Multi Summon  
- **Cost:** 100 Sakura Crystals (10 pulls)
- **Implementation:** `WaifuSummonCog.nwnl_multi_summon()`
- **Features:**
  - **2★ Guarantee:** Always at least one 2★ or higher per 10x multi-summon
  - 3★ pity system (see above)
  - Batch processing of 10 summons
  - Summary statistics
  - Individual high-rarity embeds
  - Aggregated low-rarity summary

#### `/nwnl_super_multiple_summon` - Super Multi Summon
- **Cost:** 100 Sakura Crystals per multi (1-10 multis)
- **Implementation:** `WaifuSummonCog.nwnl_super_multiple_summon()`
- **Features:**
  - Performs multiple 10x multi-summons in a single command
  - Each multi-summon always guarantees at least one 2★ or higher
  - 3★ pity system applies across all pulls
  - Results are aggregated and summarized
  - Per-multi breakdown and legendary (3★) card info always shown

#### `/nwnl_collection [user]` - View Collection
- **Parameters:** Optional user mention
- **Implementation:** `WaifuSummonCog.nwnl_collection()`
- **Features:**
  - Star level distribution
  - Resource summary
  - Top 5 highest star characters
  - Upgradeable character count
  - Academy information display

#### `/nwnl_profile <waifu_name>` - Character Profile
- **Parameters:** Waifu name (with autocomplete)
- **Implementation:** `WaifuSummonCog.nwnl_profile()`
- **Features:**
  - Detailed character information
  - Star progression data
  - Shard counts and upgrade requirements
  - Power calculations
  - Ownership status and obtain date

### **Academy Management Commands**

#### `/nwnl_status` - Academy Status
- **Implementation:** `WaifuAcademyCog._nwnl_status_impl()`
- **Features:**
  - Current rank and progress to next rank
  - Currency balances
  - Collection statistics
  - Power calculations
  - Academy creation date

#### `/nwnl_daily` - Daily Rewards
- **Cooldown:** 24 hours
- **Implementation:** `WaifuAcademyCog._nwnl_daily_impl()`
- **Features:**
  - Crystal rewards
  - Cooldown validation
  - Streak tracking
  - Automatic rank checks

#### `/nwnl_rename_academy <name>` - Rename Academy
- **Parameters:** New academy name
- **Implementation:** `WaifuAcademyCog.nwnl_rename_academy()`
- **Features:**
  - Name validation
  - Database update
  - Confirmation message

#### `/nwnl_reset_account` - Reset Account
- **Implementation:** `WaifuAcademyCog.nwnl_reset_account()`
- **Features:**
  - Complete data reset
  - Confirmation requirement
  - Restore default values
  - Logging for safety

#### `/nwnl_delete_account` - Delete Account
- **Implementation:** `WaifuAcademyCog.nwnl_delete_account()`
- **Features:**
  - Permanent deletion
  - Cascade delete relationships
  - Final confirmation
  - Irreversible action warning

### **Shop System Commands**

#### `/nwnl_shop [category] [page]` - Browse Shop
- **Parameters:** Optional category filter, page number
- **Implementation:** `ShopCog.nwnl_shop()`
- **Features:**
  - Paginated item display
  - Category filtering
  - Currency balance display
  - Item requirement checking
  - Interactive navigation buttons

#### `/nwnl_buy <item_id> [quantity]` - Purchase Item
- **Parameters:** Item ID, optional quantity
- **Implementation:** `ShopCog.nwnl_buy()`
- **Features:**
  - Item validation
  - Currency checking
  - Rank requirement validation
  - Transaction processing
  - Inventory addition

#### `/nwnl_inventory [page]` - View Inventory
- **Parameters:** Optional page number
- **Implementation:** `ShopCog.nwnl_inventory()`
- **Features:**
  - Paginated inventory display
  - Item expiration status
  - Quantity tracking
  - Acquisition dates

#### `/nwnl_purchase_history [limit]` - Purchase History
- **Parameters:** Optional result limit
- **Implementation:** `ShopCog.nwnl_purchase_history()`
- **Features:**
  - Transaction history
  - Cost tracking
  - Date information
  - Status verification

#### `/nwnl_use_item <item_name>` - Use Item
- **Parameters:** Item name (with autocomplete)
- **Implementation:** `ShopCog.nwnl_use_item()`
- **Features:**
  - Item validation
  - Effect application
  - Guarantee ticket processing
  - Inventory consumption
  - Result display

---

## 🔧 **Service Layer Documentation**


### **BannerManager** (`services/banner_manager.py`)

#### **Overview**
The `BannerManager` is responsible for all banner logic, waifu pool management, and rate-up handling. It operates entirely in memory and is the single source of truth for all banners in the system.

#### **Banner Types**
- **Series Banner:** Pool is all waifus with a given `series_id`.
- **Character-List Banner:** Pool is a custom list of waifu IDs.

#### **Key Responsibilities**
- Define and manage all banners (no DB storage)
- Provide APIs to list banners, retrieve waifu pools, and handle rate-up logic
- Support dynamic updates and event banners

#### **Key Methods**

##### `get_all_banners() -> List[Dict]`
- Returns all banners (series and character-list types) with metadata

##### `get_banner_waifu_pool(banner_id: int) -> List[Dict]`
- Returns the waifu pool for a given banner, including rate-up info

##### `get_banner_by_id(banner_id: int) -> Dict`
- Returns metadata for a specific banner

##### `is_valid_banner(banner_id: int) -> bool`
- Checks if a banner is currently available

---

### **WaifuService** (`services/waifu_service.py`)

#### **Core Constants**
```python
class WaifuService:
  # Banner-based gacha rates for 1-3 star pulls
  GACHA_RATES = {
    3: {"rate_up": 3.5, "rest": 1.5},
    2: {"rate_up": 10.0, "rest": 10.0},
    1: {"rate_up": 35.0, "rest": 30.0},
  }
  # Pity system
  PITY_3_STAR = 50
  # Shard rewards from duplicates
  SHARD_REWARDS = {3: 90, 2: 20, 1: 5}
  # Upgrade costs
  UPGRADE_COSTS = {2: 50, 3: 100, 4: 150, 5: 200}
  # Maximum star level
  MAX_STAR_LEVEL = 5
  # Cost per summon
  SUMMON_COST = 10
```

#### **Banner Logic**
- All summon methods use the user's selected banner (from `users.selected_banner_id`).
- The waifu pool and rate-up logic are provided by the BannerManager for every summon.
- If no banner is selected, summon commands return an error.

#### **Key Methods**


##### `perform_summon(discord_id: str) -> Dict[str, Any]`
- **Purpose:** Execute single character summon
- **Process:**
  1. Validate user currency
  2. Deduct summon cost
  3. Retrieve waifu pool from BannerManager for user's selected banner
  4. Determine pull rarity (including pity)
  5. Select random character from pool (with rate-up logic)
  6. Process duplicate/new logic
  7. Apply automatic upgrades
  8. Return comprehensive result


##### `perform_multi_summon(discord_id: str) -> Dict[str, Any]`
- **Purpose:** Execute 10-character summon with guarantees
- **Process:**
  1. Validate 100 crystal cost
  2. Retrieve waifu pool from BannerManager for user's selected banner
  3. Process 10 individual summons using the pool
  4. **2★ Guarantee:** If all 10 rolls are 1★, one is upgraded to 2★ (guaranteed)
  5. 3★ pity logic (see above)
  6. Aggregate results and statistics
  7. Return batch summary

##### `_handle_summon_result(discord_id: str, waifu: Dict, pulled_rarity: int) -> Dict[str, Any]`
- **Purpose:** Process individual summon result
- **Process:**
  1. Check if user owns character
  2. Add new character or award shards
  3. Trigger automatic upgrades
  4. Handle excess shard conversion
  5. Return detailed result data

##### `_check_and_perform_auto_upgrades(discord_id: str, waifu_id: int, current_shards: int, current_star: int) -> Dict[str, Any]`
- **Purpose:** Automatically upgrade character stars
- **Process:**
  1. Check upgrade requirements
  2. Perform multiple upgrades if possible
  3. Update database with new values
  4. Convert excess shards to quartz
  5. Return upgrade summary

##### `check_and_update_rank(discord_id: str) -> int`
- **Purpose:** Evaluate and update user rank
- **Process:**
  1. Calculate total collection power
  2. Count owned waifus
  3. Determine appropriate rank
  4. Update database if rank increased
  5. Return current rank


### **DatabaseService** (`services/database.py`)

#### **Connection Management**
```python
class DatabaseService:
  def __init__(self, config: Config):
    self.config = config
    self.connection_pool = None
    self.logger = logging.getLogger(__name__)
    
  async def initialize(self):
    """Initialize PostgreSQL connection pool."""
    self.connection_pool = await asyncpg.create_pool(
      self.config.database.url,
      min_size=1,
      max_size=10
    )
```

#### **Transaction Safety**
All critical operations use transactions:
```python
async def purchase_item(self, user_id: str, item_id: int, quantity: int = 1) -> bool:
  async with self.connection_pool.acquire() as conn:
    async with conn.transaction():
      # All database operations here
      # Automatic rollback on error
      # Automatic commit on success
```

#### **Key Methods**

##### `set_user_selected_banner(discord_id: str, banner_id: int) -> None`
- **Purpose:** Set the user's selected banner
- **Features:** Persists selection in `users.selected_banner_id`

##### `get_user_selected_banner(discord_id: str) -> Optional[int]`
- **Purpose:** Get the user's currently selected banner

##### `get_or_create_user(discord_id: str) -> Dict[str, Any]`
- **Purpose:** Retrieve user or create with defaults
- **Default values:** 2000 crystals, rank 1, empty academy name

##### `add_waifu_to_user(discord_id: str, waifu_id: int) -> Dict[str, Any]`
- **Purpose:** Add character to user collection
- **Features:** Duplicate detection, star level initialization

##### `get_user_collection(discord_id: str) -> List[Dict[str, Any]]`
- **Purpose:** Retrieve user's complete collection
- **Features:** Join with waifu data, star level information

##### `get_shop_items(category: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]`
- **Purpose:** Retrieve shop inventory
- **Features:** Category filtering, active status filtering

### **Command Queue System**
```python
class CommandQueueService:
    """Ensures sequential command execution per user."""

#### `/nwnl_banner_list` - List Available Banners
- **Implementation:** `BannerCog.nwnl_banner_list()`
- **Features:**
  - Lists all banners defined in the server's BannerManager (series and character-list types)
  - Shows banner type, featured waifus, and any rate-up details
  - Indicates which banners are currently available/active

#### `/nwnl_banner_select <banner_id>` - Select Active Banner
- **Parameters:** Banner ID (with autocomplete)
- **Implementation:** `BannerCog.nwnl_banner_select()`
- **Features:**
  - Sets the user's active banner for all summons (persisted in `users.selected_banner_id`)
  - Only banners defined in the BannerManager can be selected
  - Confirmation and error handling if the banner is not available
  - All summons will use the waifu pool and rate-up logic from the selected banner
  - Error if no banner is selected

- **pull_from_mal.py**: Pulls character and anime data from MyAnimeList, outputs to characters_mal.csv and anime_mal.csv.
  - **2★ Guarantee:** Always at least one 2★ or higher per 10x multi-summon
  - 3★ pity system (see above)
  - Batch processing of 10 summons from the user's selected banner
  - Banner rate-up logic applies
  - Summary statistics
  - Individual high-rarity embeds
  - Aggregated low-rarity summary
  - Error if no banner is selected
- config.yml: Main configuration file for database and system settings.
- secrets.json: Stores sensitive database credentials.
  - Performs multiple 10x multi-summons in a single command, all from the user's selected banner
  - Each multi-summon always guarantees at least one 2★ or higher
  - 3★ pity system applies across all pulls
  - Banner rate-up logic applies
  - Results are aggregated and summarized
  - Per-multi breakdown and legendary (3★) card info always shown
  - Error if no banner is selected
2. **Use `@commands.hybrid_command` decorator**
3. **Implement through `queue_command` for user safety**
4. **Follow error handling patterns**
5. **Add comprehensive logging**

Example structure:
```python
@commands.hybrid_command(name="new_command", description="Description")
async def new_command(self, ctx: commands.Context):
    await ctx.defer()
    return await self.queue_command(ctx, self._new_command_impl)

async def _new_command_impl(self, ctx: commands.Context):
    try:
        # Implementation here
        pass
    except Exception as e:
        self.logger.error(f"Error in new_command: {e}")
        # Error response
```


### **Database Modifications**

1. **Update schema in `_create_tables_postgres()`**
2. **Add migration SQL for existing data:**
  - For new columns (e.g., `selected_banner_id`), write a migration script to add the column if it does not exist.
  - **Note:** Banners are no longer stored in the database. Only series, waifus, and user-selected banner IDs are persisted.
  - Always test migrations on a development database before production.
3. **Update relevant service methods**
4. **Test with development database**
5. **Document schema changes in both code and documentation**

### **Service Extensions**

1. **Extend `WaifuService` for game mechanics**
2. **Extend `DatabaseService` for data operations**
3. **Add new services to `ServiceContainer`**
4. **Maintain dependency injection pattern**
5. **Add comprehensive error handling**

### **Testing Patterns**

1. **Use development configuration**
2. **Test with small datasets**
3. **Verify transaction safety**
4. **Test error conditions**
5. **Validate currency calculations**

### **Configuration Management**

System uses `config.yml` for all configuration:
```yaml
database:
  url: "postgresql://user:pass@host:port/db"
  
waifu_system:
  starting_crystals: 2000
  summon_cost: 10
  
daily_rewards:
  crystal_amount: 50
```

### **Logging Strategy**

- **Service-level logging:** Each service has dedicated logger
- **Error tracking:** Comprehensive error logs with context
- **Transaction logging:** All currency operations logged
- **Performance monitoring:** Command execution timing

---

## 🚀 **Future Enhancements**

### **Planned Features**
1. **Events system:** Special gacha events with bonus rates
2. **Battle system:** Use collected waifus in battles
3. **Trading system:** Limited waifu trading between users
4. **Achievement system:** Goals and rewards for progression
5. **Guild features:** Academy alliances and competitions

### **Technical Improvements**
1. **Caching layer:** Redis for frequently accessed data
2. **Performance optimization:** Query optimization and indexing
3. **Analytics dashboard:** System metrics and user statistics
4. **API endpoints:** REST API for external integrations
5. **Mobile app:** Companion mobile application

---

## 📞 **Support & Maintenance**

### **Error Handling**
- All commands use try-catch blocks
- Database transactions prevent data corruption
- Comprehensive logging for debugging
- User-friendly error messages

### **Performance Monitoring**
- Command execution timing
- Database query performance
- Memory usage tracking
- User activity metrics

### **Backup Strategy**
- Daily PostgreSQL backups
- Configuration file versioning
- Code repository with Git
- Disaster recovery procedures

---

*This documentation covers the complete NWNL Academy system as implemented. For specific implementation details, refer to the source code in the respective service and command files.*
