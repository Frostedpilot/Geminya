# World Threat UI Implementation Plan

## Overview
This document provides a comprehensive implementation plan for the World Threat Discord UI, following established patterns from the Expedition system.

---

## File Structure
```
cogs/commands/world_threat.py          # Main cog with slash commands
```

---

## 1. Main Cog: WorldThreatCog

**Location**: `cogs/commands/world_threat.py`

### Slash Commands to Implement

#### `/wt_status` - Main Hub Command
- **Purpose**: Display boss info, personal progress, action buttons
- **Returns**: `StatusView` (interactive embed with buttons)
- **Shows**:
  - Boss name, dominant stats, cursed stat
  - Current buffs/curses (formatted by category)
  - Server total points + next server checkpoint
  - Personal points + next personal checkpoint
  - Research stacks (if any)
  - Cooldown timer (if on cooldown)
  - Adaptation level

#### `/wt_fight` - Initiate Fight
- **Purpose**: Start team selection flow
- **Flow**: Check cooldown → Load available characters → Show `TeamSelectView`
- **Error handling**: No active boss, cooldown active

#### `/wt_research` - Perform Research
- **Purpose**: Quick research action with confirmation
- **Flow**: Check cooldown → Show `ConfirmResearchView` → Execute
- **Returns**: Success message with new stack count

#### `/wt_leaderboard` (Optional, future)
- **Purpose**: Show top contributors
- **Implementation**: Paginated list of top 10-25 players by cumulative points

---

## 2. UI Views

### A. StatusView - Main Hub

**Pattern Reference**: Similar to `ExpeditionListView` but with action buttons

**Class Structure**:
```python
class StatusView(discord.ui.View):
    def __init__(self, boss_data, player_status, user_id, world_threat_service):
        super().__init__(timeout=300.0)
        self.boss_data = boss_data
        self.player_status = player_status
        self.user_id = user_id
        self.world_threat_service = world_threat_service
        # Calculate cooldown remaining
        self._setup_ui()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the command user can interact"""
        return interaction.user.id == self.user_id
    
    # Buttons:
    # - "⚔️ Fight Boss" (disabled if on cooldown or no boss)
    # - "🔬 Research" (disabled if on cooldown or at max stacks)
    # - "🔄 Refresh" (reload current status)
    # - "📊 My Progress" (show personal stats detail)
```

**Embed Structure**:
```
Title: 🌍 World Threat: [Boss Name]
Description: Server-wide cooperative boss battle

Field 1: 📊 Boss Stats
- Dominant Stats: [stat1], [stat2]
- Cursed Stat: [stat]
- Adaptation Level: [level] (0.8^level damage multiplier)

Field 2: 🎯 Active Buffs (Favored Affinities)
- Elemental: Fire, Water
- Archetype: Tank
- Series: [series names]
- Genre: Action

Field 3: 💀 Active Curses (Forbidden)
- Genre: Shounen
- Series: Naruto
- Elemental: Dark

Field 4: 🌐 Server Progress
- Total Points: 1,234,567
- Next Checkpoint: 5,000,000 (3,765,433 to go)

Field 5: 👤 Your Progress
- Your Points: 12,345
- Research Stacks: x2 (next fight x4 multiplier)
- Next Checkpoint: 25,000 (12,655 to go)
- Action: ✅ Ready / ⏳ Resets at midnight (UTC+7)

Footer: Last updated <timestamp>
```

---

### B. TeamSelectView - Character Selection for Fight

**Pattern Reference**: Adapted from `CharacterSelectView` in expeditions

**Key Differences from Expeditions**:
- Select **6 characters** instead of 3
- **Pre-filtered input**: Service already removes cursed characters
- **No equipment**: Simplified, no equipment selection
- Show **series bonus** indicator (all 6 same series)
- Live **point calculation preview** using WT formula
- **Simplified scoring**: Focus on dominant/cursed stats only

