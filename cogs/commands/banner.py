"""
User-facing banner commands: list active banners and show banner details.
"""

import discord
from discord.ext import commands
from services.database import DatabaseService

class Banner(commands.Cog):

    @commands.hybrid_command(name="nwnl_banner_waifupool", description="Show the waifu pool for a banner, with scrolling buttons.")
    @discord.app_commands.describe(banner_id="Banner ID to show waifu pool for")
    async def nwnl_banner_waifupool(self, ctx, banner_id: int):
        """Show the waifu pool for a banner, paginated with buttons."""
        banner = await self.db.get_banner(banner_id)
        if not banner:
            await ctx.send("Banner not found.")
            return
        items = await self.db.get_banner_items(banner_id)
        waifu_ids = [item['item_id'] for item in items]
        rate_up_ids = set(item['item_id'] for item in items if item.get('rate_up'))

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
            waifu_display = [str(wid) for wid in waifu_ids]

        # Pagination setup
        page_size = 10
        total_pages = max(1, (len(waifu_display) + page_size - 1) // page_size)

        def get_page(page):
            start = page * page_size
            end = start + page_size
            lines = waifu_display[start:end]
            return lines

        class WaifuPoolView(discord.ui.View):
            def __init__(self, author_id, timeout=60):
                super().__init__(timeout=timeout)
                self.page = 0
                self.author_id = author_id
                self.message = None
                self.update_buttons()

            def update_buttons(self):
                self.clear_items()
                self.add_item(self.PrevButton(self))
                self.add_item(self.NextButton(self))

            class PrevButton(discord.ui.Button):
                def __init__(self, parent):
                    super().__init__(style=discord.ButtonStyle.primary, label="Previous", disabled=parent.page == 0)
                    self.parent = parent
                async def callback(self, interaction: discord.Interaction):
                    if interaction.user.id != self.parent.author_id:
                        await interaction.response.send_message("You can't control this menu.", ephemeral=True)
                        return
                    if self.parent.page > 0:
                        self.parent.page -= 1
                        await self.parent.update_message(interaction)

            class NextButton(discord.ui.Button):
                def __init__(self, parent):
                    super().__init__(style=discord.ButtonStyle.primary, label="Next", disabled=(parent.page >= total_pages - 1))
                    self.parent = parent
                async def callback(self, interaction: discord.Interaction):
                    if interaction.user.id != self.parent.author_id:
                        await interaction.response.send_message("You can't control this menu.", ephemeral=True)
                        return
                    if self.parent.page < total_pages - 1:
                        self.parent.page += 1
                        await self.parent.update_message(interaction)

            async def update_message(self, interaction):
                embed = discord.Embed(
                    title=f"Waifu Pool for Banner: {banner['name']} (ID: {banner['id']})",
                    description="\n".join(get_page(self.page)) or "None",
                    color=0x4A90E2,
                )
                embed.set_footer(text=f"Page {self.page + 1}/{total_pages}")
                self.update_buttons()
                await interaction.response.edit_message(embed=embed, view=self)

        # Send first page
        embed = discord.Embed(
            title=f"Waifu Pool for Banner: {banner['name']} (ID: {banner['id']})",
            description="\n".join(get_page(0)) or "None",
            color=0x4A90E2,
        )
        embed.set_footer(text=f"Page 1/{total_pages}")
        view = WaifuPoolView(ctx.author.id)
        await ctx.send(embed=embed, view=view)
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
        """Show details for a specific banner, including waifu pool and series info."""
        banner = await self.db.get_banner(banner_id)
        if not banner:
            await ctx.send("Banner not found.")
            return
        items = await self.db.get_banner_items(banner_id)
        waifu_ids = [item['item_id'] for item in items]
        rate_up_ids = set(item['item_id'] for item in items if item.get('rate_up'))

        # Parse series_ids and fetch series info
        series_ids = banner.get('series_ids') or []
        if isinstance(series_ids, str):
            import json as _json
            try:
                series_ids = _json.loads(series_ids)
            except Exception:
                series_ids = [series_ids]
        series_map = {}
        if isinstance(series_ids, list) and series_ids:
            # Fetch all series info
            for sid in series_ids:
                try:
                    sid_int = int(sid)
                    series = await self.db.get_series_by_id(sid_int)
                    if series:
                        series_map[sid_int] = series.get('name', f"Series {sid_int}")
                except Exception:
                    continue

        # Only show 2* and 3* waifus, and do NOT show series beside each waifu
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
            waifu_display = [str(wid) for wid in waifu_ids]

        embed = discord.Embed(title=f"Banner: {banner['name']} (ID: {banner['id']})", color=0x4A90E2)
        # If only one series_id, fetch its image_link and set as banner image
        if isinstance(series_ids, list) and len(series_ids) == 1:
            try:
                series_id = int(series_ids[0])
                series = await self.db.get_series_by_id(series_id)
                if series and series.get('image_link'):
                    embed.set_image(url=series['image_link'])
            except Exception:
                pass

        # Show series names in a dedicated field at the top
        if series_map:
            series_lines = [sname for sname in series_map.values()]
            embed.add_field(name="Series", value="\n".join(series_lines), inline=False)

        embed.add_field(name="Type", value=banner['type'], inline=True)
        embed.add_field(name="Active", value=str(banner['is_active']), inline=True)
        embed.add_field(name="Time", value=f"{banner['start_time']} - {banner['end_time']}", inline=False)
        embed.add_field(name="Description", value=banner['description'] or "No description.", inline=False)
    # Waifu pool removed to avoid exceeding Discord field length limits
        await ctx.send(embed=embed)

    @staticmethod
    def _waifu_in_series(waifu_id, series_id, waifu_objs):
        if not waifu_objs:
            return False
        for w in waifu_objs:
            if w['waifu_id'] == waifu_id and w.get('series_id') == series_id:
                return True
        return False

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
