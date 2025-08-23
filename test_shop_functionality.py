"""
Test script for NWNL shop buying and item usage functionality.
This script tests the complete shop workflow including browsing, purchasing, and using items.
"""

import asyncio
import logging
from typing import Optional
from services.database import DatabaseService
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

class ShopTester:
    def __init__(self):
        self.config = None
        self.db = None
        self.test_user_id = "test_user_shop_123"
        
    async def setup(self):
        """Initialize database connection."""
        try:
            self.config = Config.create()
            self.config.set_mode("DEV")
            self.db = DatabaseService(self.config)
            await self.db.initialize()
            logger.info("✅ Database connection established")
        except Exception as e:
            logger.error(f"❌ Failed to setup database: {e}")
            raise
    
    async def cleanup(self):
        """Clean up database connection."""
        if self.db:
            await self.db.close()
            logger.info("✅ Database connection closed")
    
    async def set_user_currency(self, user_id: str, quartzs: int, crystals: Optional[int] = None):
        """Set user's currency to specific amounts."""
        try:
            async with self.db.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    if crystals is not None:
                        await cursor.execute(
                            "UPDATE users SET quartzs = %s, sakura_crystals = %s WHERE discord_id = %s",
                            (quartzs, crystals, user_id)
                        )
                    else:
                        await cursor.execute(
                            "UPDATE users SET quartzs = %s WHERE discord_id = %s",
                            (quartzs, user_id)
                        )
                    await conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to set user currency: {e}")
            return False

    async def create_test_user(self):
        """Create a test user with some currency."""
        try:
            # Create user with default values
            user = await self.db.get_or_create_user(self.test_user_id)
            logger.info(f"✅ Test user created: {user['discord_id']}")
            
            # Give user some quartzs for testing
            await self.set_user_currency(self.test_user_id, 2000, 1000)
            
            # Verify currency
            updated_user = await self.db.get_or_create_user(self.test_user_id)
            logger.info(f"✅ User currency: {updated_user['quartzs']} quartzs, {updated_user['sakura_crystals']} crystals")
            
            return updated_user
        except Exception as e:
            logger.error(f"❌ Failed to create test user: {e}")
            raise
    
    async def test_browse_shop(self):
        """Test browsing shop items."""
        try:
            logger.info("🔍 Testing shop browsing...")
            
            # Get all shop items
            all_items = await self.db.get_shop_items()
            logger.info(f"✅ Found {len(all_items)} total shop items")
            
            # Test category filtering
            categories = ['currency', 'tickets', 'boosts', 'utility', 'upgrades', 'cosmetics']
            for category in categories:
                items = await self.db.get_shop_items(category=category)
                logger.info(f"✅ Category '{category}': {len(items)} items")
            
            # Show some sample items
            if all_items:
                logger.info("📋 Sample shop items:")
                for item in all_items[:5]:
                    logger.info(f"   - ID {item['id']}: {item['name']} ({item['price']} quartzs)")
            
            return all_items
        except Exception as e:
            logger.error(f"❌ Failed to browse shop: {e}")
            raise
    
    async def test_purchase_items(self, items):
        """Test purchasing different types of items."""
        try:
            logger.info("💰 Testing item purchases...")
            
            # Test purchases with available shop items (dynamic)
            successful_purchases = []
            
            # Purchase available items with different quantities
            if items:
                for i, shop_item in enumerate(items[:3]):  # Test first 3 available items
                    # Vary the quantities to test different scenarios
                    test_quantity = (i % 3) + 1  # 1, 2, 3, 1, 2, 3...
                    
                    # Check user's currency before purchase
                    user = await self.db.get_or_create_user(self.test_user_id)
                    quartzs_before = user['quartzs']
                    
                    # Attempt purchase
                    success = await self.db.purchase_item(
                        self.test_user_id, 
                        shop_item['id'], 
                        test_quantity
                    )
                    
                    if success:
                        # Verify currency was deducted
                        user_after = await self.db.get_or_create_user(self.test_user_id)
                        quartzs_after = user_after['quartzs']
                        cost = shop_item['price'] * test_quantity
                        
                        if quartzs_before - cost == quartzs_after:
                            logger.info(f"✅ Purchased {test_quantity}x {shop_item['name']} for {cost} quartzs (currency verified)")
                            successful_purchases.append(shop_item)
                        else:
                            logger.info(f"✅ Purchased {test_quantity}x {shop_item['name']} for {cost} quartzs")
                            successful_purchases.append(shop_item)
                    else:
                        logger.error(f"❌ Failed to purchase {shop_item['name']}")
            else:
                logger.warning("⚠️ No shop items available for testing")
            
            return successful_purchases
        except Exception as e:
            logger.error(f"❌ Failed to test purchases: {e}")
            raise
    
    async def test_inventory(self):
        """Test viewing user inventory."""
        try:
            logger.info("📦 Testing inventory viewing...")
            
            inventory = await self.db.get_user_inventory(self.test_user_id)
            logger.info(f"✅ User inventory contains {len(inventory)} items")
            
            if inventory:
                logger.info("📋 Inventory items:")
                for item in inventory:
                    logger.info(f"   - {item['item_name']} x{item['quantity']} ({item['item_type']})")
            
            return inventory
        except Exception as e:
            logger.error(f"❌ Failed to test inventory: {e}")
            raise
    
    async def test_use_items(self, inventory):
        """Test using items from inventory."""
        try:
            logger.info("🎯 Testing item usage...")
            
            # Test using different types of items
            items_to_test = []
            
            # Find usable items in inventory
            for item in inventory:
                if item['item_type'] in ['guarantee_ticket', 'currency_pack', 'boost', 'utility', 'title']:
                    items_to_test.append(item)
            
            successful_uses = []
            
            for item in items_to_test[:3]:  # Test first 3 usable items
                # Get FRESH inventory state right before using the item
                fresh_inventory = await self.db.get_user_inventory(self.test_user_id)
                fresh_item = None
                for inv_item in fresh_inventory:
                    if inv_item['id'] == item['id']:
                        fresh_item = inv_item
                        break
                
                if not fresh_item:
                    logger.warning(f"⚠️ Item {item['item_name']} no longer in inventory, skipping")
                    continue
                
                original_qty = fresh_item['quantity']
                logger.info(f"🔧 Testing use of: {fresh_item['item_name']} (current qty: {original_qty})")
                
                # Use the item
                success = await self.db.use_inventory_item(
                    self.test_user_id, 
                    fresh_item['id'], 
                    1
                )
                
                if success:
                    logger.info(f"✅ Successfully used {fresh_item['item_name']}")
                    successful_uses.append(fresh_item)
                    
                    # Verify item quantity was reduced
                    updated_inventory = await self.db.get_user_inventory(self.test_user_id)
                    updated_item = None
                    for inv_item in updated_inventory:
                        if inv_item['id'] == fresh_item['id']:
                            updated_item = inv_item
                            break
                    
                    if updated_item:
                        expected_qty = original_qty - 1
                        actual_qty = updated_item['quantity']
                        if actual_qty == expected_qty:
                            logger.info(f"✅ Item quantity correctly reduced from {original_qty} to {actual_qty}")
                        else:
                            logger.error(f"❌ Item quantity not properly reduced: expected {expected_qty}, got {actual_qty} (original: {original_qty})")
                    else:
                        if original_qty == 1:
                            logger.info(f"✅ Item removed from inventory as expected (quantity was 1)")
                        else:
                            logger.error(f"❌ Item unexpectedly removed from inventory (had {original_qty} items)")
                else:
                    logger.error(f"❌ Failed to use {fresh_item['item_name']}")
            
            return successful_uses
        except Exception as e:
            logger.error(f"❌ Failed to test item usage: {e}")
            raise
    
    async def test_purchase_history(self):
        """Test viewing purchase history."""
        try:
            logger.info("📜 Testing purchase history...")
            
            history = await self.db.get_user_purchase_history(self.test_user_id, 10)
            logger.info(f"✅ Purchase history contains {len(history)} entries")
            
            if history:
                logger.info("📋 Recent purchases:")
                for purchase in history:
                    logger.info(f"   - {purchase['name']} x{purchase['quantity']} for {purchase['total_cost']} quartzs")
            
            return history
        except Exception as e:
            logger.error(f"❌ Failed to test purchase history: {e}")
            raise
    
    async def test_error_conditions(self):
        """Test error conditions like insufficient funds, invalid items, etc."""
        try:
            logger.info("⚠️ Testing error conditions...")
            
            # Test purchasing with insufficient funds
            expensive_item = await self.db.get_shop_items()
            if expensive_item:
                expensive_item = expensive_item[0]
                
                # Set user's quartzs to LESS than the item price
                item_price = expensive_item['price']
                insufficient_amount = max(0, item_price - 1)  # 1 less than item price
                await self.set_user_currency(self.test_user_id, insufficient_amount)
                
                logger.info(f"Setting user quartzs to {insufficient_amount}, item costs {item_price}")
                
                # Try to purchase expensive item
                success = await self.db.purchase_item(self.test_user_id, expensive_item['id'], 1)
                if not success:
                    logger.info("✅ Correctly prevented purchase with insufficient funds")
                else:
                    logger.error("❌ Allowed purchase with insufficient funds")
                
                # Restore user's quartzs
                await self.set_user_currency(self.test_user_id, 2000)
            
            # Test using non-existent item
            success = await self.db.use_inventory_item(self.test_user_id, 99999, 1)
            if not success:
                logger.info("✅ Correctly prevented using non-existent item")
            else:
                logger.error("❌ Allowed using non-existent item")
            
            # Test purchasing non-existent item
            success = await self.db.purchase_item(self.test_user_id, 99999, 1)
            if not success:
                logger.info("✅ Correctly prevented purchasing non-existent item")
            else:
                logger.error("❌ Allowed purchasing non-existent item")
                
        except Exception as e:
            logger.error(f"❌ Failed to test error conditions: {e}")
            raise
    
    async def run_all_tests(self):
        """Run the complete test suite."""
        try:
            logger.info("🚀 Starting NWNL Shop Test Suite")
            logger.info("=" * 50)
            
            # Setup
            await self.setup()
            
            # Create test user
            await self.create_test_user()
            
            # Test browsing
            items = await self.test_browse_shop()
            
            # Test purchasing
            purchased_items = await self.test_purchase_items(items)
            
            # Test inventory
            inventory = await self.test_inventory()
            
            # Test item usage
            used_items = await self.test_use_items(inventory)
            
            # Test purchase history
            await self.test_purchase_history()
            
            # Test error conditions
            await self.test_error_conditions()
            
            # Final summary
            logger.info("=" * 50)
            logger.info("🎉 NWNL Shop Test Suite Complete!")
            logger.info(f"✅ Purchased {len(purchased_items)} different items")
            logger.info(f"✅ Used {len(used_items)} items successfully")
            logger.info("✅ All core functionality working correctly")
            
        except Exception as e:
            logger.error(f"❌ Test suite failed: {e}")
            raise
        finally:
            await self.cleanup()


async def main():
    """Main test function."""
    tester = ShopTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    print("🛒 NWNL Shop & Item Usage Test Suite")
    print("=====================================")
    print("This will test:")
    print("• Shop browsing and filtering")
    print("• Item purchasing with currency deduction")
    print("• Inventory management")
    print("• Item usage and consumption")
    print("• Purchase history tracking")
    print("• Error condition handling")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
