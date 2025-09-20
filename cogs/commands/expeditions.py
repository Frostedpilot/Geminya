MAX_EXPEDITION_SLOTS = 5  # Should match ExpeditionManager default
"""Expedition system Discord commands with comprehensive UI."""

import discord
from discord.ext import commands
from discord import app_commands
from typing import List, Dict
from datetime import datetime, timedelta, timezone

from cogs.base_command import BaseCommand
from services.container import ServiceContainer
from src.wanderer_game.systems.loot_generator import LootGenerator


class CharacterSearchModal(discord.ui.Modal):
    """Modal for searching characters by name."""
    
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
        
        # Update start button state after _setup_ui recreates it
        for item in self.character_view.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "start_expedition":
                item.disabled = len(self.character_view.selected_characters) == 0
                break
        
        embed = await self.character_view._create_character_selection_embed()
        await interaction.response.edit_message(embed=embed, view=self.character_view)


class ExpeditionListView(discord.ui.View):
    """View for browsing expeditions (list only, no selection)."""
    
    def __init__(self, expeditions: List[Dict], user_id: int):
        super().__init__(timeout=300.0)
        self.expeditions = expeditions
        self.user_id = user_id
        self.current_page = 0
        self.items_per_page = 10  # Show more details, so fewer per page
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI components based on current page."""
        self.clear_items()
        
        # Add pagination buttons if needed
        self._add_pagination_buttons()
    
    def _add_pagination_buttons(self):
        """Add pagination buttons if needed."""
        total_pages = self.total_pages
        
        if total_pages > 1:
            # Previous page button
            prev_button = discord.ui.Button(
                label="◀️ Previous",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page == 0,
                custom_id="prev_page"
            )
            prev_button.callback = self.previous_page
            self.add_item(prev_button)
            
            # Page indicator
            page_button = discord.ui.Button(
                label=f"Page {self.current_page + 1}/{total_pages}",
                style=discord.ButtonStyle.primary,
                disabled=True,
                custom_id="page_indicator"
            )
            self.add_item(page_button)
            
            # Next page button
            next_button = discord.ui.Button(
                label="▶️ Next",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page >= total_pages - 1,
                custom_id="next_page"
            )
            next_button.callback = self.next_page
            self.add_item(next_button)
        
        # Add "Start Expedition" button to redirect to start command
        # REMOVED: Button removed to prevent bugs as requested
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return (len(self.expeditions) + self.items_per_page - 1) // self.items_per_page
    
    async def previous_page(self, interaction: discord.Interaction):
        """Go to previous page."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can navigate pages.", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self._setup_ui()
            
            embed = await self._create_expedition_list_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    async def next_page(self, interaction: discord.Interaction):
        """Go to next page."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can navigate pages.", ephemeral=True)
            return
        
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._setup_ui()
            
            embed = await self._create_expedition_list_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    # async def redirect_to_start(self, interaction: discord.Interaction):
    #     """Redirect user to use the start command."""
    #     # REMOVED: Method disabled as button was removed to prevent bugs
    #     pass
    
    async def _create_expedition_list_embed(self) -> discord.Embed:
        """Create expedition list embed for current page."""
        embed = discord.Embed(
            title="📜 Expedition Catalog",
            description=f"**Page {self.current_page + 1}/{self.total_pages}** | **Total:** {len(self.expeditions)} expeditions available\n\n"
                       f"Browse all available expeditions and their details:",
            color=0x8E44AD
        )
        # Calculate page boundaries
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.expeditions))
        current_expeditions = self.expeditions[start_idx:end_idx]
        # Add detailed expedition info
        for expedition in current_expeditions:
            duration = expedition.get('duration_hours', 4)
            difficulty = expedition.get('difficulty', 100)
            difficulty_tier = expedition.get('difficulty_tier', 1)
            if 'expected_encounters' in expedition:
                encounters = expedition['expected_encounters']
                encounters_str = f"~{encounters} battles"
            else:
                min_enc = max(1, int(duration * 0.5))
                max_enc = max(1, int(duration * 1.5))
                encounters_str = f"~{min_enc}-{max_enc} battles"
            favored = expedition.get('num_favored_affinities', 0)
            disfavored = expedition.get('num_disfavored_affinities', 0)
            expedition_id = expedition.get('expedition_id', 'unknown')
            difficulty_emoji = "⭐" * min(difficulty_tier, 5)
            description_parts = [
                f"🆔 **ID:** `{expedition_id}`",
                f"⏱️ **Duration:** {duration} hours",
                f"{difficulty_emoji} **Difficulty:** {difficulty}",
                f"⚔️ **Encounters:** {encounters_str}"
            ]
            # Add per-encounter affinity info
            if favored > 0 or disfavored > 0:
                description_parts.append(f"🔮 **Per Encounter:** {favored} favored, {disfavored} disfavored affinities")
                affinity_pools = expedition.get('affinity_pools', {})
                if favored > 0 and 'favored' in affinity_pools:
                    buff_names = []
                    for category, values in affinity_pools['favored'].items():
                        if isinstance(values, list) and values:
                            buff_names.extend(values)
                    if buff_names:
                        description_parts.append(f"✅ **Buffs:** {', '.join(buff_names)}")
                    else:
                        description_parts.append(f"✅ **Buffs:** {favored} character bonuses")
                if disfavored > 0 and 'disfavored' in affinity_pools:
                    debuff_names = []
                    for category, values in affinity_pools['disfavored'].items():
                        if isinstance(values, list) and values:
                            debuff_names.extend(values)
                    if debuff_names:
                        description_parts.append(f"❌ **Debuffs:** {', '.join(debuff_names)}")
                    else:
                        description_parts.append(f"❌ **Debuffs:** {disfavored} character penalties")
                if favored > 0 and not any('Buffs:' in part for part in description_parts):
                    description_parts.append(f"✅ **Buffs:** {favored} character bonuses")
                if disfavored > 0 and not any('Debuffs:' in part for part in description_parts):
                    description_parts.append(f"❌ **Debuffs:** {disfavored} character penalties")
            embed.add_field(
                name=f"🗺️ {expedition['name']}",
                value="\n".join(description_parts),
                inline=False
            )
        embed.set_footer(text="Use the buttons below to navigate • Use /nwnl_expeditions_start to begin an expedition!")
        return embed


class ExpeditionSelectView(discord.ui.View):
    """View for selecting available expeditions with pagination."""
    
    def __init__(self, expeditions: List[Dict], user_id: int, expedition_service):
        super().__init__(timeout=300.0)
        self.expeditions = expeditions
        self.user_id = user_id
        self.expedition_service = expedition_service
        self.selected_expedition = None
        self.current_page = 0
        self.items_per_page = 25  # Discord select menu limit
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI components based on current page."""
        self.clear_items()
        
        # Calculate page boundaries
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.expeditions))
        current_expeditions = self.expeditions[start_idx:end_idx]
        
        # Create select menu for expeditions
        options = []
        for i, expedition in enumerate(current_expeditions):
            duration_hours = expedition.get('duration_hours', 4)
            difficulty = expedition.get('difficulty', 100)  # Use original difficulty
            difficulty_tier = expedition.get('difficulty_tier', 1)  # For emoji
            
            # Create emoji based on difficulty tier
            difficulty_emoji = "⭐" * min(difficulty_tier, 5)
            
            options.append(discord.SelectOption(
                label=expedition['name'][:100],  # Discord limit
                description=f"{difficulty_emoji} | {duration_hours}h | Difficulty {difficulty}",  # Show original
                value=str(start_idx + i),  # Global index
                emoji="🗺️"
            ))
        
        if options:
            self.expedition_select = discord.ui.Select(
                placeholder=f"Choose an expedition... (Page {self.current_page + 1}/{self.total_pages})",
                options=options,
                custom_id="expedition_select"
            )
            self.expedition_select.callback = self.expedition_selected
            self.add_item(self.expedition_select)
        
        # Add pagination buttons
        self._add_pagination_buttons()
    
    def _add_pagination_buttons(self):
        """Add pagination buttons if needed."""
        total_pages = self.total_pages
        
        if total_pages > 1:
            # Previous page button
            prev_button = discord.ui.Button(
                label="◀️ Previous",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page == 0,
                custom_id="prev_page"
            )
            prev_button.callback = self.previous_page
            self.add_item(prev_button)
            
            # Page indicator
            page_button = discord.ui.Button(
                label=f"Page {self.current_page + 1}/{total_pages}",
                style=discord.ButtonStyle.primary,
                disabled=True,
                custom_id="page_indicator"
            )
            self.add_item(page_button)
            
            # Next page button
            next_button = discord.ui.Button(
                label="▶️ Next",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page >= total_pages - 1,
                custom_id="next_page"
            )
            next_button.callback = self.next_page
            self.add_item(next_button)
        
        # Add cancel button (always visible)
        cancel_button = discord.ui.Button(
            label="❌ Cancel",
            style=discord.ButtonStyle.danger,
            custom_id="cancel_expedition_start"
        )
        cancel_button.callback = self.cancel_expedition_start
        self.add_item(cancel_button)

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return (len(self.expeditions) + self.items_per_page - 1) // self.items_per_page
    
    async def previous_page(self, interaction: discord.Interaction):
        """Go to previous page."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can navigate pages.", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self._setup_ui()
            
            embed = await self._create_expedition_list_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    async def next_page(self, interaction: discord.Interaction):
        """Go to next page."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can navigate pages.", ephemeral=True)
            return
        
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._setup_ui()
            
            embed = await self._create_expedition_list_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    async def cancel_expedition_start(self, interaction: discord.Interaction):
        """Cancel the expedition start process."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can cancel.", ephemeral=True)
            return
        
        # Create cancellation embed
        embed = discord.Embed(
            title="❌ Expedition Start Cancelled",
            description="You have cancelled the expedition start process.\n\n"
                       "Use `/nwnl_expeditions_start` again when you're ready to begin an adventure!",
            color=0x95A5A6
        )
        
        # Clear the view to disable all buttons
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=None)

    async def _create_expedition_list_embed(self) -> discord.Embed:
        """Create expedition list embed for current page."""
        embed = discord.Embed(
            title="🗺️ Available Expeditions",
            description=f"**Page {self.current_page + 1}/{self.total_pages}** | **Total:** {len(self.expeditions)} expeditions\n\n"
                       f"Choose an expedition to view details and start your adventure:",
            color=0x3498DB
        )
        # Calculate page boundaries
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.expeditions))
        current_expeditions = self.expeditions[start_idx:end_idx]
        # Add expedition preview (first 5 of current page)
        for i, expedition in enumerate(current_expeditions[:5]):
            duration = expedition.get('duration_hours', 4)
            difficulty = expedition.get('difficulty', 100)
            difficulty_tier = expedition.get('difficulty_tier', 1)
            encounters = expedition.get('expected_encounters', 5)
            favored = expedition.get('num_favored_affinities', 0)
            disfavored = expedition.get('num_disfavored_affinities', 0)
            difficulty_emoji = "⭐" * min(difficulty_tier, 5)
            # Add per-encounter affinity info
            affinity_info = ""
            if favored > 0 or disfavored > 0:
                affinity_info = f" | 🔮 {favored} favored, {disfavored} disfavored/encounter"
            embed.add_field(
                name=f"🗺️ {expedition['name']}",
                value=f"⏱️ {duration}h | {difficulty_emoji} {difficulty} | ⚔️ ~{encounters} encounters{affinity_info}",
                inline=False
            )
        if len(current_expeditions) > 5:
            embed.add_field(
                name="📜 More Expeditions",
                value=f"And {len(current_expeditions) - 5} more expeditions available in the selection menu below!",
                inline=False
            )
        embed.set_footer(text="Select an expedition below to view details and start your adventure!")
        return embed
    
    async def expedition_selected(self, interaction: discord.Interaction):
        """Handle expedition selection."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can select expeditions.", ephemeral=True)
            return
        
        expedition_index = int(self.expedition_select.values[0])  # This is now the global index
        self.selected_expedition = self.expeditions[expedition_index]
        
        # Create character selection view
        discord_id = str(interaction.user.id)
        try:
            # Get user's available characters (excluding those in active expeditions)
            user_waifus = await self.expedition_service.db.get_user_waifus_available_for_expeditions(discord_id)
            
            if not user_waifus:
                # Check if user has ANY characters at all
                all_waifus = await self.expedition_service.db.get_user_waifus_minimal(discord_id)
                
                if not all_waifus:
                    await interaction.response.send_message("❌ You don't have any characters to send on expeditions!", ephemeral=True)
                else:
                    await interaction.response.send_message(
                        "❌ All your characters are currently on expeditions! "
                        "Complete some expeditions first using `/nwnl_expeditions_complete` to free up characters.",
                        ephemeral=True
                    )
                return
            
            # Create character selection view
            character_view = CharacterSelectView(
                user_waifus, self.user_id, self.expedition_service, self.selected_expedition
            )
            
            embed = await self._create_expedition_details_embed(self.selected_expedition)
            embed.add_field(
                name="📋 Next Step",
                value="Select up to 3 characters for this expedition below:",
                inline=False
            )
            
            await interaction.response.edit_message(embed=embed, view=character_view)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error loading characters: {str(e)}", ephemeral=True)
    
    async def _create_expedition_details_embed(self, expedition: Dict) -> discord.Embed:
        """Create detailed expedition info embed."""
        embed = discord.Embed(
            title=f"🗺️ {expedition['name']}",
            description=expedition.get('description', 'An exciting expedition awaits!'),
            color=0x3498DB
        )
        duration_hours = expedition.get('duration_hours', 4)
        difficulty = expedition.get('difficulty', 100)
        difficulty_tier = expedition.get('difficulty_tier', 1)
        encounters = expedition.get('expected_encounters', 5)
        favored = expedition.get('num_favored_affinities', 0)
        disfavored = expedition.get('num_disfavored_affinities', 0)
        # Add per-encounter affinity info
        per_encounter_affinity = ""
        if favored > 0 or disfavored > 0:
            per_encounter_affinity = f"\n🔮 **Per Encounter:** {favored} favored, {disfavored} disfavored affinities"
        embed.add_field(
            name="⏱️ Duration",
            value=f"{duration_hours} hours",
            inline=True
        )
        embed.add_field(
            name="⭐ Difficulty",
            value=f"{difficulty}",
            inline=True
        )
        embed.add_field(
            name="⚔️ Encounters",
            value=f"~{encounters} battles{per_encounter_affinity}",
            inline=True
        )
        # Add affinity information
        if favored > 0 or disfavored > 0:
            affinity_pools = expedition.get('affinity_pools', {})
            affinity_text = []
            if favored > 0 and 'favored' in affinity_pools:
                favored_items = []
                for category, values in affinity_pools['favored'].items():
                    if isinstance(values, list):
                        favored_items.append(f"**{category.title()}:** {', '.join(values)}")
                    else:
                        favored_items.append(f"**{category.title()}:** {values}")
                if favored_items:
                    affinity_text.append(f"✅ **Buffs ({favored}):**\n" + "\n".join(favored_items))
            if disfavored > 0 and 'disfavored' in affinity_pools:
                disfavored_items = []
                for category, values in affinity_pools['disfavored'].items():
                    if isinstance(values, list):
                        disfavored_items.append(f"**{category.title()}:** {', '.join(values)}")
                    else:
                        disfavored_items.append(f"**{category.title()}:** {values}")
                if disfavored_items:
                    affinity_text.append(f"❌ **Debuffs ({disfavored}):**\n" + "\n".join(disfavored_items))
            if affinity_text:
                embed.add_field(
                    name="🔮 Affinity Effects",
                    value="\n\n".join(affinity_text),
                    inline=False
                )
            else:
                embed.add_field(
                    name="🔮 Affinity Effects",
                    value=f"✅ {favored} character buffs\n❌ {disfavored} character debuffs",
                    inline=False
                )
        return embed


