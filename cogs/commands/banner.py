"""Banner commands for NWNL: show banners, select banner, and support for user-dependent banner selection."""

import discord
from discord.ext import commands
from typing import Optional

class BannerCommands(commands.Cog):
    def __init__(self, bot, services):
        self.bot = bot
        self.services = services

    @commands.command(name="nwnl_banners", help="Show all current banners (anime) available for summoning.")
    async def nwnl_banners(self, ctx):
        banners = await self.services.db.get_all_banners()
        if not banners:
            await ctx.send("No banners available.")
            return
        embed = discord.Embed(title="Current Banners", color=discord.Color.blue())
        for banner in banners:
            name = banner["title_english"] or banner["title"]
            embed.add_field(
                name=f"{name} (ID: {banner['id']})",
                value=f"MAL ID: {banner['mal_id']}\n[Image]({banner['image_url']})" if banner["image_url"] else f"MAL ID: {banner['mal_id']}",
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command(name="nwnl_choose_banner", help="Choose a banner (anime) to roll for. Usage: !nwnl_choose_banner <banner_id>")
    async def nwnl_choose_banner(self, ctx, banner_id: int):
        banner = await self.services.db.get_banner_by_id(banner_id)
        if not banner:
            await ctx.send(f"Banner with ID {banner_id} not found.")
            return
        await self.services.db.set_user_selected_banner(str(ctx.author.id), banner_id)
        name = banner["title_english"] or banner["title"]
        await ctx.send(f"You have selected banner: **{name}** (ID: {banner_id}) for your summons.")

async def setup(bot, services):
    await bot.add_cog(BannerCommands(bot, services))
