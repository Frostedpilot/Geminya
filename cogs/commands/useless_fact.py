import discord
import aiohttp
from discord.ext import commands

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


class UselessFactCog(BaseCommand):
    # Constants
    ERROR_MESSAGE = "Failed to retrieve a useless fact, nya! (｡•́︿•̀｡)"

    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

    @commands.hybrid_command(name="useless_fact", description="Tell a useless fact.")
    async def useless_fact(self, ctx: commands.Context):
        """Tell a useless fact."""
        base_url = "https://uselessfacts.jsph.pl"
        endpoint = "/api/v2/facts/random"
        modifiers = "?language=en"
        url = f"{base_url}{endpoint}{modifiers}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        await ctx.send(self.ERROR_MESSAGE)
                        self.logger.error(
                            f"Failed to fetch useless fact: {response.status}"
                        )
                        return

                    fact_data = await response.json()

            except aiohttp.ClientError as e:
                await ctx.send(self.ERROR_MESSAGE)
                self.logger.error(f"Failed to fetch useless fact: {e}")
                return
            except Exception as e:
                await ctx.send(self.ERROR_MESSAGE)
                self.logger.error(f"Unexpected error fetching useless fact: {e}")
                return

        text = fact_data.get("text", "No fact found, nya! (｡•́︿•̀｡)")
        source = fact_data.get("source", None)
        source_url = fact_data.get("source_url", None)

        embed = discord.Embed(
            title="Useless Fact",
            description=text,
            color=0x03A64B,
        )

        if source:
            embed.set_footer(text=f"Source: {source}")
        elif source_url:
            embed.set_footer(text=f"Source URL: {source_url}")
        else:
            embed.set_footer(text="Powered by uselessfacts.jsph.pl API")

        await ctx.send(embed=embed)

        self.logger.info(f"Sent a useless fact to channel {ctx.channel.id}.")


async def setup(bot: commands.Bot):
    # Get services from bot instance
    await bot.add_cog(UselessFactCog(bot, bot.services))
