async def waifu_name_autocomplete(interaction, current: str):
    # Try to get waifu list from the waifu_service if available
    waifu_list = []
    try:
        cog = interaction.client.get_cog("WaifuSummonCog")
        if cog and hasattr(cog.services, "waifu_service"):
            waifu_list = getattr(cog.services.waifu_service, '_waifu_list', [])
    except Exception:
        pass
    names = [w.get("name", "") for w in waifu_list if current.lower() in w.get("name", "").lower()]
    # Return up to 20 results
    return [discord.app_commands.Choice(name=n, value=n) for n in names[:20]]

async def series_name_autocomplete(interaction, current: str):
    # Try to get series list from the database if available
    series_list = []
    try:
        cog = interaction.client.get_cog("WaifuSummonCog")
        if cog and hasattr(cog.services, "database"):
            db = cog.services.database
            if hasattr(db, 'connection_pool'):
                async with db.connection_pool.acquire() as conn:
                    rows = await conn.fetch("SELECT name FROM series ORDER BY name")
                    series_list = [row["name"] for row in rows]
    except Exception:
        pass
    filtered = [s for s in series_list if current.lower() in s.lower()]
    return [discord.app_commands.Choice(name=s, value=s) for s in filtered[:20]]


"""New waifu summon command with star upgrade system."""

import discord
from discord.ext import commands
from typing import Optional
from cogs.base_command import BaseCommand
from services.container import ServiceContainer


async def display_mode_autocomplete(interaction: discord.Interaction, current: str):
    modes = [
        ("Full (show all info cards)", "full"),
        ("Simple (hide 2★ info cards)", "simple"),
        ("Minimal (summary only)", "minimal"),
    ]
    return [
        discord.app_commands.Choice(name=label, value=val)
        for label, val in modes if current.lower() in val or current.lower() in label.lower()
    ]

