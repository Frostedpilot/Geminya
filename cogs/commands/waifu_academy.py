"""Waifu Academy management commands."""

import discord
from discord.ext import commands
from cogs.base_command import BaseCommand
from services.container import ServiceContainer

from typing import Optional


class WaifuAcademyCog(BaseCommand):

    @commands.hybrid_command(
        name="nwnl_collection_search",
        description="🔍 Search your waifu collection by anime, genre, archetype, or element. Shows elements and archetype."
    )
    async def nwnl_collection_search(
        self,
        ctx: commands.Context,
        anime_id: Optional[int] = None,
        genre: Optional[str] = None,
        archetype: Optional[str] = None,
        element: Optional[str] = None
    ):
        """Search and filter your waifu collection. Paginate 5 per page. Shows elements and archetype."""
        await ctx.defer()
        try:
            collection = await self.services.waifu_service.get_user_collection_with_stars(str(ctx.author.id))
            if not collection:
                embed = discord.Embed(
                    title="🏫 Empty Academy",
                    description="You have no waifus yet! Use `/nwnl_summon` to start your collection!",
                    color=0x95A5A6,
                )
                await ctx.send(embed=embed)
                return

            # Filtering
            filtered = collection
            if anime_id is not None:
                filtered = [w for w in filtered if w.get("series_id") == anime_id]
            # Robust genre filtering using get_series_genres
            if genre is not None:
                genre_lower = genre.lower()
                # Only use waifus with int series_id
                series_ids = set(int(w["series_id"]) for w in filtered if isinstance(w.get("series_id"), int))
                # Map series_id to genres (cache to avoid repeated DB calls)
                series_genre_map = {}
                for sid in series_ids:
                    try:
                        genres = await self.services.waifu_service.get_series_genres(sid)
                        series_genre_map[sid] = [g.lower() for g in genres]
                    except Exception:
                        series_genre_map[sid] = []
                filtered = [w for w in filtered if isinstance(w.get("series_id"), int) and w.get("series_id") in series_genre_map and genre_lower in series_genre_map[w.get("series_id")]]
            if archetype is not None:
                filtered = [w for w in filtered if isinstance(w.get("archetype"), str) and archetype.lower() in w["archetype"].lower()]
            if element is not None:
                def element_matches(w):
                    etype = w.get("elemental_type")
                    if isinstance(etype, str):
                        return element.lower() in etype.lower()
                    elif isinstance(etype, list):
                        return any(element.lower() in str(e).lower() for e in etype)
                    return False
                filtered = [w for w in filtered if element_matches(w)]

            # Sort by star level (desc), then name
            sorted_collection = sorted(filtered, key=lambda w: (-w.get("current_star_level", w["rarity"]), -w["character_shards"], w["name"]))

            class SearchPaginator(discord.ui.View):
                def __init__(self, ctx, waifus):
                    super().__init__(timeout=180)
                    self.ctx = ctx
                    self.waifus = waifus
                    self.page_idx = 0
                    self.page_size = 5
                    self.page_count = max(1, (len(waifus) + self.page_size - 1) // self.page_size)

                def get_embed(self):
                    start = self.page_idx * self.page_size
                    end = start + self.page_size
                    waifu_page = self.waifus[start:end]
                    title = f"🔍 {self.ctx.author.display_name}'s Waifu Search Results"
                    embed = discord.Embed(
                        title=title,
                        description=f"Page {self.page_idx+1}/{self.page_count} • Total: {len(self.waifus)} waifus",
                        color=0x8E44AD,
                    )
                    if waifu_page:
                        for w in waifu_page:
                            stars = "⭐" * w.get("current_star_level", w["rarity"])
                            shards = w.get("character_shards", 0)
                            # Element display: join list or show string
                            etype = w.get("elemental_type")
                            if isinstance(etype, list):
                                elements = ", ".join(str(e) for e in etype) if etype else "?"
                            else:
                                elements = etype if etype else "?"
                            # Archetype display: always show string or "?"
                            archetype_val = w.get("archetype")
                            archetype = archetype_val if isinstance(archetype_val, str) and archetype_val.strip() else "?"
                            value = f"{stars} | {w['series']} | {shards} shards\n**Element:** {elements}\n**Archetype:** {archetype}"
                            embed.add_field(
                                name=w["name"],
                                value=value,
                                inline=False
                            )
                    else:
                        embed.add_field(name="No Characters", value="This page is empty.", inline=False)
                    embed.set_footer(text=f"Use buttons to navigate • Page {self.page_idx+1}/{self.page_count}")
                    return embed

                async def interaction_check(self, interaction: discord.Interaction) -> bool:
                    return interaction.user == self.ctx.author

                @discord.ui.button(label="⬅️ Prev", style=discord.ButtonStyle.primary, row=0)
                async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.page_idx = (self.page_idx - 1) % self.page_count
                    await interaction.response.edit_message(embed=self.get_embed(), view=self)

                @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.primary, row=0)
                async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.page_idx = (self.page_idx + 1) % self.page_count
                    await interaction.response.edit_message(embed=self.get_embed(), view=self)

            if not sorted_collection:
                embed = discord.Embed(
                    title="🔍 No Results",
                    description="No waifus matched your search criteria.",
                    color=0x95A5A6,
                )
                await ctx.send(embed=embed)
                return

            view = SearchPaginator(ctx, sorted_collection)
            await ctx.send(embed=view.get_embed(), view=view)
        except Exception as e:
            self.logger.error(f"Error in collection search: {e}")
            embed = discord.Embed(
                title="❌ Search Error",
                description="Unable to search your collection. Please try again later!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)
    @commands.hybrid_command(
        name="nwnl_missions",
        description="📅 View all daily missions and your progress"
    )
    async def nwnl_missions(self, ctx: commands.Context):
        """Show all daily missions and if the user has completed them."""
        await ctx.defer()
        try:
            db = self.services.waifu_service.db
            discord_id = str(ctx.author.id)
            from datetime import datetime, timezone
            import pytz
            tz = pytz.timezone('Asia/Bangkok')
            now_utc = datetime.now(timezone.utc)
            now_local = now_utc.astimezone(tz)
            today = now_local.date()

            # Fetch all active daily missions
            missions = await db.get_all_active_daily_missions()
            if not missions:
                embed = discord.Embed(
                    title="No Daily Missions",
                    description="There are currently no active daily missions.",
                    color=0xF39C12,
                )
                await ctx.send(embed=embed)
                return

            # Fetch all user mission progress for today
            progress_rows = await db.get_all_user_mission_progress_for_date(discord_id, today)
            progress_map = {row["mission_id"]: row for row in progress_rows}

            embed = discord.Embed(
                title="📅 Daily Missions",
                description=f"Here are your daily missions for today:",
                color=0x3498DB,
            )

            for mission in missions:
                mission_id = mission["id"]
                name = mission["name"]
                desc = mission["description"]
                target = mission["target_count"]
                reward = f"{mission['reward_amount']} {mission['reward_type']}"
                progress = progress_map.get(mission_id)
                if progress:
                    current = progress["current_progress"]
                    completed = progress["completed"]
                    claimed = progress["claimed"]
                else:
                    current = 0
                    completed = False
                    claimed = False

                # Status emoji
                if claimed:
                    status = "✅ Claimed"
                elif completed:
                    status = "🎁 Claimable"
                else:
                    status = f"❌ {current}/{target}"

                embed.add_field(
                    name=f"{name} [{status}]",
                    value=f"{desc}\n**Reward:** {reward}",
                    inline=False,
                )

            embed.set_footer(text="Complete missions to earn rewards! Claim in the relevant game or mission command.")
            await ctx.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Error displaying missions: {e}")
            embed = discord.Embed(
                title="❌ Mission Error",
                description="Unable to display missions. Please try again later!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

    @commands.hybrid_command(
        name="nwnl_status", description="📊 Check your academy status and statistics"
    )
    async def nwnl_status(self, ctx: commands.Context):
        """Display user's academy status."""
        await ctx.defer()
        return await self.queue_command(ctx, self._nwnl_status_impl)

    async def _nwnl_status_impl(self, ctx: commands.Context):
        """Implementation of nwnl_status command."""
        try:
            # Check and perform automatic rank ups FIRST
            await self.services.waifu_service.check_and_update_rank(str(ctx.author.id))
            
            # Then get the updated stats
            stats = await self.services.waifu_service.get_user_stats(str(ctx.author.id))
            user = stats["user"]

            embed = discord.Embed(
                title=f"🏫 {ctx.author.display_name}'s Academy Status", color=0x3498DB
            )

            # Academy Info
            # Handle timestamp conversion for created_at field
            created_at_timestamp = 0
            try:
                from datetime import datetime
                
                created_at = user.get("created_at")
                if created_at:
                    if isinstance(created_at, str):
                        # Parse string timestamp
                        created_at_dt = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00").replace(" ", "T")
                        )
                        created_at_timestamp = int(created_at_dt.timestamp())
                    else:
                        # Assume it's already a timestamp or datetime object
                        if hasattr(created_at, 'timestamp'):
                            created_at_timestamp = int(created_at.timestamp())
                        else:
                            created_at_timestamp = int(created_at)
            except (ValueError, TypeError, AttributeError):
                created_at_timestamp = 0

            academy_name = user.get('academy_name') or f"{ctx.author.display_name}'s Academy"
            
            embed.add_field(
                name="🏛️ Academy Details",
                value=f"**Name:** {academy_name}\n"
                f"**Rank:** Level {user['collector_rank']}\n"
                f"**Founded:** <t:{created_at_timestamp}:R>",
                inline=True,
            )

            # Resources
            sakura_crystals = user.get('sakura_crystals', 0)
            quartzs = user.get('quartzs', 0)
            pity_counter = user.get('pity_counter', 0)
            
            # Calculate pity information based on actual gacha system
            # Only 3⭐ has pity (guaranteed at 50 pulls)
            # 2⭐ is only guaranteed on 10th roll of multi-summon, not regular pity
            guaranteed_3star = max(0, 50 - pity_counter)
            
            embed.add_field(
                name="💎 Resources",
                value=f"**Sakura Crystals:** {sakura_crystals:,}\n"
                f"**Quartzs:** 💠 {quartzs:,}\n"
                f"**Pity Counter:** {pity_counter}/50\n"
                f"**Next 3⭐ in:** {guaranteed_3star} pulls",
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

            # Star level distribution (updated for new star system)
            rarity_dist = stats["rarity_distribution"]
            if rarity_dist:
                rarity_text = ""
                # Sort by star level (highest first)
                for star_level in sorted(rarity_dist.keys(), reverse=True):
                    count = rarity_dist[star_level]
                    if star_level > 5:
                        # 6+ stars get special formatting
                        rarity_text += f"🌟 {star_level}⭐: {count}\n"
                    else:
                        stars = "⭐" * star_level
                        rarity_text += f"{stars}: {count}\n"

                embed.add_field(
                    name="🌟 Star Distribution", value=rarity_text.strip(), inline=True
                )

            # Calculate rank progression (stats are already updated from the rank check above)
            current_rank = user["collector_rank"]
            current_power = stats["collection_power"]
            current_waifus = stats["total_waifus"]
            
            # Exponential progression: rank 1->2 needs 2000, 2->3 needs 4000, 3->4 needs 8000, etc.
            next_rank_power_req = 1000 * (2 ** current_rank)  # Exponential power growth
            next_rank_waifu_req = 5 * current_rank             # Linear waifu growth
            
            # Show normal progress to next rank
            power_progress = min(current_power, next_rank_power_req)
            waifu_progress = min(current_waifus, next_rank_waifu_req)
            
            # Overall progress is the minimum of both requirements
            power_percent = power_progress / next_rank_power_req if next_rank_power_req > 0 else 1
            waifu_percent = waifu_progress / next_rank_waifu_req if next_rank_waifu_req > 0 else 1
            overall_percent = min(power_percent, waifu_percent)
            
            progress_bar = self._create_progress_bar(int(overall_percent * 100), 100)
            
            rank_text = f"{progress_bar}\n"
            rank_text += f"**Power:** {current_power:,}/{next_rank_power_req:,}\n"
            rank_text += f"**Waifus:** {current_waifus}/{next_rank_waifu_req}"
            
            embed.add_field(
                name="📈 Rank Progress",
                value=rank_text,
                inline=False,
            )

            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            
            # Updated footer with more relevant commands
            footer_text = "Use /nwnl_summon to grow your academy • /nwnl_collection to view waifus"
            embed.set_footer(text=footer_text)

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
        return await self.queue_command(ctx, self._nwnl_rename_academy_impl, new_name)

    async def _nwnl_rename_academy_impl(self, ctx: commands.Context, new_name: str):
        """Implementation of nwnl_rename_academy command."""
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

            from datetime import datetime, timezone, timedelta
            import pytz

            # Set timezone for UTC+7
            tz = pytz.timezone('Asia/Bangkok')
            now_utc = datetime.now(timezone.utc)
            now_local = now_utc.astimezone(tz)
            current_timestamp = int(now_utc.timestamp())

            # Get the last daily reset timestamp
            last_daily_reset = user.get("last_daily_reset", 0)

            # Calculate the last and next reset times at 0h UTC+7
            if last_daily_reset > 0:
                last_reset_dt_utc = datetime.fromtimestamp(last_daily_reset, tz=timezone.utc)
                last_reset_local = last_reset_dt_utc.astimezone(tz)
                # The last reset's 0h UTC+7
                last_reset_zero = last_reset_local.replace(hour=0, minute=0, second=0, microsecond=0)
                if last_reset_local.hour >= 0:
                    # If last claim was after 0h, next reset is next day 0h
                    next_reset_local = last_reset_zero + timedelta(days=1)
                else:
                    next_reset_local = last_reset_zero
                next_reset_utc = next_reset_local.astimezone(timezone.utc)
                next_reset_ts = int(next_reset_utc.timestamp())
            else:
                # Never claimed before, allow claim
                next_reset_ts = 0

            if last_daily_reset > 0 and current_timestamp < next_reset_ts:
                # Not yet time for next reset
                seconds_left = next_reset_ts - current_timestamp
                hours_left = int(seconds_left // 3600)
                minutes_left = int((seconds_left % 3600) // 60)
                embed = discord.Embed(
                    title="⏰ Daily Reward Already Claimed",
                    description=f"You've already claimed your daily rewards today!",
                    color=0xF39C12,
                )
                embed.add_field(
                    name="⏳ Time Until Next Claim",
                    value=f"{hours_left}h {minutes_left}m",
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

            # Set the reset timestamp to now (UTC)
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
                value="Available after 0:00 UTC+7",
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
