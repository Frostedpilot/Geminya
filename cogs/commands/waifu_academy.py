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

            from datetime import datetime, timezone
            import time

            now = datetime.now(timezone.utc)
            current_timestamp = int(now.timestamp())
            
            # Get the last daily reset timestamp
            last_daily_reset = user.get("last_daily_reset", 0)
            
            # Calculate if 24 hours have passed since last claim
            time_since_last_claim = current_timestamp - last_daily_reset
            hours_since_claim = time_since_last_claim / 3600
            
            # Check if user can claim (24 hours = 86400 seconds)
            if last_daily_reset > 0 and time_since_last_claim < 86400:
                # Calculate remaining time
                remaining_seconds = 86400 - time_since_last_claim
                remaining_hours = int(remaining_seconds // 3600)
                remaining_minutes = int((remaining_seconds % 3600) // 60)
                
                embed = discord.Embed(
                    title="⏰ Daily Reward Already Claimed",
                    description=f"You've already claimed your daily rewards today!",
                    color=0xF39C12,
                )
                
                embed.add_field(
                    name="⏳ Time Until Next Claim",
                    value=f"{remaining_hours}h {remaining_minutes}m",
                    inline=True,
                )
                
                embed.add_field(
                    name="💎 Current Crystals",
                    value=f"{user['sakura_crystals']:,}",
                    inline=True,
                )
                
                embed.set_footer(text="Come back tomorrow for more rewards!")
                await ctx.send(embed=embed)
                return

            # Simple daily reward: 500 crystals
            daily_crystals = 500

            # Update user's crystals and daily reset timestamp
            await self.services.waifu_service.db.update_user_crystals(
                str(ctx.author.id), daily_crystals
            )
            
            # Update the last daily reset timestamp (no streak tracking)
            await self.services.waifu_service.db.update_daily_reset(
                str(ctx.author.id), current_timestamp, 0  # 0 for streak since we're not using it
            )

            # Create success embed
            embed = discord.Embed(
                title="🎁 Daily Rewards Claimed!",
                description=f"Welcome back! You've earned your daily crystals!",
                color=0x2ECC71,
            )

            embed.add_field(
                name="💎 Crystals Earned",
                value=f"**{daily_crystals}** crystals",
                inline=True,
            )

            embed.add_field(
                name="💎 Current Crystals",
                value=f"{user['sakura_crystals'] + daily_crystals:,}",
                inline=True,
            )

            embed.add_field(
                name="⏰ Next Reward",
                value="Available in 24 hours",
                inline=True,
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

    @commands.hybrid_command(
        name="nwnl_reset_account",
        description="🗑️ Reset your academy account (WARNING: Deletes ALL progress!)",
    )
    async def nwnl_reset_account(self, ctx: commands.Context, confirmation: str = ""):
        """Reset user's academy account to default state."""
        await ctx.defer()

        try:
            # Require confirmation to prevent accidental resets
            if confirmation.lower() != "confirm":
                embed = discord.Embed(
                    title="⚠️ Account Reset Confirmation",
                    description=(
                        "**WARNING: This will permanently delete ALL your academy progress!**\n\n"
                        "This includes:\n"
                        "• 🗂️ All waifus in your collection\n"
                        "• 💬 All conversations and memories\n"
                        "• 🏆 All mission progress\n"
                        "• 💎 Crystals will reset to 2000\n"
                        "• 📊 Pity counter will reset to 0\n"
                        "• 🏛️ Academy rank will reset to 1\n\n"
                        "**To confirm this action, use:**\n"
                        "`/nwnl_reset_account confirmation:confirm`"
                    ),
                    color=0xFF6B6B,
                )
                embed.set_footer(text="This action cannot be undone!")
                await ctx.send(embed=embed)
                return

            # Get current user stats before deletion
            stats = await self.services.waifu_service.get_user_stats(str(ctx.author.id))

            # Perform the reset
            success = await self.services.waifu_service.db.reset_user_account(
                str(ctx.author.id)
            )

            if success:
                embed = discord.Embed(
                    title="✅ Academy Reset Complete",
                    description=(
                        f"**{ctx.author.display_name}'s academy has been reset!**\n\n"
                        "**Previous Progress:**\n"
                        f"• Waifus: {stats['total_waifus']} (Unique: {stats['unique_waifus']})\n"
                        f"• Collection Power: {stats['collection_power']}\n"
                        f"• Academy Rank: {stats['user']['collector_rank']}\n"
                        f"• Crystals: {stats['user']['sakura_crystals']}\n\n"
                        "**New Academy:**\n"
                        "• 💎 2000 Sakura Crystals\n"
                        "• 🏛️ Rank 1 Academy\n"
                        "• 📊 Fresh pity counter\n"
                        "• 🎯 Ready for new adventures!\n\n"
                        "Use `/nwnl_summon` to start building your new collection!"
                    ),
                    color=0x2ECC71,
                )
                embed.set_footer(text="Welcome to your fresh start!")
            else:
                embed = discord.Embed(
                    title="❌ Reset Failed",
                    description="Unable to reset your academy. You may not have an existing account.",
                    color=0xFF6B6B,
                )

            await ctx.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error resetting user account: {e}")
            embed = discord.Embed(
                title="❌ Reset Error",
                description="Something went wrong during the reset process. Please try again later!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="nwnl_delete_account",
        description="🗑️💀 PERMANENTLY DELETE your academy account (IRREVERSIBLE!)",
    )
    async def nwnl_delete_account(self, ctx: commands.Context, confirmation: str = ""):
        """Permanently delete user's academy account and all data."""
        await ctx.defer()

        try:
            # Require strict confirmation to prevent accidental deletions
            if confirmation.lower() != "delete forever":
                embed = discord.Embed(
                    title="💀 PERMANENT ACCOUNT DELETION",
                    description=(
                        "**🚨 DANGER: This will PERMANENTLY DELETE your entire academy account! 🚨**\n\n"
                        "**This action will:**\n"
                        "• 💀 **PERMANENTLY DELETE** your account\n"
                        "• 🗂️ **ERASE ALL** waifus in your collection\n"
                        "• 💬 **DELETE ALL** conversations and memories\n"
                        "• 🏆 **REMOVE ALL** mission progress\n"
                        "• 📊 **DESTROY ALL** statistics and data\n\n"
                        "**⚠️ THIS CANNOT BE UNDONE! ⚠️**\n\n"
                        "**To confirm PERMANENT DELETION, use:**\n"
                        "`/nwnl_delete_account confirmation:delete forever`"
                    ),
                    color=0x8B0000,  # Dark red
                )
                embed.set_footer(text="⚠️ PERMANENT DELETION - CANNOT BE UNDONE! ⚠️")
                await ctx.send(embed=embed)
                return

            # Get current user stats before deletion
            stats = await self.services.waifu_service.get_user_stats(str(ctx.author.id))

            # Perform the deletion
            success = await self.services.waifu_service.db.delete_user_account(
                str(ctx.author.id)
            )

            if success:
                embed = discord.Embed(
                    title="💀 Account Permanently Deleted",
                    description=(
                        f"**{ctx.author.display_name}'s academy has been permanently deleted.**\n\n"
                        "**Final Statistics:**\n"
                        f"• Total Waifus: {stats['total_waifus']} (Unique: {stats['unique_waifus']})\n"
                        f"• Collection Power: {stats['collection_power']}\n"
                        f"• Academy Rank: {stats['user']['collector_rank']}\n"
                        f"• Final Crystals: {stats['user']['sakura_crystals']}\n\n"
                        "**All data has been permanently erased.**\n\n"
                        "Thank you for playing Waifu Academy. 👋\n"
                        "Use `/nwnl_summon` if you ever want to start a new academy."
                    ),
                    color=0x2C2F33,  # Dark gray
                )
                embed.set_footer(text="Account permanently deleted - all data erased.")
            else:
                embed = discord.Embed(
                    title="❌ Deletion Failed",
                    description="Unable to delete your academy. You may not have an existing account.",
                    color=0xFF6B6B,
                )

            await ctx.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error deleting user account: {e}")
            embed = discord.Embed(
                title="❌ Deletion Error",
                description="Something went wrong during the deletion process. Please try again later!",
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