**Class Structure**:
```python
class WorldThreatTeamSelectView(discord.ui.View):
    """Character selection for World Threat fights - 6 characters required."""
    
    def __init__(self, available_characters: List[Dict], boss, user_id: int, 
                 world_threat_service, player_status):
        super().__init__(timeout=300.0)
        self.available_characters = available_characters  # Pre-filtered by service
        self.boss = boss
        self.user_id = user_id
        self.world_threat_service = world_threat_service
        self.player_status = player_status
        
        self.selected_characters = []  # Will store waifu_ids, max 6
        self.search_filter = ""
        self.current_page = 0
        self.items_per_page = 25
        self.sorting_mode = 'raw_power'  # or 'buff_count'
        
        self.char_registry = world_threat_service.data_manager.get_character_registry()
        self._setup_ui()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the command user can interact"""
        return interaction.user.id == self.user_id
    
    # UI Components (Row-by-row):
    # Row 1:
    #   - "Sort: Power > Buffs" / "Sort: Buffs > Power" (toggle button)
    #   - "🔍 Search Characters" (opens modal)
    # Row 2:
    #   - Character dropdown (25 items, multi-select up to 6 across pages)
    # Row 3-4:
    #   - "◀️ Prev" | "▶️ Next" (if paginated)
    #   - "❌ Clear Search" (if search active)
    #   - "🗑️ Clear All" (if selections exist)
    #   - "❌ Cancel"
    #   - "⚔️ Start Fight" (disabled until 6 selected)
    
    # Helper methods:
    def _get_filtered_characters(self) -> List[Dict]:
        """Filter by search and sort by chosen mode."""
        
    def _calculate_char_base_power(self, char: Dict) -> float:
        """Calculate (dominant stats - cursed stat) * star_level for a character."""
        
    def _count_buff_matches(self, char: Dict) -> int:
        """Count how many boss buffs this character matches."""
        
    def _calculate_team_power_preview(self) -> Dict:
        """
        Calculate estimated points for current team selection.
        Returns breakdown of base power, multipliers, and final points.
        """
        
    def _format_affinities(self, affinity_dict: Dict, title: str) -> str:
        """Format boss affinities for display."""
```

**Character Display Format** (in dropdown):
```
Label: "⭐3 Naruto Uzumaki [SERIES★]"  # [SERIES★] if contributes to series bonus
Description: "Naruto | Power: 450 | Buffs: 2"
Emoji: "👤"
Default: True/False (if already selected)
```

**Series Bonus Visual Indicator Logic**:
```python
# When creating character options, check if character contributes to series bonus
series_bonus_indicator = ""
if self.selected_characters:
    # Get series of currently selected characters
    selected_series = set()
    for sel_id in self.selected_characters:
        sel_char = next((c for c in self.available_characters 
                        if c['waifu_id'] == sel_id), None)
        if sel_char:
            selected_series.add(sel_char['series_id'])
    
    # If all selections are same series AND this character matches
    if len(selected_series) == 1 and char['series_id'] in selected_series:
        series_bonus_indicator = " [SERIES★]"

label = f"⭐{star_level} {char['name']}{series_bonus_indicator}"
```

**Character Display Format** (in dropdown):
```
Label: ⭐3 Naruto Uzumaki
Description: Naruto | Base: 450 | Buffs: 2 | Str: 80, Spd: 75
Emoji: 👤
```

