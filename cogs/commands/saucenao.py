import discord
import saucenao_api
from discord.ext import commands

from cogs.base_command import BaseCommand
from services.container import ServiceContainer
from config import Config


class SauceNaoCog(BaseCommand):
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)
        self.api_key = self.services.config.saucenao_api_key

    @commands.hybrid_command(
        name="saucenao",
        description="Trace the sauce of a specific image.",
    )
    async def saucenao(
        self,
        ctx: commands.Context,
        image: discord.Attachment = None,
        url: str = None,
        top_n: int = 1,
    ):
        """Trace the timestamp of a specific anime screencap."""
        if not image and not url:
            await ctx.send("Please provide either a screencap image or a URL.")
            return

        url = self._get_image_url(image, url)
        if not url:
            await ctx.send("No valid image or URL provided.")
            return

        # Send processing message
        if image:
            tmp = discord.Embed(title="Processing screencap image...")
            tmp.set_image(url=image.url)
            await ctx.send(embed=tmp)
        else:
            tmp = discord.Embed(title="Processing screencap URL...")
            tmp.set_image(url=url)
            await ctx.send(embed=tmp)

        # Fetch data from API
        data = await self._fetch_saucenao_data(ctx, url)
        if not data:
            return

        # Process and send results
        await self._send_results(ctx, data, top_n)

    def _get_image_url(
        self, screencap_image: discord.Attachment, screencap_url: str
    ) -> str:
        """Get the image URL from attachment or string."""
        if screencap_image:
            return screencap_image.url
        return screencap_url

    async def _fetch_saucenao_data(
        self, ctx: commands.Context, url: str
    ) -> dict | None:
        """Fetch data from SauceNao API."""
        try:
            results = saucenao_api.SauceNao(self.api_key).from_url(url)
            if not results:
                await ctx.send("No results found for the provided image.")
                return None
            return results
        except Exception as e:
            self.logger.error(f"Error fetching data from SauceNao: {e}")
            await ctx.send("An error occurred while fetching data from SauceNao.")
            return None

    def _process_results(self, data: dict, top_n: int) -> list:
        """Process API results into formatted data."""
        results = []
        for result in data:
            thumbnail = result.thumbnail if hasattr(result, "thumbnail") else None
            similarity = result.similarity if hasattr(result, "similarity") else None
            title = result.title if hasattr(result, "title") else None
            urls = result.urls if hasattr(result, "urls") else []
            author = result.author if hasattr(result, "author") else None
            est_timestamp = result.est_time if hasattr(result, "est_time") else None
            year = result.year if hasattr(result, "year") else None

            results.append(
                {
                    "Thumbnail": thumbnail,
                    "Similarity": similarity,
                    "Title": title,
                    "Urls": urls,
                    "Author": author,
                    "Estimated timestamp": est_timestamp,
                    "Year": year,
                }
            )

        return results[:top_n]  # Limit to top_n results

    async def _send_results(self, ctx: commands.Context, data: dict, top_n: int):
        """Send formatted results to Discord."""
        results = self._process_results(data, top_n)

        for i, result in enumerate(results, 1):
            embed = discord.Embed(
                title="SauceNao Results",
                description=f"Found {len(results)} results for the provided screencap. Displaying result {i}.",
                color=0x03A64B,
            )

            if result["Thumbnail"]:
                embed.set_image(url=result["Thumbnail"])

            for key, value in result.items():
                if key == "Thumbnail":
                    continue
                if value:
                    if isinstance(value, list):
                        value = "\n".join(value)
                    embed.add_field(name=key, value=value, inline=False)

            embed.set_footer(
                text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url
            )

            await ctx.send(embed=embed)

        self.logger.info(f"SauceNao command used by {ctx.author} in {ctx.guild}")


async def setup(bot: commands.Bot):
    # Get services from bot instance
    await bot.add_cog(SauceNaoCog(bot, bot.services))
