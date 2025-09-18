# Expedition System Discord Commands

The expedition system provides an immersive adventure experience where players can send their characters on various expeditions to earn rewards. Here's a complete guide to the available Discord commands.

## Commands Overview

All expedition commands use the `/nwnl_expeditions_` prefix and are implemented as Discord slash commands.

### 📋 Available Commands

1. **`/nwnl_expeditions_list`** - View and start available expeditions
2. **`/nwnl_expeditions_status`** - Check current expedition progress
3. **`/nwnl_expeditions_complete`** - Complete finished expeditions and claim rewards
4. **`/nwnl_expeditions_logs`** - View expedition history and detailed logs

## Command Details

### 🗺️ `/nwnl_expeditions_list`
**Description:** View and start available expeditions

**Features:**
- Interactive expedition selection menu
- Detailed expedition information (duration, difficulty, encounters)
- Character team selection interface
- Real-time expedition starting

**Usage Flow:**
1. Use the command to see all available expeditions
2. Select an expedition from the dropdown menu
3. Choose up to 3 characters for your expedition team
4. Confirm and start the expedition

**Expedition Information Displayed:**
- **Name & Description:** What the expedition is about
- **Duration:** How long the expedition takes (in hours)
- **Difficulty Tier:** From 1 (easy) to 20+ (very hard)
- **Expected Encounters:** Approximate number of battles
- **Potential Rewards:** Types of rewards you can earn

### 📊 `/nwnl_expeditions_status`
**Description:** Check your current expedition status and progress

**Features:**
- Shows all active expeditions
- Displays time remaining or completion status
- Lists expedition team members
- Real-time countdown for expedition completion

**Status Information:**
- **Expedition Name:** Current expedition being undertaken
- **Time Remaining:** Hours and minutes left, or "READY TO COMPLETE!"
- **Team Members:** Characters on the expedition with their star levels
- **Progress Indicator:** Visual indication of expedition status

### 🏆 `/nwnl_expeditions_complete`
**Description:** Complete finished expeditions and claim rewards

**Features:**
- Automatically completes all ready expeditions
- Detailed reward breakdown per expedition
- Total rewards summary
- Expedition outcome indication (Success/Great Success/Perfect)

**Reward Types:**
- **💎 Sakura Crystals:** Primary currency for summoning
- **💠 Quartzs:** Premium currency for special purchases
- **📦 Items:** Equipment, consumables, and special items
- **Experience:** Character and account progression

**Outcome Types:**
- **👍 Success:** Standard completion with base rewards
- **✅ Great Success:** Enhanced rewards with bonus items
- **🌟 Perfect:** Maximum rewards with rare item chances

### 📜 `/nwnl_expeditions_logs`
**Description:** View your expedition history and detailed logs

**Features:**
- Last 10 completed expeditions
- Historical reward tracking
- Completion timestamps
- Summary statistics

**Log Information:**
- **Expedition Name:** What expedition was completed
- **Completion Time:** When the expedition finished (relative time)
- **Outcome:** How well the expedition went
- **Rewards Earned:** What was gained from the expedition
- **Total Statistics:** Lifetime expedition stats

## User Interface Features

### Interactive Selection Menus
- **Expedition Dropdown:** Browse available expeditions with difficulty indicators
- **Character Selection:** Multi-select menu for choosing expedition team members
- **Character Information:** Star level, bond level, and series information

### Rich Embeds
- **Color-coded Information:** Different colors for different types of information
- **Emoji Indicators:** Visual cues for difficulty, status, and rewards
- **Formatted Data:** Clean, readable presentation of complex information
- **Timestamps:** Discord's native timestamp formatting for times

### Real-time Updates
- **Dynamic Status:** Expedition status updates in real-time
- **Completion Notifications:** Clear indication when expeditions are ready
- **Progress Tracking:** Visual progress indicators and countdowns

## Tips for Players

### Character Selection Strategy
- **Mix Star Levels:** Combine high-star characters with lower ones for balanced teams
- **Consider Bond Levels:** Higher bond levels may improve expedition outcomes
- **Team Composition:** While not required, diverse teams can be more effective

### Timing Management
- **Plan Ahead:** Consider expedition duration when planning your gaming session
- **Multiple Expeditions:** You can run multiple expeditions simultaneously
- **Check Regularly:** Use status command to track multiple expedition progress

### Reward Optimization
- **Difficulty vs. Risk:** Higher difficulty expeditions offer better rewards but may have lower success rates
- **Complete Promptly:** Claim rewards as soon as expeditions finish
- **History Tracking:** Use logs to track your most successful expedition types

## Error Handling

The system includes comprehensive error handling for common issues:

- **No Characters Available:** Clear message if user has no characters to send
- **Database Connection Issues:** Graceful degradation with user-friendly error messages
- **Invalid Selections:** Prevention of invalid character or expedition choices
- **Rate Limiting:** Built-in protection against command spam

## Technical Features

### Performance Optimizations
- **Local Character Data:** Uses CSV files for character information to reduce database load
- **Minimal Database Queries:** Only essential data is retrieved from the database
- **Efficient UI Components:** Optimized Discord UI components for smooth interaction

### Security & Validation
- **User Verification:** Only command initiators can interact with their expedition UI
- **Input Validation:** All user inputs are validated before processing
- **Error Recovery:** Robust error handling prevents system crashes

### Integration
- **Database Synchronization:** Real-time sync with PostgreSQL database
- **Character Registry:** Integration with character management system
- **Reward System:** Seamless integration with currency and inventory systems

## Future Enhancements

Potential future features may include:
- Expedition difficulty scaling based on character levels
- Special event expeditions with unique rewards
- Guild expeditions for collaborative gameplay
- Expedition equipment and preparation systems

---

*For technical support or bug reports, please contact the development team. The expedition system is actively maintained and regularly updated with new features and improvements.*