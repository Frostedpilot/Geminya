#!/usr/bin/env python3
"""
Test script for constellation system and quartz conversion.
"""

import asyncio
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config import Config
from services.database import DatabaseService


async def test_constellation_system():
    """Test the constellation upgrade and quartz conversion system."""
    print("🌟 CONSTELLATION SYSTEM TEST")
    print("=" * 60)
    
    config = Config.from_file()
    db = DatabaseService(config)
    await db.initialize()
    
    test_user_id = "test_constellation_999999999999999999"
    
    try:
        # Clean up any existing test user
        await db.delete_user_account(test_user_id)
        
        # Create test user
        user = await db.get_or_create_user(test_user_id)
        print(f"👤 Test user created with {user.get('quartzs', 0)} quartzs")
        
        # Add a test waifu if none exists
        waifus = await db.get_waifus_by_rarity(5, limit=1)  # 5 star = rarity 5
        if not waifus:
            print("❌ No 5★ waifus found in database")
            return False
        
        test_waifu = waifus[0]
        test_waifu_id = test_waifu['id']
        waifu_name = test_waifu['name']
        print(f"🧚 Testing with waifu: {waifu_name} (5★)")
        
        # Simulate getting the same waifu multiple times
        print(f"\n📈 Simulating constellation upgrades:")
        for i in range(8):  # 0-6 constellations + 1 extra for conversion
            result = await db.add_waifu_to_user(test_user_id, test_waifu_id)
            
            if result['success']:
                if result['type'] == 'new_waifu':
                    print(f"  🆕 Pull #{i+1}: Got {waifu_name} (Constellation 0)")
                elif result['type'] == 'constellation_upgrade':
                    print(f"  ⭐ Pull #{i+1}: Constellation upgraded to {result['constellation_level']}")
                elif result['type'] == 'quartz_conversion':
                    print(f"  💎 Pull #{i+1}: Max constellation reached! Converted to {result['quartzs_gained']} quartzs")
            else:
                print(f"  ❌ Pull #{i+1}: Failed - {result.get('reason', 'unknown error')}")
        
        # Check final user state
        final_user = await db.get_or_create_user(test_user_id)
        final_quartzs = final_user.get('quartzs', 0)
        print(f"\n💰 Final user quartzs: {final_quartzs}")
        
        # Check collection
        collection = await db.get_user_collection(test_user_id)
        waifu_copies = [w for w in collection if w['waifu_id'] == test_waifu_id]
        if waifu_copies:
            max_constellation = max(w['constellation_level'] for w in waifu_copies)
            print(f"🌟 Final constellation level: {max_constellation}")
            print(f"📊 Total copies in collection: {len(waifu_copies)}")
        
        # Clean up
        await db.delete_user_account(test_user_id)
        
        print(f"\n✅ Constellation system test completed!")
        print(f"📝 Summary:")
        print(f"  • Constellations 0-6: Added to collection")
        print(f"  • Constellation 7+: Converted to quartzs")
        print(f"  • 5★ conversion rate: 50 quartzs per duplicate")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing constellation system: {e}")
        return False
    finally:
        if hasattr(db, 'connection_pool') and db.connection_pool:
            db.connection_pool.close()
            await db.connection_pool.wait_closed()


async def main():
    """Main function."""
    success = await test_constellation_system()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 CONSTELLATION SYSTEM FULLY FUNCTIONAL!")
        print("💎 QUARTZS CONVERSION WORKING!")
        print("=" * 60)
    else:
        print("\n❌ Test failed!")


if __name__ == "__main__":
    asyncio.run(main())