**Team Preview Embed** (updates as selection changes):
```
Title: 🎯 Select Team to Fight: [Boss Name]
Description: Choose **6 characters** for your attack team

⚠️ *Characters with cursed affinities are pre-filtered*
💡 *Select all from same series for 1.5x bonus!*

Color: 0x9B59B6 (purple)

Field 1: 📊 Boss Stats
- **Dominant Stats:** ATK, SPD
- **Cursed Stat:** INT
- **Adaptation:** Level 2 (0.64x damage)

Field 2: 🎯 Active Buffs
- Elemental: Fire, Water
- Archetype: Tank

Field 3: 🔬 Your Research
- Research Stacks: **2**
- Multiplier: **x4**

Field 4: 👥 Selected (6/6) [only if characters selected]
- ⭐3 Naruto Uzumaki (Naruto) - 2 buffs
- ⭐4 Sasuke Uchiha (Naruto) - 1 buff
- ⭐3 Sakura Haruno (Naruto) - 0 buffs
- ⭐2 Kakashi Hatake (Naruto) - 1 buff
- ⭐4 Itachi Uchiha (Naruto) - 3 buffs
- ⭐3 Jiraiya (Naruto) - 1 buff

Field 5: ⚡ Team Power Estimate [only if 6 selected]
- **Base Power:** 2,450
- **Affinity Bonus:** x1.40 (8 buffs)
- **Series Bonus:** ✅ x1.5 (all from Naruto!)
- **Research:** x4
- **Adaptation:** x0.64

**🔥 Estimated Points: 13,440**

Footer: 156 available | Page 1/7 | Filter: naruto
```

**Point Calculation Formula**:
```python
def _calculate_team_power_preview(self) -> Dict[str, Any]:
    """Calculate estimated points for current team selection."""
    if len(self.selected_characters) != 6:
        return {"valid": False, "message": "Need 6 characters"}
    
    base_power = 0
    buff_count = 0
    series_ids = []
    
    for waifu_id in self.selected_characters:
        char_data = next(
            (c for c in self.available_characters if c['waifu_id'] == waifu_id),
            None
        )
        if char_data:
            stats = char_data.get('stats', {})
            star_level = char_data.get('star_level', 1)
            
            # Sum dominant stats
            for stat in self.boss.dominant_stats:
                base_power += stats.get(stat, 0) * star_level
            
            # Subtract cursed stat
            cursed_stat = self.boss.cursed_stat[0]
            base_power -= stats.get(cursed_stat, 0) * star_level
            
            # Count buffs
            buff_count += self._count_buff_matches(char_data)
            series_ids.append(char_data['series_id'])
    
    # Calculate multipliers
    affinity_mult = 1.0 + (buff_count * 0.2)
    series_mult = 1.5 if len(set(series_ids)) == 1 else 1.0
    research_mult = 2 ** self.player_status.research_stacks
    adaptation_mult = 0.8 ** self.boss.adaptation_level
    
    final_points = int(
        base_power * affinity_mult * series_mult * 
        research_mult * adaptation_mult
    )
    
    return {
        "valid": True,
        "base_power": base_power,
        "affinity_mult": affinity_mult,
        "series_mult": series_mult,
        "series_bonus": series_mult > 1.0,
        "research_mult": research_mult,
        "adaptation_mult": adaptation_mult,
        "final_points": final_points,
        "buff_count": buff_count
    }
```

---

### C. ConfirmResearchView - Research Confirmation

**Pattern Reference**: Simple confirmation view like equipment removal

**Class Structure**:
```python
class ConfirmResearchView(discord.ui.View):
    def __init__(self, player_status, boss, user_id, world_threat_service):
        super().__init__(timeout=180.0)
        self.player_status = player_status
        self.boss = boss
        self.user_id = user_id
        self.world_threat_service = world_threat_service
        self._setup_ui()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    # Buttons:
    # - "✅ Confirm Research" → Execute service.perform_research()
    # - "❌ Cancel" → Close view
```

**Embed**:
```
Title: 🔬 Confirm Research Action
Description: Spend your daily action on research instead of fighting?

📚 Current Research Stacks: 1 (x2 multiplier)
📈 After Research: 2 (x4 multiplier)

💡 Your next fight will earn **4x points**!

⚠️ This uses your daily action (24h cooldown will apply)

Boss Evolution:
The boss will evolve its stats and affinities after this action.
```

---

### D. FightResultView - Display Fight Results

**Pattern Reference**: Similar to `ExpeditionResultsView`

**Class Structure**:
```python
class FightResultView(discord.ui.View):
    def __init__(self, fight_result, user_id, world_threat_service):
        super().__init__(timeout=300.0)
        self.fight_result = fight_result
        self.user_id = user_id
        self.world_threat_service = world_threat_service
        self._setup_ui()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    # Buttons:
    # - "📊 View Status" → Return to StatusView
    # - "✅ Close" → Dismiss
```

