"""Expedition system Discord commands with comprehensive UI."""

import discord
from discord.ext import commands
from discord import app_commands
from typing import List, Dict
from datetime import datetime, timedelta

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


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
        start_redirect_button = discord.ui.Button(
            label="🚀 Start an Expedition",
            style=discord.ButtonStyle.success,
            custom_id="start_expedition_redirect"
        )
        start_redirect_button.callback = self.redirect_to_start
        self.add_item(start_redirect_button)
    
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
    
    async def redirect_to_start(self, interaction: discord.Interaction):
        """Redirect user to use the start command."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can start expeditions.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🚀 Ready to Start an Expedition?",
            description="Use the `/nwnl_expeditions_start` command to begin an expedition!\n\n"
                       "That command will let you:\n"
                       "• Select an expedition\n"
                       "• Choose your team\n"
                       "• Start your adventure immediately",
            color=0x00FF00
        )
        embed.set_footer(text="Click anywhere to dismiss this message, then use /nwnl_expeditions_start")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
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
            difficulty = expedition.get('difficulty', 100)  # Use original difficulty
            difficulty_tier = expedition.get('difficulty_tier', 1)  # Keep tier for rewards
            encounters = expedition.get('expected_encounters', 5)
            favored = expedition.get('num_favored_affinities', 0)
            disfavored = expedition.get('num_disfavored_affinities', 0)
            expedition_id = expedition.get('expedition_id', 'unknown')
            
            # Create difficulty emoji based on tier for visual appeal
            difficulty_emoji = "⭐" * min(difficulty_tier, 5)
            
            # Create detailed description
            description_parts = [
                f"🆔 **ID:** `{expedition_id}`",
                f"⏱️ **Duration:** {duration} hours",
                f"{difficulty_emoji} **Difficulty:** {difficulty}",  # Show original difficulty
                f"⚔️ **Encounters:** ~{encounters} battles"
            ]
            
            if favored > 0 or disfavored > 0:
                # Get actual affinity information if available
                affinity_pools = expedition.get('affinity_pools', {})
                
                if favored > 0 and 'favored' in affinity_pools:
                    buff_details = []
                    for category, values in affinity_pools['favored'].items():
                        if isinstance(values, list) and values:
                            buff_details.append(f"**{category.title()}:** {', '.join(values)}")
                    if buff_details:
                        description_parts.append(f"✅ **Buffs:** {' | '.join(buff_details)}")
                
                if disfavored > 0 and 'disfavored' in affinity_pools:
                    debuff_details = []
                    for category, values in affinity_pools['disfavored'].items():
                        if isinstance(values, list) and values:
                            debuff_details.append(f"**{category.title()}:** {', '.join(values)}")
                    if debuff_details:
                        description_parts.append(f"❌ **Debuffs:** {' | '.join(debuff_details)}")
                
                # Fallback if no detailed affinity info
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
            difficulty = expedition.get('difficulty', 100)  # Use original difficulty
            difficulty_tier = expedition.get('difficulty_tier', 1)  # For emoji
            encounters = expedition.get('expected_encounters', 5)
            
            # Create difficulty emoji based on tier
            difficulty_emoji = "⭐" * min(difficulty_tier, 5)
            
            embed.add_field(
                name=f"🗺️ {expedition['name']}",
                value=f"⏱️ {duration}h | {difficulty_emoji} {difficulty} | ⚔️ ~{encounters} encounters",
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
            # Get user's available characters
            user_waifus = await self.expedition_service.db.get_user_waifus_minimal(discord_id)
            
            if not user_waifus:
                await interaction.response.send_message("❌ You don't have any characters to send on expeditions!", ephemeral=True)
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
        difficulty = expedition.get('difficulty', 100)  # Use original difficulty
        difficulty_tier = expedition.get('difficulty_tier', 1)  # For rewards logic
        encounters = expedition.get('expected_encounters', 5)
        favored = expedition.get('num_favored_affinities', 0)
        disfavored = expedition.get('num_disfavored_affinities', 0)
        
        embed.add_field(
            name="⏱️ Duration",
            value=f"{duration_hours} hours",
            inline=True
        )
        embed.add_field(
            name="⭐ Difficulty", 
            value=f"{difficulty}",  # Show original difficulty
            inline=True
        )
        embed.add_field(
            name="⚔️ Encounters",
            value=f"~{encounters} battles",
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
                    name="� Affinity Effects",
                    value="\n\n".join(affinity_text),
                    inline=False
                )
            else:
                embed.add_field(
                    name="🔮 Affinity Effects",
                    value=f"✅ {favored} character buffs\n❌ {disfavored} character debuffs",
                    inline=False
                )
        
        # Add dynamic potential rewards based on difficulty
        rewards = []
        if difficulty_tier >= 1:  # Use difficulty_tier for rewards logic
            rewards.append("💎 Sakura Crystals")
        if difficulty_tier >= 2:
            rewards.append("💠 Quartzs")
        if difficulty_tier >= 3:
            rewards.append("📦 Rare Items")
        if difficulty_tier >= 4:
            rewards.append("🌟 Epic Equipment")
        if difficulty_tier >= 5:
            rewards.append("💫 Legendary Gear")
        
        if not rewards:
            rewards = ["💎 Sakura Crystals", "📦 Basic Items"]
        
        embed.add_field(
            name="💎 Potential Rewards",
            value="• " + "\n• ".join(rewards) + "\n• Experience Points",
            inline=False
        )
        
        return embed


class CharacterSelectView(discord.ui.View):
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
        
        # Calculate page boundaries
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(filtered_waifus))
        current_waifus = filtered_waifus[start_idx:end_idx]
        
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
                    description=f"⭐{star_level} | Bond {bond_level} | {character.series[:40]}",
                    value=str(user_waifu_id),
                    emoji="👤",
                    default=is_selected  # Mark as default if selected
                ))
        
        if not options:
            # Add a placeholder if no characters available
            options.append(discord.SelectOption(
                label="No characters found" if self.search_filter else "No characters available",
                description="Try adjusting your search" if self.search_filter else "You need characters to go on expeditions",
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
        max_selectable = min(len(options), 3) if options[0].value != "none" else 1
        
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
            
            embed = await self._create_character_selection_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    async def character_selected(self, interaction: discord.Interaction):
        """Handle character selection with cross-page support."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can select characters.", ephemeral=True)
            return
        
        if self.character_select.values[0] == "none":
            await interaction.response.send_message("❌ No characters available for expeditions.", ephemeral=True)
            return
        
        # Handle selection/deselection
        new_selections = [int(val) for val in self.character_select.values]
        
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
        
        # Enable/disable start button based on selection
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "start_expedition":
                item.disabled = len(self.selected_characters) == 0
                break
        
        # Refresh the UI to show updated selections
        self._setup_ui()
        
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
            expedition_id = await self.expedition_service.start_expedition(
                discord_id, 
                self.expedition['expedition_id'], 
                self.selected_characters
            )
            
            # Check if expedition starting failed
            if not expedition_id.get('success', False):
                error_msg = expedition_id.get('error', 'Unknown error occurred')
                
                # Handle expedition limit specifically
                if "3 ongoing expeditions" in error_msg:
                    embed = discord.Embed(
                        title="🚫 Expedition Limit Reached",
                        description="You already have **3 ongoing expeditions** - the maximum allowed!\n\n"
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
            
            # Calculate completion time
            duration_hours = self.expedition.get('duration_hours', 4)
            completion_time = datetime.utcnow() + timedelta(hours=duration_hours)
            
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
                value=f"`{expedition_id}`",
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
            description += f"**Total Characters:** {len(self.user_waifus)}\n"
        
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
            for char_id in self.selected_characters:
                waifu = next((w for w in self.user_waifus if w['user_waifu_id'] == char_id), None)
                if waifu:
                    character = self.char_registry.get_character(waifu['waifu_id'])
                    if character:
                        star_level = waifu.get('current_star_level', 1)
                        bond_level = waifu.get('bond_level', 1)
                        character_info.append(f"⭐{star_level} **{character.name}** (Bond {bond_level})")
            
            embed.add_field(
                name=f"🎯 Selected Characters ({len(self.selected_characters)}/3)",
                value="\n".join(character_info) if character_info else "None selected",
                inline=False
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
                  f"**Difficulty:** {self.expedition.get('difficulty', 100)}\n"  # Show original difficulty
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
            if len(active_expeditions) >= 3:
                self.logger.warning(f"[DISCORD_EXPEDITION_START] User {discord_id} at expedition limit (3/3)")
                embed = discord.Embed(
                    title="🗺️ Available Expeditions",
                    description=f"🚫 **Expedition Limit Reached (3/3)**\n\n"
                               f"You have reached the maximum of 3 ongoing expeditions.\n"
                               f"Complete some expeditions first before starting new ones.\n\n"
                               f"Use `/nwnl_expeditions_complete` to claim rewards!",
                    color=0xFF6B6B
                )
                
                # Still show available expeditions for reference
                for i, expedition in enumerate(expeditions[:3]):
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
            embed.description = f"**Expedition Slots:** {slots_used}/3 used\n\n{embed.description}"
            
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
            
            # Get user's expeditions
            expeditions = await self.expedition_service.get_user_expeditions(discord_id)
            
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
                description=f"**Expedition Slots:** {len(expeditions)}/3 used\n\n"
                           f"You have {len(expeditions)} expedition(s) in progress:",
                color=0x3498DB
            )
            
            # Get character registry for names
            char_registry = self.expedition_service.data_manager.get_character_registry()
            
            for expedition in expeditions:
                status = expedition.get('status', 'in_progress')
                name = expedition.get('name', 'Unknown Expedition')
                
                # Calculate time remaining
                start_time = expedition.get('start_time')
                duration_hours = expedition.get('duration_hours', 4)
                
                if start_time:
                    end_time = start_time + timedelta(hours=duration_hours)
                    now = datetime.utcnow()
                    
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
            
            embed.set_footer(text="Maximum 3 expeditions allowed • Use /nwnl_expeditions_complete to claim rewards!")
            
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
        """Complete finished expeditions and show rewards."""
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
            
            # Create rewards summary embed
            embed = discord.Embed(
                title="🏆 Expeditions Completed!",
                description=f"You completed {len(completed_expeditions)} expedition(s) and received rewards:",
                color=0x00FF00
            )
            
            # Calculate total rewards
            total_crystals = 0
            total_quartzs = 0
            total_items = 0
            
            # Get character registry for names
            char_registry = self.expedition_service.data_manager.get_character_registry()
            
            for expedition in completed_expeditions:
                name = expedition.get('name', 'Unknown Expedition')
                loot = expedition.get('loot', {})
                
                crystals = loot.get('sakura_crystals', 0)
                quartzs = loot.get('quartzs', 0)
                items = len(loot.get('items', []))
                
                total_crystals += crystals
                total_quartzs += quartzs
                total_items += items
                
                # Show expedition results
                result_emoji = "🌟" if expedition.get('outcome') == 'perfect' else "✅" if expedition.get('outcome') == 'great_success' else "👍"
                
                embed.add_field(
                    name=f"{result_emoji} {name}",
                    value=f"💎 {crystals} Crystals\n💠 {quartzs} Quartzs\n📦 {items} Items",
                    inline=True
                )
            
            # Add total rewards summary
            embed.add_field(
                name="🎁 Total Rewards",
                value=f"💎 **{total_crystals}** Sakura Crystals\n"
                      f"💠 **{total_quartzs}** Quartzs\n"
                      f"📦 **{total_items}** Items",
                inline=False
            )
            
            embed.set_footer(text="Great job! Use /nwnl_expeditions_start to start new adventures!")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in expedition complete: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to complete expeditions: {str(e)}",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="nwnl_expeditions_logs",
        description="📜 View your expedition history and detailed logs"
    )
    async def nwnl_expeditions_logs(self, interaction: discord.Interaction):
        """Show user's expedition history and logs."""
        await interaction.response.defer()
        
        try:
            discord_id = str(interaction.user.id)
            
            # Get expedition history
            history = await self.expedition_service.get_expedition_history(discord_id, limit=10)
            
            if not history:
                embed = discord.Embed(
                    title="📜 No Expedition History",
                    description="You haven't completed any expeditions yet.\n\nUse `/nwnl_expeditions_start` to start your first adventure!",
                    color=0xF39C12
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create history embed
            embed = discord.Embed(
                title="📜 Expedition History",
                description=f"Your last {len(history)} expeditions:",
                color=0x9B59B6
            )
            
            # Get character registry for names
            char_registry = self.expedition_service.data_manager.get_character_registry()
            
            for expedition in history:
                name = expedition.get('name', 'Unknown Expedition')
                completion_time = expedition.get('completion_time')
                outcome = expedition.get('outcome', 'success')
                loot = expedition.get('loot', {})
                
                # Format completion time
                if completion_time:
                    timestamp = f"<t:{int(completion_time.timestamp())}:R>"
                else:
                    timestamp = "Unknown time"
                
                # Outcome emoji
                outcome_emoji = "🌟" if outcome == 'perfect' else "✅" if outcome == 'great_success' else "👍"
                
                # Rewards summary
                crystals = loot.get('sakura_crystals', 0)
                quartzs = loot.get('quartzs', 0)
                items = len(loot.get('items', []))
                
                embed.add_field(
                    name=f"{outcome_emoji} {name}",
                    value=f"**Completed:** {timestamp}\n"
                          f"**Rewards:** 💎{crystals} 💠{quartzs} 📦{items}",
                    inline=True
                )
            
            # Add summary stats
            total_expeditions = len(history)
            total_crystals = sum(exp.get('loot', {}).get('sakura_crystals', 0) for exp in history)
            total_quartzs = sum(exp.get('loot', {}).get('quartzs', 0) for exp in history)
            
            embed.add_field(
                name="📊 Summary",
                value=f"**Total Expeditions:** {total_expeditions}\n"
                      f"**Total Crystals:** 💎{total_crystals}\n"
                      f"**Total Quartzs:** 💠{total_quartzs}",
                inline=False
            )
            
            embed.set_footer(text="Keep exploring to build your expedition legacy!")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in expedition logs: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to load expedition logs: {str(e)}",
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
            # Convert to minutes/seconds for very short durations
            if duration < 0.0167:  # Less than 1 minute
                seconds = int(duration * 3600)
                duration_text = f"{seconds} seconds"
            else:
                minutes = int(duration * 60)
                duration_text = f"{minutes} minutes"
        
        difficulty_emoji = "⭐" * min(difficulty_tier, 5)
        
        embed.add_field(
            name="📊 Basic Information",
            value=f"⏱️ **Duration:** {duration_text}\n"
                  f"{difficulty_emoji} **Difficulty:** {difficulty}\n"
                  f"⚔️ **Expected Encounters:** ~{encounters} battles",
            inline=False
        )
        
        # Detailed Affinity Effects
        if favored > 0 or disfavored > 0:
            affinity_text = []
            
            if favored > 0:
                if 'favored' in affinity_pools and affinity_pools['favored']:
                    buff_details = []
                    for category, values in affinity_pools['favored'].items():
                        if isinstance(values, list) and values:
                            buff_details.append(f"**{category.title()}:** {', '.join(values)}")
                    
                    if buff_details:
                        affinity_text.append(f"✅ **Character Buffs ({favored}):**\n" + "\n".join(f"    • {detail}" for detail in buff_details))
                    else:
                        affinity_text.append(f"✅ **Character Buffs:** {favored} types (details not specified)")
                else:
                    affinity_text.append(f"✅ **Character Buffs:** {favored} types (details not specified)")
            
            if disfavored > 0:
                if 'disfavored' in affinity_pools and affinity_pools['disfavored']:
                    debuff_details = []
                    for category, values in affinity_pools['disfavored'].items():
                        if isinstance(values, list) and values:
                            debuff_details.append(f"**{category.title()}:** {', '.join(values)}")
                    
                    if debuff_details:
                        affinity_text.append(f"❌ **Character Debuffs ({disfavored}):**\n" + "\n".join(f"    • {detail}" for detail in debuff_details))
                    else:
                        affinity_text.append(f"❌ **Character Debuffs:** {disfavored} types (details not specified)")
                else:
                    affinity_text.append(f"❌ **Character Debuffs:** {disfavored} types (details not specified)")
            
            embed.add_field(
                name="🔮 Affinity Effects",
                value="\n\n".join(affinity_text) if affinity_text else "No affinity effects",
                inline=False
            )
        
        # Encounter Information
        if encounter_tags:
            embed.add_field(
                name="⚔️ Encounter Types",
                value="**Tags:** " + ", ".join(f"`{tag}`" for tag in encounter_tags),
                inline=False
            )
        
        # Potential Rewards (detailed)
        rewards = []
        reward_details = []
        
        if difficulty_tier >= 1:
            rewards.append("💎 Sakura Crystals")
            reward_details.append("💎 **Sakura Crystals** - Primary currency for upgrades")
        if difficulty_tier >= 2:
            rewards.append("💠 Quartzs")
            reward_details.append("💠 **Quartzs** - Advanced upgrade materials")
        if difficulty_tier >= 3:
            rewards.append("📦 Rare Items")
            reward_details.append("📦 **Rare Items** - Uncommon equipment and materials")
        if difficulty_tier >= 4:
            rewards.append("🌟 Epic Equipment")
            reward_details.append("🌟 **Epic Equipment** - High-tier gear and accessories")
        if difficulty_tier >= 5:
            rewards.append("💫 Legendary Gear")
            reward_details.append("💫 **Legendary Gear** - Extremely rare and powerful items")
        
        if not rewards:
            reward_details = ["💎 **Sakura Crystals** - Basic expedition rewards", "📦 **Basic Items** - Standard materials"]
        
        embed.add_field(
            name="🎁 Potential Rewards",
            value="\n".join(reward_details) + "\n\n*Actual rewards depend on expedition success and performance*",
            inline=False
        )
        
        # Footer with usage hint
        embed.set_footer(text=f"Use /nwnl_expeditions_start to begin this expedition • ID: {expedition_id}")
        
        return embed


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    # Get services from bot
    services = getattr(bot, 'services', None)
    if services is None:
        raise RuntimeError("Bot services not found. Make sure services are attached to the bot.")
    
    # Add the cog with services
    await bot.add_cog(ExpeditionsCog(bot, services))