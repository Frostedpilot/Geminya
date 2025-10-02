
import discord
from discord.ext import commands
from cogs.base_command import BaseCommand

class WaifuAwakenCog(BaseCommand):
    def __init__(self, bot: commands.Bot, services):
        super().__init__(bot, services)

    @commands.hybrid_command(
        name="nwnl_awaken",
        description="Awaken a waifu by waifu_id (requires Daphine)"
    )
    @discord.app_commands.describe(waifu_id="The waifu_id of the waifu to awaken")
    async def nwnl_awaken(self, ctx: commands.Context, waifu_id: int):
        waifu_service = self.services.waifu_service
        user_id = str(ctx.author.id)
        # Fetch waifu info from user's collection
        collection = await waifu_service.get_user_collection_with_stars(user_id)
        waifu = next((w for w in collection if w["waifu_id"] == waifu_id), None)
        if not waifu:
            await ctx.send(f"❌ You do not own a waifu with waifu_id {waifu_id}.")
            return
        # Confirmation embed
        embed = discord.Embed(
            title=f"Awaken {waifu['name']}?",
            description=f"Series: {waifu.get('series', 'Unknown')}\nStar Level: {waifu.get('current_star_level', waifu.get('rarity', 1))}",
            color=0xFFD700
        )
        if waifu.get('image_url'):
            embed.set_thumbnail(url=waifu['image_url'])

        class ConfirmView(discord.ui.View):
            def __init__(self, author):
                super().__init__(timeout=30)
                self.author = author
                self.value = None

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                return interaction.user == self.author

            @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, emoji="✅")
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.value = True
                self.stop()
                await interaction.response.defer()

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.value = False
                self.stop()
                await interaction.response.defer()

        view = ConfirmView(ctx.author)
        msg = await ctx.send(embed=embed, content="Do you want to awaken this waifu?", view=view)
        await view.wait()

        if view.value is None:
            await msg.edit(content="⏰ Timed out. Awakening cancelled.", view=None)
            return
        if not view.value:
            await msg.edit(content="Awakening cancelled.", view=None)
            return
        # Attempt to awaken
        result = await waifu_service.awaken_waifu(user_id, waifu_id)
        if result["success"]:
            await msg.edit(content=f"✨ {waifu['name']} has been awakened!", embed=None, view=None)
        else:
            await msg.edit(content=f"❌ Awaken failed: {result['message']}", embed=None, view=None)

async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    if not hasattr(bot, "services"):
        raise RuntimeError("ServiceContainer (bot.services) is required for WaifuAwakenCog. Please initialize bot.services before loading this cog.")
    await bot.add_cog(WaifuAwakenCog(bot, bot.services))