**Embed Structure**:
```
Title: ⚔️ Fight Complete!
Description: You dealt massive damage to [Boss Name]!
Color: 0x00FF00 (green for success)

Field 1: 💪 Battle Results
- **Points Scored: 6,234**
- Base Power: 2,450
- Affinity Multiplier: 1.35x
- Series Bonus: 1.5x
- Research Multiplier: 4x
- Adaptation Penalty: 0.8x

Field 2: 💰 Immediate Rewards
- Crystals: +623
- Daphine Bonus: ✅ (+20%)

Field 3: 🎁 Checkpoint Rewards Unlocked!
Personal Checkpoints:
  ✅ 25,000 pts → +2,500 crystals, 2 equipment

Server Checkpoints:
  (None reached this time)

Field 4: 📊 Progress Update
- Your Total: 28,234 points
- Next Personal: 50,000 (21,766 to go)
- Server Total: 1,256,789 points
- Next Server: 5,000,000 (3,743,211 to go)

Field 5: 🌀 Boss Evolution
The boss has evolved!
- New Dominant Stats: Intelligence, HP
- New Cursed Stat: Speed
- Buffs & curses have changed - check /wt_status for details

Footer: Use /wt_status to see the new boss configuration
```

---

## 3. Helper Utilities

### Format Functions
Create these helper functions in the cog or separate utils file:

```python
def format_boss_stats(boss: WorldThreatBoss) -> str:
    """Format boss stats for display in embeds."""
    lines = []
    lines.append(f"**Dominant Stats:** {', '.join(boss.dominant_stats).upper()}")
    cursed = boss.cursed_stat[0] if isinstance(boss.cursed_stat, list) else boss.cursed_stat
    lines.append(f"**Cursed Stat:** {cursed.upper()}")
    lines.append(f"**Adaptation Level:** {boss.adaptation_level} (x{0.8 ** boss.adaptation_level:.2f} damage)")
    return '\n'.join(lines)

def format_affinities(affinity_dict: Dict[str, List[str]], title: str) -> str:
    """Format buffs/curses by category."""
    if not affinity_dict or not any(affinity_dict.values()):
        return f"**{title}:** None"
    
    lines = [f"**{title}:**"]
    for category, values in affinity_dict.items():
        if values:
            category_name = category.title()
            values_str = ', '.join(values)
            lines.append(f"  • {category_name}: {values_str}")
    
    return '\n'.join(lines) if len(lines) > 1 else f"**{title}:** None"

def format_cooldown(seconds: float) -> str:
    """Format time remaining until midnight UTC+7."""
    if seconds <= 0:
        return "✅ Ready"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if hours > 0:
        return f"⏳ {hours}h {minutes}m (resets midnight UTC+7)"
    else:
        return f"⏳ {minutes}m (resets midnight UTC+7)"

def format_checkpoint_progress(current: int, checkpoints: List[int]) -> str:
    """Show next checkpoint and progress."""
    next_checkpoint = None
    for checkpoint in sorted(checkpoints):
        if current < checkpoint:
            next_checkpoint = checkpoint
            break
    
    if next_checkpoint is None:
        return f"🏆 All checkpoints reached! ({current:,} points)"
    
    remaining = next_checkpoint - current
    progress_pct = (current / next_checkpoint) * 100
    
    # Simple progress bar (10 segments)
    filled = int(progress_pct / 10)
    bar = "█" * filled + "░" * (10 - filled)
    
    return f"Next: {next_checkpoint:,} ({remaining:,} to go)\n{bar} {progress_pct:.1f}%"

def format_points(points: int) -> str:
    """Format large numbers with commas."""
    return f"{points:,}"
```

---

## 4. Implementation Flow

### Phase 1: Basic Status View ✅ START HERE
**Goal**: Get the basic UI working end-to-end

1. Create `WorldThreatCog` class extending `BaseCommand`
2. Implement `/wt_status` command
3. Create `StatusView` class with basic embed
4. Add "Refresh" button functionality
5. Test: Can view boss and player status

