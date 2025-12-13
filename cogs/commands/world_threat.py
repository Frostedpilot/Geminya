"""World Threat game mode Discord commands and UI."""

import discord
import json
from discord.ext import commands
from discord import app_commands
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


# === HELPER FUNCTIONS ===

def format_boss_stats(boss) -> str:
    """Format boss stats for display in embeds."""
    lines = []
    lines.append(f"**Dominant Stats:** {', '.join(s.upper() for s in boss.dominant_stats)}")
    lines.append(f"**Cursed Stat:** {boss.cursed_stat.upper()}")
    lines.append(f"**Adaptation:** Level {boss.adaptation_level} (x{0.9 ** boss.adaptation_level:.2f} damage)")
    return '\n'.join(lines)


def format_affinities(affinity_dict: Dict[str, List[str]], title: str, data_manager=None) -> str:
    """Format buffs/curses by category."""
    if not affinity_dict or not any(affinity_dict.values()):
        return f"**{title}:** None"
    
    lines = []
    for category, values in affinity_dict.items():
        if values:
            category_name = category.title()
            
            # For series category, convert IDs to names
            if category == "series" and data_manager:
                series_names = []
                for series_id in values:
                    series_name = data_manager.get_series_name(int(series_id))
                    if series_name:
                        series_names.append(series_name)
                    else:
                        series_names.append(series_id)
                values_str = ', '.join(series_names)
            else:
                values_str = ', '.join(values)
            
            lines.append(f"• {category_name}: {values_str}")
    
    return '\n'.join(lines) if lines else f"**{title}:** None"


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


# === REWARDS PAGINATION VIEW ===

