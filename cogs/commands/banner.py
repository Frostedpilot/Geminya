"""
User-facing banner commands: list active banners and show banner details.
"""

import discord
from discord.ext import commands
from services.database import DatabaseService

class Banner(commands.Cog):
    def __init__(self, bot, db: DatabaseService):
        self.bot = bot
        self.db = db

    @commands.hybrid_command(name="banner_list", description="List all active banners.")
    async def banner_list(self, ctx):
        """List all active banners."""
        banners = await self.db.list_banners(active_only=True)
        if not banners:
            await ctx.send("No active banners.")
            return
        embed = discord.Embed(title="Active Banners", color=0x4A90E2)
        for b in banners:
            embed.add_field(
                name=f"{b['name']} (ID: {b['id']})",
                value=f"Type: {b['type']}\n{b['description']}\nTime: {b['start_time']} - {b['end_time']}",
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="banner_info", description="Show details for a banner.")
    @discord.app_commands.describe(banner_id="Banner ID to show details for")
    async def banner_info(self, ctx, banner_id: int):
        """Show details for a specific banner, including waifu pool."""
        banner = await self.db.get_banner(banner_id)
        if not banner:
            await ctx.send("Banner not found.")
            return
        items = await self.db.get_banner_items(banner_id)
        waifu_ids = [item['item_id'] for item in items]
        waifu_list = []
        # Try to get waifu names from waifu_service if available
        waifu_service = getattr(self.bot, 'services', None)
        if waifu_service and hasattr(waifu_service, 'waifu_service'):
            waifu_objs = waifu_service.waifu_service._waifu_list
            waifu_list = [w['name'] for w in waifu_objs if w['waifu_id'] in waifu_ids]
        else:
            waifu_list = [str(wid) for wid in waifu_ids]
        embed = discord.Embed(title=f"Banner: {banner['name']} (ID: {banner['id']})", color=0x4A90E2)
        embed.add_field(name="Type", value=banner['type'], inline=True)
        embed.add_field(name="Active", value=str(banner['is_active']), inline=True)
        embed.add_field(name="Time", value=f"{banner['start_time']} - {banner['end_time']}", inline=False)
        embed.add_field(name="Description", value=banner['description'] or "No description.", inline=False)
        embed.add_field(name="Waifu Pool", value="\n".join(waifu_list) or "None", inline=False)
        await ctx.send(embed=embed)

def setup(bot):
    from services.database import DatabaseService
    db = bot.get_cog('DatabaseService') or DatabaseService(bot.config)
    bot.add_cog(Banner(bot, db))
