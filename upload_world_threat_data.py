#!/usr/bin/env python3
"""
World-Threat Raid Boss Data Upload Script

This script uploads raid boss templates from JSON to the database.
Only bosses with status "active" will be activated immediately.
Others will be stored as templates for future use.
"""

import asyncio
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def upload_raid_bosses():
    """Upload raid boss data from JSON to database"""
    import asyncpg
    
    logger.info("🔄 World-Threat Raid Boss Upload Script")
    logger.info("=" * 50)
    
    # Load database configuration
    with open('secrets.json', 'r') as f:
        secrets = json.load(f)
    
    pg_config = {
        'host': secrets.get('POSTGRES_HOST', 'localhost'),
        'port': int(secrets.get('POSTGRES_PORT', 5432)),
        'user': secrets.get('POSTGRES_USER'),
        'password': secrets.get('POSTGRES_PASSWORD'),
        'database': secrets.get('POSTGRES_DATABASE'),
    }
    
    # Load raid boss data
    json_file_path = "data/world_threat_bosses.json"
    if not os.path.exists(json_file_path):
        logger.error(f"❌ Error: {json_file_path} not found!")
        return
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    raid_bosses = data.get('raid_bosses', [])
    logger.info(f"📊 Found {len(raid_bosses)} raid boss templates to process")
    
    # Connect to database
    logger.info("Connecting to PostgreSQL database...")
    pool = await asyncpg.create_pool(**pg_config)
    
    try:
        async with pool.acquire() as conn:
            uploaded_count = 0
            skipped_count = 0
            
            for i, boss_data in enumerate(raid_bosses, 1):
                boss_name = boss_data['boss_name']
                raid_name = boss_data['raid_name']
                
                # Check if this raid already exists (by raid_name or boss_name)
                existing = await conn.fetchval(
                    "SELECT id FROM world_threat_raids WHERE raid_name = $1 OR boss_name = $2",
                    raid_name, boss_name
                )
                
                if existing:
                    logger.info(f"⏭️  Skipping {boss_name}: Already exists (ID: {existing})")
                    skipped_count += 1
                    continue
                
                logger.info(f"📥 Uploading boss {i}/{len(raid_bosses)}: {boss_name}")
                
                try:
                    # Prepare raid data for database insertion
                    raid_data = prepare_raid_data(boss_data)
                    
                    # Insert into database
                    raid_id = await conn.fetchval(
                        """
                        INSERT INTO world_threat_raids (
                            raid_name, boss_name, total_hp, current_hp, dominant_stats,
                            initial_weaknesses, initial_resistances, current_weaknesses, current_curses,
                            curse_pool, curse_limits, curse_trigger_threshold, analysis_thresholds,
                            analysis_reward_pool, created_by, description,
                            victory_rewards, analysis_milestone_rewards, status
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
                        RETURNING id
                        """,
                        raid_data['raid_name'], raid_data['boss_name'], raid_data['total_hp'], raid_data['total_hp'],
                        json.dumps(raid_data['dominant_stats']), json.dumps(raid_data['initial_weaknesses']),
                        json.dumps(raid_data['initial_resistances']), json.dumps(raid_data['current_weaknesses']),
                        json.dumps(raid_data['current_curses']), json.dumps(raid_data['curse_pool']),
                        json.dumps(raid_data['curse_limits']), raid_data['curse_trigger_threshold'],
                        json.dumps(raid_data['analysis_thresholds']), json.dumps(raid_data['analysis_reward_pool']),
                        raid_data['created_by'], raid_data['description'],
                        json.dumps(raid_data['victory_rewards']), json.dumps(raid_data['analysis_milestone_rewards']),
                        raid_data['status']
                    )
                    
                    if raid_id:
                        uploaded_count += 1
                        status = raid_data['status']
                        
                        if status == 'active':
                            logger.info(f"   ✅ Uploaded and ACTIVATED: {boss_name} (ID: {raid_id})")
                        else:
                            logger.info(f"   ✅ Uploaded as template: {boss_name} (ID: {raid_id})")
                            
                        # Print some key stats
                        logger.info(f"      HP: {raid_data['total_hp']:,}")
                        logger.info(f"      Dominant Stats: {', '.join(raid_data['dominant_stats'])}")
                        logger.info(f"      Curse Trigger: Every {raid_data['curse_trigger_threshold']} strikes")
                        logger.info(f"      Analysis Thresholds: {len(raid_data['analysis_thresholds'])} milestones")
                        
                    else:
                        logger.error(f"   ❌ Failed to upload: {boss_name}")
                        
                except Exception as e:
                    logger.error(f"   ❌ Error uploading {boss_name}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Summary
            logger.info(f"\n📈 Upload Summary:")
            logger.info(f"   Total uploaded: {uploaded_count}")
            logger.info(f"   Skipped (already exist): {skipped_count}")
            logger.info(f"   Total processed: {uploaded_count + skipped_count}/{len(raid_bosses)}")
            
            if uploaded_count > 0:
                logger.info(f"\n🎯 Raid bosses uploaded successfully!")
            else:
                logger.info(f"\n📚 No new raid bosses to upload.")
                
    except Exception as e:
        logger.error(f"❌ Upload failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await pool.close()
        logger.info("\n🔌 Database connection closed")


def prepare_raid_data(boss_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare boss data for database insertion
    
    Args:
        boss_data: Raw boss data from JSON
    
    Returns:
        Formatted data ready for database insertion
    """
    return {
        'raid_name': boss_data['raid_name'],
        'boss_name': boss_data['boss_name'],
        'total_hp': boss_data['total_hp'],
        'dominant_stats': boss_data['dominant_stats'],
        'initial_weaknesses': boss_data['initial_weaknesses'],
        'initial_resistances': boss_data['initial_resistances'],
        'current_weaknesses': boss_data['initial_weaknesses'].copy(),  # Start with initial weaknesses
        'current_curses': [],  # Start with no curses
        'curse_pool': boss_data['curse_pool'],
        'curse_limits': boss_data['curse_limits'],
        'curse_trigger_threshold': boss_data.get('curse_trigger_threshold', 100),
        'analysis_thresholds': boss_data['analysis_thresholds'],
        'analysis_reward_pool': boss_data['analysis_reward_pool'],
        'status': boss_data.get('status', 'template'),  # Use status from JSON as-is
        'created_by': boss_data.get('created_by', 'upload_script'),
        'description': boss_data.get('description', ''),
        'victory_rewards': boss_data.get('victory_rewards', {}),
        'analysis_milestone_rewards': boss_data.get('analysis_milestone_rewards', {})
    }


if __name__ == "__main__":
    asyncio.run(upload_raid_bosses())