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

    @commands.hybrid_command(name="nwnl_banner_list", description="List all active banners.")
    async def nwnl_banner_list(self, ctx):
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

    @commands.hybrid_command(name="nwnl_banner_info", description="Show details for a banner.")
    @discord.app_commands.describe(banner_id="Banner ID to show details for")
    async def nwnl_banner_info(self, ctx, banner_id: int):
        """Show details for a specific banner, including waifu pool."""
        banner = await self.db.get_banner(banner_id)
        if not banner:
            await ctx.send("Banner not found.")
            return
        items = await self.db.get_banner_items(banner_id)
        waifu_ids = [item['item_id'] for item in items]
        # Map waifu_id to rate_up/limited
        rate_up_ids = set(item['item_id'] for item in items if item.get('rate_up'))
        # Only show 2* and 3* waifus
        waifu_service = getattr(self.bot, 'services', None)
        waifu_objs = None
        if waifu_service and hasattr(waifu_service, 'waifu_service'):
            waifu_objs = waifu_service.waifu_service._waifu_list
        waifu_display = []
        if waifu_objs:
            for w in waifu_objs:
                if w['waifu_id'] in waifu_ids and w.get('rarity', 0) in (2, 3):
                    star = '★' * w['rarity']
                    tag = " (Rate-Up)" if w['waifu_id'] in rate_up_ids else (" (Limited)" if banner['type'] == 'limited' else "")
                    waifu_display.append(f"{w['name']} {star}{tag}")
        else:
            # Fallback: just show waifu_id for 2* and 3* (need waifu info for rarity)
            waifu_display = [str(wid) for wid in waifu_ids]

        embed = discord.Embed(title=f"Banner: {banner['name']} (ID: {banner['id']})", color=0x4A90E2)
        # If only one series_id, fetch its image_link and set as banner image
        series_ids = banner.get('series_ids') or []
        if isinstance(series_ids, str):
            import json as _json
            try:
                series_ids = _json.loads(series_ids)
            except Exception:
                series_ids = [series_ids]
        if isinstance(series_ids, list) and len(series_ids) == 1:
            # Fetch series image_link
            series_id = series_ids[0]
            # Fetch series info directly by series_id (primary key)
            series = await self.db.get_series_by_id(series_id)
            if series and series.get('image_link'):
                embed.set_image(url=series['image_link'])
        embed.add_field(name="Type", value=banner['type'], inline=True)
        embed.add_field(name="Active", value=str(banner['is_active']), inline=True)
        embed.add_field(name="Time", value=f"{banner['start_time']} - {banner['end_time']}", inline=False)
        embed.add_field(name="Description", value=banner['description'] or "No description.", inline=False)
        embed.add_field(name="Waifu Pool (2★ & 3★ only)", value="\n".join(waifu_display) or "None", inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    from services.database import DatabaseService
    from config import Config
    db = getattr(bot, 'db', None)
    if db is None:
        config = Config.create()
        db = DatabaseService(config)
        await db.initialize()
        bot.db = db
    await bot.add_cog(Banner(bot, db))
