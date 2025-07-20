import discord
import aiohttp
import urllib.parse
from discord.ext import commands

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


class AniTraceCog(BaseCommand):
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

    @commands.hybrid_command(
        name="anitrace",
        description="Trace the timestamp of a specific anime screencap.",
    )
    async def anitrace(
        self,
        ctx: commands.Context,
        screencap_image: discord.Attachment = None,
        screencap_url: str = None,
        top_n: int = 1,
    ):
        """Trace the timestamp of a specific anime screencap."""
        if not screencap_image and not screencap_url:
            await ctx.send("Please provide either a screencap image or a URL.")
            return

        url = self._get_image_url(screencap_image, screencap_url)
        if not url:
            await ctx.send("No valid image or URL provided.")
            return

        # Send processing message
        if screencap_image:
            tmp = discord.Embed(title="Processing screencap image...")
            tmp.set_image(url=screencap_image.url)
            await ctx.send(embed=tmp)
        else:
            tmp = discord.Embed(title="Processing screencap URL...")
            tmp.set_image(url=screencap_url)
            await ctx.send(embed=tmp)

        # Fetch data from API
        data = await self._fetch_anitrace_data(ctx, url)
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

    async def _fetch_anitrace_data(
        self, ctx: commands.Context, url: str
    ) -> dict | None:
        """Fetch data from AniTrace API."""
        api_url = f"https://api.trace.moe/search?cutBorders&url={urllib.parse.quote_plus(url)}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url) as response:
                    if response.status != 200:
                        await ctx.send(
                            f"Error from AniTrace API: HTTP {response.status}"
                        )
                        self.logger.error(
                            f"AniTrace API returned status {response.status}"
                        )
                        return None

                    data = await response.json()

            except aiohttp.ClientError as e:
                await ctx.send(f"Error connecting to AniTrace API: {str(e)}")
                self.logger.error(f"AniTrace API connection error: {e}")
                return None
            except Exception as e:
                await ctx.send(f"Unexpected error: {str(e)}")
                self.logger.error(f"Unexpected error in anitrace command: {e}")
                return None

        if not data or "result" not in data or not data["result"]:
            await ctx.send("No results found for this image.")
            return None

        return data

    def _format_time(self, seconds) -> str:
        """Format seconds into MM:SS format."""
        if isinstance(seconds, (int, float)):
            minutes = int(seconds // 60)
            seconds = int(seconds % 60)
            return f"{minutes:02d}:{seconds:02d}"
        return str(seconds)

    def _process_results(self, data: dict, top_n: int) -> list:
        """Process API results into formatted data."""
        results = []
        for result in data["result"]:
            anilist_id = result.get("anilist", "Unknown")
            episode = result.get("episode", "Unknown")
            ts_from = result.get("from", 0)
            ts_to = result.get("to", 0)
            similarity = result.get("similarity", 0)
            preview_vid_url = result.get("video")
            preview_pic_url = result.get("image")

            results.append(
                {
                    "anilist_id": anilist_id,
                    "episode": episode,
                    "ts_from": self._format_time(ts_from),
                    "ts_to": self._format_time(ts_to),
                    "similarity": (
                        f"{similarity:.2%}"
                        if isinstance(similarity, (int, float))
                        else str(similarity)
                    ),
                    "preview_vid_url": preview_vid_url,
                    "preview_pic_url": preview_pic_url,
                }
            )
        return results[:top_n]  # Limit to top_n results

    async def _send_results(self, ctx: commands.Context, data: dict, top_n: int):
        """Send formatted results to Discord."""
        results = self._process_results(data, top_n)

        for i, result in enumerate(results, 1):
            embed = discord.Embed(
                title="AniTrace Results",
                description=f"Found {len(results)} results for the provided screencap. Displaying result {i}.",
                color=0x03A64B,
            )

            for i, result in enumerate(results[:3], 1):
                field_value = (
                    f"**Timestamp:** {result['ts_from']} - {result['ts_to']}\n"
                    f"**Similarity:** {result['similarity']}"
                )

                embed.add_field(
                    name=f"#{i} - Episode {result['episode']} (AniList ID: {result['anilist_id']})",
                    value=field_value,
                    inline=False,
                )

            embed.set_footer(text="Powered by trace.moe API")

            if result["preview_pic_url"]:
                embed.set_image(url=result["preview_pic_url"])

            await ctx.send(embed=embed)

        self.logger.info(f"AniTrace command used by {ctx.author} in {ctx.guild}")


async def setup(bot: commands.Bot):
    # Get services from bot instance
    await bot.add_cog(AniTraceCog(bot, bot.services))
