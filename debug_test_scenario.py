#!/usr/bin/env python3
"""
Debug the exact test scenario step by step.
"""

import asyncio
from services.database import DatabaseService
from config import Config

async def debug_test_scenario():
    """Recreate the exact test scenario to find the bug."""
    config = Config.create()
    config.set_mode("DEV")
    db = DatabaseService(config)
    await db.initialize()
    
    try:
        user_id = 'test_user_shop_123'
        
        # Recreate the exact test scenario
        print('=== RECREATING TEST SCENARIO ===')
        
        # Get current inventory (like the test does)
        inventory = await db.get_user_inventory(user_id)
        print(f'Initial inventory: {len(inventory)} items')
        for i, item in enumerate(inventory):
            item_id = item.get('id')
            item_name = item.get('item_name', 'Unknown')
            item_qty = item.get('quantity', 0)
            print(f'  Item {i}: ID={item_id}, name={item_name}, qty={item_qty}')
        
        if not inventory:
            return
            
        # Pick the first item (like test does)
        test_item = inventory[0] 
        test_id = test_item.get('id')
        test_name = test_item.get('item_name', 'Unknown')
        test_qty = test_item.get('quantity', 0)
        
        print(f'\nTesting with: {test_name} x{test_qty} (ID: {test_id})')
        
        # Use 1 item (like test does)
        success = await db.use_inventory_item(user_id, test_id, 1)
        print(f'use_inventory_item result: {success}')
        
        # Get updated inventory (like test does)
        updated_inventory = await db.get_user_inventory(user_id)
        print(f'\nUpdated inventory: {len(updated_inventory)} items')
        for i, item in enumerate(updated_inventory):
            item_id = item.get('id')
            item_name = item.get('item_name', 'Unknown')
            item_qty = item.get('quantity', 0)
            print(f'  Item {i}: ID={item_id}, name={item_name}, qty={item_qty}')
        
        # Find the same item (like test does)
        updated_item = None
        for inv_item in updated_inventory:
            if inv_item['id'] == test_item['id']:
                updated_item = inv_item
                break
        
        print(f'\nComparison:')
        print(f'  Original: {test_name} x{test_qty} (ID: {test_id})')
        if updated_item:
            upd_name = updated_item.get('item_name', 'Unknown')
            upd_qty = updated_item.get('quantity', 0)
            upd_id = updated_item.get('id')
            print(f'  Updated:  {upd_name} x{upd_qty} (ID: {upd_id})')
            expected = test_qty - 1
            actual = upd_qty
            result = "✅ PASS" if actual == expected else "❌ FAIL"
            print(f'  Expected: {expected}, Actual: {actual} -> {result}')
        else:
            print(f'  Updated:  [ITEM REMOVED]')
            result = "✅ PASS" if test_qty == 1 else "❌ FAIL"
            print(f'  Expected removal: {result}')
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(debug_test_scenario())
