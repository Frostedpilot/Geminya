import discord
import aiohttp
from discord.ext import commands

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


class YoMamaCog(BaseCommand):
    # Constants
    ERROR_MESSAGE = "Failed to retrieve a yo mama joke, nya! (｡•́︿•̀｡)"

    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

    @commands.hybrid_command(name="yo_mama", description="Tell a yo mama joke.")
    async def yo_mama(self, ctx: commands.Context):
        """Tell a yo mama joke."""
        base_url = "https://www.yomama-jokes.com"
        endpoint = "/api/v1/jokes/random/"
        modifiers = ""
        url = f"{base_url}{endpoint}{modifiers}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        await ctx.send(self.ERROR_MESSAGE)
                        self.logger.error(
                            f"Failed to fetch yo mama joke: {response.status}"
                        )
                        return

                    joke_data = await response.json()

            except aiohttp.ClientError as e:
                await ctx.send(self.ERROR_MESSAGE)
                self.logger.error(f"Failed to fetch yo mama joke: {e}")
                return
            except Exception as e:
                await ctx.send(self.ERROR_MESSAGE)
                self.logger.error(f"Unexpected error fetching yo mama joke: {e}")
                return

        text = joke_data.get("joke", "No joke found, nya! (｡•́︿•̀｡)")
        category = joke_data.get("category", "General")

        embed = discord.Embed(
            title="Yo Mama Joke",
            description=text,
            color=0x03A64B,
        )

        if category:
            embed.set_footer(text=f"Category: {category}")
        else:
            embed.set_footer(text="Powered by www.yomama-jokes.com API")

        await ctx.send(embed=embed)

        self.logger.info(f"Sent a yo mama joke to channel {ctx.channel.id}.")


async def setup(bot: commands.Bot):
    # Get services from bot instance
    await bot.add_cog(YoMamaCog(bot, bot.services))
