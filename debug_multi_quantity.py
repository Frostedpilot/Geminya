#!/usr/bin/env python3
"""
Debug script specifically for multi-quantity item reduction bug.
"""

import asyncio
from services.database import DatabaseService
from config import Config

async def debug_multi_quantity():
    """Debug multi-quantity item reduction."""
    config = Config.create()
    config.set_mode("DEV")
    db = DatabaseService(config)
    await db.initialize()
    
    try:
        # Get a shop item
        items = await db.get_shop_items()
        if items:
            item = items[0]
            print(f"Testing with shop item: {item['name']} (ID: {item['id']})")
            
            # Add it to inventory with quantity 3
            success = await db.purchase_item('test_user_shop_123', item['id'], 3)
            print(f'Purchase 3x result: {success}')
            
            # Check inventory 
            inventory = await db.get_user_inventory('test_user_shop_123')
            test_item = None
            for inv_item in inventory:
                if inv_item['quantity'] > 1:
                    test_item = inv_item
                    break
            
            if test_item:
                item_name = test_item.get('item_name', 'Unknown')
                item_qty = test_item.get('quantity', 0)
                item_id = test_item.get('id')
                
                print(f'Found multi-item: {item_name} x{item_qty} (ID: {item_id})')
                
                # Use 1 quantity
                result = await db.use_inventory_item('test_user_shop_123', item_id, 1)
                print(f'Use 1x result: {result}')
                
                # Check if quantity reduced
                updated_inventory = await db.get_user_inventory('test_user_shop_123')
                updated_item = None
                for item in updated_inventory:
                    if item['id'] == test_item['id']:
                        updated_item = item
                        break
                
                if updated_item:
                    new_qty = updated_item.get('quantity', 0)
                    print(f'After use: {item_name} x{new_qty}')
                    if new_qty == item_qty - 1:
                        print('✅ Quantity correctly reduced')
                    else:
                        print(f'❌ Quantity NOT reduced! Expected {item_qty - 1}, got {new_qty}')
                else:
                    print('❌ Item removed completely (unexpected for qty > 1)')
            else:
                print('❌ No multi-quantity items found after purchase')
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(debug_multi_quantity())