class CharacterSelectView(discord.ui.View):
    # Global cache for series name to series_id
    _series_name_to_id_cache = None
    """View for selecting characters for expeditions with search and pagination."""
    
    def __init__(self, user_waifus: List[Dict], user_id: int, expedition_service, expedition: Dict):
        super().__init__(timeout=300.0)
        self.user_waifus = user_waifus
        self.user_id = user_id
        self.expedition_service = expedition_service
        self.expedition = expedition
        self.selected_characters = []
        self.search_filter = ""
        self.current_page = 0
        self.items_per_page = 25  # Discord select menu limit
        
        # Get character registry for names
        self.char_registry = expedition_service.data_manager.get_character_registry()
        
        # Filter and setup UI
        self._setup_ui()
    
    def _get_filtered_waifus(self) -> List[Dict]:
        """Get waifus filtered by search term."""
        if not self.search_filter:
            return self.user_waifus
        
        filtered_waifus = []
        search_lower = self.search_filter.lower()
        
        for waifu in self.user_waifus:
            character = self.char_registry.get_character(waifu['waifu_id'])
            if character:
                # Search in character name and series
                if (search_lower in character.name.lower() or 
                    search_lower in character.series.lower()):
                    filtered_waifus.append(waifu)
        
        return filtered_waifus
    
    def _setup_ui(self):
        """Setup the UI components based on current page and filter."""
        self.clear_items()
        
        # Add search modal button
        search_button = discord.ui.Button(
            label="🔍 Search Characters",
            style=discord.ButtonStyle.secondary,
            custom_id="search_characters"
        )
        search_button.callback = self.open_search_modal
        self.add_item(search_button)
        
        # Get filtered waifus
        filtered_waifus = self._get_filtered_waifus()
        
        # Safety check: if current page is beyond available pages, reset to page 0
        if filtered_waifus:
            total_pages = (len(filtered_waifus) + self.items_per_page - 1) // self.items_per_page
            if self.current_page >= total_pages:
                # ...removed debug print...
                self.current_page = 0
        
        # DEBUG: Check if we have any waifus at all
        if not filtered_waifus:
            return  # No waifus to display, exit early
        
        # Calculate page boundaries
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(filtered_waifus))
        current_waifus = filtered_waifus[start_idx:end_idx]
        
        # DEBUG: Check current page waifus
        if not current_waifus and filtered_waifus:
            pass
        
        # Create select menu for characters
        options = []
        # Track which characters on this page are already selected
        selected_on_page = []
        
        for waifu in current_waifus:
            character = self.char_registry.get_character(waifu['waifu_id'])
            if character:
                star_level = waifu.get('current_star_level', 1)
                bond_level = waifu.get('bond_level', 1)
                user_waifu_id = waifu['user_waifu_id']
                
                # Check if this character is already selected
                is_selected = user_waifu_id in self.selected_characters
                if is_selected:
                    selected_on_page.append(str(user_waifu_id))
                
                # Add selection indicator
                name_prefix = "✅ " if is_selected else ""
                
                options.append(discord.SelectOption(
                    label=f"{name_prefix}{character.name}"[:100],  # Discord limit
                    description=f"⭐{star_level} | {character.series[:40]}",
                    value=str(user_waifu_id),
                    emoji="👤",
                    default=is_selected  # Mark as default if selected
                ))
            else:
                # If character not found in registry, add fallback option
                user_waifu_id = waifu['user_waifu_id']
                is_selected = user_waifu_id in self.selected_characters
                if is_selected:
                    selected_on_page.append(str(user_waifu_id))
                
                name_prefix = "✅ " if is_selected else ""
                fallback_name = waifu.get('name', f'Character {waifu["waifu_id"]}')
                
                options.append(discord.SelectOption(
                    label=f"{name_prefix}{fallback_name}"[:100],
                    description=f"⭐{waifu.get('current_star_level', 1)} | Unknown series",
                    value=str(user_waifu_id),
                    emoji="❓",
                    default=is_selected
                ))
        
        # ALWAYS ensure we have at least one option to prevent Discord API errors
        if not options:
            # Add a placeholder if no characters available
            if self.search_filter:
                options.append(discord.SelectOption(
                    label="No characters found",
                    description="Try adjusting your search filter",
                    value="none",
                    emoji="❌"
                ))
            else:
                options.append(discord.SelectOption(
                    label="No characters available",
                    description="All characters are on expeditions or you need to get more characters",
                    value="none",
                    emoji="❌"
                ))
        
        placeholder_text = f"Choose characters (up to 3)... | Selected: {len(self.selected_characters)}/3"
        if self.search_filter:
            placeholder_text += f" | Filter: '{self.search_filter}'"
        if len(filtered_waifus) > self.items_per_page:
            total_pages = (len(filtered_waifus) + self.items_per_page - 1) // self.items_per_page
            placeholder_text += f" | Page {self.current_page + 1}/{total_pages}"
        
        # Calculate max values: allow deselection + new selections up to limit of 3
        # Account for special options like "none", "error", and "critical_error"
        character_options = [opt for opt in options if opt.value not in ["none", "error", "critical_error"]]
        if options[0].value == "none":
            max_selectable = 1
        elif options[0].value == "error":
            max_selectable = 1  # Error is a single action
        elif options[0].value == "critical_error":
            max_selectable = 1  # Critical error is a single action
        else:
            max_selectable = min(len(character_options), 3)
        
        # Final safety check: ensure options list is never empty
        if not options:
            # ...removed debug print...
            options.append(discord.SelectOption(
                label="⚠️ Error: No characters",
                description="Please contact support or reload the expedition",
                value="error",
                emoji="⚠️"
            ))
            max_selectable = 1
        
        # Additional safety: double-check before creating select menu
        if len(options) == 0:
            # ...removed debug print...
            options = [discord.SelectOption(
                label="❌ Critical Error",
                description="System failure - please restart expedition",
                value="critical_error",
                emoji="💥"
            )]
            max_selectable = 1
        
    # ...removed debug print...
        
        self.character_select = discord.ui.Select(
            placeholder=placeholder_text,
            options=options,
            custom_id="character_select",
            max_values=max_selectable
        )
        self.character_select.callback = self.character_selected
        self.add_item(self.character_select)
        
        # Add pagination buttons if needed
        self._add_pagination_buttons(filtered_waifus)
        
        # Add clear search button if there's an active filter
        if self.search_filter:
            clear_button = discord.ui.Button(
                label="❌ Clear Search",
                style=discord.ButtonStyle.secondary,
                custom_id="clear_search"
            )
            clear_button.callback = self.clear_search
            self.add_item(clear_button)
        
        # Add clear selections button if characters are selected
        if self.selected_characters:
            clear_selections_button = discord.ui.Button(
                label="🗑️ Clear All",
                style=discord.ButtonStyle.secondary,
                custom_id="clear_selections"
            )
            clear_selections_button.callback = self.clear_selections
            self.add_item(clear_selections_button)
        
        # Add cancel button
        cancel_button = discord.ui.Button(
            label="❌ Cancel",
            style=discord.ButtonStyle.danger,
            custom_id="cancel_expedition"
        )
        cancel_button.callback = self.cancel_expedition
        self.add_item(cancel_button)
        
        # Add start expedition button
        if options[0].value != "none":
            self.start_button = discord.ui.Button(
                label="🚀 Start Expedition",
                style=discord.ButtonStyle.success,
                custom_id="start_expedition",
                disabled=True
            )
            self.start_button.callback = self.start_expedition
            self.add_item(self.start_button)
    
    def _add_pagination_buttons(self, filtered_waifus: List[Dict]):
        """Add pagination buttons if needed."""
        total_pages = (len(filtered_waifus) + self.items_per_page - 1) // self.items_per_page
        
        if total_pages > 1:
            # Previous page button
            prev_button = discord.ui.Button(
                label="◀️ Prev",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page == 0,
                custom_id="prev_char_page"
            )
            prev_button.callback = self.previous_page
            self.add_item(prev_button)
            
            # Next page button
            next_button = discord.ui.Button(
                label="▶️ Next",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page >= total_pages - 1,
                custom_id="next_char_page"
            )
            next_button.callback = self.next_page
            self.add_item(next_button)
    
    async def open_search_modal(self, interaction: discord.Interaction):
        """Open search modal for character filtering."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can search characters.", ephemeral=True)
            return
        
        modal = CharacterSearchModal(self)
        await interaction.response.send_modal(modal)
    
    async def clear_search(self, interaction: discord.Interaction):
        """Clear search filter while maintaining character selections."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can clear search.", ephemeral=True)
            return
        
        self.search_filter = ""
        self.current_page = 0
        self._setup_ui()
        
        # Update start button state after _setup_ui recreates it
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "start_expedition":
                item.disabled = len(self.selected_characters) == 0
                break
        
        embed = await self._create_character_selection_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def previous_page(self, interaction: discord.Interaction):
        """Go to previous page while maintaining character selections."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can navigate pages.", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self._setup_ui()
            
            # Update start button state after _setup_ui recreates it
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.custom_id == "start_expedition":
                    item.disabled = len(self.selected_characters) == 0
                    break
            
            embed = await self._create_character_selection_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    async def next_page(self, interaction: discord.Interaction):
        """Go to next page while maintaining character selections."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can navigate pages.", ephemeral=True)
            return
        
        filtered_waifus = self._get_filtered_waifus()
        total_pages = (len(filtered_waifus) + self.items_per_page - 1) // self.items_per_page
        
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._setup_ui()
            
            # Update start button state after _setup_ui recreates it
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.custom_id == "start_expedition":
                    item.disabled = len(self.selected_characters) == 0
                    break
            
            embed = await self._create_character_selection_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    async def clear_selections(self, interaction: discord.Interaction):
        """Clear all selected characters."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can clear selections.", ephemeral=True)
            return
        
        self.selected_characters = []
        self._setup_ui()
        
        # Update start button state after _setup_ui recreates it
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "start_expedition":
                item.disabled = len(self.selected_characters) == 0
                break
        
        embed = await self._create_character_selection_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def cancel_expedition(self, interaction: discord.Interaction):
        """Cancel the expedition selection and disable all controls."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can cancel.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Expedition Cancelled",
            description="The expedition selection has been cancelled.",
            color=0xFF6B6B
        )
        # Disable all interactive components
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def character_selected(self, interaction: discord.Interaction):
        """Handle character selection with cross-page support."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can select characters.", ephemeral=True)
            return
        
        # Handle case where no values are selected (deselection) or special options
        new_selections = []  # Initialize new_selections
        
        if not self.character_select.values or (self.character_select.values and self.character_select.values[0] in ["none", "error", "critical_error"]):
            if not self.character_select.values:
                # This is a deselection case - process it normally
                new_selections = []
            elif self.character_select.values[0] == "none":
                # This is the "none" case - show helpful error message
                if self.search_filter:
                    await interaction.response.send_message("❌ No characters found matching your search. Try a different search term.", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ No characters available for expeditions. All your characters are currently on other expeditions.", ephemeral=True)
                return
            elif self.character_select.values[0] == "error":
                # This is the "error" case - show system error and return
                await interaction.response.send_message("⚠️ System error: Character data could not be loaded. Please try restarting the expedition.", ephemeral=True)
                return
            elif self.character_select.values[0] == "critical_error":
                # This is the "critical_error" case - show critical system error and return
                await interaction.response.send_message("💥 Critical system error: Please restart the expedition completely. If this persists, contact support.", ephemeral=True)
                return
        else:
            # Handle normal selection/deselection
            new_selections = [int(val) for val in self.character_select.values if val not in ["none", "error", "critical_error"]]
        
        # Update selected characters list
        # Remove any current page characters that were deselected
        current_page_waifus = self._get_current_page_waifus()
        current_page_ids = {waifu['user_waifu_id'] for waifu in current_page_waifus}
        
        # Remove any previously selected characters from current page that aren't in new selections
        self.selected_characters = [char_id for char_id in self.selected_characters 
                                   if char_id not in current_page_ids or char_id in new_selections]
        
        # Add any new selections that aren't already selected
        for char_id in new_selections:
            if char_id not in self.selected_characters:
                if len(self.selected_characters) < 3:  # Max 3 characters
                    self.selected_characters.append(char_id)
                else:
                    # If at limit, show warning
                    await interaction.response.send_message("❌ Maximum 3 characters allowed. Deselect others first.", ephemeral=True)
                    return
        
        # Refresh the UI to show updated selections
        self._setup_ui()
        
        # Enable/disable start button based on selection (after _setup_ui recreates buttons)
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "start_expedition":
                item.disabled = len(self.selected_characters) == 0
                break
        
        # Update embed with selected characters
        embed = await self._create_character_selection_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    def _get_current_page_waifus(self) -> List[Dict]:
        """Get waifus on the current page."""
        filtered_waifus = self._get_filtered_waifus()
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(filtered_waifus))
        return filtered_waifus[start_idx:end_idx]
    
    async def start_expedition(self, interaction: discord.Interaction):
        """Start the expedition with selected characters."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can start expeditions.", ephemeral=True)
            return
        
        if not self.selected_characters:
            await interaction.response.send_message("❌ Please select at least one character.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            discord_id = str(interaction.user.id)
            
            # Convert selected character IDs to the format expected by expedition service
            participant_data = []
            for char_id in self.selected_characters:
                # Find the character data from user_waifus
                waifu = next((w for w in self.user_waifus if w['user_waifu_id'] == char_id), None)
                if waifu:
                    participant_data.append({
                        "user_waifu_id": char_id,
                        "waifu_id": waifu['waifu_id'],
                        "current_star_level": waifu.get('current_star_level', 1),
                        "bond_level": waifu.get('bond_level', 1)
                    })
            
            if not participant_data:
                await interaction.response.send_message("❌ Failed to prepare character data for expedition.", ephemeral=True)
                return
            
            expedition_id = await self.expedition_service.start_expedition(
                discord_id, 
                self.expedition['expedition_id'], 
                participant_data
            )
            
            # Check if expedition starting failed
            if not expedition_id.get('success', False):
                error_msg = expedition_id.get('error', 'Unknown error occurred')
                
                # Handle expedition limit specifically
                if f"{MAX_EXPEDITION_SLOTS} ongoing expeditions" in error_msg or "3 ongoing expeditions" in error_msg:
                    embed = discord.Embed(
                        title="🚫 Expedition Limit Reached",
                        description=f"You already have **{MAX_EXPEDITION_SLOTS} ongoing expeditions** - the maximum allowed!\n\n"
                                   "Use `/nwnl_expeditions_complete` to finish some expeditions first, "
                                   "then try starting a new one.",
                        color=0xFF6B6B
                    )
                    embed.add_field(
                        name="💡 Tip",
                        value="Check `/nwnl_expeditions_status` to see which expeditions are ready to complete!",
                        inline=False
                    )
                else:
                    embed = discord.Embed(
                        title="❌ Expedition Failed to Start",
                        description=f"Error: {error_msg}",
                        color=0xFF0000
                    )
                
                await interaction.followup.send(embed=embed)
                return
            
            # Create success embed
            actual_expedition_id = expedition_id.get('expedition_id')
            embed = discord.Embed(
                title="🚀 Expedition Started!",
                description=f"Your expedition **{self.expedition['name']}** has begun!",
                color=0x00FF00
            )
            
            # Get the actual expedition record to use the real started_at timestamp
            try:
                created_expedition = await self.expedition_service.db.get_expedition_with_participants(actual_expedition_id)
                if created_expedition:
                    actual_start_time = created_expedition.get('started_at')
                    duration_hours = self.expedition.get('duration_hours', 4)
                    
                    if actual_start_time:
                        # Ensure the timestamp is timezone-aware (UTC)
                        if actual_start_time.tzinfo is None:
                            actual_start_time = actual_start_time.replace(tzinfo=timezone.utc)
                        completion_time = actual_start_time + timedelta(hours=duration_hours)
                    else:
                        # Fallback to current time if started_at is not available
                        completion_time = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
                else:
                    # Fallback to current time if expedition not found
                    duration_hours = self.expedition.get('duration_hours', 4)
                    completion_time = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
            except Exception:
                # Fallback to current time on any error
                duration_hours = self.expedition.get('duration_hours', 4)
                completion_time = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
            
            embed.add_field(
                name="⏱️ Duration",
                value=f"{duration_hours} hours",
                inline=True
            )
            embed.add_field(
                name="🏁 Completion",
                value=f"<t:{int(completion_time.timestamp())}:R>",
                inline=True
            )
            embed.add_field(
                name="🎯 Expedition ID",
                value=f"`{actual_expedition_id}`",
                inline=True
            )
            
            # Add selected characters info
            character_names = []
            for char_id in self.selected_characters:
                waifu = next((w for w in self.user_waifus if w['user_waifu_id'] == char_id), None)
                if waifu:
                    character = self.char_registry.get_character(waifu['waifu_id'])
                    if character:
                        star_level = waifu.get('current_star_level', 1)
                        character_names.append(f"⭐{star_level} {character.name}")
            
            if character_names:
                embed.add_field(
                    name="👥 Expedition Team",
                    value="\n".join(character_names),
                    inline=False
                )
            
            embed.add_field(
                name="💡 Tip",
                value="Use `/nwnl_expeditions status` to check your expedition progress!",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Expedition Failed to Start",
                description=f"Error: {str(e)}",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed)
    
    async def _create_character_selection_embed(self) -> discord.Embed:
        """Create character selection embed."""
        filtered_waifus = self._get_filtered_waifus()
        total_pages = (len(filtered_waifus) + self.items_per_page - 1) // self.items_per_page if filtered_waifus else 1
        
        title = f"👥 Select Team for: {self.expedition['name']}"
        description = f"Choose up to 3 characters for this expedition:\n\n"
        
        # Add filter info
        if self.search_filter:
            description += f"🔍 **Filter:** '{self.search_filter}' | **Found:** {len(filtered_waifus)} characters\n"
        else:
            description += f"**Available Characters:** {len(self.user_waifus)}\n"
        
        # Add note about excluded characters
        description += f"💡 *Characters already on expeditions are automatically excluded*\n"
        
        # Add pagination info
        if total_pages > 1:
            description += f"📄 **Page:** {self.current_page + 1}/{total_pages}\n"
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=0x9B59B6
        )
        
        if self.selected_characters:
            character_info = []
            team_power_raw = 0
            num_with_stats = 0
            team_characters = []
            for char_id in self.selected_characters:
                waifu = next((w for w in self.user_waifus if w['user_waifu_id'] == char_id), None)
                if waifu:
                    character = self.char_registry.get_character(waifu['waifu_id'])
                    if character:
                        star_level = waifu.get('current_star_level', 1)
                        character_info.append(f"⭐{star_level} **{character.name}**")
                        # Set star level for accurate stat preview
                        character.star_level = star_level
                        team_characters.append(character)
                    # --- Team Power calculation (raw, with star-level multiplier) ---
                    stats = waifu.get('stats')
                    char_obj = character if character else None
                    star_level = waifu.get('current_star_level', 1)
                    star_multiplier = 1 + (star_level - 1) * 0.10
                    if not stats and char_obj and hasattr(char_obj, 'base_stats'):
                        base_stats = getattr(char_obj, 'base_stats', None)
                        if base_stats:
                            stat_dict = vars(base_stats)
                            stat_values = [v for v in stat_dict.values() if isinstance(v, (int, float))]
                            if stat_values:
                                mean = sum(stat_values) / len(stat_values)
                                mean *= star_multiplier
                                team_power_raw += mean
                                num_with_stats += 1
                            continue
                    if stats and isinstance(stats, dict):
                        stat_values = [v for v in stats.values() if isinstance(v, (int, float))]
                        if stat_values:
                            mean = sum(stat_values) / len(stat_values)
                            mean *= star_multiplier
                            team_power_raw += mean
                            num_with_stats += 1
            embed.add_field(
                name=f"🎯 Selected Characters ({len(self.selected_characters)}/3)",
                value="\n".join(character_info) if character_info else "None selected",
                inline=False
            )
            # Affinity multiplier logic (match backend)
            affinity_multiplier = 1.0
            if team_characters and hasattr(self.expedition, 'get'):
                from src.wanderer_game.models.character import Affinity, AffinityType, Team as WGTeam
                favored_affinities = []
                disfavored_affinities = []
                affinity_pools = self.expedition.get('affinity_pools', {})
                # Map pool category names to AffinityType enum
                category_to_enum = {
                    'elemental': AffinityType.ELEMENTAL,
                    'archetype': AffinityType.ARCHETYPE,
                    'series': AffinityType.SERIES_ID,
                    'genre': AffinityType.GENRE,
                }
                # Helper to resolve series name to series_id using global cache
                def resolve_series_id(series_name):
                    cls = type(self)
                    if cls._series_name_to_id_cache is None:
                        # Build cache on first use
                        cache = {}
                        for char in self.char_registry.characters.values():
                            cache[char.series] = char.series_id
                        cls._series_name_to_id_cache = cache
                    return cls._series_name_to_id_cache.get(series_name, series_name)

                for category, values in affinity_pools.get('favored', {}).items():
                    enum_type = category_to_enum.get(category.lower())
                    if enum_type:
                        for value in values:
                            if enum_type == AffinityType.SERIES_ID:
                                resolved = resolve_series_id(value)
                                favored_affinities.append(Affinity(type=enum_type, value=resolved))
                            else:
                                favored_affinities.append(Affinity(type=enum_type, value=value))
                for category, values in affinity_pools.get('disfavored', {}).items():
                    enum_type = category_to_enum.get(category.lower())
                    if enum_type:
                        for value in values:
                            if enum_type == AffinityType.SERIES_ID:
                                resolved = resolve_series_id(value)
                                disfavored_affinities.append(Affinity(type=enum_type, value=resolved))
                            else:
                                disfavored_affinities.append(Affinity(type=enum_type, value=value))
                # Build Team object
                team_obj = WGTeam(characters=team_characters)
                favored_matches = team_obj.count_affinity_matches(favored_affinities)
                disfavored_matches = team_obj.count_affinity_matches(disfavored_affinities)
                affinity_multiplier = 1.25**(favored_matches) * (0.6**(disfavored_matches))
                affinity_multiplier = max(0.1, min(5.0, affinity_multiplier))
            # Show both raw and adjusted Team Power
            if num_with_stats > 0:
                embed.add_field(
                    name="💪 Team Power (Raw)",
                    value=f"{int(team_power_raw)}",
                    inline=True
                )
                embed.add_field(
                    name="🔮 Affinity Multiplier",
                    value=f"x{affinity_multiplier:.2f}",
                    inline=True
                )
                embed.add_field(
                    name="💥 Team Power (Adjusted)",
                    value=f"{int(team_power_raw * affinity_multiplier)}",
                    inline=True
                )
        else:
            embed.add_field(
                name="🎯 Selected Characters (0/3)",
                value="Select characters from any page - your selections are preserved when navigating!",
                inline=False
            )

        embed.add_field(
            name="📋 Expedition Details",
            value=f"**Duration:** {self.expedition.get('duration_hours', 4)} hours\n"
                  f"**Difficulty:** {self.expedition.get('difficulty', 100)}\n"
                  f"**Expected Encounters:** ~{self.expedition.get('expected_encounters', 5)}",
            inline=False
        )
        
        # Add search tip
        if not self.search_filter and len(self.user_waifus) > 25:
            embed.add_field(
                name="💡 Tip",
                value="Use the 🔍 **Search Characters** button to find specific characters quickly!",
                inline=False
            )
        
        return embed


