import discord
import aiohttp
from discord.ext import commands


class NekoGifCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="nekogif",
        description="Get a random gif from a specific category.",
        with_app_command=True,
    )
    async def nekogif(self, ctx):
        url = "https://nekos.best/api/v2/neko"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await ctx.channel.send("Failed to fetch the image.")
                    return

                json_data = await response.json()

                results = json_data.get("results")
                if not results:
                    await ctx.channel.send("No image found.")
                    return

                image_url = results[0].get("url")

                anime_name = None
                artist_name = None
                artist_href = None
                try:
                    anime_name = results[0].get("anime_name")
                    artist_name = results[0].get("artist_name")
                    artist_href = results[0].get("artist_href")
                except KeyError:
                    pass

                msg = f"**Anime Name:** {anime_name}\n" if anime_name else ""
                msg += f"**Artist Name:** {artist_name}\n" if artist_name else ""
                msg += f"**Artist Link:** {artist_href}\n" if artist_href else ""

                embed = discord.Embed(colour=0x141414)
                embed.set_image(url=image_url)
                await ctx.send(embed=embed)
                await ctx.send(msg)


async def setup(bot):
    await bot.add_cog(NekoGifCog(bot))
