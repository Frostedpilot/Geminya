"""Waifu summon command for the gacha system."""

import discord
from discord.ext import commands
from cogs.base_command import BaseCommand
from services.container import ServiceContainer


class WaifuSummonCog(BaseCommand):
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

    @commands.hybrid_command(
        name="nwnl_summon",
        description="🎰 Summon waifus using Sakura Crystals! (10 crystals per summon)",
    )
    async def nwnl_summon(self, ctx: commands.Context, summon_type: str = "standard"):
        """Perform a waifu summon."""
        await ctx.defer()

        try:
            # Perform the summon
            result = await self.services.waifu_service.perform_summon(
                str(ctx.author.id), summon_type
            )

            if not result["success"]:
                embed = discord.Embed(
                    title="❌ Summon Failed",
                    description=result["message"],
                    color=0xFF6B6B,
                )
                await ctx.send(embed=embed)
                return

            # Create summon result embed
            waifu = result["waifu"]
            rarity = result["rarity"]

            # Rarity colors and emojis
            rarity_config = {
                5: {"color": 0xFFD700, "emoji": "⭐⭐⭐⭐⭐", "name": "Legendary"},
                4: {"color": 0x9932CC, "emoji": "⭐⭐⭐⭐", "name": "Epic"},
                3: {"color": 0x4169E1, "emoji": "⭐⭐⭐", "name": "Rare"},
                2: {"color": 0x32CD32, "emoji": "⭐⭐", "name": "Common"},
                1: {"color": 0x808080, "emoji": "⭐", "name": "Basic"},
            }

            config = rarity_config[rarity]

            embed = discord.Embed(
                title="🎊 Summoning Results! 🎊", color=config["color"]
            )

            # Add NEW or CONSTELLATION indicator
            if result["is_new"]:
                embed.add_field(
                    name="🆕 NEW WAIFU!",
                    value=f"**{waifu['name']}** has joined your academy!",
                    inline=False,
                )
            else:
                constellation = result["constellation_level"]
                embed.add_field(
                    name=f"🌟 Constellation +{constellation}!",
                    value=f"**{waifu['name']}** grows stronger!",
                    inline=False,
                )

            # Character details
            embed.add_field(name="Character", value=f"**{waifu['name']}**", inline=True)
            embed.add_field(name="Series", value=waifu["series"], inline=True)
            embed.add_field(
                name="Element",
                value=f"{waifu.get('element', 'Unknown')} 🔮",
                inline=True,
            )
            embed.add_field(
                name="Rarity", value=f"{config['emoji']} {config['name']}", inline=True
            )
            embed.add_field(
                name="Crystals Left",
                value=f"💎 {result['crystals_remaining']}",
                inline=True,
            )

            # Add image if available
            if waifu.get("image_url"):
                embed.set_image(url=waifu["image_url"])

            embed.set_footer(
                text=f"Use /nwnl_collection to view your academy! • Summoned by {ctx.author.display_name}"
            )

            # Add special animation for high rarity
            content = ""
            if rarity >= 4:
                content = (
                    "✨🎆 **RARE SUMMON!** 🎆✨"
                    if rarity == 4
                    else "🌟💫 **LEGENDARY SUMMON!** 💫🌟"
                )

            await ctx.send(content=content, embed=embed)

            self.logger.info(
                f"User {ctx.author} summoned {waifu['name']} ({rarity}⭐) "
                f"{'NEW' if result['is_new'] else 'C' + str(result['constellation_level'])}"
            )

        except Exception as e:
            self.logger.error(f"Error in waifu summon: {e}")
            embed = discord.Embed(
                title="❌ Summon Error",
                description="Something went wrong during summoning. Please try again later!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="nwnl_collection", description="📚 View your waifu academy collection"
    )
    async def nwnl_collection(self, ctx: commands.Context, user: discord.Member = None):
        """Display user's waifu collection."""
        await ctx.defer()

        target_user = user or ctx.author

        try:
            # Get user's collection
            collection = await self.services.waifu_service.db.get_user_collection(
                str(target_user.id)
            )

            if not collection:
                embed = discord.Embed(
                    title="🏫 Empty Academy",
                    description=f"{'You have' if target_user == ctx.author else f'{target_user.display_name} has'} no waifus yet!\nUse `/nwnl_summon` to start your collection!",
                    color=0x95A5A6,
                )
                await ctx.send(embed=embed)
                return

            # Get user stats
            stats = await self.services.waifu_service.get_user_stats(
                str(target_user.id)
            )

            # Create collection embed
            embed = discord.Embed(
                title=f"🏫 {target_user.display_name}'s Waifu Academy",
                description=f"**Academy Name:** {stats['user']['academy_name']}\n"
                f"**Collector Rank:** {stats['user']['collector_rank']}\n"
                f"**Total Waifus:** {stats['total_waifus']} (Unique: {stats['unique_waifus']})",
                color=0x3498DB,
            )

            # Add rarity distribution
            rarity_dist = stats["rarity_distribution"]
            rarity_text = ""
            for rarity in sorted(rarity_dist.keys(), reverse=True):
                count = rarity_dist[rarity]
                stars = "⭐" * rarity
                rarity_text += f"{stars}: {count}\n"

            if rarity_text:
                embed.add_field(
                    name="🌟 Rarity Distribution", value=rarity_text, inline=True
                )

            # Add resources
            embed.add_field(
                name="💎 Resources",
                value=f"Sakura Crystals: {stats['user']['sakura_crystals']}\n"
                f"Collection Power: {stats['collection_power']}",
                inline=True,
            )

            # Show recent acquisitions (last 5)
            recent_waifus = collection[:5]
            recent_text = ""
            for waifu in recent_waifus:
                stars = "⭐" * waifu["rarity"]
                recent_text += f"{stars} **{waifu['name']}** ({waifu['series']})\n"

            if recent_text:
                embed.add_field(
                    name="📝 Recent Additions", value=recent_text, inline=False
                )

            embed.set_footer(
                text=f"Use /nwnl_profile <name> to view details • Academy Power: {stats['collection_power']}"
            )

            await ctx.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error displaying collection: {e}")
            embed = discord.Embed(
                title="❌ Collection Error",
                description="Unable to display collection. Please try again later!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="nwnl_profile", description="👤 View detailed profile of a waifu"
    )
    async def nwnl_profile(self, ctx: commands.Context, *, waifu_name: str):
        """Display detailed waifu profile."""
        await ctx.defer()

        try:
            # Search for the waifu
            search_results = await self.services.waifu_service.db.search_waifus(
                waifu_name, 5
            )

            if not search_results:
                embed = discord.Embed(
                    title="❌ Waifu Not Found",
                    description=f"No waifu found matching '{waifu_name}'. Try a different name or check spelling!",
                    color=0xFF6B6B,
                )
                await ctx.send(embed=embed)
                return

            # If multiple results, show the first one (or could implement selection)
            waifu = search_results[0]

            # Check if user owns this waifu
            user_collection = await self.services.waifu_service.db.get_user_collection(
                str(ctx.author.id)
            )
            user_waifu = next(
                (w for w in user_collection if w["waifu_id"] == waifu["id"]), None
            )

            # Create profile embed
            rarity_colors = {
                5: 0xFFD700,
                4: 0x9932CC,
                3: 0x4169E1,
                2: 0x32CD32,
                1: 0x808080,
            }

            embed = discord.Embed(
                title=f"👤 {waifu['name']}",
                description=waifu.get(
                    "personality_profile", "A mysterious character..."
                ),
                color=rarity_colors.get(waifu["rarity"], 0x95A5A6),
            )

            # Basic info
            embed.add_field(name="🎭 Series", value=waifu["series"], inline=True)
            embed.add_field(
                name="🏷️ Genre", value=waifu.get("genre", "Unknown"), inline=True
            )
            embed.add_field(
                name="🔮 Element", value=waifu.get("element", "Unknown"), inline=True
            )
            embed.add_field(name="⭐ Rarity", value="⭐" * waifu["rarity"], inline=True)

            # Stats (parse JSON)
            try:
                import json

                base_stats = json.loads(waifu.get("base_stats", "{}"))
                if base_stats:
                    stats_text = ""
                    for stat, value in base_stats.items():
                        stats_text += f"**{stat.title()}:** {value}\n"
                    embed.add_field(name="📊 Base Stats", value=stats_text, inline=True)
            except Exception:
                pass

            # User-specific info if owned
            if user_waifu:
                embed.add_field(
                    name="💖 Your Bond",
                    value=f"**Bond Level:** {user_waifu['bond_level']}\n"
                    f"**Constellation:** C{user_waifu['constellation_level']}\n"
                    f"**Mood:** {user_waifu['current_mood'].title()}\n"
                    f"**Conversations:** {user_waifu['total_conversations']}",
                    inline=True,
                )

                if user_waifu["custom_nickname"]:
                    embed.add_field(
                        name="🏷️ Nickname",
                        value=user_waifu["custom_nickname"],
                        inline=True,
                    )
            else:
                embed.add_field(
                    name="❓ Status",
                    value="Not in your collection\nUse `/nwnl_summon` to try getting them!",
                    inline=True,
                )

            # Add image
            if waifu.get("image_url"):
                embed.set_image(url=waifu["image_url"])

            embed.set_footer(
                text=f"Waifu ID: {waifu['id']} • Use /nwnl_chat to interact!"
            )

            await ctx.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error displaying waifu profile: {e}")
            embed = discord.Embed(
                title="❌ Profile Error",
                description="Unable to display waifu profile. Please try again later!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(WaifuSummonCog(bot, bot.services))
