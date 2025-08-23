#!/usr/bin/env python3
"""
Test the actual quantity reduction step by step.
"""

import asyncio
from services.database import DatabaseService
from config import Config

async def test_actual_reduction():
    """Test if quantity reduction actually works."""
    config = Config.create()
    config.set_mode("DEV")
    db = DatabaseService(config)
    await db.initialize()
    
    try:
        user_id = 'test_user_shop_123'
        
        # Get current inventory
        inventory = await db.get_user_inventory(user_id)
        if not inventory:
            print('No inventory items')
            return
            
        item = inventory[0]
        item_name = item.get('item_name', 'Unknown')
        item_qty = item.get('quantity', 0)
        item_id = item.get('id')
        
        print(f'BEFORE: {item_name} x{item_qty} (ID: {item_id})')
        
        # Use 1 item
        result = await db.use_inventory_item(user_id, item_id, 1)
        print(f'use_inventory_item result: {result}')
        
        # Get inventory again 
        updated_inventory = await db.get_user_inventory(user_id)
        
        # Find the same item
        updated_item = None
        for inv_item in updated_inventory:
            if inv_item['id'] == item['id']:
                updated_item = inv_item
                break
                
        if updated_item:
            updated_name = updated_item.get('item_name', 'Unknown')
            updated_qty = updated_item.get('quantity', 0)
            updated_id = updated_item.get('id')
            
            print(f'AFTER: {updated_name} x{updated_qty} (ID: {updated_id})')
            
            if updated_qty == item_qty - 1:
                print('✅ SUCCESS: Quantity correctly reduced')
            else:
                print(f'❌ FAILED: Expected {item_qty - 1}, got {updated_qty}')
        else:
            if item_qty == 1:
                print('✅ SUCCESS: Item was removed completely (quantity was 1)')
            else:
                print(f'❌ FAILED: Item unexpectedly removed (quantity was {item_qty})')
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(test_actual_reduction())
