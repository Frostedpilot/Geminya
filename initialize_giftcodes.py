"""
Initialize gift codes for the Waifu Academy system.
This script populates the gift_codes table with example codes for quartz, gems, and items.
"""

import asyncio
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_GIFT_CODES = [
    {
        "code": "SHOUKONOOB",
        "reward_type": "gems",
        "reward_value": 500,
        "is_active": True,
        "usage_limit": 99,
    },
    {
        "code": "FREEROBUX",
        "reward_type": "item",
        "reward_value": 6,
        "is_active": True,
        "usage_limit": 99,
    },
    {
        "code": "IMGOINGTORESETDATABASE",
        "reward_type": "gems",
        "reward_value": 500,
        "is_active": True,
        "usage_limit": 99,
    },
    {
        "code": "APOLOGEM",
        "reward_type": "gems",
        "reward_value": 2000,
        "is_active": True,
        "usage_limit": 99,
    }
]

async def initialize_giftcodes():
    import asyncpg
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
    logger.info("Initializing gift codes...")
    async with pool.acquire() as conn:
        added_count = 0
        for code in DEFAULT_GIFT_CODES:
            exists = await conn.fetchval("SELECT 1 FROM gift_codes WHERE code = $1", code['code'])
            if exists:
                logger.info(f"Gift code already exists: {code['code']}")
                continue
            try:
                await conn.execute(
                    """
                    INSERT INTO gift_codes (code, reward_type, reward_value, is_active, usage_limit, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    code['code'],
                    code['reward_type'],
                    code['reward_value'],
                    code['is_active'],
                    code['usage_limit'],
                    datetime.utcnow()
                )
                added_count += 1
                logger.info(f"Added gift code: {code['code']}")
            except Exception as e:
                logger.error(f"Error adding gift code {code['code']}: {e}")
        logger.info(f"Gift code initialization complete! Added {added_count} codes.")
    await pool.close()

if __name__ == "__main__":
    asyncio.run(initialize_giftcodes())
