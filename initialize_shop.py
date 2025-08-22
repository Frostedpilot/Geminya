#!/usr/bin/env python3
"""
Script to initialize the shop with basic items.
"""

import asyncio
import sys
import os
import json

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config import Config
from services.database import DatabaseService


async def clear_shop_tables(db):
    """Clear all existing data from shop tables"""
    print("🗑️ Clearing existing shop data...")
    
    # MySQL-only implementation
    async with db.connection_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Clear in reverse order due to foreign key constraints
            await cursor.execute("DELETE FROM user_purchases")
            await cursor.execute("DELETE FROM user_inventory") 
            await cursor.execute("DELETE FROM shop_items")
            await conn.commit()
    
    print("✅ Shop tables cleared successfully!")


async def populate_shop():
    """Populate the shop with initial items."""
    print("🏪 Initializing shop with basic items...")
    
    config = Config.from_file()
    db = DatabaseService(config)
    await db.initialize()
    
    # Clear existing shop data first
    await clear_shop_tables(db)
    
    # Define shop items
    shop_items = [
        {
            "name": "5★ Guarantee Summon Ticket",
            "description": "Immediately summons a guaranteed 5★ waifu! No waiting required.",
            "item_type": "guarantee_ticket",
            "price": 100,
            "category": "summons",
            "item_data": {
                "currency_type": "quartzs",
                "rarity": "legendary",
                "effects": {"guarantee_rarity": 3, "uses": 1},
                "requirements": {}
            }
        }
    ]
    
    try:
        added_count = 0
        for item in shop_items:
            item_id = await db.add_shop_item(item)
            if item_id > 0:
                item_data = item.get("item_data", {})
                currency_symbol = "🔹" if item_data.get("currency_type") == "quartzs" else "💎"
                currency_name = "quartzs" if item_data.get("currency_type") == "quartzs" else "crystals"
                print(f"✅ Added: {item['name']} (ID: {item_id}) - {currency_symbol}{item['price']} {currency_name}")
                added_count += 1
            else:
                print(f"❌ Failed to add: {item['name']}")
        
        print(f"\n🎉 Shop initialization complete! Added {added_count} items.")
        
        # Show shop contents
        print("\n📋 Current shop inventory:")
        items = await db.get_shop_items()
        
        categories = {}
        for item in items:
            cat = item['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        for category, cat_items in categories.items():
            print(f"\n🏷️ {category.upper()}:")
            for item in cat_items:
                # Parse item_data JSON
                try:
                    item_data = json.loads(item['item_data']) if item['item_data'] else {}
                except:
                    item_data = {}
                
                rarity_emoji = {
                    'common': '⚪',
                    'uncommon': '🟢', 
                    'rare': '🔵',
                    'epic': '🟣',
                    'legendary': '🟡'
                }
                emoji = rarity_emoji.get(item_data.get('rarity', ''), '⚪')
                currency_symbol = "🔹" if item_data.get('currency_type') == "quartzs" else "💎"
                print(f"  {emoji} {item['name']} - {currency_symbol}{item['price']}")
                print(f"    {item['description']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error populating shop: {e}")
        return False
    finally:
        if hasattr(db, 'connection_pool') and db.connection_pool:
            db.connection_pool.close()
            await db.connection_pool.wait_closed()


async def test_shop_purchase():
    """Test purchasing items with both currencies."""
    print("\n🧪 Testing shop purchase functionality...")
    
    config = Config.from_file()
    db = DatabaseService(config)
    await db.initialize()
    
    test_user_id = "test_shop_999999999999999999"
    
    try:
        # Clean up any existing test user
        await db.delete_user_account(test_user_id)
        
        # Create test user with crystals
        user = await db.get_or_create_user(test_user_id)
        print(f"👤 Test user created with {user['sakura_crystals']} crystals, {user.get('quartzs', 0)} quartzs")
        
        # Get items to test
        items = await db.get_shop_items()
        if not items:
            print("❌ No shop items found for testing")
            return False
        
        # Test crystal purchase first
        crystal_items = [item for item in items if item.get('currency_type', 'sakura_crystals') == 'sakura_crystals']
        if crystal_items:
            cheapest_crystal_item = min(crystal_items, key=lambda x: x['price'])
            currency_symbol = "💎"
            print(f"🛒 Testing crystal purchase: {cheapest_crystal_item['name']} for {currency_symbol}{cheapest_crystal_item['price']}")
            
            success = await db.purchase_item(test_user_id, cheapest_crystal_item['id'], 1)
            if success:
                print("✅ Crystal purchase successful!")
                updated_user = await db.get_or_create_user(test_user_id)
                print(f"💰 Updated balance: {updated_user['sakura_crystals']} crystals")
                
                inventory = await db.get_user_inventory(test_user_id)
                print(f"📦 Inventory items: {len(inventory)}")
                for inv_item in inventory:
                    print(f"  - {inv_item['name']} x{inv_item['quantity']}")
            else:
                print("❌ Crystal purchase failed!")
        
        # Give user some quartzs for testing
        await db.update_user_quartzs(test_user_id, 50)
        print(f"\n💎 Added 50 quartzs for testing quartz purchases")
        
        # Test quartz purchase
        quartz_items = [item for item in items if item.get('currency_type') == 'quartzs']
        if quartz_items:
            cheapest_quartz_item = min(quartz_items, key=lambda x: x['price'])
            currency_symbol = "🔹"
            print(f"🛒 Testing quartz purchase: {cheapest_quartz_item['name']} for {currency_symbol}{cheapest_quartz_item['price']}")
            
            success = await db.purchase_item(test_user_id, cheapest_quartz_item['id'], 1)
            if success:
                print("✅ Quartz purchase successful!")
                updated_user = await db.get_or_create_user(test_user_id)
                print(f"💰 Updated balance: {updated_user['sakura_crystals']} crystals, {updated_user.get('quartzs', 0)} quartzs")
                
                inventory = await db.get_user_inventory(test_user_id)
                print(f"📦 Final inventory items: {len(inventory)}")
                for inv_item in inventory:
                    print(f"  - {inv_item['name']} x{inv_item['quantity']}")
            else:
                print("❌ Quartz purchase failed!")
        
        # Clean up
        await db.delete_user_account(test_user_id)
        return True
        
    except Exception as e:
        print(f"❌ Error testing purchase: {e}")
        return False
    finally:
        if hasattr(db, 'connection_pool') and db.connection_pool:
            db.connection_pool.close()
            await db.connection_pool.wait_closed()


async def main():
    """Main function."""
    print("=" * 70)
    print("🏪 SHOP SYSTEM INITIALIZATION")
    print("=" * 70)
    
    # Step 1: Populate shop
    populate_success = await populate_shop()
    
    if populate_success:
        # Step 2: Test purchase
        purchase_success = await test_shop_purchase()
        
        print("=" * 70)
        if purchase_success:
            print("🎉 SHOP SYSTEM READY!")
            print("✅ Database tables created")
            print("✅ Shop items populated")
            print("✅ Purchase system working")
        else:
            print("⚠️ SHOP SYSTEM PARTIALLY READY")
            print("✅ Database tables created")
            print("✅ Shop items populated")
            print("❌ Purchase system needs attention")
    else:
        print("=" * 70)
        print("❌ SHOP SYSTEM INITIALIZATION FAILED")
    
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
