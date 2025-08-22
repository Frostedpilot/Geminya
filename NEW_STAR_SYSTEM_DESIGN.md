# 🌟 New Star System Design - Shard-Based Star Upgrade System

## 📋 Overview

This document outlines the complete redesign of the rarity system, replacing the traditional constellation levels with a star upgrade system using shards earned from duplicate pulls.

## 🎯 Core Changes

### Old System vs New System

| Aspect | Old System | New System |
|--------|------------|------------|
| **Gacha Coverage** | 1-5 star pulls | 1-3 star pulls only |
| **Higher Rarities** | Direct summon | Upgrade with shards |
| **Duplicates** | Constellation levels (C0-C6) | Shard rewards |
| **Pity System** | 90 pulls = 5★, 10 pulls = 4★ | 90 pulls = 3★, 10 pulls = 2★ |
| **Gacha Rates** | 0.6/2.0/25.0/35.0/37.4 | 5/20/75 |

## 🎰 New Gacha System

### Gacha Rates
- **3★ (Rare)**: 5% chance
- **2★ (Common)**: 20% chance  
- **1★ (Basic)**: 75% chance

### Pity System
- **90-pull pity**: Guaranteed 3★ (replaces old 5★ pity)
- **10-pull guarantee**: Guaranteed 2★ minimum (replaces old 4★ guarantee)
- **Multi-summon**: 10 rolls with guaranteed 2★ on 10th roll if none obtained

## ⭐ Star Upgrade System

### Star Progression
Characters can be upgraded from their base rarity (1-3★) up to 5★ maximum:
- **1★ → 2★**: 50 shards
- **2★ → 3★**: 100 shards
- **3★ → 4★**: 200 shards
- **4★ → 5★**: 300 shards

### Shard Rewards (Per Duplicate)
When pulling a duplicate character, players receive shards based on the **pulled character's rarity**:
- **3★ duplicate**: 90 shards
- **2★ duplicate**: 20 shards
- **1★ duplicate**: 5 shards

### Automatic Upgrades
**Key Feature**: Characters automatically upgrade immediately after receiving shards from pulls if they have sufficient shards for the next star level. This happens in real-time during the summon process:

1. **Pull Duplicate** → Receive shards based on pulled rarity
2. **Check Upgrade** → System automatically checks if upgrade is possible
3. **Auto Upgrade** → Character upgrades instantly if shards are sufficient
4. **Chain Upgrades** → Can upgrade multiple star levels in one pull if enough shards
5. **Excess Conversion** → Any remaining shards at 5★ convert to quartz

**Example**: If a 3★ character has 180 shards and you pull another 3★ duplicate (+90 shards = 270 total), the character will automatically upgrade from 3★ to 4★ (costs 200 shards), leaving 70 shards remaining.

### Excess Shard Conversion
Once a character reaches 5★ (maximum), any additional shards for that character convert to **Quartz** at a 1:1 ratio.

## 💎 Currency System Updates

### Sakura Crystals
- Remains the primary gacha currency
- Cost per summon: 10 crystals (unchanged)
- Multi-summon: 100 crystals for 10 pulls (unchanged)

### Quartz System Revision
- **New Source**: Excess shards from max-star characters (1 shard = 1 quartz)
- **Usage**: Premium shop items, special upgrades

### New Currency: Character Shards
- **Individual per character**: Each character has their own shard type
- **Non-transferable**: Cannot use Character A's shards for Character B
- **Primary purpose**: Star upgrades only

## 🗄️ Database Schema Changes

### Users Table Updates
```sql
-- No changes required to users table
-- sakura_crystals and quartzs remain the same
```

### User Waifus Table Updates
```sql
ALTER TABLE user_waifus 
ADD COLUMN current_star_level INT DEFAULT NULL,
ADD COLUMN character_shards INT DEFAULT 0;

-- Migration: Set current_star_level to waifu's base rarity for existing entries
UPDATE user_waifus uw 
SET current_star_level = (
    SELECT w.rarity 
    FROM waifus w 
    WHERE w.id = uw.waifu_id
) 
WHERE current_star_level IS NULL;
```

### New Table: Character Shards Tracking
```sql
CREATE TABLE IF NOT EXISTS user_character_shards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    waifu_id INT NOT NULL,
    shard_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (waifu_id) REFERENCES waifus(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_waifu (user_id, waifu_id),
    INDEX idx_user_shards (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## 🔧 Implementation Details

### Service Layer Changes

#### WaifuService Updates
```python
class WaifuService:
    # Updated gacha rates
    GACHA_RATES = {
        3: 5.0,    # 3-star: 5%
        2: 20.0,   # 2-star: 20%
        1: 75.0,   # 1-star: 75%
    }
    
    # Updated pity system
    PITY_3_STAR = 90   # Guaranteed 3-star every 90 pulls
    PITY_2_STAR = 10   # Guaranteed 2-star every 10 pulls
    
    # Shard rewards per star level
    SHARD_REWARDS = {
        3: 90,  # 3-star dupe = 90 shards
        2: 20,  # 2-star dupe = 20 shards
        1: 5,   # 1-star dupe = 5 shards
    }
    
    # Upgrade costs per star level
    UPGRADE_COSTS = {
        2: 50,   # 1→2 star: 50 shards
        3: 100,  # 2→3 star: 100 shards
        4: 200,  # 3→4 star: 200 shards
        5: 300,  # 4→5 star: 300 shards
    }
