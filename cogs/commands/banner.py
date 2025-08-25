"""Banner commands for NWNL: show banners, select banner, and support for user-dependent banner selection."""

import discord
from discord.ext import commands
from typing import Optional
from services.banner_manager import BannerManager

class BannerCommands(commands.Cog):
    def __init__(self, bot, services):
        self.bot = bot
        self.services = services
        self.banner_manager = BannerManager()

    @commands.command(name="nwnl_banners", help="Show all current banners available for summoning.")
    async def nwnl_banners(self, ctx):
        banners = self.banner_manager.get_all_banners()
        if not banners:
            await ctx.send("No banners available.")
            return
        embed = discord.Embed(title="Current Banners", color=discord.Color.blue())
        for banner in banners:
            name = banner.get("name", f"Banner {banner['id']}")
            desc = banner.get("description", "")
            banner_type = banner.get("type", "unknown").replace("-", " ").title()
            value = f"Type: {banner_type}\n{desc}"
            if banner.get("image_url"):
                value += f"\n[Image]({banner['image_url']})"
            embed.add_field(
                name=f"{name} (ID: {banner['id']})",
                value=value,
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command(name="nwnl_choose_banner", help="Choose a banner to roll for. Usage: !nwnl_choose_banner <banner_id>")
    async def nwnl_choose_banner(self, ctx, banner_id: int):
        banner = self.banner_manager.get_banner_by_id(banner_id)
        if not banner:
            await ctx.send(f"Banner with ID {banner_id} not found.")
            return
        # Store the selected banner ID in the user record (selected_series_id is now used for banner selection)
        await self.services.db.update_user_selected_banner(str(ctx.author.id), banner_id)
        name = banner.get("name", f"Banner {banner_id}")
        await ctx.send(f"You have selected banner: **{name}** (ID: {banner_id}) for your summons.")

async def setup(bot, services):
    await bot.add_cog(BannerCommands(bot, services))
