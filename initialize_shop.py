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
        "price": 5,
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
        
        # Remove all existing items from shop
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT COUNT(*) FROM shop_items")
            count_result = await cursor.fetchone()
            existing_count = count_result[0] if count_result else 0
            
            if existing_count > 0:
                logger.info(f"Removing {existing_count} existing shop items...")
                await cursor.execute("DELETE FROM shop_items")
                await conn.commit()
                logger.info("All existing shop items removed.")
        
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
