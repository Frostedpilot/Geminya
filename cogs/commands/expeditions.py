"""Expedition system Discord commands with comprehensive UI."""

import discord
from discord.ext import commands
from discord import app_commands
from typing import List, Dict
from datetime import datetime, timedelta

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


class ExpeditionSelectView(discord.ui.View):
    """View for selecting available expeditions."""
    
    def __init__(self, expeditions: List[Dict], user_id: int, expedition_service):
        super().__init__(timeout=300.0)
        self.expeditions = expeditions
        self.user_id = user_id
        self.expedition_service = expedition_service
        self.selected_expedition = None
        
        # Create select menu for expeditions
        options = []
        for i, expedition in enumerate(expeditions[:25]):  # Discord limit
            duration_hours = expedition.get('duration_hours', 4)
            difficulty = expedition.get('difficulty_tier', 1)
            
            # Create emoji based on difficulty
            difficulty_emoji = "⭐" * min(difficulty, 5)
            
            options.append(discord.SelectOption(
                label=expedition['name'][:100],  # Discord limit
                description=f"{difficulty_emoji} | {duration_hours}h | Tier {difficulty}",
                value=str(i),
                emoji="🗺️"
            ))
        
        self.expedition_select = discord.ui.Select(
            placeholder="Choose an expedition...",
            options=options,
            custom_id="expedition_select"
        )
        self.expedition_select.callback = self.expedition_selected
        self.add_item(self.expedition_select)
    
    async def expedition_selected(self, interaction: discord.Interaction):
        """Handle expedition selection."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can select expeditions.", ephemeral=True)
            return
        
        expedition_index = int(self.expedition_select.values[0])
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
        difficulty = expedition.get('difficulty_tier', 1)
        encounters = expedition.get('expected_encounters', 5)
        
        embed.add_field(
            name="⏱️ Duration",
            value=f"{duration_hours} hours",
            inline=True
        )
        embed.add_field(
            name="⭐ Difficulty",
            value=f"Tier {difficulty}",
            inline=True
        )
        embed.add_field(
            name="⚔️ Encounters",
            value=f"~{encounters} battles",
            inline=True
        )
        
        # Add potential rewards info
        embed.add_field(
            name="💎 Potential Rewards",
            value="• Sakura Crystals\n• Quartzs\n• Items & Equipment\n• Experience Points",
            inline=False
        )
        
        return embed


class CharacterSelectView(discord.ui.View):
    """View for selecting characters for expeditions."""
    
    def __init__(self, user_waifus: List[Dict], user_id: int, expedition_service, expedition: Dict):
        super().__init__(timeout=300.0)
        self.user_waifus = user_waifus
        self.user_id = user_id
        self.expedition_service = expedition_service
        self.expedition = expedition
        self.selected_characters = []
        
        # Get character registry for names
        self.char_registry = expedition_service.data_manager.get_character_registry()
        
        # Create select menu for characters (max 25 options)
        options = []
        for i, waifu in enumerate(user_waifus[:25]):
            character = self.char_registry.get_character(waifu['waifu_id'])
            if character:
                star_level = waifu.get('current_star_level', 1)
                bond_level = waifu.get('bond_level', 1)
                
                options.append(discord.SelectOption(
                    label=character.name[:100],  # Discord limit
                    description=f"⭐{star_level} | Bond {bond_level} | {character.series[:40]}",
                    value=str(waifu['user_waifu_id']),
                    emoji="👤"
                ))
        
        if not options:
            # Add a placeholder if no characters available
            options.append(discord.SelectOption(
                label="No characters available",
                description="You need characters to go on expeditions",
                value="none",
                emoji="❌"
            ))
        
        self.character_select = discord.ui.Select(
            placeholder="Choose characters (up to 3)...",
            options=options,
            custom_id="character_select",
            max_values=min(len(options), 3) if options[0].value != "none" else 1
        )
        self.character_select.callback = self.character_selected
        self.add_item(self.character_select)
        
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
    
    async def character_selected(self, interaction: discord.Interaction):
        """Handle character selection."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can select characters.", ephemeral=True)
            return
        
        if self.character_select.values[0] == "none":
            await interaction.response.send_message("❌ No characters available for expeditions.", ephemeral=True)
            return
        
        self.selected_characters = [int(val) for val in self.character_select.values]
        
        # Enable start button
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "start_expedition":
                item.disabled = False
                break
        
        # Update embed with selected characters
        embed = await self._create_character_selection_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
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
                self.expedition['id'], 
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
        embed = discord.Embed(
            title=f"👥 Select Team for: {self.expedition['name']}",
            description="Choose up to 3 characters for this expedition:",
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
                name="🎯 Selected Characters",
                value="\n".join(character_info) if character_info else "None selected",
                inline=False
            )
        
        embed.add_field(
            name="📋 Expedition Details",
            value=f"**Duration:** {self.expedition.get('duration_hours', 4)} hours\n"
                  f"**Difficulty:** Tier {self.expedition.get('difficulty_tier', 1)}\n"
                  f"**Expected Encounters:** ~{self.expedition.get('expected_encounters', 5)}",
            inline=False
        )
        
        return embed