**Files to create**:
- `cogs/commands/world_threat.py`

**Estimated time**: 2-3 hours

---

### Phase 2: Research Action
**Goal**: Allow players to perform research

1. Create `ConfirmResearchView` class
2. Implement `/wt_research` command
3. Wire up to `world_threat_service.perform_research()`
4. Show success/error messages
5. Test: Research increments stacks, cooldown works

**Estimated time**: 1-2 hours

---

### Phase 3: Team Selection
**Goal**: Character selection UI for fights

1. Create `TeamSelectView` class (adapt from `CharacterSelectView`)
2. Implement character filtering logic (exclude cursed)
3. Add pagination support
4. Add search modal (copy pattern from expeditions)
5. Implement live power calculation preview
6. Add series bonus detection
7. Test: Can select 6 characters, preview is accurate

**Estimated time**: 4-6 hours

---

### Phase 4: Fight Execution
**Goal**: Complete fight flow

1. Implement `/wt_fight` command flow
2. Wire team selection to `world_threat_service.perform_fight()`
3. Create `FightResultView` to display results
4. Handle checkpoint rewards display
5. Show boss evolution notification
6. Test: Full fight flow works, rewards granted

**Estimated time**: 3-4 hours

---

### Phase 5: Polish
**Goal**: Make it production-ready

1. Error handling and edge cases
2. Better formatting and emojis
3. Add help text and tooltips
4. Leaderboard command (optional)
5. Comprehensive testing
6. Documentation updates

**Estimated time**: 2-3 hours

**Total estimated time**: 12-18 hours

---

## 5. Key Patterns to Follow

### ✅ DO's

1. **Always defer before long operations**
   ```python
   await interaction.response.defer()
   # ... do work ...
   await interaction.followup.send(embed=embed)
   ```

2. **Validate interaction user**
   ```python
   async def interaction_check(self, interaction: discord.Interaction) -> bool:
       return interaction.user.id == self.user_id
   ```

3. **Use timeouts on views**
   ```python
   super().__init__(timeout=300.0)  # 5 minutes
   ```

4. **Clear and rebuild UI items**
   ```python
   self.clear_items()
   self.add_item(button1)
   self.add_item(button2)
   ```

5. **Paginate long lists**
   - Max 25 items per select menu
   - Add Previous/Next buttons
   - Show page indicators

6. **Show loading states**
   ```python
   embed.description = "⏳ Processing your request..."
   await interaction.response.edit_message(embed=embed)
   ```

7. **Handle missing data gracefully**
   ```python
   if not boss:
       await interaction.response.send_message("❌ No active World Threat boss", ephemeral=True)
       return
   ```

8. **Use ephemeral for errors**
   ```python
   await interaction.response.send_message("❌ Error message", ephemeral=True)
   ```

---

### ❌ DON'Ts

1. **Don't allow unauthorized interactions**
   - Always implement `interaction_check()`

2. **Don't forget to disable buttons after use**
   ```python
   for item in self.children:
       item.disabled = True
   await interaction.response.edit_message(view=self)
   ```

3. **Don't show raw error messages**
   ```python
   # Bad
   await interaction.response.send_message(f"Error: {str(e)}")
   
   # Good
   await interaction.response.send_message("❌ Unable to process request. Please try again.", ephemeral=True)
   ```

4. **Don't hardcode values**
   ```python
   # Bad
   if points >= 10000:
   
   # Good
   if points >= self.world_threat_service.PERSONAL_CHECKPOINTS[0]:
   ```

5. **Don't forget timezone awareness**
   ```python
   # Always use UTC
   from datetime import datetime, timezone
   timestamp = datetime.now(timezone.utc)
   ```

6. **Don't exceed Discord limits**
   - Embed titles: 256 chars
   - Embed descriptions: 4096 chars
   - Field values: 1024 chars
   - Total embed size: 6000 chars
   - Select options: 25 max

---

## 6. Cog Registration

