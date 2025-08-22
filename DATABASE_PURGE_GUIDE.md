# Database Purge Script

## Overview
The `purge_database.py` script provides a safe way to completely clear all data from your waifu database while preserving the schema structure.

## What it does

### ✅ Removes ALL data from:
- **Users table** - All user accounts and progress
- **Waifus table** - All character data 
- **User Collections** - All summoned waifus
- **Shop Data** - All shop items and purchase history
- **User Inventory** - All owned items
- **Conversations** - All chat history
- **Mission Progress** - All daily mission data
- **Events** - All event data

### ✅ Preserves:
- **Database schema** - All table structures remain intact
- **Indexes and constraints** - Foreign key relationships preserved
- **Auto-increment sequences** - Reset to start from 1

## Usage

```bash
python purge_database.py
```

### Safety Features
- **Double confirmation required** - You must type exact phrases to proceed
- **Detailed logging** - Shows exactly what's being deleted
- **Optional verification** - Can check that purge was successful
- **Graceful error handling** - Rolls back on any errors

### Confirmation Steps
1. Type `PURGE` when prompted
2. Type `YES DELETE EVERYTHING` for final confirmation
3. Script will show progress as it clears each table
4. Optionally run verification to confirm database is empty

## After Purging

Once the database is purged, you can:

1. **Repopulate with fresh data:**
   ```bash
   python populate_from_mal.py
   ```

2. **Initialize shop system:**
   ```bash
   python initialize_shop.py
   ```

3. **Start the bot normally:**
   ```bash
   python start_dev.py
   ```

## Example Output

```
🗑️  Database Purge Script
==================================================
⚠️  WARNING: This will DELETE ALL DATA from the database!
   - All users will be removed
   - All waifus will be removed
   - All user collections will be removed
   - All shop data will be removed
   - All user items will be removed
   - The database schema will remain intact
==================================================
Type 'PURGE' to confirm deletion: PURGE
Are you absolutely sure? Type 'YES DELETE EVERYTHING': YES DELETE EVERYTHING

🔄 Starting database purge...
✅ Purged 150 records from user_inventory
✅ Purged 89 records from user_purchases
✅ Purged 45 records from user_waifus
✅ Purged 12 records from shop_items
✅ Purged 234 records from waifus
✅ Purged 23 records from users

✅ Database purge completed successfully!
📊 Total records deleted: 553
🗃️  Database schema remains intact
🔄 You can now run populate_from_mal.py to add fresh data

Run verification check? (y/n): y

🔍 Verifying purge results...
✅ users: Empty
✅ waifus: Empty
✅ user_waifus: Empty
✅ shop_items: Empty
✅ user_inventory: Empty
✅ user_purchases: Empty
✅ conversations: Empty
✅ daily_missions: Empty
✅ events: Empty

✅ Verification complete: Database is clean!
```

## When to Use

- **Fresh start** - Want to clear all test data
- **Development reset** - Need clean state for testing
- **Data corruption** - Database has invalid/corrupted data
- **Schema changes** - After major database modifications
- **Production setup** - Clearing dev data before go-live

## Safety Notes

⚠️ **This operation is IRREVERSIBLE**
⚠️ **Make sure you have backups if needed**
⚠️ **Double-check you're running against the correct database**
⚠️ **All user progress will be permanently lost**

The script is designed to be safe with multiple confirmations, but once executed, the data cannot be recovered without a backup.
