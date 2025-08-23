#!/usr/bin/env python3
"""
Debug script to check table counts and data persistence.
"""

import asyncio
import sys
import logging
from services.database import DatabaseService
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_tables():
    """Check both user_purchases and user_inventory tables."""
    config = Config.create()
    config.set_mode("DEV")
    db = DatabaseService(config)
    await db.initialize()
    
    try:
        user_id = 'test_user_shop_123'
        
        # Check using raw SQL to bypass any processing
        async with db.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Check table counts
                print("📊 Table counts:")
                for table in ['user_purchases', 'user_inventory']:
                    await cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id = %s", (user_id,))
                    count = await cursor.fetchone()
                    print(f"  {table}: {count[0]} rows")
                
                print("\n📦 User inventory items (raw - all):")
                await cursor.execute("SELECT * FROM user_inventory WHERE user_id = %s ORDER BY acquired_at DESC", (user_id,))
                rows = await cursor.fetchall()
                if rows:
                    for i, row in enumerate(rows):
                        active_status = "ACTIVE" if row[8] == 1 else "INACTIVE" if row[8] == 0 else "NULL"
                        print(f"  Item {i}: ID={row[0]}, Name={row[2]}, Qty={row[4]}, Active={active_status}")
                else:
                    print("  No items found")
                    
                print("\n📦 User inventory items (active only):")
                await cursor.execute("SELECT * FROM user_inventory WHERE user_id = %s AND is_active = TRUE ORDER BY acquired_at DESC", (user_id,))
                active_rows = await cursor.fetchall()
                if active_rows:
                    for i, row in enumerate(active_rows):
                        print(f"  Active Item {i}: ID={row[0]}, Name={row[2]}, Qty={row[4]}")
                else:
                    print("  No active items found")
                    
                print("\n💰 Recent purchases (raw):")
                await cursor.execute("SELECT * FROM user_purchases WHERE user_id = %s ORDER BY purchased_at DESC LIMIT 3", (user_id,))
                purchases = await cursor.fetchall()
                if purchases:
                    for i, purchase in enumerate(purchases):
                        print(f"  Purchase {i}: ID={purchase[0]}, Item={purchase[2]}, Qty={purchase[3]}")
                else:
                    print("  No purchases found")
                    
        # Also test the database service methods
        print("\n🔍 Using database service methods:")
        inventory = await db.get_user_inventory(user_id)
        print(f"  get_user_inventory returned: {len(inventory)} items")
        
        history = await db.get_user_purchase_history(user_id, 3)
        print(f"  get_user_purchase_history returned: {len(history)} items")
        
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(debug_tables())