class ExpeditionResultsView(discord.ui.View):
    async def setup_item_lookup(self, expedition_service):
        """Fetch and cache item lookup mapping for real item names."""
        try:
            item_data = await expedition_service.db.get_shop_items()
            self.item_lookup = {}
            for item in item_data:
                item_id_int = item.get('id')
                if item_id_int:
                    self.item_lookup[f"item_{item_id_int}"] = item
        except Exception as e:
            self.item_lookup = {}
            # ...removed debug print...
        # Fallback: always have a dict
        if not hasattr(self, 'item_lookup'):
            self.item_lookup = {}
    """View for displaying detailed expedition results with pagination."""
    
    def __init__(self, completed_expeditions: List[Dict], user_id: int):
        super().__init__(timeout=300.0)
        self.completed_expeditions = completed_expeditions
        self.user_id = user_id
        self.current_expedition_idx = 0
        self.current_page_type = "summary"  # "summary", "encounters", "rewards"
        self.encounter_page = 0
        
        self.max_encounters_per_page = 3
        self._setup_buttons()
    
    def _setup_buttons(self):
        """Setup navigation buttons based on current state."""
        self.clear_items()
        
        if len(self.completed_expeditions) > 1:
            # Expedition navigation
            prev_exp_button = discord.ui.Button(
                label="⬅️ Prev Expedition",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_expedition_idx == 0,
                row=0
            )
            prev_exp_button.callback = self.prev_expedition
            self.add_item(prev_exp_button)
            
            next_exp_button = discord.ui.Button(
                label="Next Expedition ➡️",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_expedition_idx >= len(self.completed_expeditions) - 1,
                row=0
            )
            next_exp_button.callback = self.next_expedition
            self.add_item(next_exp_button)
        
        # Page type navigation
        summary_button = discord.ui.Button(
            label="📊 Summary",
            style=discord.ButtonStyle.primary if self.current_page_type == "summary" else discord.ButtonStyle.secondary,
            row=1
        )
        summary_button.callback = self.show_summary
        self.add_item(summary_button)
        
        encounters_button = discord.ui.Button(
            label="⚔️ Encounters",
            style=discord.ButtonStyle.primary if self.current_page_type == "encounters" else discord.ButtonStyle.secondary,
            row=1
        )
        encounters_button.callback = self.show_encounters
        self.add_item(encounters_button)
        
        rewards_button = discord.ui.Button(
            label="🎁 Rewards",
            style=discord.ButtonStyle.primary if self.current_page_type == "rewards" else discord.ButtonStyle.secondary,
            row=1
        )
        rewards_button.callback = self.show_rewards
        self.add_item(rewards_button)
        
        # Encounter pagination (only show when on encounters page)
        if self.current_page_type == "encounters":
            current_expedition = self.completed_expeditions[self.current_expedition_idx]
            expedition_log = current_expedition.get('expedition_log', [])
            
            # Filter log to get encounter lines
            encounter_lines = [line for line in expedition_log if line.startswith("Encounter ")]
            total_encounters = len(encounter_lines)
            
            if total_encounters > self.max_encounters_per_page:
                max_pages = (total_encounters + self.max_encounters_per_page - 1) // self.max_encounters_per_page
                
                prev_encounter_button = discord.ui.Button(
                    label="⬅️ Prev",
                    style=discord.ButtonStyle.secondary,
                    disabled=self.encounter_page == 0,
                    row=2
                )
                prev_encounter_button.callback = self.prev_encounter_page
                self.add_item(prev_encounter_button)
                
                next_encounter_button = discord.ui.Button(
                    label="Next ➡️",
                    style=discord.ButtonStyle.secondary,
                    disabled=self.encounter_page >= max_pages - 1,
                    row=2
                )
                next_encounter_button.callback = self.next_encounter_page
                self.add_item(next_encounter_button)
    
    def _get_current_expedition(self) -> Dict:
        """Get the currently selected expedition."""
        return self.completed_expeditions[self.current_expedition_idx]
    
    def _create_summary_embed(self) -> discord.Embed:
        """Create the summary embed for the current expedition."""
        expedition = self._get_current_expedition()
        expedition_name = expedition.get('expedition_name', 'Unknown Expedition')
        outcome = expedition.get('outcome', 'success')
        
        # Determine outcome emoji and color
        if outcome == 'perfect':
            outcome_emoji = "🌟"
            color = 0xFFD700  # Gold
            outcome_text = "Perfect Success"
        elif outcome == 'great_success':
            outcome_emoji = "✅"
            color = 0x00FF00  # Green
            outcome_text = "Great Success"
        elif outcome == 'success':
            outcome_emoji = "👍"
            color = 0x00AA00  # Dark Green
            outcome_text = "Success"
        else:
            outcome_emoji = "❌"
            color = 0xFF0000  # Red
            outcome_text = "Failure"
        
        embed = discord.Embed(
            title=f"{outcome_emoji} {expedition_name}",
            description=f"**Final Outcome:** {outcome_text}",
            color=color
        )
        
        # Add expedition info
        if len(self.completed_expeditions) > 1:
            embed.set_author(name=f"Expedition {self.current_expedition_idx + 1} of {len(self.completed_expeditions)}")
        
        # Get detailed results if available
        result_summary = expedition.get('result_summary', {})
        
        # Encounters summary
        total_encounters = result_summary.get('encounters', 0)
        great_successes = result_summary.get('great_successes', 0)
        successes = result_summary.get('successes', 0)
        failures = result_summary.get('failures', 0)
        mishaps = result_summary.get('mishaps', 0)
        
        encounters_text = (
            f"**Total Encounters:** {total_encounters}\n"
            f"🌟 Great Successes: {great_successes}\n"
            f"✅ Successes: {successes}\n"
            f"❌ Failures: {failures}\n"
            f"💥 Mishaps: {mishaps}"
        )
        
        embed.add_field(
            name="⚔️ Encounter Results",
            value=encounters_text,
            inline=True
        )
        
        # Rewards summary
        loot = expedition.get('loot', {})
        crystals = loot.get('sakura_crystals', 0)
        quartzs = loot.get('quartzs', 0)
        items_list = loot.get('items', [])
        items_count = len(items_list)
        
        # Filter to only show dedicated items (not gems/quartzs which are converted to currency)
        dedicated_items = []
        for item in items_list:
            if hasattr(item, 'item_type'):
                from src.wanderer_game.models import LootType
                if item.item_type not in [LootType.GEMS, LootType.QUARTZS]:
                    dedicated_items.append(item)
            else:
                item_type = item.get('type', '').lower()
                if item_type not in ['gems', 'quartzs']:
                    dedicated_items.append(item)

        rewards_text = (
            f"💎 {crystals} Sakura Crystals\n"
            f"💠 {quartzs} Quartzs\n"
            f"📦 {len(dedicated_items)} Dedicated Items"
        )

        if dedicated_items:
            rewards_text += "\n\n**Dedicated Items Found:**"
            displayed_items = 0
            max_display_items = 5  # Limit to prevent embed overflow
            for item in dedicated_items:
                if displayed_items >= max_display_items:
                    remaining_items = len(dedicated_items) - displayed_items
                    rewards_text += f"\n... and {remaining_items} more dedicated items"
                    break
                # Use real item name if available
                if hasattr(item, 'item_id'):
                    item_id = item.item_id
                    item_name = getattr(self, 'item_lookup', {}).get(item_id, {}).get('name', item_id)
                    item_tier = item.rarity.value if hasattr(item.rarity, 'value') else str(item.rarity)
                    item_value = getattr(item, 'value', 0)
                    quantity = getattr(item, 'quantity', 1)
                    if quantity > 1:
                        display_name = f"{quantity}x {item_name}"
                    else:
                        display_name = item_name
                else:
                    item_id = item.get('item_id', '')
                    item_name = getattr(self, 'item_lookup', {}).get(item_id, {}).get('name', item.get('name', 'Unknown Item'))
                    item_tier = item.get('tier', 'Common')
                    item_value = item.get('value', 0)
                    quantity = item.get('quantity', 1)
                    if quantity > 1:
                        display_name = f"{quantity}x {item_name}"
                    else:
                        display_name = item_name
                rarity_emoji = {
                    'common': '⚪',
                    'uncommon': '🟢', 
                    'rare': '🔵',
                    'epic': '🟣',
                    'legendary': '🟠'
                }.get(str(item_tier).lower(), '⚪')
                rewards_text += f"\n{rarity_emoji} {display_name} ({item_tier})"
                displayed_items += 1
        
        embed.add_field(
            name="🎁 Rewards Earned",
            value=rewards_text,
            inline=True
        )
        
        # Final multiplier outcome and value (always show)
        final_multiplier_numeric = result_summary.get('final_multiplier_numeric', 1.0)
        final_multiplier_name = result_summary.get('final_multiplier', 'standard')
        
        # Emoji for outcome
        multiplier_emoji = {
            'catastrophe': '💥',
            'setback': '📉',
            'standard': '⚖️',
            'jackpot': '🎰'
        }.get(final_multiplier_name.lower(), '🎲')

        # Always show both outcome and value
        if final_multiplier_numeric > 1.0:
            multiplier_text = f"{multiplier_emoji} **{final_multiplier_name.title()}** — **{final_multiplier_numeric}x** reward bonus"
        elif final_multiplier_numeric < 1.0:
            penalty_percent = int((1.0 - final_multiplier_numeric) * 100)
            multiplier_text = f"{multiplier_emoji} **{final_multiplier_name.title()}** — **{final_multiplier_numeric}x** reward penalty (-{penalty_percent}%)"
        else:
            multiplier_text = f"{multiplier_emoji} **{final_multiplier_name.title()}** — **{final_multiplier_numeric}x** (no change)"

        embed.add_field(
            name="🎲 Final Multiplier",
            value=multiplier_text,
            inline=False
        )

        embed.set_footer(text="Use the buttons below to view detailed encounters and rewards!")
        return embed
    
    def _create_encounters_embed(self) -> discord.Embed:
        """Create the encounters embed for the current expedition."""
        expedition = self._get_current_expedition()
        expedition_name = expedition.get('expedition_name', 'Unknown Expedition')
        
        embed = discord.Embed(
            title=f"⚔️ {expedition_name} - Encounters",
            color=0x3498DB
        )
        
        if len(self.completed_expeditions) > 1:
            embed.set_author(name=f"Expedition {self.current_expedition_idx + 1} of {len(self.completed_expeditions)}")
        
        # Get expedition log
        expedition_log = expedition.get('expedition_log', [])
        if not expedition_log:
            embed.description = "No encounter details available."
            return embed
        
        # Get final luck score from expedition results
        final_luck_score = expedition.get('final_luck_score')
        
        # Find encounter sections in the log
        encounter_sections = []
        current_encounter = None
        
        for line in expedition_log:
            if line.startswith("Encounter "):
                if current_encounter:
                    encounter_sections.append(current_encounter)
                current_encounter = {"title": line, "details": []}
            elif current_encounter and line.strip():
                if not line.startswith("==="):
                    current_encounter["details"].append(line)
        
        if current_encounter:
            encounter_sections.append(current_encounter)
        
        # Get encounter results from expedition data to access difficulty info
        encounter_results = expedition.get('encounter_results', [])
        
        # Paginate encounters
        start_idx = self.encounter_page * self.max_encounters_per_page
        end_idx = start_idx + self.max_encounters_per_page
        page_encounters = encounter_sections[start_idx:end_idx]
        
        if not page_encounters:
            embed.description = "No encounters on this page."
        else:
            for i, encounter in enumerate(page_encounters, start=start_idx + 1):
                title = encounter["title"]
                difficulty_text = ""
                loot_info = ""
                description_text = ""
                # Get the encounter result for this encounter if available
                encounter_result = None
                if i <= len(encounter_results):
                    encounter_result = encounter_results[i-1]  # 0-indexed
                    # Difficulty
                    if hasattr(encounter_result, 'encounter') and hasattr(encounter_result.encounter, 'difficulty'):
                        difficulty = encounter_result.encounter.difficulty
                        if difficulty is not None:
                            difficulty_text = f" (Difficulty: {difficulty})"
                    # Description
                    description_text = getattr(encounter_result, 'description', "")
                    # Generated loot
                    if hasattr(encounter_result, 'loot_items') and encounter_result.loot_items:
                        loot_lines = []
                        for item in encounter_result.loot_items:
                            if hasattr(item, 'item_type'):
                                from src.wanderer_game.models import LootType
                                if item.item_type == LootType.GEMS:
                                    loot_lines.append(f"💎 {item.quantity} Sakura Crystals")
                                elif item.item_type == LootType.QUARTZS:
                                    loot_lines.append(f"💠 {item.quantity} Quartzs")
                                else:
                                    # Use real item name if available
                                    item_id = item.item_id
                                    item_name = getattr(self, 'item_lookup', {}).get(item_id, {}).get('name', item_id)
                                    rarity = item.rarity.value if hasattr(item.rarity, 'value') else str(item.rarity)
                                    loot_lines.append(f"📦 {item.quantity}x {item_name} ({rarity})")
                            else:
                                item_type = item.get('type', '').lower()
                                if item_type == 'gems':
                                    loot_lines.append(f"💎 {item.get('quantity', 1)} Sakura Crystals")
                                elif item_type == 'quartzs':
                                    loot_lines.append(f"💠 {item.get('quantity', 1)} Quartzs")
                                else:
                                    # Use real item name if available
                                    item_id = item.get('item_id', '')
                                    item_name = getattr(self, 'item_lookup', {}).get(item_id, {}).get('name', item.get('name', 'Unknown Item'))
                                    loot_lines.append(f"📦 {item.get('quantity', 1)}x {item_name}")
                        if loot_lines:
                            loot_info = "\n" + "\n".join(loot_lines)
                # Mishap: show removed item if present
                mishap_removed_info = ""
                if encounter_result is not None:
                    # Mishap detection: outcome may be an enum or string
                    outcome_val = getattr(encounter_result, 'outcome', None)
                    is_mishap = False
                    if outcome_val is not None:
                        if hasattr(outcome_val, 'value'):
                            is_mishap = outcome_val.value == 'mishap'
                        else:
                            is_mishap = str(outcome_val) == 'mishap'
                    if is_mishap:
                        removed_item = getattr(encounter_result, 'mishap_removed_item', None)
                        if removed_item:
                            item_id = getattr(removed_item, 'item_id', None)
                            item_name = self.item_lookup.get(item_id, {}).get('name', item_id) if item_id else str(removed_item)
                            quantity = getattr(removed_item, 'quantity', 1)
                            rarity = getattr(removed_item, 'rarity', None)
                            rarity_str = ''
                            if rarity:
                                rarity_str = getattr(rarity, 'value', str(rarity))
                            mishap_removed_info = f"\n💥 **Item Lost:** {quantity}x {item_name} {f'({rarity_str})' if rarity_str else ''}"
                        else:
                            mishap_removed_info = "\n💥 **Item Lost:** None (no items left to lose)"
                # Add the encounter as a field
                value_text = (description_text + loot_info + mishap_removed_info) if (description_text or loot_info or mishap_removed_info) else "No details."
                embed.add_field(
                    name=f"{title}{difficulty_text}",
                    value=value_text,
                    inline=False
                )
                #
        
        # Add final multiplier outcome info if available
        footer_text = ""
        final_multiplier = expedition.get('final_multiplier')
        if final_multiplier:
            # Get emoji for the outcome
            multiplier_emoji = {
                'catastrophe': '💥',
                'setback': '📉', 
                'standard': '⚖️',
                'jackpot': '🎰'
            }.get(final_multiplier.lower(), '🎲')
            footer_text = f"{multiplier_emoji} Final Roll: {final_multiplier.title()} • "
        
        # Add pagination info
        total_encounters = len(encounter_sections)
        if total_encounters > self.max_encounters_per_page:
            max_pages = (total_encounters + self.max_encounters_per_page - 1) // self.max_encounters_per_page
            footer_text += f"Page {self.encounter_page + 1} of {max_pages} • {total_encounters} total encounters"
        else:
            footer_text += f"{total_encounters} total encounters"
        
        embed.set_footer(text=footer_text)
        
        return embed
    
    def _create_rewards_embed(self) -> discord.Embed:
        """Create the rewards embed for the current expedition."""
        expedition = self._get_current_expedition()
        expedition_name = expedition.get('expedition_name', 'Unknown Expedition')
        
        embed = discord.Embed(
            title=f"🎁 {expedition_name} - Rewards",
            color=0xFFD700
        )
        
        if len(self.completed_expeditions) > 1:
            embed.set_author(name=f"Expedition {self.current_expedition_idx + 1} of {len(self.completed_expeditions)}")
        
        loot = expedition.get('loot', {})
        
        # Currency rewards
        crystals = loot.get('sakura_crystals', 0)
        quartzs = loot.get('quartzs', 0)
        
        if crystals > 0 or quartzs > 0:
            currency_text = ""
            if crystals > 0:
                currency_text += f"💎 **{crystals}** Sakura Crystals\n"
            if quartzs > 0:
                currency_text += f"💠 **{quartzs}** Quartzs"
            
            embed.add_field(
                name="💰 Currency Rewards",
                value=currency_text,
                inline=False
            )
        
        # Item rewards (dedicated items only - currency items are converted)
        items = loot.get('items', [])
        if items:
            # Filter to only show dedicated items (not gems/quartzs which are converted to currency)
            dedicated_items = []
            for item in items:
                # Check if this is a dedicated item (not currency)
                if hasattr(item, 'item_type'):
                    # Import LootType to check
                    from src.wanderer_game.models import LootType
                    if item.item_type not in [LootType.GEMS, LootType.QUARTZS]:
                        dedicated_items.append(item)
                else:
                    # For dict format, assume it's a dedicated item if it has specific properties
                    item_type = item.get('type', '').lower()
                    if item_type not in ['gems', 'quartzs']:
                        dedicated_items.append(item)
            
            if dedicated_items:
                items_text = ""
                for item in dedicated_items[:10]:  # Show up to 10 dedicated items
                    # Handle both LootItem objects and dict formats
                    if hasattr(item, 'item_id'):  # LootItem object
                        # Use real item name if available
                        item_name = self.item_lookup.get(item.item_id, {}).get('name', item.item_id)
                        item_tier = item.rarity.value if hasattr(item.rarity, 'value') else str(item.rarity)
                        item_value = item.value
                        quantity = getattr(item, 'quantity', 1)
                        if quantity > 1:
                            item_name = f"{quantity}x {item_name}"
                    else:  # Dict format (fallback)
                        # Use real item name if available
                        item_name = self.item_lookup.get(item.get('item_id', ''), {}).get('name', item.get('name', 'Unknown Item'))
                        item_tier = item.get('tier', 'Common')
                        item_value = item.get('value', 0)
                    
                    items_text += f"📦 **{item_name}** ({item_tier}) - {item_value} value\n"
                
                if len(dedicated_items) > 10:
                    items_text += f"\n... and {len(dedicated_items) - 10} more dedicated items"
                
                embed.add_field(
                    name=f"📦 Dedicated Items ({len(dedicated_items)} total)",
                    value=items_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name="📦 Dedicated Items",
                    value="No dedicated items were found (all items converted to currency).",
                    inline=False
                )
        else:
            embed.add_field(
                name="📦 Dedicated Items", 
                value="No dedicated items were found during this expedition.",
                inline=False
            )
        
        # Total value
        loot_result = expedition.get('loot_result', {})
        total_value = loot_result.get('total_value', 0)
        if total_value > 0:
            embed.add_field(
                name="💰 Total Loot Value",
                value=f"**{total_value}** total expedition value",
                inline=False
            )
        
        return embed
    
    def get_current_embed(self) -> discord.Embed:
        """Get the appropriate embed based on current page type."""
        if self.current_page_type == "summary":
            return self._create_summary_embed()
        elif self.current_page_type == "encounters":
            return self._create_encounters_embed()
        elif self.current_page_type == "rewards":
            return self._create_rewards_embed()
        else:
            return self._create_summary_embed()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the command user can interact with the view."""
        return interaction.user.id == self.user_id
    
    async def prev_expedition(self, interaction: discord.Interaction):
        """Navigate to previous expedition."""
        self.current_expedition_idx = max(0, self.current_expedition_idx - 1)
        self.encounter_page = 0  # Reset encounter page
        self._setup_buttons()
        embed = self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def next_expedition(self, interaction: discord.Interaction):
        """Navigate to next expedition."""
        self.current_expedition_idx = min(len(self.completed_expeditions) - 1, self.current_expedition_idx + 1)
        self.encounter_page = 0  # Reset encounter page
        self._setup_buttons()
        embed = self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def show_summary(self, interaction: discord.Interaction):
        """Show expedition summary page."""
        self.current_page_type = "summary"
        self._setup_buttons()
        embed = self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def show_encounters(self, interaction: discord.Interaction):
        """Show expedition encounters page."""
        self.current_page_type = "encounters"
        self.encounter_page = 0  # Reset to first encounter page
        self._setup_buttons()
        embed = self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def show_rewards(self, interaction: discord.Interaction):
        """Show expedition rewards page."""
        self.current_page_type = "rewards"
        self._setup_buttons()
        embed = self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def prev_encounter_page(self, interaction: discord.Interaction):
        """Navigate to previous encounter page."""
        self.encounter_page = max(0, self.encounter_page - 1)
        self._setup_buttons()
        embed = self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def next_encounter_page(self, interaction: discord.Interaction):
        """Navigate to next encounter page."""
        expedition = self._get_current_expedition()
        expedition_log = expedition.get('expedition_log', [])
        encounter_lines = [line for line in expedition_log if line.startswith("Encounter ")]
        total_encounters = len(encounter_lines)
        max_pages = (total_encounters + self.max_encounters_per_page - 1) // self.max_encounters_per_page
        
        self.encounter_page = min(max_pages - 1, self.encounter_page + 1)
        self._setup_buttons()
        embed = self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)


class ExpeditionsCog(BaseCommand):
    """Discord commands for the expedition system."""
    
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)
        self.expedition_service = services.expedition_service
    
    @app_commands.command(
        name="nwnl_expeditions_start",
        description="� View and start available expeditions"
    )
    async def nwnl_expeditions_start(self, interaction: discord.Interaction):
        """Start an expedition with selection UI."""
        discord_id = str(interaction.user.id)
        self.logger.info(f"[DISCORD_EXPEDITION_START] User {discord_id} ({interaction.user.display_name}) requested expedition start")
        
        await interaction.response.defer()
        
        try:
            # Check user's current expedition count
            self.logger.debug(f"[DISCORD_EXPEDITION_START] Checking expedition count for user {discord_id}")
            active_expeditions = await self.expedition_service.get_user_expeditions(discord_id, status='in_progress')
            
            # Get available expeditions
            self.logger.debug(f"[DISCORD_EXPEDITION_START] Loading available expeditions")
            expeditions = await self.expedition_service.get_available_expeditions()
            
            if not expeditions:
                self.logger.warning(f"[DISCORD_EXPEDITION_START] No expeditions available for user {discord_id}")
                embed = discord.Embed(
                    title="🗺️ No Expeditions Available",
                    description="There are currently no expeditions available. Check back later!",
                    color=0xF39C12
                )
                await interaction.followup.send(embed=embed)
                return
            
            self.logger.info(f"[DISCORD_EXPEDITION_START] User {discord_id} has {len(active_expeditions)} active expeditions, {len(expeditions)} expeditions available")
            
            # Check if user has reached expedition limit
            if len(active_expeditions) >= MAX_EXPEDITION_SLOTS:
                self.logger.warning(f"[DISCORD_EXPEDITION_START] User {discord_id} at expedition limit ({MAX_EXPEDITION_SLOTS}/{MAX_EXPEDITION_SLOTS})")
                embed = discord.Embed(
                    title="🗺️ Available Expeditions",
                    description=f"🚫 **Expedition Limit Reached ({MAX_EXPEDITION_SLOTS}/{MAX_EXPEDITION_SLOTS})**\n\n"
                               f"You have reached the maximum of {MAX_EXPEDITION_SLOTS} ongoing expeditions.\n"
                               f"Complete some expeditions first before starting new ones.\n\n"
                               f"Use `/nwnl_expeditions_complete` to claim rewards!",
                    color=0xFF6B6B
                )
                
                # Still show available expeditions for reference
                for i, expedition in enumerate(expeditions[:MAX_EXPEDITION_SLOTS]):
                    duration = expedition.get('duration_hours', 4)
                    difficulty = expedition.get('difficulty', 100)  # Use original difficulty
                    embed.add_field(
                        name=f"🗺️ {expedition['name']}",
                        value=f"⏱️ {duration}h | ⭐ {difficulty} | (Available after completing current expeditions)",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
                return
            
            # Create main expedition list embed
            slots_used = len(active_expeditions)
            
            # Create selection view first to get the embed
            self.logger.debug(f"[DISCORD_EXPEDITION_START] Creating selection view for user {discord_id}")
            view = ExpeditionSelectView(expeditions, interaction.user.id, self.expedition_service)
            embed = await view._create_expedition_list_embed()
            
            # Add expedition slots info at the top
            embed.description = f"**Expedition Slots:** {slots_used}/{MAX_EXPEDITION_SLOTS} used\n\n{embed.description}"
            
            await interaction.followup.send(embed=embed, view=view)
            self.logger.info(f"[DISCORD_EXPEDITION_START] Successfully sent expedition selection to user {discord_id}")
            
        except Exception as e:
            self.logger.error(f"[DISCORD_EXPEDITION_START] Error in expeditions start for user {discord_id}: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to load expeditions: {str(e)}",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="nwnl_expeditions_status",
        description="📊 Check your current expedition status and progress"
    )
    async def nwnl_expeditions_status(self, interaction: discord.Interaction):
        """Show user's current expedition status."""
        await interaction.response.defer()
        
        try:
            discord_id = str(interaction.user.id)
            
            # Get user's in-progress expeditions only
            expeditions = await self.expedition_service.get_user_expeditions(discord_id, status='in_progress')
            
            if not expeditions:
                embed = discord.Embed(
                    title="📊 No Active Expeditions",
                    description="You don't have any expeditions in progress.\n\nUse `/nwnl_expeditions_start` to start a new expedition!",
                    color=0xF39C12
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create status embed
            embed = discord.Embed(
                title="📊 Your Expedition Status",
                description=f"**Expedition Slots:** {len(expeditions)}/{MAX_EXPEDITION_SLOTS} used\n\n"
                           f"You have {len(expeditions)} expedition(s) in progress:",
                color=0x3498DB
            )
            
            # Get character registry for names
            char_registry = self.expedition_service.data_manager.get_character_registry()
            
            for expedition in expeditions:
                status = expedition.get('status', 'in_progress')
                name = expedition.get('expedition_name', 'Unknown Expedition')
                
                # Calculate time remaining
                start_time = expedition.get('started_at')
                duration_hours = expedition.get('duration_hours', 4)
                
                if start_time:
                    # Ensure timezone awareness - database timestamps are UTC
                    if start_time.tzinfo is None:
                        start_time = start_time.replace(tzinfo=timezone.utc)
                    
                    end_time = start_time + timedelta(hours=duration_hours)
                    now = datetime.now(timezone.utc)
                    
                    if status == 'in_progress' and now >= end_time:
                        time_info = "✅ **READY TO COMPLETE!**"
                    elif status == 'in_progress':
                        time_remaining = end_time - now
                        hours = int(time_remaining.total_seconds() // 3600)
                        minutes = int((time_remaining.total_seconds() % 3600) // 60)
                        time_info = f"⏱️ {hours}h {minutes}m remaining"
                    else:
                        time_info = f"🏁 Completed"
                else:
                    time_info = "⏱️ Time unknown"
                
                # Get participants
                participants = await self.expedition_service.get_expedition_participants(expedition['id'])
                participant_names = []
                
                for participant in participants:
                    waifu_id = participant.get('waifu_id')
                    if waifu_id:
                        character = char_registry.get_character(int(waifu_id))
                        if character:
                            star_level = participant.get('current_star_level', 1)
                            participant_names.append(f"⭐{star_level} {character.name}")
                
                team_info = "\n".join(participant_names[:3]) if participant_names else "No team info"
                
                embed.add_field(
                    name=f"🗺️ {name}",
                    value=f"{time_info}\n**Team:**\n{team_info}",
                    inline=True
                )
            
            embed.set_footer(text=f"Maximum {MAX_EXPEDITION_SLOTS} expeditions allowed • Use /nwnl_expeditions_complete to claim rewards!")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in expedition status: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to load expedition status: {str(e)}",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="nwnl_expeditions_complete",
        description="🏆 Complete finished expeditions and claim rewards"
    )
    async def nwnl_expeditions_complete(self, interaction: discord.Interaction):
        """Complete finished expeditions and show detailed results."""
        await interaction.response.defer()
        
        try:
            discord_id = str(interaction.user.id)
            
            # Check for completed expeditions
            completed_expeditions = await self.expedition_service.complete_user_expeditions(discord_id)
            
            if not completed_expeditions:
                embed = discord.Embed(
                    title="🏆 No Expeditions to Complete",
                    description="You don't have any expeditions ready to complete.\n\nUse `/nwnl_expeditions_status` to check your progress!",
                    color=0xF39C12
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create detailed expedition results view with pagination
            view = ExpeditionResultsView(completed_expeditions, interaction.user.id)
            await view.setup_item_lookup(self.expedition_service)
            embed = view.get_current_embed()
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            self.logger.error(f"Error in expedition complete: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to complete expeditions: {str(e)}",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="nwnl_expeditions_list",
        description="📜 Browse all available expeditions (catalog view)"
    )
    async def nwnl_expeditions_list(self, interaction: discord.Interaction):
        """List all available expeditions in a browsable catalog format."""
        discord_id = str(interaction.user.id)
        self.logger.info(f"[DISCORD_EXPEDITION_CATALOG] User {discord_id} ({interaction.user.display_name}) requested expedition catalog")
        
        await interaction.response.defer()
        
        try:
            # Get available expeditions
            self.logger.debug(f"[DISCORD_EXPEDITION_CATALOG] Loading available expeditions")
            expeditions = await self.expedition_service.get_available_expeditions()
            
            if not expeditions:
                self.logger.warning(f"[DISCORD_EXPEDITION_CATALOG] No expeditions available for user {discord_id}")
                embed = discord.Embed(
                    title="📜 No Expeditions Available",
                    description="There are currently no expeditions available. Check back later!",
                    color=0xF39C12
                )
                await interaction.followup.send(embed=embed)
                return
            
            self.logger.info(f"[DISCORD_EXPEDITION_CATALOG] User {discord_id} browsing {len(expeditions)} expeditions")
            
            # Create list view
            self.logger.debug(f"[DISCORD_EXPEDITION_CATALOG] Creating catalog view for user {discord_id}")
            view = ExpeditionListView(expeditions, interaction.user.id)
            embed = await view._create_expedition_list_embed()
            
            await interaction.followup.send(embed=embed, view=view)
            self.logger.info(f"[DISCORD_EXPEDITION_CATALOG] Successfully sent expedition catalog to user {discord_id}")
            
        except Exception as e:
            self.logger.error(f"[DISCORD_EXPEDITION_CATALOG] Error in expeditions catalog for user {discord_id}: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to load expedition catalog: {str(e)}",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="nwnl_expeditions_detail",
        description="🔍 View detailed information about a specific expedition"
    )
    @app_commands.describe(expedition_id="The ID of the expedition to view details for")
    async def nwnl_expeditions_detail(self, interaction: discord.Interaction, expedition_id: str):
        """Show detailed information about a specific expedition by ID."""
        discord_id = str(interaction.user.id)
        self.logger.info(f"[DISCORD_EXPEDITION_DETAIL] User {discord_id} ({interaction.user.display_name}) requested details for expedition {expedition_id}")
        
        await interaction.response.defer()
        
        try:
            # Get available expeditions
            expeditions = await self.expedition_service.get_available_expeditions()
            
            # Find the specific expedition
            expedition = None
            for exp in expeditions:
                if exp.get('expedition_id') == expedition_id:
                    expedition = exp
                    break
            
            if not expedition:
                self.logger.warning(f"[DISCORD_EXPEDITION_DETAIL] Expedition {expedition_id} not found for user {discord_id}")
                embed = discord.Embed(
                    title="🔍 Expedition Not Found",
                    description=f"No expedition found with ID: `{expedition_id}`\n\nUse `/nwnl_expeditions_list` to see available expeditions and their IDs.",
                    color=0xFF6B6B
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            self.logger.info(f"[DISCORD_EXPEDITION_DETAIL] Showing details for expedition {expedition_id} to user {discord_id}")
            
            # Create detailed embed
            embed = await self._create_detailed_expedition_embed(expedition)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"[DISCORD_EXPEDITION_DETAIL] Error showing expedition details for user {discord_id}: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to load expedition details: {str(e)}",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _create_detailed_expedition_embed(self, expedition: Dict) -> discord.Embed:
        """Create a comprehensive detailed view of an expedition."""
        name = expedition.get('name', 'Unknown Expedition')
        expedition_id = expedition.get('expedition_id', 'unknown')
        duration = expedition.get('duration_hours', 4)
        difficulty = expedition.get('difficulty', 100)
        difficulty_tier = expedition.get('difficulty_tier', 1)
        encounters = expedition.get('expected_encounters', 5)
        favored = expedition.get('num_favored_affinities', 0)
        disfavored = expedition.get('num_disfavored_affinities', 0)
        encounter_tags = expedition.get('encounter_pool_tags', [])
        affinity_pools = expedition.get('affinity_pools', {})
        # Create main embed
        embed = discord.Embed(
            title=f"🗺️ {name}",
            description=f"**Expedition ID:** `{expedition_id}`\n\n"
                       f"Complete details for this expedition:",
            color=0x3498DB
        )
        # Basic Information
        duration_text = f"{duration} hours"
        if duration < 1:
            if duration < 0.0167:
                seconds = int(duration * 3600)
                duration_text = f"{seconds} seconds"
            else:
                minutes = int(duration * 60)
                duration_text = f"{minutes} minutes"
        difficulty_emoji = "⭐" * min(difficulty_tier, 5)
        # Add per-encounter affinity info to basic info
        per_encounter_affinity = ""
        if favored > 0 or disfavored > 0:
            per_encounter_affinity = f"\n🔮 **Per Encounter:** {favored} favored, {disfavored} disfavored affinities"
        embed.add_field(
            name="📊 Basic Information",
            value=f"⏱️ **Duration:** {duration_text}\n"
                  f"{difficulty_emoji} **Difficulty:** {difficulty}\n"
                  f"⚔️ **Expected Encounters:** ~{encounters} battles"
                  f"{per_encounter_affinity}",
            inline=False
        )
        # Comprehensive Affinity Effects
        if favored > 0 or disfavored > 0:
            affinity_text = []
            if favored > 0:
                if 'favored' in affinity_pools and affinity_pools['favored']:
                    buff_details = []
                    for category, values in affinity_pools['favored'].items():
                        if isinstance(values, list) and values:
                            category_display = category.title().replace('_', ' ')
                            value_list = ', '.join(f"`{value}`" for value in values)
                            buff_details.append(f"🔸 **{category_display}:** {value_list}")
                    if buff_details:
                        affinity_text.append(f"✅ **Character Performance Buffs ({favored} categories):**\n" + "\n".join(buff_details))
                    else:
                        affinity_text.append(f"✅ **Character Performance Buffs:** {favored} affinity types (specific details not available)")
                else:
                    affinity_text.append(f"✅ **Character Performance Buffs:** {favored} affinity types (specific details not available)")
            if disfavored > 0:
                if 'disfavored' in affinity_pools and affinity_pools['disfavored']:
                    debuff_details = []
                    for category, values in affinity_pools['disfavored'].items():
                        if isinstance(values, list) and values:
                            category_display = category.title().replace('_', ' ')
                            value_list = ', '.join(f"`{value}`" for value in values)
                            debuff_details.append(f"🔸 **{category_display}:** {value_list}")
                            if category.lower() in ['series', 'anime']:
                                debuff_details.append("     ↳ *Characters from these series suffer performance penalties*")
                            elif category.lower() in ['archetype', 'role']:
                                debuff_details.append("     ↳ *Characters with these roles face combat disadvantages*")
                            elif category.lower() in ['personality', 'trait']:
                                debuff_details.append("     ↳ *Characters with these traits perform worse*")
                    if debuff_details:
                        affinity_text.append(f"❌ **Character Performance Debuffs ({disfavored} categories):**\n" + "\n".join(debuff_details))
                    else:
                        affinity_text.append(f"❌ **Character Performance Debuffs:** {disfavored} affinity types (specific details not available)")
                else:
                    affinity_text.append(f"❌ **Character Performance Debuffs:** {disfavored} affinity types (specific details not available)")
            embed.add_field(
                name="🔮 Character Affinity Effects",
                value="\n\n".join(affinity_text) if affinity_text else "No affinity effects for this expedition",
                inline=False
            )
        else:
            embed.add_field(
                name="🔮 Character Affinity Effects",
                value="🎯 **No Affinity Effects** - All characters perform equally on this expedition",
                inline=False
            )
        # Encounter Information
        if encounter_tags:
            embed.add_field(
                name="⚔️ Encounter Types",
                value="**Tags:** " + ", ".join(f"`{tag}`" for tag in encounter_tags),
                inline=False
            )
        embed.set_footer(text=f"Use /nwnl_expeditions_start to begin this expedition • ID: {expedition_id}")
        return embed

    @app_commands.command(
        name="nwnl_loot_probability",
        description="🎯 View item probability chances for different difficulty levels"
    )
    @app_commands.describe(
        difficulty="The difficulty level to calculate probabilities for (default: 1000)"
    )
    async def nwnl_loot_probability(self, interaction: discord.Interaction, difficulty: int = 1000):
        """Display beautiful item probability breakdown for a given difficulty."""
        await interaction.response.defer()
        
        try:
            # Validate difficulty range
            if difficulty < 1:
                difficulty = 1
            elif difficulty > 10000:
                difficulty = 10000
            
            # Initialize LootGenerator
            loot_generator = LootGenerator()
            
            # Get probability data directly (not simulation)
            type_probabilities = loot_generator._calculate_type_probabilities(difficulty)
            item_configs_with_probs = []
            
            # Calculate item probabilities if items have a chance
            if type_probabilities.get('items', 0) > 0:
                # Calculate total weight for normalization
                total_weight = sum(
                    loot_generator._calculate_item_probability_weight(difficulty, config[3])
                    for config in loot_generator.item_configs
                )
                
                # Get individual probabilities for each item configuration
                if total_weight > 0:
                    for item_id, amount, rarity, target_difficulty in loot_generator.item_configs:
                        item_weight = loot_generator._calculate_item_probability_weight(difficulty, target_difficulty)
                        item_prob = type_probabilities['items'] * (item_weight / total_weight) * 100  # Convert to percentage
                        item_configs_with_probs.append((item_id, amount, rarity, item_prob))
            
            # Create main embed
            embed = discord.Embed(
                title="🎯 Loot Probability Calculator",
                description=f"**Difficulty Level:** {difficulty:,}\n"
                           f"*Showing exact mathematical probabilities*",
                color=0x9B59B6
            )
            
            # Add type distribution
            type_text = []
            for loot_type, probability in type_probabilities.items():
                percentage = probability * 100  # Convert from decimal to percentage
                if loot_type == 'gems':
                    emoji = "💎"
                elif loot_type == 'quartzs':
                    emoji = "💠"
                elif loot_type == 'items':
                    emoji = "📦"
                else:
                    emoji = "❓"
                
                type_text.append(f"{emoji} **{loot_type.title()}:** {percentage:.1f}%")
            
            embed.add_field(
                name="📊 Loot Type Distribution",
                value="\n".join(type_text),
                inline=False
            )
            
            # Add ALL item probabilities - show each configuration separately
            if item_configs_with_probs:
                # Sort items by probability (highest first)
                sorted_items = sorted(item_configs_with_probs, key=lambda x: x[3], reverse=True)
                
                # Get item data for names from the database service
                try:
                    # Use the expedition service's database to get item data
                    item_data = await self.expedition_service.db.get_shop_items()
                    # Create lookup mapping string item IDs to shop items by integer ID
                    item_lookup = {}
                    for item in item_data:
                        # Map loot generator string IDs (item_1, item_2, etc.) to database integer IDs
                        item_id_int = item.get('id')
                        if item_id_int:
                            item_lookup[f"item_{item_id_int}"] = item
                except Exception as e:
                    self.logger.error(f"Error loading shop items: {e}")
                    item_lookup = {}
                
                # Show ALL item configurations with their probabilities
                all_items = []
                for item_id, amount, rarity, probability in sorted_items:
                    item_info = item_lookup.get(item_id, {})
                    item_name = item_info.get('name', f'Item {item_id}')
                    
                    # Get rarity emoji
                    rarity_emoji = {
                        'COMMON': '⚪',
                        'UNCOMMON': '🟢', 
                        'RARE': '🔵',
                        'EPIC': '🟣',
                        'LEGENDARY': '🟠',
                        'MYTHIC': '🔴'
                    }.get(rarity.name if hasattr(rarity, 'name') else str(rarity).upper(), '⚪')
                    
                    # Format probability with appropriate precision
                    if probability >= 0.01:
                        prob_str = f"{probability:.2f}%"
                    elif probability >= 0.001:
                        prob_str = f"{probability:.3f}%"
                    else:
                        prob_str = f"{probability:.4f}%"
                    
                    all_items.append(f"{rarity_emoji} **{item_name}** x{amount} - {prob_str}")
                
                if all_items:
                    # Split into chunks if too many items (Discord has field value limits)
                    items_per_field = 10
                    for i in range(0, len(all_items), items_per_field):
                        chunk = all_items[i:i + items_per_field]
                        field_name = "🎁 Item Probabilities" if i == 0 else f"🎁 Item Probabilities (cont. {i//items_per_field + 1})"
                        embed.add_field(
                            name=field_name,
                            value="\n".join(chunk),
                            inline=False
                        )
                else:
                    embed.add_field(
                        name="🎁 Item Probabilities",
                        value="*No item configurations found*",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="🎁 Item Probabilities", 
                    value="*No item probabilities available (items type has 0% chance)*",
                    inline=False
                )
            
            # Add helpful information
            embed.add_field(
                name="💡 Tips",
                value="• Higher difficulty = better item chances\n"
                      "• Each item configuration shown separately (same item, different amounts)\n"
                      "• Uses exact mathematical probabilities (not simulation)\n"
                      "• Items use forgiving selection (distance up to 1000 still possible)\n"
                      "• Gem amounts increase with difficulty using normal distribution\n"
                      "• Quartz probability peaks around difficulty 1000",
                inline=False
            )
            
            # Footer with calculation details
            embed.set_footer(text="Exact mathematical probabilities • Each item config shown separately • Range: 1-10,000 difficulty")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in loot probability command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to calculate probabilities: {str(e)}",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    # Get services from bot
    services = getattr(bot, 'services', None)
    if services is None:
        raise RuntimeError("Bot services not found. Make sure services are attached to the bot.")
    
    # Add the cog with services
    await bot.add_cog(ExpeditionsCog(bot, services))