class ExpeditionsCog(BaseCommand):
    """Discord commands for the expedition system."""
    
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)
        self.expedition_service = services.expedition_service
    
    @app_commands.command(
        name="nwnl_expeditions_list",
        description="🗺️ View and start available expeditions"
    )
    async def nwnl_expeditions_list(self, interaction: discord.Interaction):
        """List available expeditions with selection UI."""
        discord_id = str(interaction.user.id)
        self.logger.info(f"[DISCORD_EXPEDITION_LIST] User {discord_id} ({interaction.user.display_name}) requested expedition list")
        
        await interaction.response.defer()
        
        try:
            # Check user's current expedition count
            self.logger.debug(f"[DISCORD_EXPEDITION_LIST] Checking expedition count for user {discord_id}")
            active_expeditions = await self.expedition_service.get_user_expeditions(discord_id, status='in_progress')
            
            # Get available expeditions
            self.logger.debug(f"[DISCORD_EXPEDITION_LIST] Loading available expeditions")
            expeditions = await self.expedition_service.get_available_expeditions()
            
            if not expeditions:
                self.logger.warning(f"[DISCORD_EXPEDITION_LIST] No expeditions available for user {discord_id}")
                embed = discord.Embed(
                    title="🗺️ No Expeditions Available",
                    description="There are currently no expeditions available. Check back later!",
                    color=0xF39C12
                )
                await interaction.followup.send(embed=embed)
                return
            
            self.logger.info(f"[DISCORD_EXPEDITION_LIST] User {discord_id} has {len(active_expeditions)} active expeditions, {len(expeditions)} expeditions available")
            
            # Check if user has reached expedition limit
            if len(active_expeditions) >= 3:
                self.logger.warning(f"[DISCORD_EXPEDITION_LIST] User {discord_id} at expedition limit (3/3)")
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
                    difficulty = expedition.get('difficulty_tier', 1)
                    embed.add_field(
                        name=f"🗺️ {expedition['name']}",
                        value=f"⏱️ {duration}h | ⭐ Tier {difficulty} | (Available after completing current expeditions)",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
                return
            
            # Create main expedition list embed
            slots_used = len(active_expeditions)
            embed = discord.Embed(
                title="🗺️ Available Expeditions",
                description=f"**Expedition Slots:** {slots_used}/3 used\n\n"
                           f"Choose from {len(expeditions)} available expeditions:",
                color=0x3498DB
            )
            
            # Add expedition preview (first 5)
            for i, expedition in enumerate(expeditions[:5]):
                duration = expedition.get('duration_hours', 4)
                difficulty = expedition.get('difficulty_tier', 1)
                encounters = expedition.get('expected_encounters', 5)
                
                embed.add_field(
                    name=f"🗺️ {expedition['name']}",
                    value=f"⏱️ {duration}h | ⭐ Tier {difficulty} | ⚔️ ~{encounters} encounters",
                    inline=False
                )
            
            if len(expeditions) > 5:
                embed.add_field(
                    name="📜 More Expeditions",
                    value=f"And {len(expeditions) - 5} more expeditions available in the selection menu below!",
                    inline=False
                )
            
            embed.set_footer(text="Select an expedition below to view details and start your adventure!")
            
            # Create selection view
            self.logger.debug(f"[DISCORD_EXPEDITION_LIST] Creating selection view for user {discord_id}")
            view = ExpeditionSelectView(expeditions, interaction.user.id, self.expedition_service)
            
            await interaction.followup.send(embed=embed, view=view)
            self.logger.info(f"[DISCORD_EXPEDITION_LIST] Successfully sent expedition list to user {discord_id}")
            
        except Exception as e:
            self.logger.error(f"[DISCORD_EXPEDITION_LIST] Error in expeditions list for user {discord_id}: {e}", exc_info=True)
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
                    description="You don't have any expeditions in progress.\n\nUse `/nwnl_expeditions_list` to start a new expedition!",
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
            
            embed.set_footer(text="Great job! Use /nwnl_expeditions_list to start new adventures!")
            
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
                    description="You haven't completed any expeditions yet.\n\nUse `/nwnl_expeditions_list` to start your first adventure!",
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


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    # Get services from bot
    services = getattr(bot, 'services', None)
    if services is None:
        raise RuntimeError("Bot services not found. Make sure services are attached to the bot.")
    
    # Add the cog with services
    await bot.add_cog(ExpeditionsCog(bot, services))