Add to your bot initialization file (e.g., `start_geminya.py`):

```python
from cogs.commands.world_threat import WorldThreatCog

# In the bot setup function:
async def setup_cogs(bot, services):
    # ... other cogs ...
    await bot.add_cog(WorldThreatCog(bot, services))
    logger.info("World Threat cog loaded")
```

---

## 7. Testing Checklist

Before deploying to production, verify:

### Basic Functionality
- [ ] Boss data loads correctly in status view
- [ ] Player status displays accurately
- [ ] All buttons render properly
- [ ] Views timeout after 5 minutes

### Cooldown System
- [ ] Cooldown timer displays correctly
- [ ] Actions blocked during cooldown
- [ ] Cooldown resets after 24 hours
- [ ] Time remaining shows accurate countdown

### Research Action
- [ ] Research increments stacks (max 2)
- [ ] Multiplier displays correctly (x2, x4)
- [ ] Boss evolves after research
- [ ] Adaptation thresholds work (5, 10 actions)

### Character Selection
- [ ] Cursed characters filtered out
- [ ] Can select exactly 6 characters
- [ ] Search function works
- [ ] Pagination works correctly
- [ ] Character data displays properly

### Fight System
- [ ] Team validation works (6 characters, no cursed)
- [ ] Point calculation is accurate
- [ ] Series bonus detected (all 6 same series)
- [ ] Research multiplier applies correctly
- [ ] Adaptation penalty applies

### Rewards
- [ ] Immediate rewards granted (crystals)
- [ ] Daphine bonus applies (x1.2)
- [ ] Personal checkpoints trigger
- [ ] Server checkpoints trigger
- [ ] Rewards don't duplicate

### Boss Evolution
- [ ] Stats re-roll after each action
- [ ] Buffs/curses change
- [ ] Adaptation level increases correctly
- [ ] Extra buff slots granted at thresholds

### Error Handling
- [ ] No active boss → friendly error
- [ ] Cooldown active → clear message
- [ ] Invalid team → helpful error
- [ ] Network errors handled gracefully
- [ ] User-friendly error messages

### UI/UX
- [ ] Embeds look good (formatting, emojis)
- [ ] Colors are appropriate (green=success, red=error)
- [ ] Timestamps display correctly
- [ ] Numbers formatted with commas
- [ ] Progress bars render properly

### Edge Cases
- [ ] First action ever (no timestamp)
- [ ] All checkpoints reached
- [ ] No characters available
- [ ] Max research stacks
- [ ] Boss at max adaptation

---

## 8. Future Enhancements

Consider implementing later:

1. **Leaderboard System**
   - Top contributors by total points
   - Recent activity feed
   - Team leaderboard (guilds/alliances)

2. **Advanced Stats**
   - Personal fight history
   - Average points per fight
   - Best team compositions
   - Boss difficulty trends

3. **Notifications**
   - DM when cooldown expires
   - Alert when server checkpoint reached
   - Boss change announcements

4. **Social Features**
   - Share fight results
   - Challenge friends
   - Team recommendations

5. **Analytics Dashboard**
   - Server-wide statistics
   - Boss defeat predictions
   - Optimal strategy suggestions

---

## 9. Code Example: Basic Cog Structure

