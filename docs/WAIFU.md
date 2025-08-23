# 🌸 No Waifu No Laifu (NWNL) Academy: Gacha Collection System 🌸

Welcome to **NWNL Academy** - a comprehensive waifu collection system with gacha mechanics, automatic star progression, and academy management!

## 🎯 **System Overview**

NWNL Academy is a Discord bot-based gacha collection system where users can:
- **Summon waifus** using Sakura Crystals through a 1★-3★ gacha system
- **Automatically upgrade** characters to 4★ and 5★ using shards from duplicates
- **Manage their academy** with ranks, daily rewards, and guarantee tickets
- **Track collection progress** with detailed statistics and power calculations

## ⭐ **Star System (Core Mechanic)**

### 🎰 **Gacha Pulls (1★-3★)**
- **1★ (Basic):** 85% rate - Gray rarity, common characters
- **2★ (Epic):** 14% rate - Purple rarity, rare characters  
- **3★ (Legendary):** 1% rate - Gold rarity, legendary characters
- **Pity System:** Guaranteed 3★ at 50 pulls without one

### 🔥 **Automatic Star Upgrades (4★-5★)**
- **Duplicate pulls** give shards based on original rarity:
  - 1★ duplicates = 5 shards
  - 2★ duplicates = 20 shards  
  - 3★ duplicates = 90 shards
- **Automatic upgrades** when sufficient shards collected:
  - 1★ → 2★: 50 shards
  - 2★ → 3★: 100 shards
  - 3★ → 4★: 150 shards
  - 4★ → 5★: 200 shards
- **Quartz conversion:** When 5★ character gets duplicates, excess shards become quartz

## 💎 **Currency System**

### � **Sakura Crystals (Primary Currency)**
- **Single summon:** 10 crystals
- **Multi-summon (10x):** 100 crystals (guaranteed 2★+ on 10th pull)
- **Daily reward:** Claim crystals daily
- **Starting amount:** 2000 crystals for new users

### 💠 **Quartz (Premium Currency)**  
- **Source:** Converting excess shards from maxed (5★) characters
- **Use:** Purchase guarantee tickets from shop
- **Value:** High-value currency for guaranteed rolls

## � **Academy System**

### 📊 **Collector Ranks**
- **Automatic progression** based on collection power and waifu count
- **Exponential requirements:** Each rank needs double the power of previous
- **Formula:** Rank N requires 1000 × 2^N power + 5×N waifus
- **Power calculation:** Each waifu contributes rarity² × 100 power

### 🎁 **Daily Rewards**
- **24-hour cooldown** system
- **Fixed rewards:** Crystals and other bonuses
- **Streak tracking** for consecutive claims

## 🛒 **Shop System**

### � **Guarantee Tickets**
- **Only shop item:** Guarantee tickets for guaranteed high-rarity pulls
- **Purchase with:** Quartz (premium currency)
- **Usage:** Use from inventory for guaranteed pulls
- **Simple system:** No complex item types, focused on core functionality

## 📋 **Commands Reference**

### 🎰 **Summoning & Collection**

- `/nwnl_summon`: Basic single summon (10 crystals)
- `/nwnl_multi_summon`: 10-pull summon (100 crystals, guaranteed 2★+ on 10th)
- `/nwnl_collection [user]`: View waifu collection with star levels
- `/nwnl_profile <waifu_name>`: View detailed waifu information

### 🏫 **Academy Management**

- `/nwnl_status`: Check academy rank, currencies, and statistics
- `/nwnl_daily`: Claim daily rewards
- `/nwnl_rename_academy <name>`: Rename your academy
- `/nwnl_reset_account`: Reset all academy data
- `/nwnl_delete_account`: Permanently delete account

### 🛒 **Shop System**

- `/nwnl_shop`: Browse guarantee tickets
- `/nwnl_buy <item>`: Purchase guarantee tickets
- `/nwnl_inventory`: View purchased items
- `/nwnl_purchase_history`: View purchase history
- `/nwnl_use_item <item>`: Use guarantee tickets

