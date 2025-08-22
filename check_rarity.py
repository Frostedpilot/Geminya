#!/usr/bin/env python3
"""
Quick check to see how rarity is stored in the database.
"""

import asyncio
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config import Config
from services.database import DatabaseService


async def check_rarity_format():
    """Check how rarity is stored in waifus table."""
    config = Config.from_file()
    db = DatabaseService(config)
    await db.initialize()
    
    try:
        if db.db_type == "mysql":
            async with db.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT name, rarity FROM waifus LIMIT 5")
                    results = await cursor.fetchall()
                    
                    print("Sample waifus and their rarity values:")
                    for name, rarity in results:
                        print(f"  {name}: {rarity} (type: {type(rarity)})")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if hasattr(db, 'connection_pool') and db.connection_pool:
            db.connection_pool.close()
            await db.connection_pool.wait_closed()


if __name__ == "__main__":
    asyncio.run(check_rarity_format())