class WaifuSummonCog(BaseCommand):

    @commands.hybrid_command(
        name="nwnl_collection_list",
        description="📖 View your waifu collection as a paginated list"
    )
    async def nwnl_collection_list(self, ctx: commands.Context, user: Optional[discord.Member] = None):
        """Display the user's waifu collection as a paginated list with navigation buttons."""
        await ctx.defer()
        target_user = user if user is not None else ctx.author
        @commands.hybrid_command(
            name="nwnl_collection_list",
            description="📖 View your waifu collection as a paginated list"
        )
        @discord.app_commands.describe(
            user="(Optional) View another user's collection",
            series_id="(Optional) Only show waifus from this series ID"
        )
        async def nwnl_collection_list(self, ctx: commands.Context, user: Optional[discord.Member] = None, series_id: Optional[int] = None):
            """Display the user's waifu collection as a paginated list with navigation buttons. Optionally filter by series_id."""
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

                # Filter by series_id if provided
                filtered_collection = collection
                if series_id is not None:
                    filtered_collection = [w for w in collection if w.get("series_id") == series_id]
                # Always sort by star level (desc), then name
                sorted_collection = sorted(filtered_collection, key=lambda w: (-w.get("current_star_level", w["rarity"]), w["name"]))

                class CollectionPaginator(discord.ui.View):
                    def __init__(self, ctx, waifus, user, series_id):
                        super().__init__(timeout=180)
                        self.ctx = ctx
                        self.waifus = waifus
                        self.user = user
                        self.series_id = series_id
                        self.page_idx = 0
                        self.page_size = 10
                        self.page_count = max(1, (len(waifus) + self.page_size - 1) // self.page_size)

                    def get_embed(self):
                        start = self.page_idx * self.page_size
                        end = start + self.page_size
                        waifu_page = self.waifus[start:end]
                        title = f"🏫 {self.user.display_name}'s Waifu Collection"
                        if self.series_id is not None:
                            title += f" (Series ID: {self.series_id})"
                        embed = discord.Embed(
                            title=title,
                            description=f"Page {self.page_idx+1}/{self.page_count} • Total: {len(self.waifus)} waifus",
                            color=0x3498DB,
                        )
                        if waifu_page:
                            for w in waifu_page:
                                stars = "⭐" * w.get("current_star_level", w["rarity"])
                                shards = w.get("character_shards", 0)
                                value = f"{stars} | {w['series']}"
                                if shards > 0:
                                    value += f" | {shards} shards"
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

                view = CollectionPaginator(ctx, sorted_collection, target_user, series_id)
                await ctx.send(embed=view.get_embed(), view=view)
            except Exception as e:
                self.logger.error(f"Error displaying collection list: {e}")
                embed = discord.Embed(
                    title="❌ Collection List Error",
                    description="Unable to display collection list. Please try again later!",
                    color=0xFF6B6B,
                )
                await ctx.send(embed=embed)
            await ctx.send(embed=embed)


    @commands.hybrid_command(
        name="nwnl_database",
        description="📚 View all series and their characters in the database with pagination"
    )
    @discord.app_commands.describe(series_name="(Optional) Search for a series by name")
    async def nwnl_database(self, ctx: commands.Context, *, series_name: Optional[str] = None):
        """Display all series and their characters with pagination and buttons. Optionally filter by series name."""
        await ctx.defer()
        try:
            # Fetch all series
            if hasattr(self.services.database, 'connection_pool'):
                async with self.services.database.connection_pool.acquire() as conn:
                    if series_name:
                        # Case-insensitive partial match on name or english_name
                        rows = await conn.fetch(
                            "SELECT * FROM series WHERE LOWER(name) LIKE $1 OR LOWER(english_name) LIKE $1 ORDER BY name",
                            f"%{series_name.lower()}%"
                        )
                    else:
                        rows = await conn.fetch("SELECT * FROM series ORDER BY name")
                    all_series = [dict(row) for row in rows]
            else:
                all_series = []
            if not all_series:
                embed = discord.Embed(
                    title="❌ No Series Found",
                    description="No series found in the database." if not series_name else f"No series found matching '{series_name}'.",
                    color=0xFF6B6B,
                )
                await ctx.send(embed=embed)
                return

            # Helper to fetch waifus for a series from the local in-memory list
            def get_waifus_for_series(series_row):
                waifu_list = getattr(self.services.waifu_service, '_waifu_list', [])
                series_id = series_row.get('series_id')
                series_name = series_row.get('name')
                waifus = [w for w in waifu_list if (w.get('series_id') == series_id) or (w.get('series') == series_name)]
                return waifus

            # Build a list of (series, waifus) pairs
            series_waifus = []
            for s in all_series:
                waifus = get_waifus_for_series(s)
                series_waifus.append((s, waifus))

            # Paginated view class
            class DatabasePaginator(discord.ui.View):
                def __init__(self, ctx, series_waifus):
                    super().__init__(timeout=180)
                    self.ctx = ctx
                    self.series_waifus = series_waifus
                    self.series_idx = 0
                    self.page_idx = 0
                    self.update_page_count()

                def update_page_count(self):
                    _, waifus = self.series_waifus[self.series_idx]
                    self.page_count = max(1, (len(waifus) + 24) // 25)
                    if self.page_idx >= self.page_count:
                        self.page_idx = self.page_count - 1

                def get_embed(self):
                    series, waifus = self.series_waifus[self.series_idx]
                    self.update_page_count()
                    start = self.page_idx * 25
                    end = start + 25
                    waifu_page = waifus[start:end]
                    embed = discord.Embed(
                        title=f"🏷️ {series.get('name', 'Unknown Series')} (ID: {series.get('series_id', '?')})",
                        description=series.get('english_name', ''),
                        color=0x8e44ad,
                    )
                    if waifu_page:
                        lines = [f"{'⭐'*w.get('rarity', 1)} {w.get('name', 'Unknown')} (ID: {w.get('waifu_id', '?')})" for w in waifu_page]
                        embed.add_field(
                            name=f"Characters (Page {self.page_idx+1}/{self.page_count})",
                            value="\n".join(lines),
                            inline=False
                        )
                    else:
                        embed.add_field(name="No Characters", value="This series has no characters.", inline=False)
                    embed.set_footer(text=f"Series {self.series_idx+1}/{len(self.series_waifus)} • Use buttons to navigate")
                    return embed

                async def interaction_check(self, interaction: discord.Interaction) -> bool:
                    return interaction.user == self.ctx.author

                @discord.ui.button(label="⏮️ Series", style=discord.ButtonStyle.secondary, row=0)
                async def prev_series(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.series_idx = (self.series_idx - 1) % len(self.series_waifus)
                    self.page_idx = 0
                    await interaction.response.edit_message(embed=self.get_embed(), view=self)

                @discord.ui.button(label="⏭️ Series", style=discord.ButtonStyle.secondary, row=0)
                async def next_series(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.series_idx = (self.series_idx + 1) % len(self.series_waifus)
                    self.page_idx = 0
                    await interaction.response.edit_message(embed=self.get_embed(), view=self)

                @discord.ui.button(label="⬅️ Page", style=discord.ButtonStyle.primary, row=1)
                async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.update_page_count()
                    self.page_idx = (self.page_idx - 1) % self.page_count
                    await interaction.response.edit_message(embed=self.get_embed(), view=self)

                @discord.ui.button(label="➡️ Page", style=discord.ButtonStyle.primary, row=1)
                async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.update_page_count()
                    self.page_idx = (self.page_idx + 1) % self.page_count
                    await interaction.response.edit_message(embed=self.get_embed(), view=self)

            view = DatabasePaginator(ctx, series_waifus)
            await ctx.send(embed=view.get_embed(), view=view)
        except Exception as e:
            self.logger.error(f"Error displaying NWNL database: {e}")
            embed = discord.Embed(
                title="❌ Database Error",
                description="Unable to display NWNL database. Please try again later!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="nwnl_series",
        description="📺 View detailed info about an anime series by name"
    )
    @discord.app_commands.autocomplete(series_name=series_name_autocomplete)
    async def nwnl_series(self, ctx: commands.Context, *, series_name: str):
        """Display detailed info about an anime series, including all characters in the series, with pagination."""
        await ctx.defer()
        try:
            # Search for the series (case-insensitive, partial match)
            # Try exact match first
            series = await self.services.database.get_series_by_name(series_name)
            if not series:
                # Try partial match if exact not found, matching both name and english_name
                all_series = []
                if hasattr(self.services.database, 'connection_pool'):
                    async with self.services.database.connection_pool.acquire() as conn:
                        rows = await conn.fetch("SELECT * FROM series")
                        all_series = [dict(row) for row in rows]
                # Build a matching queue: prioritize name, then english_name
                matches = []
                for s in all_series:
                    if series_name.lower() in (s.get('name') or '').lower():
                        matches.append(s)
                for s in all_series:
                    if series_name.lower() in (s.get('english_name') or '').lower() and s not in matches:
                        matches.append(s)
                series = matches[0] if matches else None
            if not series:
                embed = discord.Embed(
                    title="❌ Series Not Found",
                    description=f"No series found matching '{series_name}'. Try a different name or check spelling!",
                    color=0xFF6B6B,
                )
                await ctx.send(embed=embed)
                return

            # Fetch all waifus for this series from the local in-memory list
            waifu_list = getattr(self.services.waifu_service, '_waifu_list', [])
            series_id = series.get('series_id')
            series_name_actual = series.get('name')
            waifus = [w for w in waifu_list if (w.get('series_id') == series_id) or (w.get('series') == series_name_actual)]
            waifus = sorted(waifus, key=lambda w: (-w.get('rarity', 1), w.get('name', '')))

            # Paginated view for waifus in this series
            class SeriesPaginator(discord.ui.View):
                def __init__(self, ctx, series, waifus):
                    super().__init__(timeout=180)
                    self.ctx = ctx
                    self.series = series
                    self.waifus = waifus
                    self.page_idx = 0
                    self.page_count = max(1, (len(waifus) + 24) // 25)

                def get_embed(self):
                    start = self.page_idx * 25
                    end = start + 25
                    waifu_page = self.waifus[start:end]
                    embed = discord.Embed(
                        title=f"📺 {self.series.get('name', 'Unknown Series')} (ID: {self.series.get('series_id', '?')})",
                        description=self.series.get('english_name', ''),
                        color=0x4A90E2,
                    )
                    # Add image if available
                    if self.series.get('image_link'):
                        embed.set_image(url=self.series['image_link'])
                    # Add info fields, truncate if needed
                    display_fields = [
                        ('Studios', 'studios'),
                        ('Genres', 'genres'),
                        ('Synopsis', 'synopsis'),
                        ('Favorites', 'favorites'),
                        ('Members', 'members'),
                        ('Score', 'score'),
                        ('Genre', 'genre'),
                        ('Description', 'description'),
                    ]
                    for label, key in display_fields:
                        val = self.series.get(key)
                        if val and str(val).strip() and str(val).lower() != 'nan':
                            sval = str(val)
                            if len(sval) > 1024:
                                sval = sval[:1021] + '...'
                            embed.add_field(name=label, value=sval, inline=False)
                    # Add waifu list for this page
                    if waifu_page:
                        lines = [f"{'⭐'*w.get('rarity', 1)} {w.get('name', 'Unknown')} (ID: {w.get('waifu_id', '?')})" for w in waifu_page]
                        embed.add_field(
                            name=f"Characters (Page {self.page_idx+1}/{self.page_count})",
                            value="\n".join(lines),
                            inline=False
                        )
                    else:
                        embed.add_field(name="No Characters", value="This series has no characters.", inline=False)
                    embed.set_footer(text=f"Series ID: {self.series.get('series_id', 'N/A')} • Page {self.page_idx+1}/{self.page_count} • Use buttons to navigate")
                    return embed

                async def interaction_check(self, interaction: discord.Interaction) -> bool:
                    return interaction.user == self.ctx.author

                @discord.ui.button(label="⬅️ Page", style=discord.ButtonStyle.primary, row=0)
                async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.page_idx = (self.page_idx - 1) % self.page_count
                    await interaction.response.edit_message(embed=self.get_embed(), view=self)

                @discord.ui.button(label="➡️ Page", style=discord.ButtonStyle.primary, row=0)
                async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.page_idx = (self.page_idx + 1) % self.page_count
                    await interaction.response.edit_message(embed=self.get_embed(), view=self)

            view = SeriesPaginator(ctx, series, waifus)
            await ctx.send(embed=view.get_embed(), view=view)
        except Exception as e:
            self.logger.error(f"Error displaying series info: {e}")
            embed = discord.Embed(
                title="❌ Series Error",
                description="Unable to display series info. Please try again later!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)


    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)


    @commands.hybrid_command(
        name="nwnl_summon",
        description="🎰 Summon waifus using Sakura Crystals with NEW star system! (10 crystals per summon)",
    )
    @discord.app_commands.describe(banner_id="Banner ID to summon from (optional)")
    async def nwnl_summon(self, ctx: commands.Context, banner_id: Optional[int] = None):
        """Perform a waifu summon with the new star upgrade system."""
        await ctx.defer()
        # Only use explicit banner_id; no fallback to user_selected_banners
        return await self.queue_command(ctx, self._nwnl_summon_impl, banner_id)

    async def _nwnl_summon_impl(self, ctx: commands.Context, banner_id: Optional[int] = None):
        """Implementation of nwnl_summon command."""
        try:
            # Perform the summon using the new service
            result = await self.services.waifu_service.perform_summon(str(ctx.author.id), banner_id=banner_id)

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

            # Character details (no about text)
            embed.add_field(name="Character", value=f"**{waifu['name']}**", inline=True)
            embed.add_field(name="Series", value=waifu.get("series", "Unknown"), inline=True)
            embed.add_field(name="Element",
                            value=f"{waifu.get('element', 'Unknown')} 🔮",
                            inline=True,
                            )            
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
                value=f"💎 {result.get('crystals_remaining', result.get('crystals', 'N/A'))}",
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
    @discord.app_commands.describe(
        display_mode="How much detail to show for each pull (full, simple, minimal)",
        banner_id="Banner ID to summon from (optional)"
    )
    @discord.app_commands.autocomplete(display_mode=display_mode_autocomplete)
    async def nwnl_multi_summon(self, ctx: commands.Context, banner_id: Optional[int] = None, display_mode: str = "full"):
        """Perform 10 waifu summons with the new star upgrade system."""
        await ctx.defer()
        # Only use explicit banner_id; no fallback to user_selected_banners
        result = await self.services.waifu_service.perform_multi_summon(str(ctx.author.id), banner_id=banner_id)
        result["display_mode"] = display_mode

        # Rarity colors and emojis (3★ = old 5★ Legendary, 2★ = old 4★ Epic, 1★ = old 1★ Basic)
        rarity_config = {
            3: {"color": 0xFFD700, "emoji": "⭐⭐⭐", "name": "Legendary"},
            2: {"color": 0x9932CC, "emoji": "⭐⭐", "name": "Epic"},
            1: {"color": 0x808080, "emoji": "⭐", "name": "Basic"},
        }

        # If minimal mode, show only the Other Summons Summary and the final summary embed
        if display_mode == "minimal":
            if not result["success"]:
                embed = discord.Embed(
                    title="❌ Multi-Summon Failed",
                    description=result["message"],
                    color=0xFF6B6B,
                )
                await ctx.send(embed=embed)
                return

            # Build low-rarity pulls summary (all pulls, no individual cards)
            low_rarity_pulls = []
            for i, summon_result in enumerate(result["results"]):
                waifu = summon_result["waifu"]
                rarity = summon_result["rarity"]
                config = rarity_config[rarity]
                if summon_result["is_new"]:
                    status = "🆕 NEW"
                elif summon_result.get("quartz_gained", 0) > 0 and summon_result.get("shards_gained", 0) == 0:
                    status = f"💠 +{summon_result['quartz_gained']} quartz (maxed)"
                else:
                    status = f"💫 +{summon_result['shards_gained']} shards"
                low_rarity_pulls.append(
                    f"**#{i+1}** {config['emoji']} **{waifu['name']}** ({waifu.get('series', 'Unknown')}) - {status}"
                )

            embeds = []
            if low_rarity_pulls:
                summary_embed = discord.Embed(
                    title="📋 Other Summons Summary",
                    description="\n".join(low_rarity_pulls),
                    color=0x95A5A6,
                )
                embeds.append(summary_embed)

            rarity_counts = result["rarity_counts"]
            rarity_text = []
            for rarity in [3, 2, 1]:
                count = rarity_counts.get(rarity, 0)
                if count > 0:
                    config = rarity_config[rarity]
                    rarity_text.append(f"{config['emoji']} {config['name']}: {count}")

            final_summary = discord.Embed(
                title="📊 Multi-Summon Summary",
                color=0x4A90E2,
            )
            final_summary.add_field(
                name="📊 Rarity Breakdown",
                value="\n".join(rarity_text) if rarity_text else "No results",
                inline=True,
            )

            # New waifus summary
            new_waifus = result.get("new_waifus", [])
            if new_waifus:
                new_names = [w["name"] for w in new_waifus[:5]]
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
                for char_name, shards in list(shard_summary.items())[:3]:
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
                upgrade_text = upgrade_summary[:5]
                if len(upgrade_summary) > 5:
                    upgrade_text.append(f"...and {len(upgrade_summary) - 5} more!")
                final_summary.add_field(
                    name="⬆️ AUTO UPGRADES!",
                    value="\n".join(upgrade_text),
                    inline=False,
                )

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
            final_summary.set_footer(
                text=f"Multi-summon complete! Cost: {result['total_cost']} crystals • Remaining: {result['crystals_remaining']} crystals"
            )
            embeds.append(final_summary)
            await ctx.send(embeds=embeds)
            # Log the multi-summon results
            self.logger.info(
                f"User {ctx.author} performed x{result['count']} multi-summon (minimal): "
                f"3★:{rarity_counts.get(3,0)}, 2★:{rarity_counts.get(2,0)}, "
                f"1★:{rarity_counts.get(1,0)}"
            )
            return

        try:
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
                3: {"color": 0xFFD700, "emoji": "⭐⭐⭐", "name": "Legendary"},
                2: {"color": 0x9932CC, "emoji": "⭐⭐", "name": "Epic"},
                1: {"color": 0x808080, "emoji": "⭐", "name": "Basic"},
            }

            # Separate high-rarity (2★+) and low-rarity (1★) pulls like the old system
            embeds = []
            special_content_parts = []
            low_rarity_pulls = []
            high_rarity_count = 0
            waifu_embeds = []
            waifu_fields_for_summary = []
            for i, summon_result in enumerate(result["results"]):
                waifu = summon_result["waifu"]
                rarity = summon_result["rarity"]
                config = rarity_config[rarity]
                # Display logic based on display_mode
                show_card = True
                if result["display_mode"] == "simple" and rarity == 2:
                    show_card = False
                elif result["display_mode"] == "minimal":
                    show_card = False
                # Only allow up to 9 waifu embeds, add 10th as a field in summary
                if rarity >= 2 and show_card:
                    if len(waifu_embeds) < 9:
                        high_rarity_count += 1
                        embed = discord.Embed(
                            title=f"🎊 Summon #{i+1} - {config['name']} Pull! 🎊",
                            color=config["color"],
                        )
                        if summon_result["is_new"]:
                            embed.add_field(
                                name="🆕 NEW WAIFU!",
                                value=f"**{waifu['name']}** has joined your academy at {summon_result['current_star_level']}★!",
                                inline=False,
                            )
                        else:
                            if summon_result.get("quartz_gained", 0) > 0 and summon_result.get("shards_gained", 0) == 0:
                                embed.add_field(
                                    name="🌟 Max Level Duplicate!",
                                    value=f"**{waifu['name']}** is already 5⭐! Converted to {summon_result['quartz_gained']} quartz!",
                                    inline=False,
                                )
                            else:
                                embed.add_field(
                                    name="🌟 Duplicate Summon!",
                                    value=f"**{waifu['name']}** gained {summon_result['shards_gained']} shards!",
                                    inline=False,
                                )
                        if summon_result.get("upgrades_performed"):
                            upgrade_text = []
                            for upgrade in summon_result["upgrades_performed"]:
                                upgrade_text.append(f"🔥 {upgrade['from_star']}★ → {upgrade['to_star']}★")
                            embed.add_field(
                                name="⬆️ AUTOMATIC UPGRADES!",
                                value="\n".join(upgrade_text),
                                inline=False,
                            )
                        # Only show basic info, no about text
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
                        if waifu.get("image_url"):
                            embed.set_image(url=waifu["image_url"])
                        waifu_embeds.append(embed)
                        if rarity == 3:
                            special_content_parts.append(
                                f"🌟💫✨ **LEGENDARY PULL!** ✨💫🌟\n"
                                f"🎆🎇 **{waifu['name']}** 🎇🎆\n"
                                f"💎 The stars have aligned! A legendary waifu graces your academy! 💎"
                            )
                        elif rarity == 2:
                            special_content_parts.append(
                                f"✨🎆 **EPIC PULL!** 🎆✨\n"
                                f"🌟 **{waifu['name']}** 🌟\n"
                                f"🎉 An epic waifu has answered your call! 🎉"
                            )
                    else:
                        waifu_fields_for_summary.append((summon_result, i+1))
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
            
            # Add the 10th waifu as a field in the summary embed if needed
            if waifu_fields_for_summary:
                summon_result, idx = waifu_fields_for_summary[0]
                waifu = summon_result["waifu"]
                rarity = summon_result["rarity"]
                config = rarity_config[rarity]
                value = f"Series: {waifu.get('series', 'Unknown')}\nStars: {'⭐' * summon_result['current_star_level']} ({summon_result['current_star_level']}★)\n"
                if summon_result["is_new"]:
                    value += f"🆕 NEW WAIFU!"
                else:
                    if summon_result.get("quartz_gained", 0) > 0 and summon_result.get("shards_gained", 0) == 0:
                        value += f"🌟 Max Level Duplicate! +{summon_result['quartz_gained']} quartz"
                    else:
                        value += f"🌟 Duplicate Summon! +{summon_result['shards_gained']} shards"
                if summon_result.get("upgrades_performed"):
                    upgrade_text = ", ".join(f"{u['from_star']}★→{u['to_star']}★" for u in summon_result["upgrades_performed"])
                    value += f"\n⬆️ Upgrades: {upgrade_text}"
                final_summary.add_field(
                    name=f"#{idx} {config['emoji']} {waifu['name']}",
                    value=value,
                    inline=False
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
                    name="✨ 3★ LEGENDARY Characters",
                    value="\n".join(three_star_chars),
                    inline=False,
                )

            # Add 2★ characters field if any
            if two_star_chars:
                final_summary.add_field(
                    name="🟣 2★ RARE Characters", 
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
            embeds = waifu_embeds + embeds
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

            # Send up to 9 waifu embeds + summary embed (max 10)
            await ctx.send(content=special_content, embeds=embeds[:10])

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
    @discord.app_commands.autocomplete(waifu_name=waifu_name_autocomplete)
    async def nwnl_profile(self, ctx: commands.Context, *, waifu_name: str):
        """Display all matching waifu profiles with star system information, using a paginator."""
        await ctx.defer()
        try:
            # Search for all matching waifus
            search_results = await self.services.database.search_waifus(waifu_name, 20)
            if not search_results:
                embed = discord.Embed(
                    title="❌ Waifu Not Found",
                    description=f"No waifu found matching '{waifu_name}'. Try a different name or check spelling!",
                    color=0xFF6B6B,
                )
                await ctx.send(embed=embed)
                return

            # Get user's collection once
            collection = await self.services.database.get_user_collection(str(ctx.author.id))
            collection_dict = {w["waifu_id"]: w for w in collection}

            rarity_colors = {
                5: 0xFF0000,  # Red for 5★ (Mythic)
                4: 0xFFD700,  # Gold for 4★ (Legendary)
                3: 0x9932CC,  # Purple for 3★ (Epic)
                2: 0x4169E1,  # Blue for 2★ (Rare)
                1: 0x808080,  # Gray for 1★ (Common)
            }


            class ProfilePaginator(discord.ui.View):
                def __init__(self, ctx, waifus, collection_dict, waifu_service):
                    super().__init__(timeout=180)
                    self.ctx = ctx
                    self.waifus = waifus
                    self.collection_dict = collection_dict
                    self.waifu_service = waifu_service
                    self.idx = 0

                def build_embed(self, waifu, user_waifu, current_star, star_progress=None, combat_stats=None):
                    description = waifu.get("about") or waifu.get("personality_profile") or "A mysterious character..."
                    embed = discord.Embed(
                        title=f"👤 {waifu['name']}",
                        description=description,
                        color=rarity_colors.get(current_star, 0x95A5A6),
                    )
                    embed.add_field(name="🎭 Series", value=waifu["series"], inline=True)
                    embed.add_field(name="🏷️ Genre", value=waifu.get("genre", "Unknown"), inline=True)
                    embed.add_field(name="🔮 Element", value=waifu.get("element", "Unknown"), inline=True)
                    embed.add_field(name="⭐ Base Rarity", value="⭐" * waifu["rarity"], inline=True)
                    if waifu.get("mal_id"):
                        embed.add_field(name="🔗 MAL ID", value=str(waifu["mal_id"]), inline=True)
                    if waifu.get("birthday"):
                        embed.add_field(name="🎂 Birthday", value=str(waifu["birthday"]), inline=True)
                    if user_waifu:
                        embed.add_field(name="🌟 Star Progress", value=star_progress or "Loading...", inline=True)
                        embed.add_field(
                            name="⚡ Combat Stats",
                            value=combat_stats or f"**Power:** Loading...\n"
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
                        obtained_at = user_waifu.get("obtained_at")
                        if obtained_at:
                            if isinstance(obtained_at, str):
                                embed.add_field(
                                    name="📅 Obtained",
                                    value=f"<t:{int(obtained_at)}:R>" if obtained_at.isdigit() else "Unknown",
                                    inline=True,
                                )
                            else:
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
                    if waifu.get("image_url"):
                        embed.set_image(url=waifu["image_url"])
                    if user_waifu:
                        footer_text = f"ID: {waifu['waifu_id']} • Auto upgrades with shards • /nwnl_collection to view all"
                    else:
                        footer_text = f"ID: {waifu['waifu_id']} • Use /nwnl_summon to try collecting • /nwnl_collection to view owned"
                    embed.set_footer(text=f"{footer_text} • Match {self.idx+1}/{len(self.waifus)}")
                    return embed

                async def get_embed(self):
                    waifu = self.waifus[self.idx]
                    user_waifu = self.collection_dict.get(waifu["waifu_id"])
                    current_star = user_waifu.get("current_star_level", waifu["rarity"]) if user_waifu else waifu["rarity"]
                    star_progress = None
                    combat_stats = None
                    if user_waifu:
                        shards = await self.waifu_service.get_character_shards(str(self.ctx.author.id), waifu["waifu_id"])
                        is_max_star = current_star >= 5
                        star_info = f"**Current Star Level:** {'⭐' * current_star} ({current_star}★)\n"
                        star_info += f"**Star Shards:** {shards:,}"
                        if is_max_star:
                            star_info += " (MAX STAR - converts to quartz)"
                        else:
                            next_star = current_star + 1
                            upgrade_costs = {2: 50, 3: 100, 4: 150, 5: 200}
                            required = upgrade_costs.get(next_star, 999)
                            star_info += f"/{required:,} (for {next_star}★)"
                            if shards >= required:
                                star_info += " 🔥 READY TO UPGRADE!"
                        star_progress = star_info
                        # Power calculation
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
                        combat_stats = f"**Power:** {power:,}\n" \
                            f"**Bond Level:** {user_waifu.get('bond_level', 1)}\n" \
                            f"**Conversations:** {user_waifu.get('total_conversations', 0)}"
                    return self.build_embed(waifu, user_waifu, current_star, star_progress, combat_stats)

                async def interaction_check(self, interaction: discord.Interaction) -> bool:
                    return interaction.user == self.ctx.author

                @discord.ui.button(label="⬅️ Prev", style=discord.ButtonStyle.primary, row=0)
                async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.idx = (self.idx - 1) % len(self.waifus)
                    embed = await self.get_embed()
                    await interaction.response.edit_message(embed=embed, view=self)

                @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.primary, row=0)
                async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.idx = (self.idx + 1) % len(self.waifus)
                    embed = await self.get_embed()
                    await interaction.response.edit_message(embed=embed, view=self)

            view = ProfilePaginator(ctx, search_results, collection_dict, self.services.waifu_service)
            embed = await view.get_embed()
            await ctx.send(embed=embed, view=view)
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
    # Ensure bot.services exists
    if not hasattr(bot, "services"):
        raise RuntimeError("ServiceContainer (bot.services) is required for WaifuSummonCog. Please initialize bot.services before loading this cog.")
    await bot.add_cog(WaifuSummonCog(bot, bot.services))
