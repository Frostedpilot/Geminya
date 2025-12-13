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
    {
        "name": "3★ Guarantee Ticket",
        "description": "Guarantees a 3★ waifu summon (max rarity for direct summons)",
        "price": 300,
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
    {
        "name": "2★ Series Ticket",
        "description": "Choose a series and receive a random 2★ character from that series.",
        "price": 100,
        "category": "tickets",
        "item_type": "series_ticket",
        "item_data": {
            "rarity": "rare",
            "currency_type": "quartzs"
        },
        "effects": {
            "choose_series": True,
            "guarantee_rarity": 2
        },
        "stock_limit": -1,
        "is_active": True
    },
    {
        "name": "3★ Series Ticket",
        "description": "Choose a series and receive a random 3★ character from that series.",
        "price": 500,
        "category": "tickets",
        "item_type": "series_ticket",
        "item_data": {
            "rarity": "rare",
            "currency_type": "quartzs"
        },
        "effects": {
            "choose_series": True,
            "guarantee_rarity": 3
        },
        "stock_limit": -1,
        "is_active": True
    },
    {
        "name": "1★ Selectix Ticket",
        "description": "Choose any 1★ character of your choice.",
        "price": 25,
        "category": "tickets",
        "item_type": "selectix_ticket",
        "item_data": {
            "rarity": "rare",
            "currency_type": "quartzs"
        },
        "effects": {
            "choose_character": True,
            "guarantee_rarity": 1
        },
        "stock_limit": -1,
        "is_active": True
    },
    {
        "name": "2★ Selectix Ticket",
        "description": "Choose any 2★ character of your choice.",
        "price": 200,
        "category": "tickets",
        "item_type": "selectix_ticket",
        "item_data": {
            "rarity": "rare",
            "currency_type": "quartzs"
        },
        "effects": {
            "choose_character": True,
            "guarantee_rarity": 2
        },
        "stock_limit": -1,
        "is_active": True
    },
    {
        "name": "3★ Selectix Ticket",
        "description": "Choose any 3★ character of your choice.",
        "price": 700,
        "category": "tickets",
        "item_type": "selectix_ticket",
        "item_data": {
            "rarity": "rare",
            "currency_type": "quartzs"
        },
        "effects": {
            "choose_character": True,
            "guarantee_rarity": 3
        },
        "stock_limit": -1,
        "is_active": True
    },
    {
        "name": "10-Summon All 3★ Guarantee Ticket",
        "description": "Guarantees 10 summons, all 3★ characters.",
        "price": 2500,
        "category": "tickets",
        "item_type": "multi_guarantee_ticket",
        "item_data": {
            "rarity": "legendary",
            "currency_type": "quartzs"
        },
        "effects": {
            "guarantee_rarity": 3,
            "summon_count": 10
        },
        "stock_limit": -1,
        "is_active": True
    }
]

async def initialize_shop():
    """Initialize the shop with default items."""
    import asyncpg
    # Load secrets for PostgreSQL connection
    with open('secrets.json', 'r') as f:
        secrets = json.load(f)
    pg_config = {
        'host': secrets.get('POSTGRES_HOST', 'localhost'),
        'port': int(secrets.get('POSTGRES_PORT', 5432)),
        'user': secrets.get('POSTGRES_USER'),
        'password': secrets.get('POSTGRES_PASSWORD'),
        'database': secrets.get('POSTGRES_DATABASE'),
    }
    logger.info("Connecting to PostgreSQL database...")
    pool = await asyncpg.create_pool(**pg_config)
    logger.info("Initializing shop with default items...")
    async with pool.acquire() as conn:
        # Get existing item names
        existing_items = await conn.fetch("SELECT name FROM shop_items")
        existing_names = {row['name'] for row in existing_items}
        logger.info(f"Found {len(existing_names)} existing shop items.")
        
        # Add only new items
        added_count = 0
        skipped_count = 0
        for item in DEFAULT_SHOP_ITEMS:
            if item['name'] in existing_names:
                logger.info(f"Skipped (already exists): {item['name']}")
                skipped_count += 1
                continue
            
            try:
                await conn.execute(
                    """
                    INSERT INTO shop_items (name, description, price, category, item_type, item_data, effects, stock_limit, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
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
                added_count += 1
                logger.info(f"Added item: {item['name']}")
            except Exception as e:
                logger.error(f"Error adding item {item['name']}: {e}")
        logger.info(f"Shop initialization complete! Added {added_count} new items, skipped {skipped_count} existing items.")
    await pool.close()


if __name__ == "__main__":
    asyncio.run(initialize_shop())