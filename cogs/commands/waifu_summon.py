"""New waifu summon command with star upgrade system."""

import discord
from discord.ext import commands
from typing import Optional
from cogs.base_command import BaseCommand
from services.container import ServiceContainer


class WaifuSummonCog(BaseCommand):
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

    @commands.hybrid_command(
        name="nwnl_summon",
        description="🎰 Summon waifus using Sakura Crystals with NEW star system! (10 crystals per summon)",
    )
    async def nwnl_summon(self, ctx: commands.Context):
        """Perform a waifu summon with the new star upgrade system."""
        await ctx.defer()

        try:
            # Perform the summon using the new service
            result = await self.services.waifu_service.perform_summon(str(ctx.author.id))

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
            summon_result = result

            # Rarity colors and emojis (now only 1-3 stars from gacha)
            rarity_config = {
                3: {"color": 0x4169E1, "emoji": "⭐⭐⭐", "name": "Rare"},
                2: {"color": 0x32CD32, "emoji": "⭐⭐", "name": "Common"},
                1: {"color": 0x808080, "emoji": "⭐", "name": "Basic"},
            }

            config = rarity_config[rarity]

            embed = discord.Embed(
                title="🎊 Summoning Results! 🎊", color=config["color"]
            )

            # Add NEW or DUPLICATE indicator with star info
            if summon_result["is_new"]:
                embed.add_field(
                    name="🆕 NEW WAIFU!",
                    value=f"**{waifu['name']}** has joined your academy at {summon_result['current_star_level']}★!",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="🌟 Duplicate Summon!",
                    value=f"**{waifu['name']}** gained {summon_result['shards_gained']} shards!",
                    inline=False,
                )

            # Show automatic upgrades if any occurred
            if summon_result.get("upgrades_performed"):
                upgrade_text = []
                for upgrade in summon_result["upgrades_performed"]:
                    upgrade_text.append(f"🔥 {upgrade['from_star']}★ → {upgrade['to_star']}★")
                
                embed.add_field(
                    name="⬆️ AUTOMATIC UPGRADES!",
                    value="\n".join(upgrade_text),
                    inline=False,
                )

            # Character details
            embed.add_field(name="Character", value=f"**{waifu['name']}**", inline=True)
            embed.add_field(name="Series", value=waifu.get("series", "Unknown"), inline=True)
            embed.add_field(
                name="Current Star Level",
                value=f"{'⭐' * summon_result['current_star_level']} ({summon_result['current_star_level']}★)",
                inline=True,
            )

            embed.add_field(
                name="Pull Rarity", 
                value=f"{config['emoji']} {config['name']}", 
                inline=True
            )
            
            # Show shard info for duplicates
            if not summon_result["is_new"]:
                embed.add_field(
                    name="Star Shards",
                    value=f"💫 {summon_result['total_shards']}",
                    inline=True,
                )

            embed.add_field(
                name="Crystals Left",
                value=f"💎 {result['crystals_remaining']}",
                inline=True,
            )

            # Show quartz gained if any
            if summon_result.get("quartz_gained", 0) > 0:
                embed.add_field(
                    name="Quartz Gained",
                    value=f"💠 +{summon_result['quartz_gained']} (from excess shards)",
                    inline=True,
                )

            # Add image if available
            if waifu.get("image_url"):
                embed.set_image(url=waifu["image_url"])

            embed.set_footer(
                text=f"Use /nwnl_collection to view your academy! • Summoned by {ctx.author.display_name}"
            )

            # Add special animation for upgrades
            content = ""
            if summon_result.get("upgrades_performed"):
                content = "🔥✨ **AUTO UPGRADE!** ✨🔥"
            elif rarity >= 3:
                content = "✨🎆 **RARE SUMMON!** 🎆✨"

            await ctx.send(content=content, embed=embed)

            # Log the result
            status_text = "NEW" if summon_result['is_new'] else f"+{summon_result['shards_gained']} shards"
            self.logger.info(
                f"User {ctx.author} summoned {waifu['name']} ({rarity}⭐ pull) "
                f"{status_text} Current: {summon_result['current_star_level']}⭐"
            )

        except Exception as e:
            self.logger.error(f"Error in star summon: {e}")
            embed = discord.Embed(
                title="❌ Summon Error",
                description="Something went wrong during summoning. Please try again later!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="nwnl_multi_summon",
        description="🎰🎊 Perform 10 summons with NEW star system! (100 crystals total)",
    )
    async def nwnl_multi_summon(self, ctx: commands.Context):
        """Perform 10 waifu summons with the new star upgrade system."""
        await ctx.defer()

        try:
            # Perform the multi-summon (always 10 rolls)
            result = await self.services.waifu_service.perform_multi_summon(str(ctx.author.id))

            if not result["success"]:
                embed = discord.Embed(
                    title="❌ Multi-Summon Failed",
                    description=result["message"],
                    color=0xFF6B6B,
                )
                await ctx.send(embed=embed)
                return

            # Rarity colors and emojis
            rarity_config = {
                3: {"color": 0x4169E1, "emoji": "⭐⭐⭐", "name": "Rare"},
                2: {"color": 0x32CD32, "emoji": "⭐⭐", "name": "Common"},
                1: {"color": 0x808080, "emoji": "⭐", "name": "Basic"},
            }

            # Create main embed
            embed = discord.Embed(
                title="🎊 Multi-Summon Results! 🎊",
                description=f"Summoned {result['count']} characters!",
                color=0x4169E1,
            )

            # Rarity breakdown
            rarity_counts = result["rarity_counts"]
            rarity_text = []
            for rarity in [3, 2, 1]:
                count = rarity_counts.get(rarity, 0)
                if count > 0:
                    config = rarity_config[rarity]
                    rarity_text.append(f"{config['emoji']} {config['name']}: {count}")

            embed.add_field(
                name="📊 Rarity Breakdown",
                value="\n".join(rarity_text) if rarity_text else "No results",
                inline=True,
            )

            # New waifus
            new_waifus = result["new_waifus"]
            if new_waifus:
                new_names = [w["name"] for w in new_waifus[:5]]  # Show up to 5
                if len(new_waifus) > 5:
                    new_names.append(f"...and {len(new_waifus) - 5} more!")
                
                embed.add_field(
                    name=f"🆕 New Characters ({len(new_waifus)})",
                    value="\n".join(new_names),
                    inline=True,
                )

            # Shard summary
            shard_summary = result.get("shard_summary", {})
            if shard_summary:
                shard_text = []
                for char_name, shards in list(shard_summary.items())[:3]:  # Show top 3
                    shard_text.append(f"💫 {char_name}: +{shards}")
                if len(shard_summary) > 3:
                    shard_text.append(f"...and {len(shard_summary) - 3} more!")
                
                embed.add_field(
                    name="💫 Shard Gains",
                    value="\n".join(shard_text),
                    inline=True,
                )

            # Upgrade summary
            upgrade_summary = result.get("upgrade_summary", [])
            if upgrade_summary:
                upgrade_text = upgrade_summary[:5]  # Show up to 5 upgrades
                if len(upgrade_summary) > 5:
                    upgrade_text.append(f"...and {len(upgrade_summary) - 5} more!")
                
                embed.add_field(
                    name="⬆️ AUTO UPGRADES!",
                    value="\n".join(upgrade_text),
                    inline=False,
                )

            # Summary
            embed.add_field(
                name="💎 Crystals Remaining",
                value=f"{result['crystals_remaining']}",
                inline=True,
            )
            embed.add_field(
                name="💰 Total Cost",
                value=f"{result['total_cost']} crystals",
                inline=True,
            )

            embed.set_footer(
                text=f"Use /nwnl_collection to view your academy! • Summoned by {ctx.author.display_name}"
            )

            # Add special content for upgrades
            content = ""
            if upgrade_summary:
                content = "🔥⬆️ **CHARACTERS UPGRADED!** ⬆️🔥"
            elif rarity_counts.get(3, 0) > 0:
                content = "✨🎆 **RARE SUMMONS!** 🎆✨"

            await ctx.send(content=content, embed=embed)

            self.logger.info(
                f"User {ctx.author} performed multi-summon: "
                f"{result['count']} summons, {len(new_waifus)} new, "
                f"{len(upgrade_summary)} auto-upgrades"
            )

        except Exception as e:
            self.logger.error(f"Error in star multi-summon: {e}")
            embed = discord.Embed(
                title="❌ Multi-Summon Error",
                description="Something went wrong during multi-summoning. Please try again later!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="nwnl_collection", description="📚 View your waifu academy collection with star levels"
    )
    async def nwnl_collection(self, ctx: commands.Context, user: Optional[discord.Member] = None):
        """Display user's waifu collection with new star system."""
        await ctx.defer()

        target_user = user if user is not None else ctx.author

        try:
            # Get user's collection from database
            collection = await self.services.database.get_user_collection(str(target_user.id))

            if not collection:
                embed = discord.Embed(
                    title="🏫 Empty Academy",
                    description=f"{'You have' if target_user == ctx.author else f'{target_user.display_name} has'} no waifus yet!\nUse `/nwnl_summon` to start your collection!",
                    color=0x95A5A6,
                )
                await ctx.send(embed=embed)
                return

            # Get user data
            user_data = await self.services.database.get_or_create_user(str(target_user.id))

            # Create collection embed
            embed = discord.Embed(
                title=f"🏫 {target_user.display_name}'s Waifu Academy",
                description=f"**Academy Name:** {user_data.get('academy_name', 'Unknown Academy')}\n"
                f"**Total Waifus:** {len(collection)}",
                color=0x3498DB,
            )

            # Add rarity distribution (showing current star levels)
            rarity_dist = {}
            upgradeable_count = 0
            total_shards = 0
            
            for waifu in collection:
                current_star = waifu.get("current_star_level", waifu["rarity"])
                rarity_dist[current_star] = rarity_dist.get(current_star, 0) + 1
                
                # Check if upgradeable
                shards = waifu.get("character_shards", 0)
                if current_star < 5:
                    required = {2: 50, 3: 100, 4: 200, 5: 300}.get(current_star + 1, 999)
                    if shards >= required:
                        upgradeable_count += 1
                total_shards += shards

            rarity_text = ""
            for star_level in sorted(rarity_dist.keys(), reverse=True):
                count = rarity_dist[star_level]
                stars = "⭐" * star_level
                rarity_text += f"{stars}: {count}\n"

            if rarity_text:
                embed.add_field(
                    name="🌟 Star Level Distribution", value=rarity_text, inline=True
                )

            # Add resources
            embed.add_field(
                name="💎 Resources",
                value=f"Sakura Crystals: {user_data.get('sakura_crystals', 0)}\n"
                f"Total Shards: {total_shards}\n"
                f"Quartz: {user_data.get('quartzs', 0)}",
                inline=True,
            )

            # Show highest star characters (top 5)
            sorted_collection = sorted(collection, key=lambda w: w.get("current_star_level", w["rarity"]), reverse=True)
            top_waifus = sorted_collection[:5]
            top_text = ""
            for waifu in top_waifus:
                current_star = waifu.get("current_star_level", waifu["rarity"])
                stars = "⭐" * current_star
                shards = waifu.get("character_shards", 0)
                top_text += f"{stars} **{waifu['name']}** ({waifu['series']})"
                if shards > 0:
                    top_text += f" - {shards} shards"
                # Check if can upgrade
                if current_star < 5:
                    required = {2: 50, 3: 100, 4: 200, 5: 300}.get(current_star + 1, 999)
                    if shards >= required:
                        top_text += f" 🔥"
                top_text += "\n"

            if top_text:
                embed.add_field(
                    name="✨ Highest Star Characters", value=top_text, inline=False
                )

            # Show upgradeable summary
            if upgradeable_count > 0:
                embed.add_field(
                    name="🔥 Ready to Upgrade",
                    value=f"{upgradeable_count} characters ready to upgrade!\nPull duplicates to upgrade automatically!",
                    inline=False,
                )

            embed.set_footer(
                text=f"Use /nwnl_profile <name> to view details • Total Shards: {total_shards}"
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
        name="nwnl_profile", description="👤 View detailed profile of a waifu with star information"
    )
    async def nwnl_profile(self, ctx: commands.Context, *, waifu_name: str):
        """Display detailed waifu profile with star system information."""
        await ctx.defer()

        try:
            # Search for the waifu
            search_results = await self.services.database.search_waifus(waifu_name, 5)

            if not search_results:
                embed = discord.Embed(
                    title="❌ Waifu Not Found",
                    description=f"No waifu found matching '{waifu_name}'. Try a different name or check spelling!",
                    color=0xFF6B6B,
                )
                await ctx.send(embed=embed)
                return

            # Use the first result
            waifu = search_results[0]

            # Check if user owns this waifu
            collection = await self.services.database.get_user_collection(str(ctx.author.id))
            user_waifu = next((w for w in collection if w["waifu_id"] == waifu["id"]), None)

            # Create profile embed
            rarity_colors = {
                5: 0xFFD700,
                4: 0x9932CC,
                3: 0x4169E1,
                2: 0x32CD32,
                1: 0x808080,
            }

            current_star = user_waifu.get("current_star_level", waifu["rarity"]) if user_waifu else waifu["rarity"]
            embed = discord.Embed(
                title=f"👤 {waifu['name']}",
                description=waifu.get("personality_profile", "A mysterious character..."),
                color=rarity_colors.get(current_star, 0x95A5A6),
            )

            # Basic info
            embed.add_field(name="🎭 Series", value=waifu["series"], inline=True)
            embed.add_field(name="🏷️ Genre", value=waifu.get("genre", "Unknown"), inline=True)
            embed.add_field(name="🔮 Element", value=waifu.get("element", "Unknown"), inline=True)
            embed.add_field(name="⭐ Base Rarity", value="⭐" * waifu["rarity"], inline=True)

            # User-specific info if owned
            if user_waifu:
                current_star = user_waifu.get("current_star_level", waifu["rarity"])
                shards = user_waifu.get("character_shards", 0)
                is_max_star = current_star >= 5

                star_info = f"**Current Star Level:** {'⭐' * current_star} ({current_star}★)\n"
                star_info += f"**Star Shards:** {shards}"
                
                if is_max_star:
                    star_info += " (MAX STAR)"
                else:
                    next_star = current_star + 1
                    required = {2: 50, 3: 100, 4: 200, 5: 300}.get(next_star, 999)
                    star_info += f"/{required} (for {next_star}★)"
                    if shards >= required:
                        star_info += " 🔥 READY!"
                
                embed.add_field(
                    name="🌟 Star Progress",
                    value=star_info,
                    inline=True,
                )

                embed.add_field(
                    name="💖 Your Bond",
                    value=f"**Bond Level:** {user_waifu.get('bond_level', 1)}\n"
                    f"**Mood:** {user_waifu.get('current_mood', 'happy').title()}\n"
                    f"**Conversations:** {user_waifu.get('total_conversations', 0)}",
                    inline=True,
                )

                if user_waifu.get("custom_nickname"):
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