```

#### New Methods Required

```python
async def add_character_shards(self, discord_id: str, waifu_id: int, amount: int) -> int:
    """Add shards for a specific character. Returns new total."""
    
async def get_character_shards(self, discord_id: str, waifu_id: int) -> int:
    """Get current shard count for a specific character."""
    
async def upgrade_character_star(self, discord_id: str, waifu_id: int) -> Dict[str, Any]:
    """Upgrade a character's star level using shards."""
    
async def convert_excess_shards_to_quartz(self, discord_id: str, waifu_id: int, excess_shards: int) -> int:
    """Convert excess shards to quartz for max-star characters."""
```

### Database Service Updates

```python
async def handle_duplicate_pull(self, discord_id: str, waifu_id: int) -> Dict[str, Any]:
    """Handle duplicate character pull with new shard system."""
    # 1. Get character's current star level from user_waifus
    # 2. Calculate shard reward based on current star level
    # 3. Add shards to user_character_shards table
    # 4. If character is 5-star, convert excess shards to quartz
    # 5. Return pull result with shard information
```

## 🎮 User Experience Changes

### Summon Results Display
```
🎰 Summon Result:
⭐⭐ Rem (Re:Zero) - 2-Star
🆕 NEW character added to collection!

🔹 +20 Character Shards earned!
📊 Total Rem shards: 20/100 (needs 80 more for 3⭐ upgrade)
```

### Collection Display Updates
```
📚 Your Collection:
⭐⭐⭐ Rem (Re:Zero) - 3-Star [C0]
🔹 Shards: 45/200 (for 4⭐ upgrade)
💖 Bond Level: 5

⭐⭐⭐⭐⭐ Emilia (Re:Zero) - 5-Star MAX [C0]
✨ All upgrades complete!
🔹 Excess shards convert to Quartz
```

### New Commands Required

```
/nwnl_upgrade <character_name> - Upgrade character star level using shards
/nwnl_shards [character_name] - View shard counts (all or specific character)
/nwnl_shard_shop - Browse items purchasable with different shard types
```

## 📊 Balancing Considerations

### Shard Economy Balance
- **1★ Character**: 5 shards/dupe → needs 10 dupes to reach 2★ (50 shards)
- **2★ Character**: 20 shards/dupe → needs 5 dupes to reach 3★ (100 shards)  
- **3★ Character**: 90 shards/dupe → needs 3 dupes to reach 4★ (200 shards + 70 excess)

### Progression Curve
- **Early Game**: Focus on 1★→2★ upgrades (affordable at 50 shards)
- **Mid Game**: 2★→3★ upgrades (100 shards, moderate cost)
- **Late Game**: 3★→4★ and 4★→5★ upgrades (200-300 shards, premium investment)

### Quartz Generation
With the new system, quartz becomes more valuable and harder to obtain:
- Only from excess shards of 5★ characters
- Creates long-term progression goal

## 🔄 Migration Strategy

### Phase 1: Database Migration
1. Add new columns to `user_waifus` table
2. Create `user_character_shards` table
3. Migrate existing data (set `current_star_level` to base rarity)

### Phase 2: Service Updates
1. Update `WaifuService` with new rates and logic
2. Implement shard tracking methods
3. Update duplicate handling logic

### Phase 3: Command Updates
1. Update summon result displays
2. Modify collection viewing commands
3. Add new upgrade and shard management commands

### Phase 4: Testing & Deployment
1. Test all upgrade paths thoroughly
2. Verify shard economy balance
3. Deploy with announcement to users

## 🚨 Breaking Changes

### User Impact
- **Constellation system removed**: C0-C6 replaced with star upgrades
- **Gacha rates changed**: No more direct 4★/5★ pulls
- **Pity system adjusted**: 3★ and 2★ guarantees instead of 5★/4★
- **Automatic upgrades**: Characters upgrade immediately after pulls

### Backwards Compatibility
- Existing collections preserved with current star levels
- All existing characters retain their current rarities as starting points

## ✅ Implementation Checklist

### Database
- [ ] Create migration script for schema changes
- [ ] Add new `user_character_shards` table
- [ ] Update `user_waifus` with new columns
- [ ] Test migration with backup data

### Services
- [ ] Update `WaifuService` gacha rates
- [ ] Implement shard tracking methods
- [ ] Update duplicate handling logic
- [ ] Add star upgrade functionality

### Commands
- [ ] Update summon result displays
- [ ] Modify collection commands
- [ ] Create upgrade command
- [ ] Create shard management commands

### Documentation
- [ ] Update user guides
- [ ] Create migration announcement
- [ ] Update help commands
- [ ] Document new features

## 🎯 Success Metrics

### Engagement Goals
- Increased long-term retention through upgrade progression
- More meaningful duplicate pulls (shards vs simple constellation)
- Enhanced collection management and planning

### Economy Health
- Balanced shard generation vs upgrade costs
- Sustainable quartz economy
- Clear progression paths for all player types

---

*This design maintains the core gacha excitement while adding meaningful progression through the star upgrade system. The shard-based approach gives value to every pull, even low-rarity duplicates, while creating long-term goals for dedicated players.*
