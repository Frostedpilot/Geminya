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

    @app_commands.command(name="giftcode", description="Redeem a gift code for rewards!")
    @app_commands.describe(code="The gift code to redeem")
    async def giftcode(self, interaction: discord.Interaction, code: str):
        await interaction.response.defer(thinking=True)
        user_id = str(interaction.user.id)
        status = await self.db.redeem_gift_code(user_id, code)
        if status == "success":
            await interaction.followup.send(f"✅ Successfully redeemed code `{code}`! Check your inventory or balance.")
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
