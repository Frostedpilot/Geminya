#!/usr/bin/env python3
"""
Debug purchase issue - why items aren't being added to inventory.
"""

import asyncio
from services.database import DatabaseService
from config import Config

async def debug_purchase():
    config = Config.create()
    config.set_mode("DEV")
    db = DatabaseService(config)
    await db.initialize()
    
    try:
        # Create the debug user first
        user = await db.get_or_create_user('debug_user')
        print(f"User created/found: {user}")
        
        # Check what happens during a purchase
        items = await db.get_shop_items()
        if items:
            item = items[0]
            print(f"Shop item: {item}")
            print(f"item_data type: {type(item.get('item_data'))}")
            print(f"effects type: {type(item.get('effects'))}")
            print(f"item_data value: {item.get('item_data')}")
            print(f"effects value: {item.get('effects')}")
            
            # Try the purchase with debug
            result = await db.purchase_item('debug_user', item['id'], 1)
            print(f"Purchase result: {result}")
            
            # Check what's in inventory table
            async with db.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute('SELECT * FROM user_inventory WHERE user_id = %s', ('debug_user',))
                    inventory_records = await cursor.fetchall()
                    print(f"Raw inventory records: {len(inventory_records)}")
                    for record in inventory_records:
                        print(f"  {dict(record)}")
                        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(debug_purchase())
