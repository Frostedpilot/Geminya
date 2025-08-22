"""
Initialize shop with default items for the NWNL system.
This script populates the shop with various items for the No Waifu No Laifu academy.
"""

import asyncio
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default shop items for NWNL
DEFAULT_SHOP_ITEMS = [
    # Currency Packs
    {
        "name": "Sakura Crystal Pack (Small)",
        "description": "A small pack of Sakura Crystals for summoning waifus",
        "price": 50,
        "category": "currency",
        "item_type": "currency_pack",
        "item_data": {
            "rarity": "common",
            "currency_type": "quartzs"
        },
        "effects": {
            "sakura_crystals": 100
        },
        "stock_limit": -1,
        "is_active": True
    },
    {
        "name": "Sakura Crystal Pack (Medium)",
        "description": "A medium pack of Sakura Crystals for summoning waifus",
        "price": 200,
        "category": "currency",
        "item_type": "currency_pack",
        "item_data": {
            "rarity": "uncommon",
            "currency_type": "quartzs"
        },
        "effects": {
            "sakura_crystals": 500
        },
        "stock_limit": -1,
        "is_active": True
    },
    {
        "name": "Sakura Crystal Pack (Large)",
        "description": "A large pack of Sakura Crystals for summoning waifus",
        "price": 800,
        "category": "currency",
        "item_type": "currency_pack",
        "item_data": {
            "rarity": "rare",
            "currency_type": "quartzs"
        },
        "effects": {
            "sakura_crystals": 2500
        },
        "stock_limit": -1,
        "is_active": True
    },
    
    # Guarantee Tickets
    {
        "name": "1★ Guarantee Ticket",
        "description": "Guarantees a 1★ waifu summon",
        "price": 25,
        "category": "tickets",
        "item_type": "guarantee_ticket",
        "item_data": {
            "rarity": "common",
            "currency_type": "quartzs"
        },
        "effects": {
            "guarantee_rarity": 1
        },
        "stock_limit": -1,
        "is_active": True
    },
    {
        "name": "2★ Guarantee Ticket",
        "description": "Guarantees a 2★ waifu summon",
        "price": 100,
        "category": "tickets",
        "item_type": "guarantee_ticket",
        "item_data": {
            "rarity": "uncommon",
            "currency_type": "quartzs"
        },
        "effects": {
            "guarantee_rarity": 2
        },
        "stock_limit": -1,
        "is_active": True
    },
    {
        "name": "3★ Guarantee Ticket",
        "description": "Guarantees a 3★ waifu summon (max rarity for direct summons)",
        "price": 500,
        "category": "tickets",
        "item_type": "guarantee_ticket",
        "item_data": {
            "rarity": "rare",
            "currency_type": "quartzs"
        },
        "effects": {
            "guarantee_rarity": 3
        },
        "stock_limit": -1,
        "is_active": True
    },
    
    # Boosts
    {
        "name": "Bond Experience Boost",
        "description": "2x bond experience for 24 hours",
        "price": 150,
        "category": "boosts",
        "item_type": "boost",
        "item_data": {
            "rarity": "uncommon",
            "currency_type": "quartzs"
        },
        "effects": {
            "bond_multiplier": 2.0,
            "duration_hours": 24
        },
        "stock_limit": -1,
        "is_active": True
    },
    {
        "name": "Super Bond Experience Boost",
        "description": "3x bond experience for 12 hours",
        "price": 300,
        "category": "boosts",
        "item_type": "boost",
        "item_data": {
            "rarity": "rare",
            "currency_type": "quartzs"
        },
        "effects": {
            "bond_multiplier": 3.0,
            "duration_hours": 12
        },
        "stock_limit": -1,
        "is_active": True
    },
    
    # Summon Tickets
    {
        "name": "Standard Summon Ticket",
        "description": "Equivalent to one standard summon",
        "price": 20,
        "category": "tickets",
        "item_type": "summon_ticket",
        "item_data": {
            "rarity": "common",
            "currency_type": "quartzs"
        },
        "effects": {
            "summons": 1
        },
        "stock_limit": -1,
        "is_active": True
    },
    {
        "name": "10x Summon Ticket Bundle",
        "description": "Equivalent to 10 standard summons",
        "price": 180,
        "category": "tickets",
        "item_type": "summon_ticket",
        "item_data": {
            "rarity": "uncommon",
            "currency_type": "quartzs"
        },
        "effects": {
            "summons": 10
        },
        "stock_limit": -1,
        "is_active": True
    },
    
    # Utility Items
    {
        "name": "Waifu Naming Permit",
        "description": "Allows you to give custom names to your waifus permanently",
        "price": 100,
        "category": "utility",
        "item_type": "utility",
        "item_data": {
            "rarity": "uncommon",
            "currency_type": "quartzs"
        },
        "effects": {
            "allows_naming": True
        },
        "stock_limit": -1,
        "is_active": True
    },
    
    # Collection Upgrades
    {
        "name": "Collection Expansion (+5)",
        "description": "Permanently increases your waifu collection limit by 5",
        "price": 250,
        "category": "upgrades",
        "item_type": "upgrade",
        "item_data": {
            "rarity": "rare",
            "currency_type": "quartzs"
        },
        "effects": {
            "collection_limit_increase": 5
        },
        "stock_limit": -1,
        "is_active": True
    },
    {
        "name": "Collection Expansion (+10)",
        "description": "Permanently increases your waifu collection limit by 10",
        "price": 450,
        "category": "upgrades",
        "item_type": "upgrade",
        "item_data": {
            "rarity": "epic",
            "currency_type": "quartzs"
        },
        "effects": {
            "collection_limit_increase": 10
        },
        "stock_limit": -1,
        "is_active": True
    },
    
    # Cosmetics
    {
        "name": "Cherry Blossom Profile Frame",
        "description": "A beautiful cherry blossom frame for your profile",
        "price": 75,
        "category": "cosmetics",
        "item_type": "frame",
        "item_data": {
            "rarity": "uncommon",
            "currency_type": "quartzs"
        },
        "effects": {
            "frame_type": "cherry_blossom",
            "frame_url": "https://example.com/frames/cherry_blossom.png"
        },
        "stock_limit": -1,
        "is_active": True
    },
    {
        "name": "Academy Student Title",
        "description": "Show your dedication with the 'Academy Student' title",
        "price": 50,
        "category": "cosmetics",
        "item_type": "title",
        "item_data": {
            "rarity": "common",
            "currency_type": "quartzs"
        },
        "effects": {
            "title": "Academy Student",
            "title_color": "#4A90E2"
        },
        "stock_limit": -1,
        "is_active": True
    },
    {
        "name": "Star Collector Title",
        "description": "Show your prowess with the 'Star Collector' title",
        "price": 200,
        "category": "cosmetics",
        "item_type": "title",
        "item_data": {
            "rarity": "rare",
            "currency_type": "quartzs"
        },
        "effects": {
            "title": "Star Collector",
            "title_color": "#FFD700"
        },
        "stock_limit": -1,
        "is_active": True
    }
]

