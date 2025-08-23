#!/usr/bin/env python3
"""
Debug the exact issue with get_user_inventory vs raw database.
"""

import asyncio
from services.database import DatabaseService
from config import Config

async def debug_inventory_method():
    """Debug what get_user_inventory is actually returning."""
    config = Config.create()
    config.set_mode("DEV")
    db = DatabaseService(config)
    await db.initialize()
    
    try:
        user_id = 'test_user_shop_123'
        
        print("🔍 Checking raw database...")
        async with db.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute('SELECT * FROM user_inventory WHERE user_id = %s', (user_id,))
                raw_results = await cursor.fetchall()
                print(f'Raw DB records: {len(raw_results)}')
                for i, r in enumerate(raw_results):
                    row_data = list(r)  # Convert to list for easier access
                    print(f'  Raw {i}: ID={row_data[0]}, user={row_data[1]}, name={row_data[2]}, qty={row_data[4]}')
        
        print("\n🔍 Checking get_user_inventory method...")
        inventory = await db.get_user_inventory(user_id)
        print(f'get_user_inventory returns: {len(inventory)} items')
        for i, item in enumerate(inventory):
            print(f'  Method {i}: ID={item.get("id")}, name={item.get("item_name")}, qty={item.get("quantity")}')
            
        print(f"\n🔍 Raw item structure:")
        if inventory:
            print(f'First item keys: {list(inventory[0].keys())}')
            print(f'First item values: {dict(inventory[0])}')
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(debug_inventory_method())
