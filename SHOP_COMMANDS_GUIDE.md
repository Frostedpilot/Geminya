🛍️ SHOP SYSTEM COMMANDS REFERENCE
======================================================================

The complete Discord shop system has been implemented! Here are the available commands:

## 🏪 SHOP COMMANDS

### `/shop [category] [page]`
**Browse the academy shop**
- `category` (optional): Filter by item category (summons, currency, boosts, cosmetics, utility, passes, upgrades)
- `page` (optional): Page number for shop listings (default: 1)

**Features:**
- ✅ Displays user's current currency (💎 Crystals & 🔹 Quartzs)
- ✅ Shows items organized by category with rarity indicators
- ✅ Interactive navigation with Previous/Next/Refresh buttons
- ✅ Item details include ID, name, price, requirements, and description
- ✅ Pagination for large item lists (8 items per page)

### `/buy <item_id> [quantity]`
**Purchase an item from the shop**
- `item_id` (required): The ID number of the item to purchase
- `quantity` (optional): Number of items to buy (default: 1)

**Features:**
- ✅ Automatic currency detection (Crystals vs Quartzs)
- ✅ Requirements checking (rank, level, etc.)
- ✅ Sufficient funds validation
- ✅ Atomic transactions with rollback on failure
- ✅ Purchase confirmation with updated balance
- ✅ Item effects display

### `/inventory [page]`
**View your purchased items**
- `page` (optional): Page number for inventory listings (default: 1)

**Features:**
- ✅ Shows all owned items with quantities
- ✅ Rarity indicators and acquisition dates
- ✅ Active/expired status tracking
- ✅ Pagination for large inventories (10 items per page)

### `/purchase_history [limit]`
**View your purchase history**
- `limit` (optional): Number of recent purchases to show (1-50, default: 20)

**Features:**
- ✅ Complete transaction history
- ✅ Purchase dates and amounts
- ✅ Transaction status tracking
- ✅ Currency type indicators

## 💰 CURRENCY SYSTEM

### 💎 Sakura Crystals
- **Primary currency** for regular shop items
- Earned through daily login (500 per day)
- Starting amount: 2,000 crystals
- Used for: Summon tickets, boosts, decorations, passes, expansions

### 🔹 Quartzs
- **Premium currency** earned from max constellation waifus
- Conversion rates when constellation 7+ is pulled:
  - 1★ waifu = 1 quartz
  - 2★ waifu = 2 quartzs
  - 3★ waifu = 5 quartzs
  - 4★ waifu = 15 quartzs
  - 5★ waifu = 50 quartzs
- Used for: Premium items, rare cosmetics, constellation enhancers

## 🛒 SHOP CATEGORIES

### 📦 Summons (💎/🔹)
- Multi-Summon Ticket (90💎) - 10 summons for price of 9
- Rare Summon Catalyst (300💎) - Boost 4★/5★ rates
- Premium Waifu Selector (25🔹) - Choose any 5★ waifu

### 💰 Currency (💎)
- Daily Crystal Pack (100💎) - Get 500 bonus crystals

### ⚡ Boosts (💎)
- Bond Accelerator (150💎) - 2x bond gains for 24 hours

### 🎨 Cosmetics (💎/🔹)
- Academy Decoration (200💎) - Customize academy appearance
- Golden Avatar Frame (10🔹) - Exclusive golden profile frame
- Legendary Title (20🔹) - "Waifu Master" title

### 🔧 Utility (💎)
- Waifu Name Tag (75💎) - Give custom nicknames to waifus

### 🎫 Passes (💎)
- Crystal Mining Pass (500💎) - Double daily rewards for 7 days

### 📈 Upgrades (💎/🔹)
- Academy Expansion (1000💎) - Increase collection limit by 50
- Constellation Enhancer (15🔹) - Upgrade any waifu's constellation

## 🎯 FEATURES

### ✅ Dual Currency Support
- Automatic detection of item currency type
- Separate balance tracking for both currencies
- Currency-specific purchase validation

### ✅ Requirements System
- Rank/level requirements for premium items
- Automatic validation before purchase
- Clear error messages for unmet requirements

### ✅ Interactive UI
- Pagination with navigation buttons
- Real-time balance updates
- Rich embed displays with emojis and formatting

### ✅ Purchase Protection
- Atomic transactions with rollback
- Duplicate purchase prevention
- Transaction history tracking

### ✅ Inventory Management
- Item quantity tracking
- Expiration date support
- Active/inactive status

======================================================================
🎉 The shop system is fully integrated and ready for use!
Players can now earn quartzs through constellation 7+ pulls and spend
them on exclusive premium items not available for regular crystals.
======================================================================
