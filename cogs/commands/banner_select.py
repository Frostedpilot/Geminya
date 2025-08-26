"""
User command to select a default banner for summoning.
"""

import discord
from discord.ext import commands
from typing import Optional
from services.database import DatabaseService

# In-memory user banner selection (for demo; replace with DB for persistence)
user_selected_banners = {}

class BannerSelect(commands.Cog):
    def __init__(self, bot, db: DatabaseService):
        self.bot = bot
        self.db = db

    @commands.hybrid_command(name="select_banner", description="Select a default banner for summoning.")
    @discord.app_commands.describe(banner_id="Banner ID to select as your default banner")
    async def select_banner(self, ctx, banner_id: int):
        """Select a default banner for summoning."""
        banner = await self.db.get_banner(banner_id)
        if not banner or not banner["is_active"]:
            await ctx.send("Banner not found or not active.")
            return
        user_selected_banners[str(ctx.author.id)] = banner_id
        await ctx.send(f"Selected banner {banner['name']} (ID: {banner_id}) as your default.")

    @commands.hybrid_command(name="my_banner", description="Show your currently selected default banner.")
    async def my_banner(self, ctx):
        """Show your currently selected default banner."""
        banner_id = user_selected_banners.get(str(ctx.author.id))
        if not banner_id:
            await ctx.send("You have not selected a default banner. Use /select_banner.")
            return
        banner = await self.db.get_banner(banner_id)
        if not banner:
            await ctx.send("Your selected banner no longer exists.")
            return
        await ctx.send(f"Your default banner: {banner['name']} (ID: {banner_id})")

def setup(bot):
    from services.database import DatabaseService
    db = bot.get_cog('DatabaseService') or DatabaseService(bot.config)
    bot.add_cog(BannerSelect(bot, db))
