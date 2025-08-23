#!/usr/bin/env python3
"""
Simple test to verify quantity reduction works on fresh data.
"""

import asyncio
from services.database import DatabaseService
from config import Config

async def clean_test():
    """Test quantity reduction on clean data."""
    config = Config.create()
    config.set_mode("DEV")
    db = DatabaseService(config)
    await db.initialize()
    
    try:
        test_user = "clean_test_user"
        
        # Create fresh user
        await db.get_or_create_user(test_user)
        
        # Give them currency
        user = await db.get_or_create_user(test_user)
        current_quartzs = user.get('quartzs', 0)
        if current_quartzs < 100:
            # Set to 1000 quartzs for testing
            async with db.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("UPDATE users SET quartzs = 1000 WHERE discord_id = %s", (test_user,))
                    await conn.commit()
        
        # Get shop item
        items = await db.get_shop_items()
        if not items:
            print("❌ No shop items found")
            return
            
        item = items[0]
        print(f"Testing with: {item['name']} (costs {item['price']} quartzs)")
        
        # Purchase 5 of them
        success = await db.purchase_item(test_user, item['id'], 5)
        print(f"Purchase 5x: {success}")
        
        if not success:
            print("❌ Purchase failed")
            return
        
        # Check inventory
        inventory = await db.get_user_inventory(test_user)
        if not inventory:
            print("❌ No inventory items")
            return
            
        target_item = None
        for inv_item in inventory:
            if inv_item['item_name'] == item['name']:
                target_item = inv_item
                break
        
        if not target_item:
            print("❌ Target item not found in inventory")
            return
        
        print(f"Before use: {target_item['item_name']} x{target_item['quantity']} (ID: {target_item['id']})")
        
        # Use 2 of them
        use_result = await db.use_inventory_item(test_user, target_item['id'], 2)
        print(f"Use 2x result: {use_result}")
        
        # Check inventory again
        updated_inventory = await db.get_user_inventory(test_user)
        updated_item = None
        for inv_item in updated_inventory:
            if inv_item['id'] == target_item['id']:
                updated_item = inv_item
                break
        
        if updated_item:
            print(f"After use: {updated_item['item_name']} x{updated_item['quantity']} (ID: {updated_item['id']})")
            
            expected_qty = target_item['quantity'] - 2
            actual_qty = updated_item['quantity']
            
            if actual_qty == expected_qty:
                print(f"✅ SUCCESS: Quantity correctly reduced from {target_item['quantity']} to {actual_qty}")
            else:
                print(f"❌ FAILED: Expected {expected_qty}, got {actual_qty}")
        else:
            print("❌ Item not found after use (unexpected)")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(clean_test())
