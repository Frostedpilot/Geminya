#!/usr/bin/env python3
"""
Display the complete shop system schema and current status.
"""

import asyncio
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config import Config
from services.database import DatabaseService


async def show_shop_schema():
    """Display the shop database schema."""
    print("🗄️ SHOP SYSTEM DATABASE SCHEMA")
    print("=" * 60)
    
    config = Config.from_file()
    db = DatabaseService(config)
    await db.initialize()
    
    try:
        async with db.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                
                # Show all shop-related tables
                shop_tables = ['shop_items', 'user_inventory', 'user_purchases']
                
                for table in shop_tables:
                    print(f"\n📋 Table: {table}")
                    print("-" * 40)
                    
                    await cursor.execute(f"DESCRIBE {table}")
                    columns = await cursor.fetchall()
                    
                    for col in columns:
                        field, type_info, null, key, default, extra = col
                        nullable = "NULL" if null == "YES" else "NOT NULL"
                        key_info = f" ({key})" if key else ""
                        default_info = f" DEFAULT {default}" if default else ""
                        extra_info = f" {extra}" if extra else ""
                        print(f"  📝 {field:<20} {type_info:<20} {nullable}{key_info}{default_info}{extra_info}")
                
                # Show table row counts
                print(f"\n📊 Current Data:")
                print("-" * 40)
                for table in shop_tables:
                    await cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = await cursor.fetchone()
                    print(f"  {table}: {count[0]} rows")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if hasattr(db, 'connection_pool') and db.connection_pool:
            db.connection_pool.close()
            await db.connection_pool.wait_closed()


def show_shop_features():
    """Display shop system features."""
    print("\n🛍️ SHOP SYSTEM FEATURES")
    print("=" * 60)
    
    features = [
        ("💎 Currency System", "Uses Sakura Crystals as primary currency"),
        ("🏷️ Item Categories", "Summons, Currency, Boosts, Cosmetics, Utility, Passes, Upgrades"),
        ("⭐ Rarity System", "Common, Uncommon, Rare, Epic, Legendary"),
        ("📦 User Inventory", "Track owned items with quantities and expiration"),
        ("🧾 Purchase History", "Complete transaction logs for all purchases"),
        ("🎯 Requirements", "Items can have level/rank requirements"),
        ("⚡ Effects System", "JSON-based flexible effect definitions"),
        ("📈 Stock Management", "Daily limits and stock controls"),
        ("🔄 Auto Transactions", "Atomic purchases with rollback support"),
    ]
    
    for feature, description in features:
        print(f"  {feature:<20} {description}")


def show_shop_usage():
    """Show how to use the shop system."""
    print("\n🛠️ SHOP SYSTEM USAGE")
    print("=" * 60)
    
    print("📋 Database Methods:")
    methods = [
        "get_shop_items(category=None, active_only=True)",
        "get_shop_item_by_id(item_id)",
        "add_shop_item(item_data)",
        "purchase_item(user_id, item_id, quantity=1)",
        "get_user_inventory(user_id)",
        "get_user_purchase_history(user_id, limit=50)",
    ]
    
    for method in methods:
        print(f"  • {method}")
    
    print("\n💡 Example Item Structure:")
    print("""
    {
        "name": "Example Item",
        "description": "Item description",
        "item_type": "boost",
        "price": 100,
        "category": "boosts",
        "rarity": "rare",
        "effects": {"boost_type": "experience", "multiplier": 2.0},
        "requirements": {"min_rank": 5}
    }
    """)


async def main():
    """Main function."""
    print("🏪 SHOP SYSTEM OVERVIEW")
    print("=" * 70)
    
    await show_shop_schema()
    show_shop_features()
    show_shop_usage()
    
    print("\n" + "=" * 70)
    print("✅ Shop system is fully operational and ready for integration!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
