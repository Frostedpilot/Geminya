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
        return await self.queue_command(ctx, self._nwnl_summon_impl)

    async def _nwnl_summon_impl(self, ctx: commands.Context):
        """Implementation of nwnl_summon command."""
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

            # Rarity colors and emojis (3★ = old 5★ Legendary, 2★ = old 4★ Epic, 1★ = old 1★ Basic)
            rarity_config = {
                3: {"color": 0xFFD700, "emoji": "⭐⭐⭐", "name": "Legendary"},  # Gold like old 5★
                2: {"color": 0x9932CC, "emoji": "⭐⭐", "name": "Epic"},        # Purple like old 4★
                1: {"color": 0x808080, "emoji": "⭐", "name": "Basic"},         # Gray like old 1★
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
                # Different message based on whether character is maxed or not
                if summon_result.get("quartz_gained", 0) > 0 and summon_result.get("shards_gained", 0) == 0:
                    # Character is already maxed (5⭐), shards converted to quartz
                    embed.add_field(
                        name="🌟 Max Level Duplicate!",
                        value=f"**{waifu['name']}** is already 5⭐! Converted to {summon_result['quartz_gained']} quartz!",
                        inline=False,
                    )
                else:
                    # Normal duplicate with shards
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

            # Add special animation for high rarity like the old system
            content = ""
            if summon_result.get("upgrades_performed"):
                content = "🔥✨ **AUTO UPGRADE!** ✨🔥"
            elif rarity == 3:  # 3★ = old 5★ Legendary
                content = "🌟💫 **LEGENDARY SUMMON!** 💫🌟"
            elif rarity == 2:  # 2★ = old 4★ Epic  
                content = "✨🎆 **EPIC SUMMON!** 🎆✨"

            await ctx.send(content=content, embed=embed)

            # Log the result
            if summon_result['is_new']:
                status_text = "NEW"
            elif summon_result.get("quartz_gained", 0) > 0 and summon_result.get("shards_gained", 0) == 0:
                status_text = f"+{summon_result['quartz_gained']} quartz (maxed)"
            else:
                status_text = f"+{summon_result['shards_gained']} shards"
                
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

            # Rarity colors and emojis (3★ = old 5★ Legendary, 2★ = old 4★ Epic, 1★ = old 1★ Basic)
            rarity_config = {
                3: {"color": 0xFFD700, "emoji": "⭐⭐⭐", "name": "Legendary"},  # Gold like old 5★
                2: {"color": 0x9932CC, "emoji": "⭐⭐", "name": "Epic"},        # Purple like old 4★
                1: {"color": 0x808080, "emoji": "⭐", "name": "Basic"},         # Gray like old 1★
            }

            # Separate high-rarity (2★+) and low-rarity (1★) pulls like the old system
            embeds = []
            special_content_parts = []
            low_rarity_pulls = []
            high_rarity_count = 0

            for i, summon_result in enumerate(result["results"]):
                waifu = summon_result["waifu"]
                rarity = summon_result["rarity"]
                config = rarity_config[rarity]

                if rarity >= 2:  # 2★+ gets full embed (like old 4★+ system)
                    high_rarity_count += 1
                    # Create individual summon embed
                    embed = discord.Embed(
                        title=f"🎊 Summon #{i+1} - {config['name']} Pull! 🎊",
                        color=config["color"],
                    )

                    # Add NEW or DUPLICATE indicator with star info
                    if summon_result["is_new"]:
                        embed.add_field(
                            name="🆕 NEW WAIFU!",
                            value=f"**{waifu['name']}** has joined your academy at {summon_result['current_star_level']}★!",
                            inline=False,
                        )
                    else:
                        # Different message based on whether character is maxed or not
                        if summon_result.get("quartz_gained", 0) > 0 and summon_result.get("shards_gained", 0) == 0:
                            # Character is already maxed (5⭐), shards converted to quartz
                            embed.add_field(
                                name="🌟 Max Level Duplicate!",
                                value=f"**{waifu['name']}** is already 5⭐! Converted to {summon_result['quartz_gained']} quartz!",
                                inline=False,
                            )
                        else:
                            # Normal duplicate with shards
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
                    embed.add_field(
                        name="Character", value=f"**{waifu['name']}**", inline=True
                    )
                    embed.add_field(name="Series", value=waifu.get("series", "Unknown"), inline=True)
                    embed.add_field(
                        name="Element",
                        value=f"{waifu.get('element', 'Unknown')} 🔮",
                        inline=True,
                    )
                    embed.add_field(
                        name="Current Stars",
                        value=f"{'⭐' * summon_result['current_star_level']} ({summon_result['current_star_level']}★)",
                        inline=True,
                    )
                    embed.add_field(
                        name="Pull Rarity",
                        value=f"{config['emoji']} {config['name']}",
                        inline=True,
                    )

                    # Add image if available (for 2★ and above like old system)
                    if waifu.get("image_url"):
                        embed.set_image(url=waifu["image_url"])

                    embeds.append(embed)

                    # Collect special messages for high rarity pulls like old system
                    if rarity == 3:  # 3★ = old 5★ Legendary
                        special_content_parts.append(
                            f"🌟💫✨ **LEGENDARY PULL!** ✨💫🌟\n"
                            f"🎆🎇 **{waifu['name']}** 🎇🎆\n"
                            f"💎 The stars have aligned! A legendary waifu graces your academy! 💎"
                        )
                    elif rarity == 2:  # 2★ = old 4★ Epic
                        special_content_parts.append(
                            f"✨🎆 **EPIC PULL!** 🎆✨\n"
                            f"🌟 **{waifu['name']}** 🌟\n"
                            f"🎉 An epic waifu has answered your call! 🎉"
                        )
                else:  # 1★ goes to summary like old system
                    if summon_result["is_new"]:
                        status = "🆕 NEW"
                    elif summon_result.get("quartz_gained", 0) > 0 and summon_result.get("shards_gained", 0) == 0:
                        status = f"💠 +{summon_result['quartz_gained']} quartz (maxed)"
                    else:
                        status = f"💫 +{summon_result['shards_gained']} shards"
                    
                    low_rarity_pulls.append(
                        f"**#{i+1}** {config['emoji']} **{waifu['name']}** ({waifu.get('series', 'Unknown')}) - {status}"
                    )

            # Create summary embed for low-rarity pulls if any (like old system)
            if low_rarity_pulls:
                summary_embed = discord.Embed(
                    title="📋 Other Summons Summary",
                    description="\n".join(low_rarity_pulls),
                    color=0x95A5A6,
                )
                embeds.append(summary_embed)

            # Rarity breakdown
            rarity_counts = result["rarity_counts"]
            rarity_text = []
            for rarity in [3, 2, 1]:
                count = rarity_counts.get(rarity, 0)
                if count > 0:
                    config = rarity_config[rarity]
                    rarity_text.append(f"{config['emoji']} {config['name']}: {count}")

            # Create final summary embed
            final_summary = discord.Embed(
                title="📊 Multi-Summon Summary",
                color=0x4A90E2,
            )
            
            final_summary.add_field(
                name="📊 Rarity Breakdown",
                value="\n".join(rarity_text) if rarity_text else "No results",
                inline=True,
            )

            # Display 2★ and 3★ characters individually, combine 1★ characters
            individual_results = result.get("results", [])
            
            # Separate characters by rarity
            three_star_chars = []
            two_star_chars = []
            one_star_count = 0
            
            for summon_result in individual_results:
                waifu = summon_result["waifu"]
                rarity = summon_result["rarity"]
                
                if rarity == 3:
                    star_display = "⭐⭐⭐"
                    upgrade_info = ""
                    if summon_result.get("upgrades_performed"):
                        upgrade_info = " ⬆️"
                    three_star_chars.append(f"{star_display} **{waifu['name']}**{upgrade_info}")
                elif rarity == 2:
                    star_display = "⭐⭐"
                    upgrade_info = ""
                    if summon_result.get("upgrades_performed"):
                        upgrade_info = " ⬆️"
                    two_star_chars.append(f"{star_display} **{waifu['name']}**{upgrade_info}")
                else:  # rarity == 1
                    one_star_count += 1

            # Add 3★ characters field if any
            if three_star_chars:
                final_summary.add_field(
                    name="✨ 3★ RARE Characters",
                    value="\n".join(three_star_chars),
                    inline=False,
                )

            # Add 2★ characters field if any
            if two_star_chars:
                final_summary.add_field(
                    name="🟣 2★ COMMON Characters", 
                    value="\n".join(two_star_chars),
                    inline=False,
                )

            # Add 1★ summary if any
            if one_star_count > 0:
                final_summary.add_field(
                    name="⭐ 1★ BASIC Characters",
                    value=f"Summoned {one_star_count} basic character{'s' if one_star_count > 1 else ''}",
                    inline=False,
                )

            # New waifus summary
            new_waifus = result.get("new_waifus", [])
            if new_waifus:
                new_names = [w["name"] for w in new_waifus[:5]]  # Show up to 5
                if len(new_waifus) > 5:
                    new_names.append(f"...and {len(new_waifus) - 5} more!")
                
                final_summary.add_field(
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
                
                final_summary.add_field(
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
                
                final_summary.add_field(
                    name="⬆️ AUTO UPGRADES!",
                    value="\n".join(upgrade_text),
                    inline=False,
                )

            # Summary
            final_summary.add_field(
                name="💎 Crystals Remaining",
                value=f"{result['crystals_remaining']}",
                inline=True,
            )
            final_summary.add_field(
                name="💰 Total Cost",
                value=f"{result['total_cost']} crystals",
                inline=True,
            )
            
            # Add the final summary to embeds
            embeds.append(final_summary)

            # Add footer to the last embed
            if embeds:
                embeds[-1].set_footer(
                    text=f"Multi-summon complete! Cost: {result['total_cost']} crystals • "
                    f"Remaining: {result['crystals_remaining']} crystals"
                )

            # Create special content message for high rarity pulls like old system
            special_content = ""
            if special_content_parts:
                special_content = "\n\n".join(special_content_parts)

                # Add overall celebration for multiple high rarity pulls like old system
                three_star_count = sum(1 for r in result["results"] if r["rarity"] == 3)
                two_star_count = sum(1 for r in result["results"] if r["rarity"] == 2)

                if three_star_count >= 2:  # Multiple 3★ = old multiple 5★
                    special_content = (
                        "🌟�⭐ **MIRACLE MULTI-SUMMON!** ⭐💫🌟\n"
                        f"🎆🎇✨ **{three_star_count} LEGENDARY WAIFUS!** ✨🎇🎆\n"
                        "�👑 The academy is blessed with divine fortune! 👑💎\n\n"
                        + special_content
                    )
                elif three_star_count == 1 and two_star_count >= 1:  # 3★ + 2★ = old 5★ + 4★
                    special_content = (
                        "🌟🎆  **INCREDIBLE MULTI-SUMMON!** 🎆🌟\n"
                        "✨ Perfect combination of Legendary and Epic! ✨\n\n"
                        + special_content
                    )

            # Send the embeds like old system (Discord supports up to 10 embeds per message)
            await ctx.send(content=special_content, embeds=embeds)

            # Log the multi-summon results like old system
            rarity_counts = result["rarity_counts"]
            self.logger.info(
                f"User {ctx.author} performed x{result['count']} multi-summon: "
                f"3★:{rarity_counts.get(3,0)}, 2★:{rarity_counts.get(2,0)}, "
                f"1★:{rarity_counts.get(1,0)}"
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

            # Create profile embed with updated star system colors
            rarity_colors = {
                5: 0xFF0000,  # Red for 5★ (Mythic)
                4: 0xFFD700,  # Gold for 4★ (Legendary) 
                3: 0x9932CC,  # Purple for 3★ (Epic)
                2: 0x4169E1,  # Blue for 2★ (Rare)
                1: 0x808080,  # Gray for 1★ (Common)
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
            
            # Add MAL ID if available
            if waifu.get("mal_id"):
                embed.add_field(name="🔗 MAL ID", value=str(waifu["mal_id"]), inline=True)
            
            # Add birthday if available  
            if waifu.get("birthday"):
                embed.add_field(name="🎂 Birthday", value=str(waifu["birthday"]), inline=True)

            # User-specific info if owned
            if user_waifu:
                current_star = user_waifu.get("current_star_level", waifu["rarity"])
                
                # Get shards from WaifuService (not database field)
                shards = await self.services.waifu_service.get_character_shards(str(ctx.author.id), waifu["id"])
                
                is_max_star = current_star >= 5  # Max 5★ system

                star_info = f"**Current Star Level:** {'⭐' * current_star} ({current_star}★)\n"
                star_info += f"**Star Shards:** {shards:,}"
                
                if is_max_star:
                    star_info += " (MAX STAR - converts to quartz)"
                else:
                    next_star = current_star + 1
                    # Updated costs: 2=50, 3=100, 4=150, 5=200
                    upgrade_costs = {2: 50, 3: 100, 4: 150, 5: 200}
                    required = upgrade_costs.get(next_star, 999)
                    star_info += f"/{required:,} (for {next_star}★)"
                    if shards >= required:
                        star_info += " 🔥 READY TO UPGRADE!"
                
                embed.add_field(
                    name="🌟 Star Progress",
                    value=star_info,
                    inline=True,
                )

                # Calculate character power based on star level  
                if current_star == 1:
                    power = 100
                elif current_star == 2:
                    power = 250
                elif current_star == 3:
                    power = 500
                elif current_star == 4:
                    power = 1000
                elif current_star >= 5:
                    power = 2000 * (2 ** (current_star - 5))
                else:
                    power = 100

                embed.add_field(
                    name="⚡ Combat Stats",
                    value=f"**Power:** {power:,}\n"
                    f"**Bond Level:** {user_waifu.get('bond_level', 1)}\n"
                    f"**Conversations:** {user_waifu.get('total_conversations', 0)}",
                    inline=True,
                )

                if user_waifu.get("custom_nickname"):
                    embed.add_field(
                        name="🏷️ Nickname",
                        value=user_waifu["custom_nickname"],
                        inline=True,
                    )
                
                # Add when obtained info
                obtained_at = user_waifu.get("obtained_at")
                if obtained_at:
                    if isinstance(obtained_at, str):
                        embed.add_field(
                            name="📅 Obtained",
                            value=f"<t:{int(obtained_at)}:R>" if obtained_at.isdigit() else "Unknown",
                            inline=True,
                        )
                    else:
                        # Assume it's a datetime object
                        timestamp = int(obtained_at.timestamp()) if hasattr(obtained_at, 'timestamp') else 0
                        embed.add_field(
                            name="📅 Obtained",
                            value=f"<t:{timestamp}:R>",
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

            # Updated footer with more relevant commands
            if user_waifu:
                footer_text = f"ID: {waifu['id']} • Auto upgrades with shards • /nwnl_collection to view all"
            else:
                footer_text = f"ID: {waifu['id']} • Use /nwnl_summon to try collecting • /nwnl_collection to view owned"
            
            embed.set_footer(text=footer_text)

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
    # Get services from bot instance  
    await bot.add_cog(WaifuSummonCog(bot, bot.services))