class RewardsPaginationView(discord.ui.View):
    """Paginated view for reward information."""
    
    def __init__(self, reward_type: str, player_status=None, boss=None, db=None):
        super().__init__(timeout=300)
        self.reward_type = reward_type
        self.player_status = player_status
        self.boss = boss
        self.db = db
        self.item_lookup = {}
        self.current_page = 0
    
    async def setup(self):
        """Async setup to load item data."""
        if self.db:
            try:
                item_data = await self.db.get_shop_items()
                for item in item_data:
                    item_id_int = item.get('id')
                    if item_id_int:
                        self.item_lookup[f"item_{item_id_int}"] = item
            except Exception:
                pass
        self._setup_pages()
        self._setup_ui()
    
    def _setup_pages(self):
        """Setup pages based on reward type."""
        from services.world_threat_service import WorldThreatService
        
        if self.reward_type == "immediate":
            # Page 0: Explanation
            # Page 1+: Tier rewards (4 tiers per page)
            self.pages = []
            
            # Page 0: Crystal formula explanation
            self.pages.append({
                "title": "💰 Immediate Rewards (Per Fight)",
                "description": "Rewards earned instantly after each fight based on your score.",
                "color": 0x3498DB,
                "fields": [
                    {
                        "name": "💎 Crystals",
                        "value": (
                            "**Formula:** `Score ÷ 10`\n"
                            "**Awakened Bonus:** Multiplied by `1.2^awakened_count`\n"
                            "Example: 50,000 score with 3 awakened = 8,640 crystals"
                        ),
                        "inline": False
                    },
                    {
                        "name": "🎯 Tier Rewards",
                        "value": "Cumulative tiers - you get ALL tiers you qualify for!\nUse navigation buttons to see all tier details.",
                        "inline": False
                    }
                ]
            })
            
            # Tier pages (4 tiers per page for better visibility)
            tiers_per_page = 4
            sorted_tiers = sorted(WorldThreatService.IMMEDIATE_REWARD_TIERS, reverse=True)
            
            for i in range(0, len(sorted_tiers), tiers_per_page):
                tier_batch = sorted_tiers[i:i+tiers_per_page]
                tiers_text = ""
                
                for min_points, rewards in tier_batch:
                    tiers_text += f"**{min_points:,}+ points:**\n"
                    if rewards.get('quartzs', 0) > 0:
                        tiers_text += f"  💠 {rewards['quartzs']:,} Quartzs\n"
                    if rewards.get('daphine', 0) > 0:
                        tiers_text += f"  🦋 {rewards['daphine']:,} Daphine\n"
                    if rewards.get('items'):
                        for item_dict in rewards['items']:
                            item_id = item_dict.get('item_id', '')
                            quantity = item_dict.get('quantity', 1)
                            item_name = self.item_lookup.get(item_id, {}).get('name', item_id)
                            if quantity > 1:
                                tiers_text += f"  🎁 {quantity}x {item_name}\n"
                            else:
                                tiers_text += f"  🎁 {item_name}\n"
                    tiers_text += "\n"
                
                page_num = (i // tiers_per_page) + 1
                self.pages.append({
                    "title": f"💰 Immediate Rewards - Tiers ({page_num})",
                    "description": "Cumulative rewards - you receive ALL tiers you qualify for!",
                    "color": 0x3498DB,
                    "fields": [
                        {"name": f"Tier Group {page_num}", "value": tiers_text.strip(), "inline": False}
                    ]
                })
        
        elif self.reward_type == "personal":
            # Split personal checkpoints into multiple pages (4 checkpoints per page)
            self.pages = []
            checkpoints_per_page = 4
            
            # Add current score if available
            current_score_text = ""
            if self.player_status:
                current_score_text = f"\n**Your Current Score:** {self.player_status.cumulative_points:,} points\n\n"
            
            sorted_checkpoints = sorted(WorldThreatService.PERSONAL_CHECKPOINTS, reverse=True)
            
            for i in range(0, len(sorted_checkpoints), checkpoints_per_page):
                checkpoint_batch = sorted_checkpoints[i:i+checkpoints_per_page]
                checkpoints_text = ""
                
                for checkpoint in checkpoint_batch:
                    rewards = WorldThreatService.PERSONAL_CHECKPOINT_REWARDS[checkpoint]
                    # Mark claimed checkpoints
                    claimed = ""
                    if self.player_status and checkpoint in self.player_status.claimed_personal_checkpoints:
                        claimed = " ✅"
                    checkpoints_text += f"**{checkpoint:,} Total Points:**{claimed}\n"
                    if rewards.get('crystals', 0) > 0:
                        checkpoints_text += f"  💎 {rewards['crystals']:,} Crystals\n"
                    if rewards.get('quartzs', 0) > 0:
                        checkpoints_text += f"  💠 {rewards['quartzs']:,} Quartzs\n"
                    if rewards.get('daphine', 0) > 0:
                        checkpoints_text += f"  🦋 {rewards['daphine']:,} Daphine\n"
                    if rewards.get('items'):
                        for item_dict in rewards['items']:
                            item_id = item_dict.get('item_id', '')
                            quantity = item_dict.get('quantity', 1)
                            item_name = self.item_lookup.get(item_id, {}).get('name', item_id)
                            if quantity > 1:
                                checkpoints_text += f"  🎁 {quantity}x {item_name}\n"
                            else:
                                checkpoints_text += f"  🎁 {item_name}\n"
                    checkpoints_text += "\n"
                
                page_num = (i // checkpoints_per_page) + 1
                total_pages = (len(sorted_checkpoints) + checkpoints_per_page - 1) // checkpoints_per_page
                
                description = "Rewards earned when YOU reach cumulative point milestones.\nEach checkpoint can only be claimed once per boss cycle."
                if i == 0 and current_score_text:
                    description += current_score_text
                
                self.pages.append({
                    "title": f"🏆 Personal Checkpoint Rewards ({page_num}/{total_pages})",
                    "description": description,
                    "color": 0xE74C3C,
                    "fields": [
                        {"name": "📊 Milestones", "value": checkpoints_text.strip(), "inline": False}
                    ]
                })
            
            # Add note on last page
            if self.pages:
                self.pages[-1]["fields"].append({
                    "name": "ℹ️ Note",
                    "value": "These rewards are based on your personal cumulative points and are separate from immediate rewards.",
                    "inline": False
                })
        
        elif self.reward_type == "server":
            # Split server checkpoints into multiple pages (4 checkpoints per page)
            self.pages = []
            checkpoints_per_page = 4
            
            # Add current server score if available
            current_score_text = ""
            if self.boss:
                current_score_text = f"\n**Server Total Score:** {self.boss.server_total_points:,} points\n\n"
            
            sorted_checkpoints = sorted(WorldThreatService.SERVER_CHECKPOINTS, reverse=True)
            
            for i in range(0, len(sorted_checkpoints), checkpoints_per_page):
                checkpoint_batch = sorted_checkpoints[i:i+checkpoints_per_page]
                checkpoints_text = ""
                
                for checkpoint in checkpoint_batch:
                    rewards = WorldThreatService.SERVER_CHECKPOINT_REWARDS[checkpoint]
                    # Mark claimed checkpoints
                    claimed = ""
                    if self.player_status and checkpoint in self.player_status.claimed_server_checkpoints:
                        claimed = " ✅"
                    checkpoints_text += f"**{checkpoint:,} Server Total:**{claimed}\n"
                    if rewards.get('crystals', 0) > 0:
                        checkpoints_text += f"  💎 {rewards['crystals']:,} Crystals\n"
                    if rewards.get('quartzs', 0) > 0:
                        checkpoints_text += f"  💠 {rewards['quartzs']:,} Quartzs\n"
                    if rewards.get('daphine', 0) > 0:
                        checkpoints_text += f"  🦋 {rewards['daphine']:,} Daphine\n"
                    if rewards.get('items'):
                        for item_dict in rewards['items']:
                            item_id = item_dict.get('item_id', '')
                            quantity = item_dict.get('quantity', 1)
                            item_name = self.item_lookup.get(item_id, {}).get('name', item_id)
                            if quantity > 1:
                                checkpoints_text += f"  🎁 {quantity}x {item_name}\n"
                            else:
                                checkpoints_text += f"  🎁 {item_name}\n"
                    checkpoints_text += "\n"
                
                page_num = (i // checkpoints_per_page) + 1
                total_pages = (len(sorted_checkpoints) + checkpoints_per_page - 1) // checkpoints_per_page
                
                description = "Rewards EVERYONE receives when the server reaches total point milestones.\nEach checkpoint can only be claimed once per boss cycle."
                if i == 0 and current_score_text:
                    description += current_score_text
                
                self.pages.append({
                    "title": f"🌍 Server Checkpoint Rewards ({page_num}/{total_pages})",
                    "description": description,
                    "color": 0xF1C40F,
                    "fields": [
                        {"name": "🌐 Global Milestones", "value": checkpoints_text.strip(), "inline": False}
                    ]
                })
            
            # Add note on last page
            if self.pages:
                self.pages[-1]["fields"].append({
                    "name": "ℹ️ Note",
                    "value": "When a server checkpoint is reached, ALL players get these rewards automatically. Work together!",
                    "inline": False
                })
    
    def _setup_ui(self):
        """Setup navigation buttons."""
        self.clear_items()
        
        # Previous button
        prev_button = discord.ui.Button(
            label="◀ Previous",
            style=discord.ButtonStyle.primary,
            disabled=self.current_page == 0
        )
        prev_button.callback = self._prev_page
        self.add_item(prev_button)
        
        # Next button
        next_button = discord.ui.Button(
            label="Next ▶",
            style=discord.ButtonStyle.primary,
            disabled=self.current_page >= len(self.pages) - 1
        )
        next_button.callback = self._next_page
        self.add_item(next_button)
    
    def create_embed(self) -> discord.Embed:
        """Create embed for current page."""
        page_data = self.pages[self.current_page]
        
        embed = discord.Embed(
            title=page_data["title"],
            description=page_data["description"],
            color=page_data["color"]
        )
        
        for field in page_data["fields"]:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field["inline"]
            )
        
        if len(self.pages) > 1:
            embed.set_footer(text=f"Page {self.current_page + 1}/{len(self.pages)} • World Threat Rewards")
        else:
            embed.set_footer(text="World Threat Rewards System")
        
        return embed
    
    async def _prev_page(self, interaction: discord.Interaction):
        """Go to previous page."""
        self.current_page = max(0, self.current_page - 1)
        self._setup_ui()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def _next_page(self, interaction: discord.Interaction):
        """Go to next page."""
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        self._setup_ui()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)


# === CHARACTER SEARCH MODAL ===

class CharacterSearchModal(discord.ui.Modal):
    """Modal for searching characters by name or series."""
    
    def __init__(self, character_view):
        super().__init__(title="🔍 Search Characters")
        self.character_view = character_view
        
        self.search_input = discord.ui.TextInput(
            label="Character Name or Series",
            placeholder="Enter character name or series to search...",
            default=character_view.search_filter,
            max_length=100,
            required=False
        )
        self.add_item(self.search_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle search submission."""
        self.character_view.search_filter = self.search_input.value.strip()
        self.character_view.current_page = 0  # Reset to first page
        self.character_view._setup_ui()
        
        # Update start button state
        for item in self.character_view.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "start_fight":
                item.disabled = len(self.character_view.selected_characters) != 6
                break
        
        embed = await self.character_view._create_selection_embed()
        await interaction.response.edit_message(embed=embed, view=self.character_view)


# === TEAM SELECTION VIEW ===

class WorldThreatTeamSelectView(discord.ui.View):
    """Character selection for World Threat fights - 6 characters required."""
    
    def __init__(self, available_characters: List[Dict], boss, user_id: int, 
                 world_threat_service, player_status, db=None):
        super().__init__(timeout=300.0)
        self.available_characters = available_characters
        self.boss = boss
        self.user_id = user_id
        self.world_threat_service = world_threat_service
        self.db = db
        self.item_lookup = {}
        self.player_status = player_status
        
        self.selected_characters = []  # waifu_ids, max 6
        self.search_filter = ""
        self.current_page = 0
        self.items_per_page = 25
        self.sorting_mode = 'raw_power'  # or 'buff_count'
        
        self.char_registry = world_threat_service.data_manager.get_character_registry()
        self._setup_ui()
    
    async def setup_item_lookup(self):
        """Load item data for displaying item names."""
        if self.db:
            try:
                item_data = await self.db.get_shop_items()
                for item in item_data:
                    item_id_int = item.get('id')
                    if item_id_int:
                        self.item_lookup[f"item_{item_id_int}"] = item
            except Exception:
                pass
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the command user can interact."""
        return interaction.user.id == self.user_id
    
    def _calculate_char_base_power(self, char: Dict) -> float:
        """Calculate (dominant stats - cursed stat) * (1 + 0.1*(star-1)) for a character."""
        stats = char.get('stats', {})
        star_level = char.get('star_level', 1)
        
        # Sum dominant stats
        dominant_sum = sum(stats.get(stat, 0) for stat in self.boss.dominant_stats)
        
        # Subtract cursed stat
        cursed_value = stats.get(self.boss.cursed_stat, 0)
        
        # Apply star level multiplier: 1 + 0.1 * (star - 1)
        star_multiplier = 1 + 0.1 * (star_level - 1)
        
        # Apply formula: (dominant - cursed) * star_multiplier
        power = (dominant_sum - cursed_value) * star_multiplier
        
        return max(0, power)
    
    def _count_buff_matches(self, char: Dict) -> int:
        """Count how many boss buffs this character matches (max 3 per character)."""
        buff_count = 0
        
        # Check elemental buffs
        if "elemental" in self.boss.buffs:
            char_elementals = char.get('elemental_types', [])
            for elemental in char_elementals:
                if elemental in self.boss.buffs["elemental"]:
                    buff_count += 1
                    break  # Only count once per category
        
        # Check archetype buffs
        if "archetype" in self.boss.buffs:
            if char.get('archetype') in self.boss.buffs["archetype"]:
                buff_count += 1
        
        # Check series buffs
        if "series" in self.boss.buffs:
            if str(char.get('series_id')) in self.boss.buffs["series"]:
                buff_count += 1
        
        # Check genre buffs
        if "genre" in self.boss.buffs:
            char_genres = char.get('anime_genres', [])
            for genre in char_genres:
                if genre in self.boss.buffs["genre"]:
                    buff_count += 1
                    break  # Only count once per category
        
        return min(buff_count, 3)  # Cap at 3
    
    def _get_filtered_characters(self) -> List[Dict]:
        """Filter by search and sort by chosen mode."""
        characters = self.available_characters.copy()
        
        # Apply search filter
        if self.search_filter:
            search_lower = self.search_filter.lower()
            characters = [
                char for char in characters
                if search_lower in char['name'].lower() 
                or search_lower in char.get('series', '').lower()
            ]
        
        # Annotate with calculated values
        for char in characters:
            char['__base_power'] = self._calculate_char_base_power(char)
            char['__buff_count'] = self._count_buff_matches(char)
        
        # Sort based on mode
        if self.sorting_mode == 'raw_power':
            characters.sort(
                key=lambda c: (c['__base_power'], c['__buff_count']),
                reverse=True
            )
        else:  # buff_count mode
            characters.sort(
                key=lambda c: (c['__buff_count'], c['__base_power']),
                reverse=True
            )
        
        return characters
    
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
                
                # Calculate character's base power: (dominant - cursed) * (1 + 0.1*(star-1))
                dominant_sum = sum(stats.get(stat, 0) for stat in self.boss.dominant_stats)
                cursed_value = stats.get(self.boss.cursed_stat, 0)
                star_multiplier = 1 + 0.1 * (star_level - 1)
                char_power = (dominant_sum - cursed_value) * star_multiplier
                base_power += max(0, char_power)
                
                # Count buffs
                buff_count += self._count_buff_matches(char_data)
                series_ids.append(char_data.get('series_id'))
        
        # Calculate multipliers
        affinity_mult = 1.0 + (buff_count * 0.2)
        series_mult = 1.5 if len(set(series_ids)) == 1 else 1.0
        research_mult = 2 ** self.player_status.research_stacks
        adaptation_mult = 0.9 ** self.boss.adaptation_level
        
        final_points = int(
            base_power * affinity_mult * series_mult * 
            research_mult * adaptation_mult
        )
        
        # Get series name if bonus applies
        series_name = None
        if series_mult > 1.0 and series_ids:
            first_char = next(
                (c for c in self.available_characters if c['waifu_id'] == self.selected_characters[0]),
                None
            )
            if first_char:
                series_name = first_char.get('series', 'Unknown')
        
        return {
            "valid": True,
            "base_power": base_power,
            "affinity_mult": affinity_mult,
            "series_mult": series_mult,
            "series_bonus": series_mult > 1.0,
            "series_name": series_name,
            "research_mult": research_mult,
            "adaptation_mult": adaptation_mult,
            "final_points": final_points,
            "buff_count": buff_count
        }
    
    async def _create_selection_embed(self) -> discord.Embed:
        """Create the main selection embed with team preview."""
        
        embed = discord.Embed(
            title=f"🎯 Select Team to Fight: {self.boss.boss_name}",
            description=(
                f"Choose **6 characters** for your attack team\n\n"
                f"⚠️ *Characters with cursed affinities are pre-filtered*\n"
                f"💡 *Select all from same series for 1.5x bonus!*"
            ),
            color=0x9B59B6
        )
        
        # Show boss info
        boss_info = format_boss_stats(self.boss)
        embed.add_field(name="📊 Boss Stats", value=boss_info, inline=False)
        
        # Show active buffs
        buffs_text = format_affinities(self.boss.buffs, "Active Buffs", self.world_threat_service.data_manager)
        embed.add_field(name="🎯 Buffs", value=buffs_text or "None", inline=True)
        
        # Show active curses
        curses_text = format_affinities(self.boss.curses, "Active Curses", self.world_threat_service.data_manager)
        embed.add_field(name="⚠️ Curses", value=curses_text or "None", inline=True)
        
        # Show research multiplier
        research_text = (
            f"Research Stacks: **{self.player_status.research_stacks}**\n"
            f"Multiplier: **x{2**self.player_status.research_stacks}**"
        )
        embed.add_field(name="🔬 Your Research", value=research_text, inline=True)
        
        # Show selected characters
        if self.selected_characters:
            char_list = []
            for waifu_id in self.selected_characters:
                char_data = next(
                    (c for c in self.available_characters if c['waifu_id'] == waifu_id),
                    None
                )
                if char_data:
                    star = char_data.get('star_level', 1)
                    buffs = self._count_buff_matches(char_data)
                    char_list.append(
                        f"⭐{star} **{char_data['name']}** "
                        f"({char_data.get('series', 'Unknown')}) - {buffs} buffs"
                    )
            
            embed.add_field(
                name=f"👥 Selected ({len(self.selected_characters)}/6)",
                value="\n".join(char_list) if char_list else "None",
                inline=False
            )
            
            # Show power calculation if full team
            if len(self.selected_characters) == 6:
                calc = self._calculate_team_power_preview()
                
                power_text = (
                    f"**Base Power:** {calc['base_power']:,}\n"
                    f"**Affinity Bonus:** x{calc['affinity_mult']:.2f} "
                    f"({calc['buff_count']} buffs)\n"
                )
                
                if calc['series_bonus']:
                    power_text += (
                        f"**Series Bonus:** ✅ x{calc['series_mult']} "
                        f"(all from {calc['series_name']}!)\n"
                    )
                else:
                    power_text += f"**Series Bonus:** ❌ (mixed series)\n"
                
                power_text += (
                    f"**Research:** x{calc['research_mult']}\n"
                    f"**Adaptation:** x{calc['adaptation_mult']:.2f}\n\n"
                    f"**🔥 Estimated Points: {calc['final_points']:,}**"
                )
                
                embed.add_field(
                    name="⚡ Team Power Estimate",
                    value=power_text,
                    inline=False
                )
        else:
            embed.add_field(
                name="👥 Team Status",
                value="No characters selected yet. Choose 6 to continue.",
                inline=False
            )
        
        # Footer
        filtered = self._get_filtered_characters()
        footer_text = f"{len(filtered)} available | Page {self.current_page+1}"
        if self.search_filter:
            footer_text += f" | Filter: {self.search_filter}"
        embed.set_footer(text=footer_text)
        
        return embed
    
    def _setup_ui(self):
        """Setup the UI components based on current page and filter."""
        self.clear_items()
        
        # Row 1: Control buttons
        sorting_label = (
            "Sort: Power > Buffs" if self.sorting_mode == 'raw_power' 
            else "Sort: Buffs > Power"
        )
        sorting_button = discord.ui.Button(
            label=sorting_label,
            style=discord.ButtonStyle.primary,
            custom_id="toggle_sorting"
        )
        sorting_button.callback = self.toggle_sorting
        self.add_item(sorting_button)
        
        search_button = discord.ui.Button(
            label="🔍 Search",
            style=discord.ButtonStyle.secondary,
            custom_id="search_characters"
        )
        search_button.callback = self.open_search_modal
        self.add_item(search_button)
        
        # Get filtered characters
        filtered = self._get_filtered_characters()
        
        # Safety check for page bounds
        if filtered:
            total_pages = (len(filtered) + self.items_per_page - 1) // self.items_per_page
            if self.current_page >= total_pages:
                self.current_page = 0
        
        if not filtered:
            # No characters available
            self.add_item(discord.ui.Button(
                label="❌ No characters available",
                style=discord.ButtonStyle.secondary,
                disabled=True
            ))
            return
        
        # Row 2: Character selection dropdown
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(filtered))
        current_chars = filtered[start_idx:end_idx]
        
        # Check which series are selected for bonus indicator
        selected_series = set()
        if self.selected_characters:
            for sel_id in self.selected_characters:
                sel_char = next(
                    (c for c in self.available_characters if c['waifu_id'] == sel_id),
                    None
                )
                if sel_char:
                    selected_series.add(sel_char.get('series_id'))
        
        # Build character options
        options = []
        for char in current_chars:
            waifu_id = char['waifu_id']
            is_selected = waifu_id in self.selected_characters
            
            # Series bonus indicator
            series_bonus_indicator = ""
            if len(selected_series) == 1 and char.get('series_id') in selected_series:
                series_bonus_indicator = " [SERIES★]"
            
            name_prefix = "✅ " if is_selected else ""
            star_level = char.get('star_level', 1)
            label = f"⭐{star_level} {name_prefix}{char['name']}{series_bonus_indicator}"[:100]
            
            base_power = char.get('__base_power', 0)
            buff_count = char.get('__buff_count', 0)
            series = char.get('series', 'Unknown')[:40]
            
            desc = f"{series} | Power: {base_power:.0f} | Buffs: {buff_count}"
            
            options.append(discord.SelectOption(
                label=label,
                description=desc,
                value=str(waifu_id),
                emoji="👤",
                default=is_selected
            ))
        
        # Calculate max selectable
        max_selectable = min(len(options), 6)
        
        # Create placeholder text
        total_pages = (len(filtered) + self.items_per_page - 1) // self.items_per_page
        placeholder = f"Select team ({len(self.selected_characters)}/6)"
        if total_pages > 1:
            placeholder += f" | Page {self.current_page+1}/{total_pages}"
        
        character_select = discord.ui.Select(
            placeholder=placeholder,
            options=options,
            custom_id="character_select",
            max_values=max_selectable
        )
        character_select.callback = self.character_selected
        self.add_item(character_select)
        
        # Row 3-4: Action buttons
        # Pagination
        if total_pages > 1:
            prev_button = discord.ui.Button(
                label="◀️ Prev",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page == 0,
                custom_id="prev_page"
            )
            prev_button.callback = self.previous_page
            self.add_item(prev_button)
            
            next_button = discord.ui.Button(
                label="▶️ Next",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page >= total_pages - 1,
                custom_id="next_page"
            )
            next_button.callback = self.next_page
            self.add_item(next_button)
        
        # Clear search
        if self.search_filter:
            clear_search_button = discord.ui.Button(
                label="❌ Clear Search",
                style=discord.ButtonStyle.secondary,
                custom_id="clear_search"
            )
            clear_search_button.callback = self.clear_search
            self.add_item(clear_search_button)
        
        # Clear selections
        if self.selected_characters:
            clear_all_button = discord.ui.Button(
                label="🗑️ Clear All",
                style=discord.ButtonStyle.secondary,
                custom_id="clear_all"
            )
            clear_all_button.callback = self.clear_all_selections
            self.add_item(clear_all_button)
        
        # Cancel
        cancel_button = discord.ui.Button(
            label="❌ Cancel",
            style=discord.ButtonStyle.danger,
            custom_id="cancel"
        )
        cancel_button.callback = self.cancel_selection
        self.add_item(cancel_button)
        
        # Start Fight
        start_button = discord.ui.Button(
            label="⚔️ Start Fight",
            style=discord.ButtonStyle.success,
            custom_id="start_fight",
            disabled=len(self.selected_characters) != 6
        )
        start_button.callback = self.start_fight
        self.add_item(start_button)
    
    # === CALLBACKS ===
    
    async def toggle_sorting(self, interaction: discord.Interaction):
        """Toggle sorting mode."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can change sorting.", ephemeral=True)
            return
        
        self.sorting_mode = 'buff_count' if self.sorting_mode == 'raw_power' else 'raw_power'
        self.current_page = 0
        self._setup_ui()
        embed = await self._create_selection_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def open_search_modal(self, interaction: discord.Interaction):
        """Open search modal."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can search.", ephemeral=True)
            return
        
        modal = CharacterSearchModal(self)
        await interaction.response.send_modal(modal)
    
    async def character_selected(self, interaction: discord.Interaction):
        """Handle character selection."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can select characters.", ephemeral=True)
            return
        
        selected_values = interaction.data.get('values', [])
        selected_ids = [int(v) for v in selected_values]
        
        # Update selections (maintain cross-page selection)
        # Remove deselected from this page
        current_page_ids = set()
        filtered = self._get_filtered_characters()
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(filtered))
        for char in filtered[start_idx:end_idx]:
            current_page_ids.add(char['waifu_id'])
        
        # Remove current page chars that weren't selected
        self.selected_characters = [
            cid for cid in self.selected_characters 
            if cid not in current_page_ids
        ]
        
        # Add newly selected (up to 6 total)
        for cid in selected_ids:
            if cid not in self.selected_characters and len(self.selected_characters) < 6:
                self.selected_characters.append(cid)
        
        self._setup_ui()
        embed = await self._create_selection_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def previous_page(self, interaction: discord.Interaction):
        """Go to previous page."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can navigate.", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self._setup_ui()
            embed = await self._create_selection_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    async def next_page(self, interaction: discord.Interaction):
        """Go to next page."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can navigate.", ephemeral=True)
            return
        
        filtered = self._get_filtered_characters()
        total_pages = (len(filtered) + self.items_per_page - 1) // self.items_per_page
        
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._setup_ui()
            embed = await self._create_selection_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    async def clear_search(self, interaction: discord.Interaction):
        """Clear search filter."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can clear search.", ephemeral=True)
            return
        
        self.search_filter = ""
        self.current_page = 0
        self._setup_ui()
        embed = await self._create_selection_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def clear_all_selections(self, interaction: discord.Interaction):
        """Clear all selected characters."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can clear selections.", ephemeral=True)
            return
        
        self.selected_characters = []
        self._setup_ui()
        embed = await self._create_selection_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def cancel_selection(self, interaction: discord.Interaction):
        """Cancel team selection."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can cancel.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Fight Cancelled",
            description="Team selection has been cancelled.",
            color=0xFF6B6B
        )
        # Disable all components
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def start_fight(self, interaction: discord.Interaction):
        """Start the fight with selected team."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can start the fight.", ephemeral=True)
            return
        
        if len(self.selected_characters) != 6:
            await interaction.response.send_message("❌ You need exactly 6 characters selected.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Re-check cooldown to prevent exploit
        action_check = await self.world_threat_service.can_perform_action(str(self.user_id))
        if not action_check["can_act"]:
            time_remaining = action_check["time_remaining"]
            await interaction.followup.send(
                f"⏳ Your action is on cooldown. {format_cooldown(time_remaining)}",
                ephemeral=True
            )
            return
        
        # Build team data for service
        team_data = []
        for waifu_id in self.selected_characters:
            char_data = next(
                (c for c in self.available_characters if c['waifu_id'] == waifu_id),
                None
            )
            if char_data:
                team_data.append({
                    "waifu_id": waifu_id,
                    "star_level": char_data.get('star_level', 1)
                })
        
        # Call service to perform fight
        result = await self.world_threat_service.perform_fight(
            str(self.user_id),
            team_data
        )
        
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            await interaction.followup.send(f"❌ Fight failed: {error_msg}", ephemeral=True)
            return
        
        # Show results
        points = result.get("points_scored", 0)
        calc = result.get("calculation_breakdown", {})
        immediate_rewards = result.get("immediate_rewards", {})
        checkpoint_rewards = result.get("checkpoint_rewards", {})
        awakened_count = result.get('awakened_count', 0)
        awakened_multiplier = result.get('awakened_multiplier', 1.0)
        total_points = result.get('total_points', 0)
        
        embed = discord.Embed(
            title=f"⚔️ Fight Complete vs {self.boss.boss_name}!",
            description=f"You scored **{points:,} points**!",
            color=0x00FF00
        )
        
        # Battle results
        battle_text = (
            f"**Base Power:** {calc.get('base_power', 0):,}\n"
            f"**Affinity Bonus:** x{calc.get('affinity_multiplier', 1.0):.2f}\n"
            f"**Series Bonus:** {'✅' if calc.get('series_multiplier', 1.0) > 1.0 else '❌'} x{calc.get('series_multiplier', 1.0):.1f}\n"
            f"**Research:** x{calc.get('research_multiplier', 1)}\n"
            f"**Adaptation:** x{calc.get('adaptation_multiplier', 1.0):.2f}"
        )
        embed.add_field(name="💪 Battle Results", value=battle_text, inline=False)
        
        # Combined rewards (Immediate + Personal Checkpoints)
        crystals = immediate_rewards.get('crystals', 0)
        quartzs = immediate_rewards.get('quartzs', 0)
        daphine = immediate_rewards.get('daphine', 0)
        
        personal_rewards = checkpoint_rewards.get('personal', [])
        
        # Add personal checkpoint rewards to totals
        personal_crystals = 0
        personal_quartzs = 0
        personal_daphine = 0
        for pr in personal_rewards:
            reward = pr.get('reward', {})
            personal_crystals += reward.get('crystals', 0)
            personal_quartzs += reward.get('quartzs', 0)
            personal_daphine += reward.get('daphine', 0)
        
        total_crystals = crystals + personal_crystals
        total_quartzs = quartzs + personal_quartzs
        total_daphine = daphine + personal_daphine
        
        # Build reward display
        reward_text = "**Immediate Rewards:**\n"
        if crystals > 0:
            reward_text += f"💎 **Crystals:** +{crystals:,}"
            if awakened_count > 0:
                reward_text += f" (🦋 {awakened_count}x awakened x{awakened_multiplier:.2f})"
            reward_text += "\n"
        if quartzs > 0:
            reward_text += f"💠 **Quartzs:** +{quartzs:,}\n"
        if daphine > 0:
            reward_text += f"🦋 **Daphine:** +{daphine:,}\n"
        
        # Display immediate items (merge duplicates)
        immediate_items = immediate_rewards.get('items', [])
        if immediate_items:
            # Merge items by item_id
            merged_items = {}
            for item_dict in immediate_items:
                item_id = item_dict.get('item_id', '')
                quantity = item_dict.get('quantity', 1)
                if item_id in merged_items:
                    merged_items[item_id] += quantity
                else:
                    merged_items[item_id] = quantity
            
            # Display merged items
            for item_id, total_quantity in merged_items.items():
                item_name = self.item_lookup.get(item_id, {}).get('name', item_id)
                if total_quantity > 1:
                    reward_text += f"🎁 **{total_quantity}x {item_name}**\n"
                else:
                    reward_text += f"🎁 **{item_name}**\n"
        
        # Personal checkpoint rewards
        personal_items = []
        for pr in personal_rewards:
            reward = pr.get('reward', {})
            personal_items.extend(reward.get('items', []))
        
        if personal_crystals > 0 or personal_quartzs > 0 or personal_daphine > 0 or personal_items:
            reward_text += f"\n**Personal Checkpoint Rewards:**\n"
            if personal_crystals > 0:
                reward_text += f"💎 **Crystals:** +{personal_crystals:,}\n"
            if personal_quartzs > 0:
                reward_text += f"💠 **Quartzs:** +{personal_quartzs:,}\n"
            if personal_daphine > 0:
                reward_text += f"🦋 **Daphine:** +{personal_daphine:,}\n"
            
            # Display personal checkpoint items (merge duplicates)
            if personal_items:
                # Merge items by item_id
                merged_items = {}
                for item_dict in personal_items:
                    item_id = item_dict.get('item_id', '')
                    quantity = item_dict.get('quantity', 1)
                    if item_id in merged_items:
                        merged_items[item_id] += quantity
                    else:
                        merged_items[item_id] = quantity
                
                # Display merged items
                for item_id, total_quantity in merged_items.items():
                    item_name = self.item_lookup.get(item_id, {}).get('name', item_id)
                    if total_quantity > 1:
                        reward_text += f"🎁 **{total_quantity}x {item_name}**\n"
                    else:
                        reward_text += f"🎁 **{item_name}**\n"
        
        # Next personal checkpoint
        reward_text += f"\n**Next Personal Checkpoint:**\n"
        next_checkpoint = None
        from services.world_threat_service import WorldThreatService
        for checkpoint in sorted(WorldThreatService.PERSONAL_CHECKPOINTS):
            if total_points < checkpoint:
                next_checkpoint = checkpoint
                break
        
        if next_checkpoint:
            remaining = next_checkpoint - total_points
            reward_text += f"  🎯 {next_checkpoint:,} points ({remaining:,} to go)"
        else:
            reward_text += f"  ✅ All checkpoints completed!"
        
        embed.add_field(name="🎁 Rewards Earned", value=reward_text, inline=False)
        
        # Progress update
        progress_text = f"**Your Total:** {total_points:,} points"
        embed.add_field(name="📊 Your Progress", value=progress_text, inline=False)
        
        # Boss evolved
        embed.add_field(
            name="🌀 Boss Evolution",
            value="The boss has evolved! Use `/wt_status` to see new stats.",
            inline=False
        )
        
        # Disable all components
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True
        
        await interaction.edit_original_response(view=self)
        await interaction.followup.send(embed=embed)
        
        # Server checkpoint announcements (separate embeds)
        server_rewards = checkpoint_rewards.get('server', [])
        if server_rewards:
            for sr in server_rewards:
                checkpoint = sr['checkpoint']
                reward = sr.get('reward', {})
                
                server_embed = discord.Embed(
                    title="🌟 SERVER BREAKTHROUGH! 🌟",
                    description=f"The server has reached **{checkpoint:,} total points**!",
                    color=0xFFD700  # Gold color
                )
                
                # Show what everyone gets
                reward_list = []
                if reward.get('crystals', 0) > 0:
                    reward_list.append(f"💎 {reward['crystals']:,} Crystals")
                if reward.get('quartzs', 0) > 0:
                    reward_list.append(f"💠 {reward['quartzs']:,} Quartzs")
                if reward.get('daphine', 0) > 0:
                    reward_list.append(f"🦋 {reward['daphine']:,} Daphine")
                
                # Display server checkpoint items
                server_items = reward.get('items', [])
                if server_items:
                    for item_dict in server_items:
                        item_id = item_dict.get('item_id', '')
                        quantity = item_dict.get('quantity', 1)
                        item_name = self.item_lookup.get(item_id, {}).get('name', item_id)
                        if quantity > 1:
                            reward_list.append(f"🎁 {quantity}x {item_name}")
                        else:
                            reward_list.append(f"🎁 {item_name}")
                
                if reward_list:
                    server_embed.add_field(
                        name="🎁 Everyone Receives:",
                        value="\n".join(reward_list),
                        inline=False
                    )
                
                # Find next server checkpoint
                next_server_checkpoint = None
                for next_cp in sorted(WorldThreatService.SERVER_CHECKPOINTS):
                    if next_cp > checkpoint:
                        next_server_checkpoint = next_cp
                        break
                
                keep_fighting_text = f"Thanks to **{interaction.user.display_name}**'s contribution!"
                if next_server_checkpoint:
                    keep_fighting_text += f"\n\n**Next Goal:** {next_server_checkpoint:,} points"
                else:
                    keep_fighting_text += "\n\n🏆 Final server checkpoint reached!"
                
                server_embed.add_field(
                    name="💪 Keep Fighting!",
                    value=keep_fighting_text,
                    inline=False
                )
                
                server_embed.set_footer(text=f"World Threat: {self.boss.boss_name}")
                
                await interaction.followup.send(embed=server_embed)


# === STATUS VIEW ===

class StatusView(discord.ui.View):
    """Main status view for World Threat with pagination."""
    
    def __init__(self, boss, player_status, user_id: int, world_threat_service, db=None):
        super().__init__(timeout=300.0)
        self.boss = boss
        self.player_status = player_status
        self.user_id = user_id
        self.world_threat_service = world_threat_service
        self.db = db
        self.item_lookup = {}
        self.current_page = 0  # 0 = Boss Info, 1 = Rewards & Progress
        self._setup_ui()
    
    async def setup_item_lookup(self):
        """Load item data for displaying item names."""
        if self.db:
            try:
                item_data = await self.db.get_shop_items()
                for item in item_data:
                    item_id_int = item.get('id')
                    if item_id_int:
                        self.item_lookup[f"item_{item_id_int}"] = item
            except Exception:
                pass
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the command user can interact."""
        return interaction.user.id == self.user_id
    
    async def _create_status_embed(self) -> discord.Embed:
        """Create the status embed based on current page."""
        from services.world_threat_service import WorldThreatService
        
        if self.current_page == 0:
            # Page 1: Boss Info & Current Status
            embed = discord.Embed(
                title=f"🌍 World Threat: {self.boss.boss_name}",
                description="Server-wide cooperative boss battle",
                color=0x8E44AD
            )
            
            # Boss stats
            boss_stats = format_boss_stats(self.boss)
            embed.add_field(name="📊 Boss Stats", value=boss_stats, inline=False)
            
            # Active buffs
            buffs_text = format_affinities(self.boss.buffs, "Buffs", self.world_threat_service.data_manager)
            embed.add_field(name="🎯 Active Buffs (Favored)", value=buffs_text, inline=True)
            
            # Active curses
            curses_text = format_affinities(self.boss.curses, "Curses", self.world_threat_service.data_manager)
            embed.add_field(name="💀 Active Curses (Forbidden)", value=curses_text, inline=True)
            
            # Adaptation progress
            adaptation_text = (
                f"**Current Level:** {self.boss.adaptation_level}\n"
                f"**Damage Multiplier:** x{0.9 ** self.boss.adaptation_level:.2f}\n"
                f"**Research Actions:** {self.boss.total_research_actions}\n\n"
            )
            
            if self.boss.adaptation_level < 2:
                next_threshold = WorldThreatService.RESEARCH_ADAPTATION_THRESHOLD_2 if self.boss.adaptation_level == 1 else WorldThreatService.RESEARCH_ADAPTATION_THRESHOLD_1
                remaining = next_threshold - self.boss.total_research_actions
                progress_pct = (self.boss.total_research_actions / next_threshold) * 100
                filled = int(progress_pct / 10)
                bar = "█" * filled + "░" * (10 - filled)
                
                adaptation_text += f"**Next Evolution:** {next_threshold} research ({remaining} to go)\n"
                adaptation_text += f"{bar} {progress_pct:.1f}%"
            else:
                adaptation_text += "🔒 **Maximum adaptation reached**"
            
            embed.add_field(name="🧬 Adaptation Progress", value=adaptation_text, inline=False)
            
            # Current status summary
            action_check = await self.world_threat_service.can_perform_action(str(self.user_id))
            action_status = format_cooldown(action_check.get("time_remaining", 0))
            research_text = f"x{2**self.player_status.research_stacks}" if self.player_status.research_stacks > 0 else "None"
            
            status_text = (
                f"**Server Total:** {self.boss.server_total_points:,} points\n"
                f"**Your Total:** {self.player_status.cumulative_points:,} points\n"
                f"**Research Stacks:** {self.player_status.research_stacks} ({research_text} multiplier)\n"
                f"**Action Status:** {action_status}"
            )
            embed.add_field(name="📈 Current Status", value=status_text, inline=False)
            
            embed.set_footer(text=f"Page 1/2 • Last updated {datetime.now(timezone.utc).strftime('%H:%M UTC')}")
        
        else:
            # Page 2: Checkpoint Rewards & Progress
            embed = discord.Embed(
                title=f"🎁 Checkpoint Rewards & Progress",
                description="Track your progress towards milestone rewards",
                color=0x8E44AD
            )
            
            # Server progress with detailed rewards
            server_checkpoints = WorldThreatService.SERVER_CHECKPOINTS
            next_server_checkpoint = None
            next_server_rewards = None
            for checkpoint in sorted(server_checkpoints):
                if self.boss.server_total_points < checkpoint:
                    next_server_checkpoint = checkpoint
                    next_server_rewards = WorldThreatService.SERVER_CHECKPOINT_REWARDS.get(checkpoint, {})
                    break
            
            server_text = f"**Current Total:** {self.boss.server_total_points:,}\n\n"
            
            if next_server_checkpoint:
                remaining = next_server_checkpoint - self.boss.server_total_points
                progress_pct = (self.boss.server_total_points / next_server_checkpoint) * 100
                filled = int(progress_pct / 10)
                bar = "█" * filled + "░" * (10 - filled)
                
                server_text += f"**Next Checkpoint:** {next_server_checkpoint:,} ({remaining:,} to go)\n"
                server_text += f"{bar} {progress_pct:.1f}%\n\n"
                server_text += "**Rewards for Everyone:**\n"
                if next_server_rewards.get('crystals', 0) > 0:
                    server_text += f"💎 {next_server_rewards['crystals']:,} Crystals\n"
                if next_server_rewards.get('quartzs', 0) > 0:
                    server_text += f"💠 {next_server_rewards['quartzs']:,} Quartzs\n"
                if next_server_rewards.get('daphine', 0) > 0:
                    server_text += f"🦋 {next_server_rewards['daphine']:,} Daphine\n"
                
                # Display server checkpoint items
                server_items = next_server_rewards.get('items', [])
                if server_items:
                    for item_dict in server_items:
                        item_id = item_dict.get('item_id', '')
                        quantity = item_dict.get('quantity', 1)
                        item_name = self.item_lookup.get(item_id, {}).get('name', item_id)
                        if quantity > 1:
                            server_text += f"🎁 {quantity}x {item_name}\n"
                        else:
                            server_text += f"🎁 {item_name}\n"
            else:
                server_text += "🏆 All server checkpoints reached!"
            
            embed.add_field(name="🌐 Server Progress", value=server_text, inline=False)
            
            # Personal progress with detailed rewards
            personal_checkpoints = WorldThreatService.PERSONAL_CHECKPOINTS
            next_personal_checkpoint = None
            next_personal_rewards = None
            for checkpoint in sorted(personal_checkpoints):
                if self.player_status.cumulative_points < checkpoint:
                    next_personal_checkpoint = checkpoint
                    next_personal_rewards = WorldThreatService.PERSONAL_CHECKPOINT_REWARDS.get(checkpoint, {})
                    break
            
            action_check = await self.world_threat_service.can_perform_action(str(self.user_id))
            action_status = format_cooldown(action_check.get("time_remaining", 0))
            research_text = f"x{2**self.player_status.research_stacks}" if self.player_status.research_stacks > 0 else "None"
            
            personal_text = (
                f"**Your Points:** {self.player_status.cumulative_points:,}\n"
                f"**Research Stacks:** {self.player_status.research_stacks} ({research_text} multiplier)\n"
                f"**Action Status:** {action_status}\n\n"
            )
            
            if next_personal_checkpoint:
                remaining = next_personal_checkpoint - self.player_status.cumulative_points
                progress_pct = (self.player_status.cumulative_points / next_personal_checkpoint) * 100
                filled = int(progress_pct / 10)
                bar = "█" * filled + "░" * (10 - filled)
                
                personal_text += f"**Next Checkpoint:** {next_personal_checkpoint:,} ({remaining:,} to go)\n"
                personal_text += f"{bar} {progress_pct:.1f}%\n\n"
                personal_text += "**Rewards:**\n"
                if next_personal_rewards.get('crystals', 0) > 0:
                    personal_text += f"💎 {next_personal_rewards['crystals']:,} Crystals\n"
                if next_personal_rewards.get('quartzs', 0) > 0:
                    personal_text += f"💠 {next_personal_rewards['quartzs']:,} Quartzs\n"
                if next_personal_rewards.get('daphine', 0) > 0:
                    personal_text += f"🦋 {next_personal_rewards['daphine']:,} Daphine\n"
                
                # Display personal checkpoint items
                personal_items = next_personal_rewards.get('items', [])
                if personal_items:
                    for item_dict in personal_items:
                        item_id = item_dict.get('item_id', '')
                        quantity = item_dict.get('quantity', 1)
                        item_name = self.item_lookup.get(item_id, {}).get('name', item_id)
                        if quantity > 1:
                            personal_text += f"🎁 {quantity}x {item_name}\n"
                        else:
                            personal_text += f"🎁 {item_name}\n"
            else:
                personal_text += "🏆 All personal checkpoints reached!"
            
            embed.add_field(name="👤 Your Progress", value=personal_text, inline=False)
            
            embed.set_footer(text=f"Page 2/2 • Last updated {datetime.now(timezone.utc).strftime('%H:%M UTC')}")
        
        return embed
    
    def _setup_ui(self):
        """Setup UI buttons with pagination."""
        self.clear_items()
        
        # Previous button
        prev_button = discord.ui.Button(
            label="◀ Previous",
            style=discord.ButtonStyle.primary,
            custom_id="prev_page",
            disabled=self.current_page == 0
        )
        prev_button.callback = self.prev_page
        self.add_item(prev_button)
        
        # Refresh button
        refresh_button = discord.ui.Button(
            label="🔄 Refresh",
            style=discord.ButtonStyle.secondary,
            custom_id="refresh"
        )
        refresh_button.callback = self.refresh_status
        self.add_item(refresh_button)
        
        # Next button
        next_button = discord.ui.Button(
            label="Next ▶",
            style=discord.ButtonStyle.primary,
            custom_id="next_page",
            disabled=self.current_page == 1
        )
        next_button.callback = self.next_page
        self.add_item(next_button)
    
    async def prev_page(self, interaction: discord.Interaction):
        """Go to previous page."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can navigate.", ephemeral=True)
            return
        
        self.current_page = max(0, self.current_page - 1)
        self._setup_ui()
        
        # Refresh data
        self.boss = await self.world_threat_service.get_boss()
        self.player_status = await self.world_threat_service.get_player_status(str(self.user_id))
        
        embed = await self._create_status_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def next_page(self, interaction: discord.Interaction):
        """Go to next page."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can navigate.", ephemeral=True)
            return
        
        self.current_page = min(1, self.current_page + 1)
        self._setup_ui()
        
        # Refresh data
        self.boss = await self.world_threat_service.get_boss()
        self.player_status = await self.world_threat_service.get_player_status(str(self.user_id))
        
        embed = await self._create_status_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def refresh_status(self, interaction: discord.Interaction):
        """Refresh the status display."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can refresh.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Reload data
        self.boss = await self.world_threat_service.get_boss()
        self.player_status = await self.world_threat_service.get_player_status(str(self.user_id))
        
        embed = await self._create_status_embed()
        await interaction.edit_original_response(embed=embed, view=self)


# === CONFIRM RESEARCH VIEW ===

class ConfirmResearchView(discord.ui.View):
    """Confirmation view for research action."""
    
    def __init__(self, player_status, boss, user_id: int, world_threat_service):
        super().__init__(timeout=180.0)
        self.player_status = player_status
        self.boss = boss
        self.user_id = user_id
        self.world_threat_service = world_threat_service
        self._setup_ui()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    async def _create_confirmation_embed(self) -> discord.Embed:
        """Create the confirmation embed."""
        current_stacks = self.player_status.research_stacks
        new_stacks = min(current_stacks + 1, self.world_threat_service.MAX_RESEARCH_STACKS)
        current_mult = 2 ** current_stacks
        new_mult = 2 ** new_stacks
        
        embed = discord.Embed(
            title="🔬 Confirm Research Action",
            description="Spend your daily action on research instead of fighting?",
            color=0x3498DB
        )
        
        status_text = (
            f"📚 **Current Research Stacks:** {current_stacks} (x{current_mult} multiplier)\n"
            f"📈 **After Research:** {new_stacks} (x{new_mult} multiplier)\n\n"
            f"💡 Your next fight will earn **x{new_mult} points**!"
        )
        embed.add_field(name="Research Status", value=status_text, inline=False)
        
        warning_text = (
            f"⚠️ This uses your daily action (24h cooldown will apply)\n\n"
            f"🌀 **Boss Evolution:**\n"
            f"The boss will evolve its stats and affinities after this action."
        )
        embed.add_field(name="Important", value=warning_text, inline=False)
        
        return embed
    
    def _setup_ui(self):
        """Setup UI buttons."""
        self.clear_items()
        
        confirm_button = discord.ui.Button(
            label="✅ Confirm Research",
            style=discord.ButtonStyle.success,
            custom_id="confirm"
        )
        confirm_button.callback = self.confirm_research
        self.add_item(confirm_button)
        
        cancel_button = discord.ui.Button(
            label="❌ Cancel",
            style=discord.ButtonStyle.secondary,
            custom_id="cancel"
        )
        cancel_button.callback = self.cancel_research
        self.add_item(cancel_button)
    
    async def confirm_research(self, interaction: discord.Interaction):
        """Execute research action."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can confirm.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Re-check cooldown to prevent exploit
        action_check = await self.world_threat_service.can_perform_action(str(self.user_id))
        if not action_check["can_act"]:
            time_remaining = action_check["time_remaining"]
            await interaction.followup.send(
                f"⏳ Your action is on cooldown. {format_cooldown(time_remaining)}",
                ephemeral=True
            )
            return
        
        # Perform research
        result = await self.world_threat_service.perform_research(str(self.user_id))
        
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            await interaction.followup.send(f"❌ Research failed: {error_msg}", ephemeral=True)
            return
        
        new_stacks = result.get("new_stacks", 0)
        multiplier = result.get("research_multiplier", 1)
        
        embed = discord.Embed(
            title="🔬 Research Complete!",
            description=f"You now have **{new_stacks} research stacks** (x{multiplier} multiplier)",
            color=0x00FF00
        )
        
        info_text = (
            f"✅ Research action completed successfully\n"
            f"⏳ Your action is now on cooldown for 24 hours\n"
            f"🌀 The boss has evolved its stats and affinities\n\n"
            f"💡 Your next fight will earn **{multiplier}x points**!"
        )
        embed.add_field(name="Status", value=info_text, inline=False)
        
        # Disable all buttons
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        
        await interaction.edit_original_response(view=self)
        await interaction.followup.send(embed=embed)
    
    async def cancel_research(self, interaction: discord.Interaction):
        """Cancel research action."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can cancel.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Research Cancelled",
            description="Research action has been cancelled.",
            color=0xFF6B6B
        )
        
        # Disable all buttons
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)


# === MAIN COG ===

class WorldThreatCog(BaseCommand):
    """Discord commands for World Threat game mode."""
    
    @app_commands.command(name="nwnl_wt_status", description="📊 View the current World Threat status")
    async def nwnl_wt_status(self, interaction: discord.Interaction):
        """Display current boss and player status."""
        await interaction.response.defer()
        
        try:
            # Get boss and player data
            boss = await self.services.world_threat_service.get_boss()
            if not boss:
                await interaction.followup.send(
                    "❌ No active World Threat boss. Contact an administrator.",
                    ephemeral=True
                )
                return
            
            player_status = await self.services.world_threat_service.get_player_status(str(interaction.user.id))
            
            # Create and send view
            view = StatusView(
                boss, 
                player_status, 
                interaction.user.id, 
                self.services.world_threat_service,
                db=self.services.database
            )
            
            # Load item data for displaying item names
            await view.setup_item_lookup()
            
            embed = await view._create_status_embed()
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            self.logger.error(f"Error in wt_status: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ An error occurred while loading World Threat status.",
                ephemeral=True
            )
    
    @app_commands.command(name="nwnl_wt_research", description="🔬 Perform research on the World Threat boss")
    async def nwnl_wt_research(self, interaction: discord.Interaction):
        """Initiate research action."""
        await interaction.response.defer()
        
        try:
            # Check cooldown
            action_check = await self.services.world_threat_service.can_perform_action(str(interaction.user.id))
            if not action_check["can_act"]:
                time_remaining = action_check["time_remaining"]
                await interaction.followup.send(
                    f"⏳ Your action is on cooldown. {format_cooldown(time_remaining)}",
                    ephemeral=True
                )
                return
            
            # Get current status
            boss = await self.services.world_threat_service.get_boss()
            if not boss:
                await interaction.followup.send(
                    "❌ No active World Threat boss.",
                    ephemeral=True
                )
                return
            
            player_status = await self.services.world_threat_service.get_player_status(str(interaction.user.id))
            
            # Check if already at max stacks
            if player_status.research_stacks >= self.services.world_threat_service.MAX_RESEARCH_STACKS:
                await interaction.followup.send(
                    f"❌ You already have maximum research stacks ({self.services.world_threat_service.MAX_RESEARCH_STACKS}).\n"
                    f"Use them by fighting the boss with `/wt_fight`!",
                    ephemeral=True
                )
                return
            
            # Show confirmation view
            view = ConfirmResearchView(player_status, boss, interaction.user.id, self.services.world_threat_service)
            embed = await view._create_confirmation_embed()
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            self.logger.error(f"Error in wt_research: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ An error occurred. Please try again.",
                ephemeral=True
            )
    
    @app_commands.command(name="nwnl_wt_fight", description="⚔️ Fight the World Threat boss")
    async def nwnl_wt_fight(self, interaction: discord.Interaction):
        """Start the fight flow with team selection."""
        await interaction.response.defer()
        
        try:
            # Check cooldown
            action_check = await self.services.world_threat_service.can_perform_action(str(interaction.user.id))
            if not action_check["can_act"]:
                time_remaining = action_check["time_remaining"]
                await interaction.followup.send(
                    f"⏳ Your action is on cooldown. {format_cooldown(time_remaining)}",
                    ephemeral=True
                )
                return
            
            # Get boss
            boss = await self.services.world_threat_service.get_boss()
            if not boss:
                await interaction.followup.send(
                    "❌ No active World Threat boss. Contact an administrator.",
                    ephemeral=True
                )
                return
            
            # Get player status
            player_status = await self.services.world_threat_service.get_player_status(str(interaction.user.id))
            
            # Get available characters (already filtered by service)
            available_characters = await self.services.world_threat_service.get_available_characters(str(interaction.user.id))
            
            if len(available_characters) < 6:
                await interaction.followup.send(
                    f"❌ You need at least 6 available characters to fight.\n"
                    f"You have {len(available_characters)} available.\n"
                    f"Some characters may be excluded due to cursed affinities.",
                    ephemeral=True
                )
                return
            
            # Show team selection view
            view = WorldThreatTeamSelectView(
                available_characters,
                boss,
                interaction.user.id,
                self.services.world_threat_service,
                player_status,
                db=self.services.database
            )
            
            # Load item data for displaying item names in rewards
            await view.setup_item_lookup()
            
            embed = await view._create_selection_embed()
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            self.logger.error(f"Error in wt_fight: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ An error occurred. Please try again.",
                ephemeral=True
            )
    
    @app_commands.command(name="nwnl_wt_rewards", description="📜 View reward distribution explanation")
    @app_commands.describe(reward_type="Choose which reward type to view")
    @app_commands.choices(reward_type=[
        app_commands.Choice(name="Immediate Rewards (per fight)", value="immediate"),
        app_commands.Choice(name="Personal Checkpoints (cumulative)", value="personal"),
        app_commands.Choice(name="Server Checkpoints (global)", value="server")
    ])
    async def nwnl_wt_rewards(self, interaction: discord.Interaction, reward_type: str):
        """Display reward distribution explanation for the chosen type."""
        await interaction.response.defer()
        
        try:
            from services.world_threat_service import WorldThreatService
            
            # Get player status and boss for displaying current scores
            player_status = await self.services.world_threat_service.get_player_status(str(interaction.user.id))
            boss = await self.services.world_threat_service.get_boss()
            
            # Create view with data
            view = RewardsPaginationView(
                reward_type,
                player_status=player_status,
                boss=boss,
                db=self.services.database
            )
            
            # Setup async (loads item data)
            await view.setup()
            
            embed = view.create_embed()
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            self.logger.error(f"Error in wt_rewards: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ An error occurred while fetching reward information.",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Setup function for loading the cog."""
    await bot.add_cog(WorldThreatCog(bot, bot.services))