## �️ **Database Schema (Current Implementation)**

### `waifus` table

```sql
CREATE TABLE waifus (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    series VARCHAR(255) NOT NULL,
    genre VARCHAR(100) NOT NULL,
    element VARCHAR(50),
    rarity INT NOT NULL CHECK (rarity >= 1 AND rarity <= 3),
    image_url TEXT,
    mal_id INT,
    favorites INT DEFAULT 0,
    base_stats TEXT,
    birthday DATE,
    favorite_gifts TEXT,
    special_dialogue TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `users` table

```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    discord_id VARCHAR(20) UNIQUE NOT NULL,
    academy_name VARCHAR(100),
    collector_rank INT DEFAULT 1,
    sakura_crystals INT DEFAULT 2000,
    quartzs INT DEFAULT 0,
    pity_counter INT DEFAULT 0,
    last_daily_claim TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `user_waifus` table

```sql
CREATE TABLE user_waifus (
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
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (waifu_id) REFERENCES waifus (id)
);
```

### Additional Tables

- `user_purchases`: Shop purchase history
- `user_inventory`: Current owned items
- `user_shards`: Shard tracking (legacy/compatibility)

## 📊 **Data Pipeline Workflow**

### 🔄 **Character Data Management Process**

1. **`pull_from_mal.py`** - Pull character and anime data from MyAnimeList
   - Output: `data/characters_mal.csv`, `data/anime_mal.csv`
   - Fetches character details, favorites, series information

2. **`character_edit.py`** - Clean and filter character data  
   - Input: `data/characters_mal.csv`
   - Output: `data/character_final.csv`
   - Removes male characters, redundant data, applies filters

3. **Manual Editing Phase** - Hand-edit star assignments
   - Copy `character_final.csv` data to `data/characters_cleaned.xlsx`
   - Manually assign star ratings (1★-3★) based on popularity/preferences
   - Save edited Excel file for processing

4. **`process_character_final.py`** - Final processing and validation
   - Input: `data/characters_cleaned.xlsx` (manually edited)
   - Output: `data/character_final.csv` (database-ready)
   - Validates data, preserves manual star assignments, prepares for upload

5. **`upload_to_mysql.py`** - Upload to database
   - Input: `data/character_final.csv`
   - Action: Inserts/updates character data in MySQL database
   - Result: Characters available in gacha system

### 📁 **Key Data Files**

- `data/characters_mal.csv` - Raw MAL character data
- `data/anime_mal.csv` - Raw MAL anime data  
- `data/character_final.csv` - Cleaned character data (before manual editing)
- `data/characters_cleaned.xlsx` - Excel file for manual star assignment
- `data/character_final.csv` - Final processed data (after manual editing)

## 🎯 **System Characteristics**

### ✅ **What's Currently Working**

- **Complete gacha system** with 1★-3★ pulls and automatic 4★-5★ upgrades
- **Comprehensive academy management** with ranks, dailies, and statistics
- **Shop system** focused on guarantee tickets only
- **Data pipeline** for character management from MAL to database
- **Race condition prevention** with command queuing
- **Automatic progression** system for ranks and star levels

### 🚧 **Planned/Future Features**

- **Interactive features:** Chat, dating, gifts, mood system
- **Advanced gameplay:** Classes, mini-games, events
- **Social features:** Trading, guilds, competitions
- **AI integration:** Personality-driven conversations
- **Enhanced progression:** Bond levels, memories, achievements

## 🎮 **System Design Philosophy**

The NWNL system prioritizes:
- **Core mechanics first:** Solid gacha and collection foundation
- **Automatic progression:** Reducing manual upgrade complexity  
- **Data-driven approach:** MAL integration for authentic character data
- **Scalable architecture:** Built for future feature expansion
- **User-friendly experience:** Clear commands and intuitive progression
