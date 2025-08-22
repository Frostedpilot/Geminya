"""
Shop command for the waifu academy system.
Handles browsing shop items, purchasing, and inventory management.
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List, Dict, Any
import json
import math

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


def format_number(num: int) -> str:
    """Format a number with appropriate separators."""
    if num >= 1000000:
        return f"{num / 1000000:.1f}M"
    elif num >= 1000:
        return f"{num / 1000:.1f}K"
    else:
        return str(num)


class ShopCog(BaseCommand):
    """Shop system commands for browsing and purchasing items."""

    def __init__(self, bot, services: ServiceContainer):
        super().__init__(bot, services)
        self.group_name = "Shop"
        # Create a shortcut for database access
        self.db = self.services.waifu_service.db

    @app_commands.command(name="nwnl_shop", description="Browse the academy shop")
    @app_commands.describe(
        category="Filter by item category",
        page="Page number for shop listings"
    )
    async def nwnl_shop(
        self, 
        interaction: discord.Interaction, 
        category: Optional[str] = None,
        page: int = 1
    ):
        """Display the shop with items available for purchase."""
        await interaction.response.defer()
        
        try:
            user = await self.db.get_or_create_user(str(interaction.user.id))
            
            # Get shop items - handle the type issue by calling without category if None
            if category:
                items = await self.db.get_shop_items(category=category, active_only=True)
            else:
                items = await self.db.get_shop_items(active_only=True)
            if not items:
                embed = discord.Embed(
                    title="🏪 Academy Shop",
                    description="The shop is currently empty. Come back later!",
                    color=0xFF6B6B
                )
                await interaction.followup.send(embed=embed)
                return

            # Pagination setup
            items_per_page = 8
            total_pages = math.ceil(len(items) / items_per_page)
            page = max(1, min(page, total_pages))
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_items = items[start_idx:end_idx]

            # Create embed
            embed = discord.Embed(
                title="🏪 Academy Shop",
                description=f"Browse items and use `/buy <item_id>` to purchase",
                color=0x4A90E2
            )
            
            # Add user currency info
            crystals = user.get('sakura_crystals', 0)
            quartzs = user.get('quartzs', 0)
            embed.add_field(
                name="💰 Your Currency",
                value=f"💎 {format_number(crystals)} Crystals\n🔹 {format_number(quartzs)} Quartzs",
                inline=False
            )

            # Group items by category for better display
            categories = {}
            for item in page_items:
                cat = item.get('category', 'general').title()
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)

            # Add items to embed
            for cat_name, cat_items in categories.items():
                items_text = ""
                for item in cat_items:
                    # Currency symbol
                    currency_type = item.get('currency_type', 'sakura_crystals')
                    currency_symbol = "🔹" if currency_type == "quartzs" else "💎"
                    
                    # Rarity emoji
                    rarity_emojis = {
                        'common': '⚪',
                        'uncommon': '🟢',
                        'rare': '🔵',
                        'epic': '🟣',
                        'legendary': '🟡'
                    }
                    rarity_emoji = rarity_emojis.get(item.get('rarity', 'common'), '⚪')
                    
                    # Requirements
                    requirements = ""
                    if item.get('requirements'):
                        req_data = json.loads(item['requirements']) if isinstance(item['requirements'], str) else item['requirements']
                        if req_data.get('min_rank'):
                            requirements = f" (Rank {req_data['min_rank']}+)"
                    
                    items_text += f"{rarity_emoji} **ID {item['id']}** - {item['name']}\n"
                    items_text += f"   {currency_symbol}{format_number(item['price'])}{requirements}\n"
                    items_text += f"   *{item.get('description', 'No description')}*\n\n"

                if items_text:
                    embed.add_field(
                        name=f"🏷️ {cat_name}",
                        value=items_text.strip(),
                        inline=False
                    )

            # Add pagination info
            embed.set_footer(text=f"Page {page}/{total_pages} • Total Items: {len(items)}")

            # Create view with navigation buttons
            view = ShopView(self.db, page, total_pages, category, interaction.user.id)
            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            self.logger.error(f"Error in shop command: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while loading the shop.",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="nwnl_buy", description="Purchase an item from the shop")
    @app_commands.describe(
        item_id="The ID of the item to purchase",
        quantity="Number of items to buy (default: 1)"
    )
    async def nwnl_buy(
        self, 
        interaction: discord.Interaction, 
        item_id: int,
        quantity: int = 1
    ):
        """Purchase an item from the shop."""
        await interaction.response.defer()
        
        try:
            if quantity <= 0:
                embed = discord.Embed(
                    title="❌ Invalid Quantity",
                    description="Quantity must be a positive number.",
                    color=0xFF0000
                )
                await interaction.followup.send(embed=embed)
                return

            # Get item details
            item = await self.db.get_shop_item_by_id(item_id)
            if not item:
                embed = discord.Embed(
                    title="❌ Item Not Found",
                    description=f"No item found with ID {item_id}.",
                    color=0xFF0000
                )
                await interaction.followup.send(embed=embed)
                return

            if not item.get('is_active', True):
                embed = discord.Embed(
                    title="❌ Item Unavailable",
                    description="This item is currently unavailable.",
                    color=0xFF0000
                )
                await interaction.followup.send(embed=embed)
                return

            # Check requirements
            user = await self.db.get_or_create_user(str(interaction.user.id))
            requirements = item.get('requirements')
            if requirements:
                req_data = json.loads(requirements) if isinstance(requirements, str) else requirements
                min_rank = req_data.get('min_rank', 0)
                if user.get('collector_rank', 1) < min_rank:
                    embed = discord.Embed(
                        title="❌ Requirements Not Met",
                        description=f"You need to be at least Rank {min_rank} to purchase this item.\nYour current rank: {user.get('collector_rank', 1)}",
                        color=0xFF0000
                    )
                    await interaction.followup.send(embed=embed)
                    return

            # Check currency
            total_price = item['price'] * quantity
            currency_type = item.get('currency_type', 'sakura_crystals')
            currency_symbol = "🔹" if currency_type == "quartzs" else "💎"
            currency_name = "Quartzs" if currency_type == "quartzs" else "Crystals"
            
            user_currency = user.get(currency_type, 0)
            if user_currency < total_price:
                embed = discord.Embed(
                    title="❌ Insufficient Currency",
                    description=f"You need {currency_symbol}{format_number(total_price)} {currency_name} but only have {currency_symbol}{format_number(user_currency)}.",
                    color=0xFF0000
                )
                await interaction.followup.send(embed=embed)
                return

            # Attempt purchase
            success = await self.db.purchase_item(str(interaction.user.id), item_id, quantity)
            
            if success:
                # Get updated user data
                updated_user = await self.db.get_or_create_user(str(interaction.user.id))
                new_balance = updated_user.get(currency_type, 0)
                
                embed = discord.Embed(
                    title="✅ Purchase Successful!",
                    description=f"You purchased **{quantity}x {item['name']}**",
                    color=0x00FF00
                )
                embed.add_field(
                    name="💸 Transaction",
                    value=f"Cost: {currency_symbol}{format_number(total_price)} {currency_name}\nNew Balance: {currency_symbol}{format_number(new_balance)} {currency_name}",
                    inline=False
                )
                
                # Add item effects info
                effects = item.get('effects')
                if effects:
                    effects_data = json.loads(effects) if isinstance(effects, str) else effects
                    effects_text = []
                    for key, value in effects_data.items():
                        effects_text.append(f"• {key.replace('_', ' ').title()}: {value}")
                    
                    if effects_text:
                        embed.add_field(
                            name="⚡ Item Effects",
                            value="\n".join(effects_text),
                            inline=False
                        )
                
                embed.set_footer(text="Use /inventory to view your purchased items")
                await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Purchase Failed",
                    description="The purchase could not be completed. Please try again.",
                    color=0xFF0000
                )
                await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error in buy command: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while processing your purchase.",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="nwnl_inventory", description="View your purchased items")
    @app_commands.describe(page="Page number for inventory listings")
    async def nwnl_inventory(self, interaction: discord.Interaction, page: int = 1):
        """Display user's inventory of purchased items."""
        await interaction.response.defer()
        
        try:
            inventory = await self.db.get_user_inventory(str(interaction.user.id))
            
            if not inventory:
                embed = discord.Embed(
                    title="📦 Your Inventory",
                    description="Your inventory is empty. Visit the shop to purchase items!",
                    color=0x95A5A6
                )
                await interaction.followup.send(embed=embed)
                return

            # Pagination
            items_per_page = 10
            total_pages = math.ceil(len(inventory) / items_per_page)
            page = max(1, min(page, total_pages))
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_items = inventory[start_idx:end_idx]

            embed = discord.Embed(
                title="📦 Your Inventory",
                description="Items you've purchased from the shop",
                color=0x9B59B6
            )

            for item in page_items:
                # Rarity emoji
                rarity_emojis = {
                    'common': '⚪',
                    'uncommon': '🟢',
                    'rare': '🔵',
                    'epic': '🟣',
                    'legendary': '🟡'
                }
                rarity_emoji = rarity_emojis.get(item.get('rarity', 'common'), '⚪')
                
                # Status and expiration
                status = ""
                if not item.get('is_active', True):
                    status = " (Expired)"
                elif item.get('expires_at'):
                    status = f" (Expires: {item['expires_at']})"
                
                embed.add_field(
                    name=f"{rarity_emoji} {item['name']} x{item['quantity']}{status}",
                    value=f"*{item.get('description', 'No description')}*\nAcquired: {item.get('acquired_at', 'Unknown')}",
                    inline=False
                )

            embed.set_footer(text=f"Page {page}/{total_pages} • Total Items: {len(inventory)}")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error in inventory command: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while loading your inventory.",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="nwnl_purchase_history", description="View your purchase history")
    @app_commands.describe(limit="Number of recent purchases to show (max 50)")
    async def nwnl_purchase_history(self, interaction: discord.Interaction, limit: int = 20):
        """Display user's purchase history."""
        await interaction.response.defer()
        
        try:
            limit = max(1, min(limit, 50))  # Clamp between 1 and 50
            history = await self.db.get_user_purchase_history(str(interaction.user.id), limit)
            
            if not history:
                embed = discord.Embed(
                    title="🧾 Purchase History",
                    description="You haven't made any purchases yet.",
                    color=0x95A5A6
                )
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title="🧾 Purchase History",
                description=f"Your last {len(history)} purchases",
                color=0x3498DB
            )

            for purchase in history:
                currency_symbol = "🔹" if purchase.get('currency_type') == "quartzs" else "💎"
                
                embed.add_field(
                    name=f"{purchase['name']} x{purchase['quantity']}",
                    value=f"Price: {currency_symbol}{format_number(purchase['total_price'])}\nDate: {purchase.get('purchase_date', 'Unknown')}\nStatus: {purchase.get('transaction_status', 'Unknown')}",
                    inline=True
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error in purchase_history command: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while loading your purchase history.",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="nwnl_use_item", description="Use an item from your inventory")
    @app_commands.describe(item_name="Name of the item to use")
    async def nwnl_use_item(self, interaction: discord.Interaction, item_name: str):
        """Use an item from inventory and apply its effects."""
        await interaction.response.defer()
        
        try:
            user_id = str(interaction.user.id)
            
            # Get user's inventory
            inventory = await self.db.get_user_inventory(user_id)
            
            if not inventory:
                embed = discord.Embed(
                    title="📦 Empty Inventory",
                    description="You don't have any items to use! Visit the shop to purchase items.",
                    color=0xff6b6b
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Find the item in inventory
            item_to_use = None
            for item in inventory:
                if item['name'].lower() == item_name.lower():
                    item_to_use = item
                    break
            
            if not item_to_use:
                available_items = [item['name'] for item in inventory]
                embed = discord.Embed(
                    title="❌ Item Not Found",
                    description=f"You don't have '{item_name}' in your inventory.\n\n**Available items:**\n{', '.join(available_items) if available_items else 'None'}",
                    color=0xff6b6b
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Check if item can be used
            if not item_to_use.get('is_active', True):
                embed = discord.Embed(
                    title="❌ Item Expired",
                    description=f"The item '{item_to_use['name']}' has expired and cannot be used.",
                    color=0xff6b6b
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Use the item and apply effects
            result = await self.apply_item_effects(user_id, item_to_use)
            
            if result['success']:
                # Remove one instance of the item from inventory
                await self.db.use_inventory_item(user_id, item_to_use['id'], 1)
                
                embed = discord.Embed(
                    title="✅ Item Used Successfully!",
                    description=f"**{item_to_use['name']}** has been used!\n\n{result['description']}",
                    color=0x7ed321
                )
                
                # Add remaining quantity info if applicable
                remaining = item_to_use['quantity'] - 1
                if remaining > 0:
                    embed.add_field(
                        name="📦 Remaining",
                        value=f"You have {remaining} more of this item.",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Cannot Use Item",
                    description=result['error'],
                    color=0xff6b6b
                )
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Error using item: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while using the item. Please try again later.",
                color=0xff6b6b
            )
            await interaction.followup.send(embed=embed)

    async def apply_item_effects(self, user_id: str, item: dict) -> dict:
        """Apply the effects of using an item"""
        try:
            effects_data = item.get('effects')
            if isinstance(effects_data, str):
                effects = json.loads(effects_data)
            else:
                effects = effects_data or {}
                
            item_type = item.get('item_type', '')
            
            if item_type == "guarantee_ticket":
                # Perform immediate guaranteed roll
                guarantee_rarity = effects.get('guarantee_rarity', 5)
                
                # Use the existing waifu service from our container
                waifu_service = self.services.waifu_service
                
                # Perform guaranteed roll using modified logic
                rolled_waifu = await self._perform_guaranteed_roll(user_id, guarantee_rarity, waifu_service)
                
                if rolled_waifu:
                    # Build detailed success message
                    constellation_text = ""
                    if rolled_waifu.get('constellation', 1) > 1:
                        constellation_text = f" (C{rolled_waifu['constellation']})"
                    
                    quartzs_text = ""
                    if rolled_waifu.get('quartzs_gained', 0) > 0:
                        quartzs_text = f"\n🔹 +{rolled_waifu['quartzs_gained']} Quartzs (C6+ duplicate)"
                    
                    new_text = "**NEW!** " if rolled_waifu.get('is_new', True) else ""
                    
                    return {
                        'success': True,
                        'description': f"🌟 **Guaranteed {guarantee_rarity}★ Roll Complete!**\n\n✨ {new_text}You summoned: **{rolled_waifu['name']}**{constellation_text} ({rolled_waifu['rarity']}★)\n*From: {rolled_waifu.get('source', 'Unknown')}*{quartzs_text}"
                    }
                else:
                    return {
                        'success': False,
                        'error': "Failed to perform guaranteed roll. Please try again later."
                    }
            
            elif item_type == "currency_pack":
                # Add crystals to user
                crystals = effects.get('sakura_crystals', 0)
                await self.db.add_crystals(user_id, crystals)
                return {
                    'success': True,
                    'description': f"💎 Added **{format_number(crystals)} Sakura Crystals** to your account!"
                }
            
            elif item_type == "boost":
                # Apply temporary boost
                multiplier = effects.get('bond_multiplier', 1.0)
                duration = effects.get('duration_hours', 24)
                await self.db.apply_user_boost(user_id, 'bond', multiplier, duration)
                return {
                    'success': True,
                    'description': f"⚡ Bond experience multiplier of **{multiplier}x** applied for **{duration} hours**!"
                }
            
            elif item_type == "summon_ticket":
                # Add summon tickets (convert to crystals for simplicity)
                summons = effects.get('summons', 1)
                crystals_equivalent = summons * 10  # Assuming 10 crystals per summon
                await self.db.add_crystals(user_id, crystals_equivalent)
                return {
                    'success': True,
                    'description': f"🎟️ Added **{summons} summon(s)** worth of crystals (**{crystals_equivalent} crystals**) to your account!"
                }
            
            elif item_type == "selector":
                # Mark user as having a selector available
                rarity = effects.get('rarity', '5_star')
                await self.db.set_user_selector(user_id, rarity)
                return {
                    'success': True,
                    'description': f"🎯 You can now select a **{rarity.replace('_', '★')}** waifu! Use the waifu summon system to make your selection."
                }
            
            elif item_type == "enhancer":
                # Mark user as having constellation enhancer
                boost = effects.get('constellation_boost', 1)
                await self.db.add_constellation_enhancer(user_id, boost)
                return {
                    'success': True,
                    'description': f"⭐ You can now enhance a waifu's constellation by **{boost} level**! The enhancement will be applied to your next constellation upgrade."
                }
            
            elif item_type in ["decoration", "frame", "title"]:
                # Unlock cosmetic items
                await self.db.unlock_cosmetic(user_id, item_type, effects)
                cosmetic_name = effects.get('decoration_type') or effects.get('frame_type') or effects.get('title', 'cosmetic item')
                return {
                    'success': True,
                    'description': f"✨ **{cosmetic_name.title()}** cosmetic unlocked! Check your profile to equip it."
                }
            
            elif item_type == "utility":
                # Unlock utility features
                if effects.get('allows_naming'):
                    await self.db.unlock_feature(user_id, 'waifu_naming')
                    return {
                        'success': True,
                        'description': "🏷️ You can now give **custom names** to your waifus! This feature has been permanently unlocked."
                    }
            
            elif item_type == "upgrade":
                # Apply permanent upgrades
                if 'collection_limit_increase' in effects:
                    increase = effects['collection_limit_increase']
                    await self.db.increase_collection_limit(user_id, increase)
                    return {
                        'success': True,
                        'description': f"📈 Your waifu collection limit has been permanently increased by **{increase}**!"
                    }
            
            else:
                return {
                    'success': False,
                    'error': f"Unknown item type: **{item_type}**. This item cannot be used yet."
                }
                
        except Exception as e:
            self.logger.error(f"Error applying item effects: {e}")
            return {
                'success': False,
                'error': "Failed to apply item effects. Please try again later."
            }

    async def _perform_guaranteed_roll(self, user_id: str, rarity: int, waifu_service) -> Optional[Dict[str, Any]]:
        """Perform a guaranteed roll for the specified rarity without cost."""
        try:
            # Get available waifus of the guaranteed rarity
            available_waifus = await self.db.get_waifus_by_rarity(rarity, 50)
            
            if not available_waifus:
                self.logger.error(f"No waifus available for rarity {rarity}")
                return None
            
            # Select random waifu from the guaranteed rarity
            import random
            selected_waifu = random.choice(available_waifus)
            
            # Add to user's collection (this handles constellation logic and quartzs conversion)
            result = await self.db.add_waifu_to_user(user_id, selected_waifu["id"])
            
            # Return the waifu data
            return {
                'id': selected_waifu['id'],
                'name': selected_waifu['name'],
                'rarity': selected_waifu['rarity'],
                'source': selected_waifu.get('source', 'Unknown'),
                'constellation': result.get('constellation', 1),
                'is_new': result.get('is_new', True),
                'quartzs_gained': result.get('quartzs_gained', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error performing guaranteed roll: {e}")
            return None


class ShopView(discord.ui.View):
    """View for shop navigation buttons."""
    
    def __init__(self, database, current_page: int, total_pages: int, category: Optional[str], user_id: int):
        super().__init__(timeout=300)
        self.db = database
        self.current_page = current_page
        self.total_pages = total_pages
        self.category = category
        self.user_id = user_id
        
        # Disable buttons based on page position
        if current_page <= 1:
            self.previous_button.disabled = True
        if current_page >= total_pages:
            self.next_button.disabled = True

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your shop session!", ephemeral=True)
            return
            
        await self._update_page(interaction, self.current_page - 1)

    @discord.ui.button(label="▶ Next", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your shop session!", ephemeral=True)
            return
            
        await self._update_page(interaction, self.current_page + 1)

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.secondary)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your shop session!", ephemeral=True)
            return
            
        await self._update_page(interaction, self.current_page)

    async def _update_page(self, interaction: discord.Interaction, new_page: int):
        """Update the shop display with a new page."""
        try:
            await interaction.response.defer()
            
            # Get updated shop items and user data
            user = await self.db.get_or_create_user(str(interaction.user.id))
            items = await self.db.get_shop_items(category=self.category, active_only=True)
            
            if not items:
                embed = discord.Embed(
                    title="🏪 Academy Shop",
                    description="The shop is currently empty.",
                    color=0xFF6B6B
                )
                await interaction.edit_original_response(embed=embed, view=None)
                return

            # Pagination
            items_per_page = 8
            total_pages = math.ceil(len(items) / items_per_page)
            page = max(1, min(new_page, total_pages))
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_items = items[start_idx:end_idx]

            # Create updated embed
            embed = discord.Embed(
                title="🏪 Academy Shop",
                description=f"Browse items and use `/buy <item_id>` to purchase",
                color=0x4A90E2
            )
            
            # Add user currency info
            crystals = user.get('sakura_crystals', 0)
            quartzs = user.get('quartzs', 0)
            embed.add_field(
                name="💰 Your Currency",
                value=f"💎 {format_number(crystals)} Crystals\n🔹 {format_number(quartzs)} Quartzs",
                inline=False
            )

            # Group and add items
            categories = {}
            for item in page_items:
                cat = item.get('category', 'general').title()
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)

            for cat_name, cat_items in categories.items():
                items_text = ""
                for item in cat_items:
                    currency_type = item.get('currency_type', 'sakura_crystals')
                    currency_symbol = "🔹" if currency_type == "quartzs" else "💎"
                    
                    rarity_emojis = {
                        'common': '⚪', 'uncommon': '🟢', 'rare': '🔵',
                        'epic': '🟣', 'legendary': '🟡'
                    }
                    rarity_emoji = rarity_emojis.get(item.get('rarity', 'common'), '⚪')
                    
                    requirements = ""
                    if item.get('requirements'):
                        req_data = json.loads(item['requirements']) if isinstance(item['requirements'], str) else item['requirements']
                        if req_data.get('min_rank'):
                            requirements = f" (Rank {req_data['min_rank']}+)"
                    
                    items_text += f"{rarity_emoji} **ID {item['id']}** - {item['name']}\n"
                    items_text += f"   {currency_symbol}{format_number(item['price'])}{requirements}\n"
                    items_text += f"   *{item.get('description', 'No description')}*\n\n"

                if items_text:
                    embed.add_field(
                        name=f"🏷️ {cat_name}",
                        value=items_text.strip(),
                        inline=False
                    )

            embed.set_footer(text=f"Page {page}/{total_pages} • Total Items: {len(items)}")

            # Update view
            new_view = ShopView(self.db, page, total_pages, self.category, self.user_id)
            await interaction.edit_original_response(embed=embed, view=new_view)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to update shop display.",
                color=0xFF0000
            )
            await interaction.edit_original_response(embed=embed, view=None)


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(ShopCog(bot, bot.services))
