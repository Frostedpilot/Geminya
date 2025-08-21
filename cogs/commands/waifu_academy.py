"""Waifu Academy management commands."""

import discord
from discord.ext import commands
from cogs.base_command import BaseCommand
from services.container import ServiceContainer


class WaifuAcademyCog(BaseCommand):
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

    @commands.hybrid_command(
        name="nwnl_status", description="📊 Check your academy status and statistics"
    )
    async def nwnl_status(self, ctx: commands.Context):
        """Display user's academy status."""
        await ctx.defer()

        try:
            stats = await self.services.waifu_service.get_user_stats(str(ctx.author.id))
            user = stats["user"]

            embed = discord.Embed(
                title=f"🏫 {ctx.author.display_name}'s Academy Status", color=0x3498DB
            )

            # Academy Info
            # Use the new integer timestamp field, fallback to old field if needed
            created_at_timestamp = user.get("created_at_new", 0)
            if created_at_timestamp == 0:
                # Fallback to old timestamp format
                try:
                    from datetime import datetime

                    created_at_str = user.get("created_at", "2025-01-01 00:00:00")
                    if isinstance(created_at_str, str):
                        created_at_dt = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00").replace(" ", "T")
                        )
                        created_at_timestamp = int(created_at_dt.timestamp())
                    else:
                        created_at_timestamp = int(created_at_str or 0)
                except (ValueError, TypeError):
                    created_at_timestamp = 0

            embed.add_field(
                name="🏛️ Academy Details",
                value=f"**Name:** {user['academy_name']}\n"
                f"**Rank:** Level {user['collector_rank']}\n"
                f"**Founded:** <t:{created_at_timestamp}:R>",
                inline=True,
            )

            # Resources
            embed.add_field(
                name="💎 Resources",
                value=f"**Sakura Crystals:** {user['sakura_crystals']}\n"
                f"**Pity Counter:** {user['pity_counter']}/90\n"
                f"**Next 4⭐ in:** {max(0, 10 - user['pity_counter'])} pulls",
                inline=True,
            )

            # Collection Stats
            embed.add_field(
                name="📚 Collection",
                value=f"**Total Waifus:** {stats['total_waifus']}\n"
                f"**Unique Waifus:** {stats['unique_waifus']}\n"
                f"**Collection Power:** {stats['collection_power']}",
                inline=True,
            )

            # Rarity breakdown
            rarity_dist = stats["rarity_distribution"]
            if rarity_dist:
                rarity_text = ""
                for rarity in sorted(rarity_dist.keys(), reverse=True):
                    count = rarity_dist[rarity]
                    stars = "⭐" * rarity
                    rarity_text += f"{stars}: {count}\n"

                embed.add_field(
                    name="🌟 Rarity Distribution", value=rarity_text, inline=True
                )

            # Progress to next rank (placeholder logic)
            next_rank_requirement = user["collector_rank"] * 50
            progress = min(stats["collection_power"], next_rank_requirement)
            progress_bar = self._create_progress_bar(progress, next_rank_requirement)

            embed.add_field(
                name="📈 Rank Progress",
                value=f"{progress_bar}\n{progress}/{next_rank_requirement} power",
                inline=False,
            )

            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_footer(text="Use /nwnl_summon to grow your academy!")

            await ctx.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error displaying academy status: {e}")
            embed = discord.Embed(
                title="❌ Status Error",
                description="Unable to display academy status. Please try again later!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="nwnl_rename_academy", description="🏷️ Rename your waifu academy"
    )
    async def nwnl_rename_academy(self, ctx: commands.Context, *, new_name: str):
        """Rename user's academy."""
        await ctx.defer()

        # Validate name length
        if len(new_name) > 50:
            embed = discord.Embed(
                title="❌ Name Too Long",
                description="Academy name must be 50 characters or less!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)
            return

        if len(new_name) < 3:
            embed = discord.Embed(
                title="❌ Name Too Short",
                description="Academy name must be at least 3 characters long!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)
            return

        try:
            # Update academy name in database
            user = await self.services.waifu_service.db.get_or_create_user(
                str(ctx.author.id)
            )

            # Here we would need to add an update method to DatabaseService
            # For now, let's create a simple embed acknowledging the request
            embed = discord.Embed(
                title="🏷️ Academy Renamed!",
                description=f"Your academy has been renamed to: **{new_name}**",
                color=0x2ECC71,
            )
            embed.set_footer(text="Feature coming soon - database update needed!")

            await ctx.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error renaming academy: {e}")
            embed = discord.Embed(
                title="❌ Rename Error",
                description="Unable to rename academy. Please try again later!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="nwnl_shop", description="🛒 Browse the academy shop")
    async def nwnl_shop(self, ctx: commands.Context):
        """Display the academy shop."""
        await ctx.defer()

        embed = discord.Embed(
            title="🛒 Waifu Academy Shop",
            description="Welcome to the academy shop! Purchase items with Sakura Crystals.",
            color=0xE74C3C,
        )

        # Shop items (placeholder - could be stored in database)
        shop_items = [
            {
                "name": "10x Summon Bundle",
                "price": 90,
                "description": "10 summons for the price of 9!",
            },
            {
                "name": "Sakura Crystal Pack",
                "price": 0,
                "description": "Get 100 free crystals! (Daily)",
            },
            {
                "name": "Bond Boost Potion",
                "price": 50,
                "description": "Increase bond level faster",
            },
            {
                "name": "Academy Decoration",
                "price": 25,
                "description": "Customize your academy",
            },
            {
                "name": "Nickname Permit",
                "price": 20,
                "description": "Give custom nicknames to waifus",
            },
        ]

        shop_text = ""
        for i, item in enumerate(shop_items, 1):
            shop_text += f"**{i}.** {item['name']} - 💎{item['price']}\n{item['description']}\n\n"

        embed.add_field(name="Available Items", value=shop_text, inline=False)

        embed.add_field(
            name="💡 How to Purchase",
            value="Shop functionality coming soon!\nFor now, enjoy free summoning with your starter crystals!",
            inline=False,
        )

        embed.set_footer(text="More items will be added in future updates!")

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="nwnl_daily", description="🎁 Claim your daily rewards"
    )
    async def nwnl_daily(self, ctx: commands.Context):
        """Claim daily rewards."""
        await ctx.defer()

        try:
            user = await self.services.waifu_service.db.get_or_create_user(
                str(ctx.author.id)
            )

            # Check if user can claim daily (simplified logic)
            from datetime import datetime, timedelta

            now = datetime.now()

            # For now, just give rewards (in a real implementation, check last_daily_reset)
            daily_crystals = 50
            await self.services.waifu_service.db.update_user_crystals(
                str(ctx.author.id), daily_crystals
            )

            embed = discord.Embed(
                title="🎁 Daily Rewards Claimed!",
                description=f"You received **{daily_crystals} Sakura Crystals**!",
                color=0x2ECC71,
            )

            embed.add_field(
                name="💎 Current Crystals",
                value=f"{user['sakura_crystals'] + daily_crystals}",
                inline=True,
            )

            embed.add_field(
                name="⏰ Next Daily", value="Available tomorrow!", inline=True
            )

            embed.set_footer(text="Come back tomorrow for more rewards!")

            await ctx.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error claiming daily rewards: {e}")
            embed = discord.Embed(
                title="❌ Daily Error",
                description="Unable to claim daily rewards. Please try again later!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)

    def _create_progress_bar(self, current: int, maximum: int, length: int = 10) -> str:
        """Create a progress bar string."""
        if maximum == 0:
            return "▱" * length

        filled = int((current / maximum) * length)
        empty = length - filled

        return "▰" * filled + "▱" * empty


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(WaifuAcademyCog(bot, bot.services))
