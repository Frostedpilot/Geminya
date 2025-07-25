import discord
import aiohttp
from discord.ext import commands

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


class NekoGifCog(BaseCommand):
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

    @commands.hybrid_command(
        name="nekogif",
        description="Get a random neko gif from nekos.best API.",
        with_app_command=True,
    )
    @discord.app_commands.choices(
        category=[
            discord.app_commands.Choice(name=category.capitalize(), value=category)
            for category in [
                "baka",
                "bite",
                "blush",
                "bored",
                "cry",
                "cuddle",
                "dance",
                "facepalm",
                "handhold",
                "happy",
                "highfive",
                "hug",
                "kitsune",
                "kiss",
                "laugh",
                "neko",
                "nod",
                "nom",
                "nope",
                "pat",
                "poke",
                "pout",
                "punch",
                "shrug",
                "waifu",
            ]
        ]
    )
    async def nekogif(
        self, ctx: commands.Context, category: discord.app_commands.Choice[str]
    ):
        """Fetch a random neko gif and display it with attribution."""
        base_url = "https://nekos.best/api/v2/"

        category = category.value.lower()

        url = base_url + category

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        await ctx.send(
                            "Failed to fetch the image, nya! Please try again later. (´･ω･`)"
                        )
                        self.logger.warning(
                            f"nekos.best API returned status {response.status}"
                        )
                        return

                    json_data = await response.json()

                    results = json_data.get("results")
                    if not results:
                        await ctx.send(
                            "No image found, nya! The API might be having issues. (｡•́︿•̀｡)"
                        )
                        self.logger.warning("Empty results from nekos.best API")
                        return

                    image_url = results[0].get("url")
                    if not image_url:
                        await ctx.send("No image URL found, nya! (´･ω･`)")
                        return

                    # Extract metadata
                    anime_name = results[0].get("anime_name")
                    artist_name = results[0].get("artist_name")
                    artist_href = results[0].get("artist_href")

                    # Build attribution message
                    attribution_parts = []
                    if anime_name:
                        attribution_parts.append(f"**Anime:** {anime_name}")
                    if artist_name:
                        if artist_href:
                            attribution_parts.append(
                                f"**Artist:** [{artist_name}]({artist_href})"
                            )
                        else:
                            attribution_parts.append(f"**Artist:** {artist_name}")

                    # Create embed
                    embed = discord.Embed(
                        title="Random Neko Gif, nya! ฅ^•ﻌ•^ฅ", color=0x141414
                    )
                    embed.set_image(url=image_url)

                    if attribution_parts:
                        embed.description = "\n".join(attribution_parts)

                    embed.set_footer(text="Powered by nekos.best API")

                    await ctx.send(embed=embed)
                    self.logger.info(f"Neko gif sent to {ctx.author} in {ctx.guild}")

        except aiohttp.ClientTimeout:
            await ctx.send(
                "The request timed out, nya! Please try again later. (´･ω･`)"
            )
            self.logger.error("Timeout when fetching from nekos.best API")
        except aiohttp.ClientError as e:
            await ctx.send(
                "Network error occurred, nya! Please try again later. (´･ω･`)"
            )
            self.logger.error(f"Network error when fetching neko gif: {e}")
        except Exception as e:
            await ctx.send("Something went wrong while fetching the gif, nya! (´･ω･`)")
            self.logger.error(f"Unexpected error in nekogif command: {e}")


async def setup(bot: commands.Bot):
    # Get services from bot instance
    await bot.add_cog(NekoGifCog(bot, bot.services))