async def initialize_shop():
    """Initialize the shop with default items."""
    try:
        # Simple database connection using direct MySQL config
        import aiomysql
        
        # Load database config from config.yml
        import yaml
        with open('config.yml', 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Load secrets for MySQL connection
        try:
            with open('secrets.json', 'r') as f:
                secrets = json.load(f)
        except FileNotFoundError:
            logger.error("secrets.json not found. Please create it with your MySQL credentials.")
            return
        
        mysql_config = {
            'host': secrets.get('MYSQL_HOST', 'localhost'),
            'port': int(secrets.get('MYSQL_PORT', 3306)),
            'user': secrets.get('MYSQL_USER'),
            'password': secrets.get('MYSQL_PASSWORD'),
            'db': secrets.get('MYSQL_DATABASE'),
        }
        
        logger.info("Connecting to MySQL database...")
        
        # Create connection
        conn = await aiomysql.connect(**mysql_config)
        
        logger.info("Initializing shop with default items...")
        
        # Check if shop_items table exists and has items
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT COUNT(*) FROM shop_items")
            count_result = await cursor.fetchone()
            existing_count = count_result[0] if count_result else 0
            
            if existing_count > 0:
                logger.info(f"Shop already has {existing_count} items. Skipping initialization.")
                await conn.close()
                return
        
        # Add all default items
        added_count = 0
        async with conn.cursor() as cursor:
            for item in DEFAULT_SHOP_ITEMS:
                try:
                    query = """
                    INSERT INTO shop_items (name, description, price, category, item_type, item_data, effects, stock_limit, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    params = (
                        item['name'],
                        item.get('description', ''),
                        item['price'],
                        item['category'],
                        item['item_type'],
                        json.dumps(item.get('item_data', {})),
                        json.dumps(item.get('effects', {})),
                        item.get('stock_limit', -1),
                        item.get('is_active', True)
                    )
                    
                    await cursor.execute(query, params)
                    await conn.commit()
                    added_count += 1
                    logger.info(f"Added item: {item['name']} (ID: {cursor.lastrowid})")
                    
                except Exception as e:
                    logger.error(f"Error adding item {item['name']}: {e}")
        
        logger.info(f"Shop initialization complete! Added {added_count} items.")
        
        # Close connection
        conn.close()
        
    except Exception as e:
        logger.error(f"Error initializing shop: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(initialize_shop())
