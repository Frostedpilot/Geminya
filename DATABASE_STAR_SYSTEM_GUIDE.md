# Database Scripts for New 3★ Star System

This document explains the updated database management scripts for the new 3★ star system.

## ✅ Updated Scripts

### 1. `reset_database_star_system.py` - **NEW COMPREHENSIVE RESET**
**Purpose**: Complete database reset and setup for the new 3★ system
**Usage**: `python reset_database_star_system.py`

**What it does**:
- 🗑️ Purges all existing data (keeps schema)
- 🔧 Ensures star system schema is ready (star_shards, updated_at columns)
- 🏪 Initializes shop with 3★ system items
- 📋 Optional character data upload

**New Shop Items Added**:
- **3★ Guarantee Summon Ticket** - 100 quartzs
- **2★ Guarantee Summon Ticket** - 50 quartzs  
- **Star Shard Bundle** - 75 quartzs (50 shards)

### 2. `purge_database.py` - **UPDATED**
**Purpose**: Purge all data while keeping schema
**Changes**: 
- ✅ Added `user_character_shards` table to purge list
- ✅ Proper foreign key order maintained

### 3. `initialize_shop.py` - **UPDATED**
**Purpose**: Initialize shop with items
**Changes**:
- ❌ Removed old "5★ Guarantee Summon Ticket"
- ✅ Added "3★ Guarantee Summon Ticket" (100 quartzs)
- ✅ Added "2★ Guarantee Summon Ticket" (50 quartzs)
- ✅ Added "Star Shard Bundle" (75 quartzs, 50 shards)

### 4. `wipe_waifu_database.py` - **NO CHANGES NEEDED**
**Purpose**: Complete database wipe (drops all tables)
**Status**: ✅ Already compatible (drops all tables regardless of names)

## 🗃️ Database Schema Changes

### New Tables Added:
- `user_character_shards` - Tracks shards per character per user

### New Columns Added:
- `user_waifus.star_shards` - Current shard count for character
- `user_waifus.current_star_level` - Current star level (1-3★)
- `user_character_shards.updated_at` - Timestamp for shard updates

### Schema Compatibility:
- ✅ `waifus.rarity` still supports 1-5 (for data integrity)
- ✅ Upgrade system can still create 4-5★ characters
- ✅ Gacha system only gives 1-3★ characters

## 🎮 Usage Recommendations

### For Fresh Setup:
```bash
python reset_database_star_system.py   # Complete reset
python upload_to_mysql.py              # Upload characters
python start_geminya.py                # Start bot
```

### For Data Purge Only:
```bash
python purge_database.py               # Keep schema, purge data
python upload_to_mysql.py              # Re-upload characters
```

### For Shop Reset Only:
```bash
python initialize_shop.py              # Reset shop items
```

### For Complete Wipe:
```bash
python wipe_waifu_database.py          # Nuclear option
python reset_database_star_system.py   # Rebuild everything
```

## 🔧 Migration Status

All database scripts are now compatible with the new 3★ star system:

- ✅ **Schema Migration**: `migrate_star_system.py` + `fix_star_system_schema.py`
- ✅ **Data Purging**: `purge_database.py` (includes user_character_shards)
- ✅ **Shop Setup**: `initialize_shop.py` (3★ max items)
- ✅ **Complete Reset**: `reset_database_star_system.py` (new comprehensive script)
- ✅ **Character Data**: `upload_to_mysql.py` (supports 1-3★ assignments)

## 🎯 Next Steps

1. **Test the reset script**: `python reset_database_star_system.py`
2. **Upload character data**: `python upload_to_mysql.py`
3. **Start the bot**: `python start_geminya.py`
4. **Test new summon commands**: `/nwnl_summon`, `/nwnl_multi_summon`

The database is now fully prepared for the new 3★ star system! 🌟
