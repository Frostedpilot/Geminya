# World Threat Reward System

## Overview
The World Threat reward system has three tiers of rewards that are automatically distributed to players:

1. **Immediate Rewards** - Given instantly after each fight based on points scored
2. **Personal Checkpoint Rewards** - Given when player reaches cumulative point milestones
3. **Server Checkpoint Rewards** - Given when entire server reaches cumulative point milestones

## Reward Types
All rewards consist of 4 possible components:
- **Crystals (Sakura Crystals)** - Primary currency
- **Quartzs** - Secondary currency  
- **Daphine** - Special currency for awakening characters
- **Items** - Equipment or other loot (configured as list of `(item_id, quantity)` tuples)

## Immediate Rewards

Immediate rewards are tiered based on the **points scored in a single fight action**. The player receives the highest tier they qualify for.

| Min Points | Crystals | Quartzs | Daphine | Items |
|-----------|----------|---------|---------|-------|
| 50,000+ | 5,000 | 50 | 5 | - |
| 25,000+ | 2,500 | 25 | 3 | - |
| 10,000+ | 1,000 | 10 | 1 | - |
| 5,000+ | 500 | 5 | 0 | - |
| 1,000+ | 200 | 2 | 0 | - |
| 0+ | 100 | 1 | 0 | - |

### Awakened Multiplier
**Crystal rewards** from immediate rewards are multiplied by `1.2^awakened_count` where `awakened_count` is the number of awakened characters in the fighting team (0-6).

**Example:** If you score 30,000 points with 3 awakened characters:
- Base tier: 2,500 crystals (25k+ tier)
- Awakened multiplier: 1.2^3 = 1.728
- **Final crystals: 4,320**
- Quartzs: 25 (not affected by awakened)
- Daphine: 3 (not affected by awakened)

## Personal Checkpoint Rewards

Personal checkpoints are based on **cumulative points** across all your fights. Each checkpoint can only be claimed once per boss cycle.

| Cumulative Points | Crystals | Quartzs | Daphine | Items |
|-------------------|----------|---------|---------|-------|
| 500,000 | 50,000 | 100 | 50 | - |
| 250,000 | 25,000 | 50 | 25 | - |
| 100,000 | 10,000 | 25 | 10 | - |
| 50,000 | 5,000 | 10 | 5 | - |
| 25,000 | 2,500 | 5 | 2 | - |
| 10,000 | 1,000 | 2 | 1 | - |

**Note:** Personal checkpoint rewards are NOT affected by awakened multiplier.

## Server Checkpoint Rewards

Server checkpoints are based on the **total cumulative points of all players** on the server. Each checkpoint can only be claimed once per boss cycle per player.

| Server Total Points | Crystals | Quartzs | Daphine | Items |
|---------------------|----------|---------|---------|-------|
| 10,000,000 | 100,000 | 500 | 100 | - |
| 5,000,000 | 50,000 | 250 | 50 | - |
| 1,000,000 | 25,000 | 100 | 25 | - |
| 500,000 | 10,000 | 50 | 10 | - |
| 100,000 | 5,000 | 25 | 5 | - |

**Note:** Server checkpoint rewards are NOT affected by awakened multiplier.

## Distribution Mechanism

Rewards are distributed automatically using these database methods:
- **Crystals:** `database.update_user_crystals(discord_id, amount)`
- **Quartzs:** `database.update_user_quartzs(discord_id, amount)`
- **Daphine:** `waifu_service.add_daphine(discord_id, amount)`
- **Items:** `database.distribute_loot_rewards(discord_id, items)`

Distribution happens immediately when conditions are met:
1. **Immediate rewards:** Given at end of fight action
2. **Personal checkpoints:** Checked and granted at end of fight action
3. **Server checkpoints:** Checked and granted at end of fight action

## Configuration

All reward tiers are defined as constants at the top of `WorldThreatService` class for easy editing:

```python
# services/world_threat_service.py

# Immediate reward tiers
IMMEDIATE_REWARD_TIERS = [
    (50000, {"crystals": 5000, "quartzs": 50, "daphine": 5, "items": []}),
    # ... more tiers
]

# Personal checkpoint rewards
PERSONAL_CHECKPOINT_REWARDS = {
    500000: {"crystals": 50000, "quartzs": 100, "daphine": 50, "items": []},
    # ... more checkpoints
}

# Server checkpoint rewards  
SERVER_CHECKPOINT_REWARDS = {
    10000000: {"crystals": 100000, "quartzs": 500, "daphine": 100, "items": []},
    # ... more checkpoints
}
```

To add item rewards, modify the `"items"` field with a list of tuples:
```python
"items": [(item_id_1, quantity_1), (item_id_2, quantity_2)]
```

## Example Scenario

**Player fights with 4 awakened characters and scores 35,000 points (cumulative total now 120,000):**

### Immediate Rewards:
- Base tier: 25,000+ tier (2,500 crystals, 25 quartzs, 3 daphine)
- Awakened bonus: 1.2^4 = 2.0736
- **Received:** 5,184 crystals, 25 quartzs, 3 daphine

### Personal Checkpoints Claimed:
If this is their first time reaching these thresholds:
- 100,000 checkpoint: 10,000 crystals, 25 quartzs, 10 daphine

### Total Received This Fight:
- **15,184 crystals**
- **50 quartzs**  
- **13 daphine**

## Reset Behavior

- Boss resets daily at **00:00 UTC+7**
- All checkpoints reset when boss resets
- Cumulative points reset to 0
- Players can claim all checkpoints again for the new boss