```python
import discord
from discord.ext import commands
from discord import app_commands
from typing import List, Dict, Optional
from datetime import datetime, timezone

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


class WorldThreatCog(BaseCommand):
    """Discord commands for World Threat game mode."""
    
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)
        self.world_threat_service = services.world_threat_service
    
    @app_commands.command(name="wt_status", description="📊 View the current World Threat status")
    async def wt_status(self, interaction: discord.Interaction):
        """Display current boss and player status."""
        await interaction.response.defer()
        
        try:
            # Get boss and player data
            boss = await self.world_threat_service.get_boss()
            if not boss:
                await interaction.followup.send(
                    "❌ No active World Threat boss. Contact an administrator.",
                    ephemeral=True
                )
                return
            
            player_status = await self.world_threat_service.get_player_status(str(interaction.user.id))
            
            # Create and send view
            view = StatusView(boss, player_status, interaction.user.id, self.world_threat_service)
            embed = await view.create_status_embed()
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            self.logger.error(f"Error in wt_status: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ An error occurred while loading World Threat status.",
                ephemeral=True
            )
    
    @app_commands.command(name="wt_research", description="🔬 Perform research on the World Threat boss")
    async def wt_research(self, interaction: discord.Interaction):
        """Initiate research action."""
        await interaction.response.defer()
        
        try:
            # Check cooldown
            action_check = await self.world_threat_service.can_perform_action(str(interaction.user.id))
            if not action_check["can_act"]:
                time_remaining = action_check["time_remaining"]
                await interaction.followup.send(
                    f"⏳ Your action is on cooldown. {format_cooldown(time_remaining)}",
                    ephemeral=True
                )
                return
            
            # Get current status
            boss = await self.world_threat_service.get_boss()
            player_status = await self.world_threat_service.get_player_status(str(interaction.user.id))
            
            # Show confirmation view
            view = ConfirmResearchView(player_status, boss, interaction.user.id, self.world_threat_service)
            embed = await view.create_confirmation_embed()
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            self.logger.error(f"Error in wt_research: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ An error occurred. Please try again.",
                ephemeral=True
            )
    
    @app_commands.command(name="wt_fight", description="⚔️ Fight the World Threat boss")
    async def wt_fight(self, interaction: discord.Interaction):
        """Start the fight flow with team selection."""
        await interaction.response.defer()
        
        try:
            # Check cooldown
            action_check = await self.world_threat_service.can_perform_action(str(interaction.user.id))
            if not action_check["can_act"]:
                time_remaining = action_check["time_remaining"]
                await interaction.followup.send(
                    f"⏳ Your action is on cooldown. {format_cooldown(time_remaining)}",
                    ephemeral=True
                )
                return
            
            # Get boss
            boss = await self.world_threat_service.get_boss()
            if not boss:
                await interaction.followup.send(
                    "❌ No active World Threat boss.",
                    ephemeral=True
                )
                return
            
            # Get available characters (already filtered by service)
            available_characters = await self.world_threat_service.get_available_characters(str(interaction.user.id))
            
            if len(available_characters) < 6:
                await interaction.followup.send(
                    f"❌ You need at least 6 characters to fight. You have {len(available_characters)} available.\n"
                    f"Some characters may be excluded due to cursed affinities.",
                    ephemeral=True
                )
                return
            
            # Show team selection view
            view = TeamSelectView(available_characters, boss, interaction.user.id, self.world_threat_service)
            embed = await view.create_selection_embed()
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            self.logger.error(f"Error in wt_fight: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ An error occurred. Please try again.",
                ephemeral=True
            )


# View classes would be defined here or in a separate file
class StatusView(discord.ui.View):
    """Main status view for World Threat."""
    # Implementation details...
    pass

class ConfirmResearchView(discord.ui.View):
    """Confirmation view for research action."""
    # Implementation details...
    pass

class TeamSelectView(discord.ui.View):
    """Team selection view for fights."""
    # Implementation details...
    pass

class FightResultView(discord.ui.View):
    """Results display after a fight."""
    # Implementation details...
    pass


# Helper functions
def format_cooldown(seconds: float) -> str:
    """Format time remaining until midnight UTC+7."""
    if seconds <= 0:
        return "✅ Ready"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if hours > 0:
        return f"⏳ {hours}h {minutes}m (resets midnight UTC+7)"
    else:
        return f"⏳ {minutes}m (resets midnight UTC+7)"
```

---

## 10. Summary

This implementation plan provides a comprehensive roadmap for building the World Threat UI following proven patterns from the Expedition system. The phased approach allows for incremental development and testing, ensuring each component works before moving to the next.

Key success factors:
- Follow existing patterns from expeditions
- Test thoroughly at each phase
- Handle errors gracefully
- Provide clear user feedback
- Maintain code quality and documentation

Estimated total development time: **12-18 hours** for a complete, polished implementation.
