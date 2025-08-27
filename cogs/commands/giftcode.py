"""
Gift code slash command for the Waifu Academy system.
Allows users to redeem codes for quartz, gems, or items.
"""

import discord
from discord.ext import commands
from discord import app_commands

class GiftCodeCog(commands.Cog):
    def __init__(self, bot, services):
        self.bot = bot
        self.services = services
        self.db = self.services.waifu_service.db

    @app_commands.command(name="nwnl_giftcode", description="Redeem a NWNL gift code and see your reward!")
    @app_commands.describe(code="The gift code to redeem")
    async def nwnl_giftcode(self, interaction: discord.Interaction, code: str):
        await interaction.response.defer(thinking=True)
        user_id = str(interaction.user.id)
        status = await self.db.redeem_gift_code(user_id, code)
        gift = await self.db.get_gift_code(code)
        reward_msg = None
        if gift:
            if gift['reward_type'] == 'quartz':
                reward_msg = f"You received **{gift['reward_value']} Quartz**."
            elif gift['reward_type'] == 'gems':
                reward_msg = f"You received **{gift['reward_value']} Sakura Crystals**."
            elif gift['reward_type'] == 'item':
                # Fetch item name from shop_items
                item = await self.db.get_shop_item_by_id(gift['reward_value'])
                if item:
                    reward_msg = f"You received **1x {item['name']}**."
                else:
                    reward_msg = f"You received an item (ID: {gift['reward_value']}), but it no longer exists."
            else:
                reward_msg = "Unknown reward type. Please contact an admin."
        if status == "success":
            await interaction.followup.send(f"✅ Successfully redeemed code `{code}`! {reward_msg}")
        elif status == "already":
            await interaction.followup.send(f"⚠️ You have already redeemed this code.")
        elif status == "invalid":
            await interaction.followup.send(f"❌ Invalid or inactive code.")
        elif status == "limit":
            await interaction.followup.send(f"❌ This code has reached its maximum number of redemptions.")
        elif status == "item_missing":
            await interaction.followup.send(f"❌ The item for this code no longer exists.")
        elif status == "unknown_type":
            await interaction.followup.send(f"❌ This code has an unknown reward type. Please contact an admin.")
        else:
            await interaction.followup.send(f"❌ An unknown error occurred. Please try again later.")

async def setup(bot):
    await bot.add_cog(GiftCodeCog(bot, bot.services))
