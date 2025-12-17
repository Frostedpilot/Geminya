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


def format_media_type(media_type: str) -> str:
    """Format media_type for display with proper capitalization and full names."""
    if not media_type:
        return "Unknown"
    
    media_type_mapping = {
        'anime': '📺 Anime',
        'visual_novel': '🎮 Visual Novel', 
        'game': '🎮 Game',
        'manga': '📖 Manga',
        'light_novel': '📚 Light Novel'
    }
    
    return media_type_mapping.get(media_type.lower(), f"📄 {media_type.title()}")


def format_creator(creator_json: str) -> str:
    """Format creator JSON field for display with proper labels."""
    if not creator_json or not creator_json.strip():
        return "Unknown"
    
    if creator_json.startswith('{'):
        try:
            import json
            creator_data = json.loads(creator_json)
            if creator_data:
                creator_parts = []
                # Map creator types to display names
                creator_type_mapping = {
                    'studio': 'Studio',
                    'developer': 'Developer', 
                    'author': 'Author',
                    'publisher': 'Publisher',
                    'director': 'Director',
                    'producer': 'Producer'
                }
                
                for creator_type, creator_name in creator_data.items():
                    if creator_name and creator_name.strip():
                        display_type = creator_type_mapping.get(creator_type.lower(), creator_type.title())
                        creator_parts.append(f"{display_type}: {creator_name}")
                        
                return " | ".join(creator_parts) if creator_parts else "Unknown"
            else:
                return "Unknown"
        except:
            # If JSON parsing fails, return raw value
            return creator_json
    else:
        # Not JSON, return as-is (backward compatibility)
        return creator_json


"""New waifu summon command with star upgrade system."""

import discord
from discord.ext import commands
from typing import Optional
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
        name="nwnl_series_id",
        description="📺 View detailed info about a series by series ID"
    )
    @discord.app_commands.describe(series_id="ID of the series to search for")
    async def nwnl_series_id(self, ctx: commands.Context, series_id: int):
        """Display detailed info about a series by its series_id, including all characters in the series (no pagination)."""
        await ctx.defer()
        try:
            series = await self.get_series_by_id(series_id)
            if not series:
                embed = discord.Embed(
                    title="❌ Series Not Found",
                    description=f"No series found with ID '{series_id}'. Try a different ID!",
                    color=0xFF6B6B,
                )
                await ctx.send(embed=embed)
                return

            waifu_list = getattr(self.services.waifu_service, '_waifu_list', [])
            series_id_actual = series.get('series_id')
            series_name_actual = series.get('name')
            waifus = [w for w in waifu_list if (w.get('series_id') == series_id_actual) or (w.get('series') == series_name_actual)]
            waifus = sorted(waifus, key=lambda w: (-w.get('rarity', 1), w.get('name', '')))

            embed = discord.Embed(
                title=f"📺 {series.get('name', 'Unknown Series')} (ID: {series.get('series_id', '?')})",
                description=series.get('english_name', ''),
                color=0x4A90E2,
            )
            if series.get('image_link'):
                embed.set_image(url=series['image_link'])
            display_fields = [
                ('Creator', 'creator'),
                ('Genres', 'genres'),
                ('Synopsis', 'synopsis'),
                ('Favorites', 'favorites'),
                ('Members', 'members'),
                ('Score', 'score'),
                ('Media Type', 'media_type'),
                ('Genre', 'genre'),
                ('Description', 'description'),
            ]
            for label, key in display_fields:
                val = series.get(key)
                if val and str(val).strip() and str(val).lower() != 'nan':
                    sval = str(val)
                    
                    # Format creator and media_type fields for better display
                    if key == 'creator':
                        sval = format_creator(sval)
                    elif key == 'media_type':
                        sval = format_media_type(sval)
                    
                    if len(sval) > 1024:
                        sval = sval[:1021] + '...'
                    embed.add_field(name=label, value=sval, inline=False)

            if waifus:
                # Discord embed field value limit is 1024 chars, so chunk if needed
                lines = [f"{'⭐'*w.get('rarity', 1)} {w.get('name', 'Unknown')} (ID: {w.get('waifu_id', '?')})" for w in waifus]
                waifu_text = "\n".join(lines)
                if len(waifu_text) > 1024:
                    # Truncate and indicate
                    allowed = []
                    total = 0
                    for line in lines:
                        if total + len(line) + 1 > 1024:
                            break
                        allowed.append(line)
                        total += len(line) + 1
                    waifu_text = "\n".join(allowed) + f"\n...and {len(lines) - len(allowed)} more."
                embed.add_field(
                    name=f"Characters ({len(waifus)})",
                    value=waifu_text,
                    inline=False
                )
            else:
                embed.add_field(name="No Characters", value="This series has no characters.", inline=False)
            embed.set_footer(text=f"Series ID: {series.get('series_id', 'N/A')}")
            await ctx.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Error displaying series info by ID: {e}")
            embed = discord.Embed(
                title="❌ Series Error",
                description="Unable to display series info. Please try again later!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)
    async def get_series_by_id(self, series_id: int):
        """Fetch a series from the database by its series_id. Returns a dict or None if not found."""
        if hasattr(self.services.database, 'connection_pool'):
            async with self.services.database.connection_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM series WHERE series_id = $1", series_id)
                if row:
                    return dict(row)
        return None

    @commands.hybrid_command(
        name="nwnl_collection_list",
        description="📖 View your waifu collection as a paginated list"
    )
    @discord.app_commands.describe(
        user="(Optional) View another user's collection",
        series_id="(Optional) Only show waifus from this series ID",
        base_star_level="(Optional) Filter by base star level (1-3)"
    )
    async def nwnl_collection_list(self, ctx, user: Optional[discord.Member] = None, series_id: Optional[int] = None, base_star_level: Optional[int] = None):
        """Display the user's waifu collection as a paginated list with navigation buttons. Optionally filter by series_id and base_star_level."""
        await ctx.defer()
        target_user = user if user is not None else ctx.author
        
        # Validate base_star_level parameter
        if base_star_level is not None and (base_star_level < 1 or base_star_level > 3):
            embed = discord.Embed(
                title="❌ Invalid Star Level",
                description="Base star level must be between 1 and 3.",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # Get user's collection with star and shard info
            collection = await self.services.waifu_service.get_user_collection_with_stars(str(target_user.id))
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
            
            # Filter by base_star_level (rarity) if provided
            if base_star_level is not None:
                filtered_collection = [w for w in filtered_collection if w.get("rarity") == base_star_level]
            # Sort by star level, then name
            sorted_collection = sorted(filtered_collection, key=lambda w: (-w.get("current_star_level", w["rarity"]), -w["character_shards"], w["name"]))

            class CollectionPaginator(discord.ui.View):
                def __init__(self, ctx, waifus, user, series_id, base_star_level):
                    super().__init__(timeout=180)
                    self.ctx = ctx
                    self.waifus = waifus
                    self.user = user
                    self.series_id = series_id
                    self.base_star_level = base_star_level
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
                    if self.base_star_level is not None:
                        title += f" (Base ⭐: {self.base_star_level})"
                    embed = discord.Embed(
                        title=title,
                        description=f"Page {self.page_idx+1}/{self.page_count} • Total: {len(self.waifus)} waifus",
                        color=0x3498DB,
                    )
                    if waifu_page:
                        for w in waifu_page:
                            stars = "⭐" * w.get("current_star_level", w["rarity"])
                            shards = w.get("character_shards", 0)
                            # Add awakened badge if is_awakened is True
                            awakened_badge = " 🦋 Awakened" if w.get("is_awakened") else ""
                            display_name = f"{w['name']}{awakened_badge}"
                            value = f"{stars} | {w['series']} | {shards} shards"
                            embed.add_field(
                                name=display_name,
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

            view = CollectionPaginator(ctx, sorted_collection, target_user, series_id, base_star_level)
            await ctx.send(embed=view.get_embed(), view=view)
        except Exception as e:
            self.logger.error(f"Error displaying collection list: {e}")
            embed = discord.Embed(
                title="❌ Collection List Error",
                description="Unable to display collection list. Please try again later!",
                color=0xFF6B6B,
            )
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
                        # Use POSITION to sort by relevance (best match first)
                        rows = await conn.fetch(
                            "SELECT *, LEAST(POSITION($2 IN LOWER(name)), POSITION($2 IN LOWER(english_name))) AS relevance "
                            "FROM series "
                            "WHERE LOWER(name) LIKE $1 OR LOWER(english_name) LIKE $1 "
                            "ORDER BY relevance, name",
                            f"%{series_name.lower()}%", series_name.lower()
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
                        lines = []
                        for w in waifu_page:
                            awakened_badge = " 🦋 Awakened" if w.get("is_awakened") else ""
                            lines.append(f"{'⭐'*w.get('rarity', 1)} {w.get('name', 'Unknown')}{awakened_badge} (ID: {w.get('waifu_id', '?')})")
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
        description="📺 View detailed info about a series by name"
    )
    @discord.app_commands.autocomplete(series_name=series_name_autocomplete)
    async def nwnl_series(self, ctx: commands.Context, *, series_name: str):
        """Display detailed info about a series, including all characters in the series, with pagination."""
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
                        ('Creator', 'creator'),
                        ('Genres', 'genres'),
                        ('Synopsis', 'synopsis'),
                        ('Favorites', 'favorites'),
                        ('Members', 'members'),
                        ('Score', 'score'),
                        ('Media Type', 'media_type'),
                        ('Genre', 'genre'),
                        ('Description', 'description'),
                    ]
                    for label, key in display_fields:
                        val = self.series.get(key)
                        if val and str(val).strip() and str(val).lower() != 'nan':
                            sval = str(val)
                            
                            # Format media_type and creator fields for display
                            if key == 'media_type':
                                sval = format_media_type(sval)
                            elif key == 'creator':
                                sval = format_creator(sval)
                            
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
        description="🎰 Summon waifus with NEW star system! (Cost varies by banner)",
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
            # Use new schema field 'elemental_type' (list or string)
            elem_type = waifu.get("elemental_type", "Unknown")
            if isinstance(elem_type, list):
                elem_type = ", ".join(elem_type) if elem_type else "Unknown"
            embed.add_field(name="🔮 Element",
                            value=elem_type,
                            inline=True)
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

            # Dynamic currency display based on what was used
            currency_type = result.get("currency_type", "sakura_crystals")
            currency_remaining = result.get("currency_remaining", result.get("crystals_remaining", 0))
            cost = result.get("cost", 10)
            
            # Get currency emoji and display name
            currency_emojis = {
                'sakura_crystals': '💎',
                'quartzs': '💠', 
                'daphine': '🦋'
            }
            currency_names = {
                'sakura_crystals': 'Sakura Crystals',
                'quartzs': 'Quartzs',
                'daphine': 'Daphine'
            }
            
            currency_emoji = currency_emojis.get(currency_type, '💰')
            currency_name = currency_names.get(currency_type, currency_type.title())
            
            embed.add_field(
                name=f"{currency_name} Left",
                value=f"{currency_emoji} {currency_remaining} (Cost: {cost})",
                inline=True,
            )
            
            # Show daphine gained if any (for non-sakura currencies)
            daphine_gained = result.get("daphine_gained", 0)
            if daphine_gained > 0:
                embed.add_field(
                    name="Daphine Bonus",
                    value=f"🦋 +{daphine_gained} (1% chance bonus)",
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
        description="🎰🎊 Perform 10 summons with NEW star system! (Cost varies by banner)",
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

            # Dynamic currency display
            currency_type = result.get("currency_type", "sakura_crystals")
            currency_remaining = result.get("currency_remaining", result.get("crystals_remaining", 0))
            total_cost = result.get("total_cost", 0)
            
            currency_emojis = {
                'sakura_crystals': '💎',
                'quartzs': '💠',
                'daphine': '🦋'
            }
            currency_names = {
                'sakura_crystals': 'Sakura Crystals',
                'quartzs': 'Quartzs',
                'daphine': 'Daphine'
            }
            
            currency_emoji = currency_emojis.get(currency_type, '💰')
            currency_name = currency_names.get(currency_type, currency_type.title())
            
            final_summary.add_field(
                name=f"{currency_emoji} {currency_name} Remaining",
                value=f"{currency_remaining} (Spent: {total_cost})",
                inline=True,
            )
            final_summary.add_field(
                name="💰 Total Cost",
                value=f"{result['total_cost']} {currency_name}",
                inline=True,
            )
            
            # Show daphine gained if any (for non-sakura currencies)
            daphine_gained = result.get("daphine_gained", 0)
            if daphine_gained > 0:
                final_summary.add_field(
                    name="🦋 Daphine Bonus",
                    value=f"+{daphine_gained} (1% chance per pull)",
                    inline=True,
                )
            
            final_summary.set_footer(
                text=f"Multi-summon complete! Cost: {result['total_cost']} {currency_name} • Remaining: {currency_remaining} {currency_name}"
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
                                    value=f"**{waifu['name']}** is already {self.services.waifu_service.MAX_STAR_LEVEL}⭐! Converted to {summon_result['quartz_gained']} quartz!",
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
                            # Use new schema field 'elemental_type' (list or string)
                            name="🔮 Element",
                            value=", ".join(waifu["elemental_type"]) if isinstance(waifu.get("elemental_type"), list) and waifu.get("elemental_type") else waifu.get("elemental_type", "Unknown"),
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

            # Dynamic currency display for super summon
            currency_type = result.get("currency_type", "sakura_crystals")
            currency_remaining = result.get("currency_remaining", result.get("crystals_remaining", 0))
            total_cost = result.get("total_cost", 0)
            
            currency_emojis = {
                'sakura_crystals': '💎',
                'quartzs': '💠',
                'daphine': '🦋'
            }
            currency_names = {
                'sakura_crystals': 'Sakura Crystals',
                'quartzs': 'Quartzs',
                'daphine': 'Daphine'
            }
            
            currency_emoji = currency_emojis.get(currency_type, '💰')
            currency_name = currency_names.get(currency_type, currency_type.title())

            # Summary
            final_summary.add_field(
                name=f"{currency_emoji} {currency_name} Remaining",
                value=f"{currency_remaining}",
                inline=True,
            )
            final_summary.add_field(
                name="💰 Total Cost",
                value=f"{total_cost} {currency_name}",
                inline=True,
            )
            
            # Show daphine gained if any (for non-sakura currencies)
            daphine_gained = result.get("daphine_gained", 0)
            if daphine_gained > 0:
                final_summary.add_field(
                    name="🦋 Daphine Bonus",
                    value=f"+{daphine_gained} (1% chance per pull)",
                    inline=True,
                )
            

            # Add the final summary to embeds
            embeds = waifu_embeds + embeds
            embeds.append(final_summary)

            # Add footer to the last embed
            if embeds:
                embeds[-1].set_footer(
                    text=f"Super-summon complete! Cost: {total_cost} {currency_name} • "
                    f"Remaining: {currency_remaining} {currency_name}"
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
                        "🌟💫⭐ **MIRACLE MULTI-SUMMON!** ⭐💫🌟\n"
                        f"🎆🎇✨ **{three_star_count} LEGENDARY WAIFUS!** ✨🎇🎆\n"
                        "💎👑 The academy is blessed with divine fortune! 👑💎\n\n"
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
        name="nwnl_super_summon",
        description="🎰💫 Perform multiple 10-pulls with NEW star system! (Cost varies by banner)",
    )
    @discord.app_commands.describe(
        count="Number of multi-summons to perform (1-100, each multi-summon = 10 pulls)",
        banner_id="Banner ID to summon from (optional)"
    )
    async def nwnl_super_summon(self, ctx: commands.Context, count: int, banner_id: Optional[int] = None):
        """Perform multiple multi-summons (each multi-summon = 10 pulls) with the new star upgrade system."""
        await ctx.defer()
        
        # Validate count
        if count < 1 or count > 100:
            embed = discord.Embed(
                title="❌ Invalid Count",
                description="Please choose between 1-100 multi-summons (10-1000 total pulls).",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)
            return

        # Get cost and currency info from banner (or defaults)
        try:
            cost, currency_type = await self.services.waifu_service._get_summon_cost_and_currency(banner_id)
            total_cost = cost * 10 * count  # Each multi-summon = 10 pulls
            
            # Check if user has enough of the required currency
            has_enough, current_amount = await self.services.waifu_service._check_user_currency(
                str(ctx.author.id), currency_type, total_cost
            )
            
            if not has_enough:
                currency_name = self.services.waifu_service._get_currency_display_name(currency_type)
                currency_emoji = self.services.waifu_service._get_currency_emoji(currency_type)
                embed = discord.Embed(
                    title="❌ Insufficient Currency",
                    description=f"You need {total_cost} {currency_name} for {count} multi-summon{'s' if count > 1 else ''} but have {current_amount}. {currency_emoji}",
                    color=0xFF6B6B,
                )
                await ctx.send(embed=embed)
                return
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to check currency requirements. Please try again.",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)
            return

        try:
            # Perform multiple multi-summons
            all_results = []
            total_rarity_counts = {1: 0, 2: 0, 3: 0}
            total_crystals_spent = 0
            total_daphine_gained = 0  # Track total daphine gained
            last_multi_result = None  # Store the last multi-summon result for currency info
            
            # Send initial message
            progress_embed = discord.Embed(
                title="🎰💫 Super Summon in Progress...",
                description=f"Performing {count} multi-summon{'s' if count > 1 else ''} ({count * 10} total pulls)...",
                color=0xFFD700,
            )
            progress_msg = await ctx.send(embed=progress_embed)

            # Add order index to each result for sorting
            for i in range(count):
                # Perform individual multi-summon
                result = await self.services.waifu_service.perform_multi_summon(str(ctx.author.id), banner_id=banner_id)
                last_multi_result = result  # Store the latest result
                
                if not result["success"]:
                    # If any multi-summon fails, show error and stop
                    embed = discord.Embed(
                        title="❌ Super Summon Failed",
                        description=f"Failed on multi-summon {i+1}/{count}: {result['message']}",
                        color=0xFF6B6B,
                    )
                    await progress_msg.edit(embed=embed)
                    return
                
                # Add order index to each result for sorting
                for j, summon_result in enumerate(result["results"]):
                    summon_result["pull_order"] = len(all_results) + j + 1
                
                # Aggregate results
                all_results.extend(result["results"])
                for rarity, count_val in result["rarity_counts"].items():
                    total_rarity_counts[rarity] += count_val
                total_crystals_spent += result["total_cost"]
                total_daphine_gained += result.get("daphine_gained", 0)  # Aggregate daphine gained

            # Delete progress message
            await progress_msg.delete()

            # Sort results: by original rarity (descending), then by pull order (ascending)
            sorted_results = sorted(all_results, key=lambda x: (-x["rarity"], x["pull_order"]))

            # Get final user state
            final_user = await self.services.database.get_or_create_user(str(ctx.author.id))

            # Rarity colors and emojis
            rarity_config = {
                3: {"color": 0xFFD700, "emoji": "⭐⭐⭐", "name": "Legendary"},
                2: {"color": 0x9932CC, "emoji": "⭐⭐", "name": "Epic"},
                1: {"color": 0x808080, "emoji": "⭐", "name": "Basic"},
            }

            # Create paginated view for results
            class SuperSummonPaginator(discord.ui.View):
                def __init__(self, ctx, results, total_rarity_counts, total_crystals_spent, final_currency, count, currency_type="sakura_crystals", total_daphine_gained=0):
                    super().__init__(timeout=300)
                    self.ctx = ctx
                    self.results = results
                    self.total_rarity_counts = total_rarity_counts
                    self.total_crystals_spent = total_crystals_spent
                    self.final_currency = final_currency  # Renamed from final_crystals
                    self.currency_type = currency_type
                    self.count = count
                    self.total_daphine_gained = total_daphine_gained
                    self.page_idx = 0
                    self.page_size = 10
                    self.page_count = max(1, (len(results) + self.page_size - 1) // self.page_size)

                def get_embed(self):
                    start = self.page_idx * self.page_size
                    end = start + self.page_size
                    page_results = self.results[start:end]
                    
                    embed = discord.Embed(
                        title="🌟💫 Super Summon Results 💫🌟",
                        description=f"Page {self.page_idx+1}/{self.page_count} • {len(self.results)} total pulls from {self.count} multi-summons",
                        color=0xFFD700,
                    )

                    # Add summary stats in description
                    rarity_text = []
                    for rarity in [3, 2, 1]:
                        count_val = self.total_rarity_counts.get(rarity, 0)
                        if count_val > 0:
                            config = rarity_config[rarity]
                            percentage = (count_val / len(self.results)) * 100
                            rarity_text.append(f"{config['emoji']} {count_val} ({percentage:.1f}%)")
                    
                    summary_line = " • ".join(rarity_text)
                    current_desc = embed.description or ""
                    embed.description = current_desc + f"\n**Summary:** {summary_line}"

                    # Add detailed results for this page
                    if page_results:
                        result_lines = []
                        for result in page_results:
                            waifu = result["waifu"]
                            rarity = result["rarity"]
                            pull_order = result["pull_order"]
                            current_star = result.get("current_star_level", rarity)
                            
                            # Star display
                            stars = "⭐" * current_star
                            
                            # Status (NEW/shards/quartz)
                            if result["is_new"]:
                                status = "🆕 NEW"
                            elif result.get("quartz_gained", 0) > 0 and result.get("shards_gained", 0) == 0:
                                status = f"💠 +{result['quartz_gained']} quartz"
                            else:
                                status = f"💫 +{result['shards_gained']} shards"
                            
                            # Upgrades
                            upgrade_info = ""
                            if result.get("upgrades_performed"):
                                upgrades = result["upgrades_performed"]
                                if len(upgrades) == 1:
                                    upgrade_info = f" ⬆️ {upgrades[0]['from_star']}→{upgrades[0]['to_star']}★"
                                else:
                                    upgrade_info = f" ⬆️ {len(upgrades)} upgrades"
                            
                            # Series (truncated if too long)
                            series = waifu.get("series", "Unknown")
                            if len(series) > 20:
                                series = series[:17] + "..."
                            
                            # Build the line
                            result_line = f"**#{pull_order}** {stars} **{waifu['name']}** ({series})\n{status}{upgrade_info}"
                            result_lines.append(result_line)
                        
                        embed.add_field(
                            name="� Detailed Results",
                            value="\n\n".join(result_lines),
                            inline=False
                        )
                    else:
                        embed.add_field(name="No Results", value="This page is empty.", inline=False)
                    
                    # Get currency display info
                    currency_emojis = {
                        'sakura_crystals': '💎',
                        'quartzs': '💠',
                        'daphine': '🦋'
                    }
                    currency_names = {
                        'sakura_crystals': 'Crystals',
                        'quartzs': 'Quartzs',
                        'daphine': 'Daphine'
                    }
                    
                    currency_emoji = currency_emojis.get(self.currency_type, '💰')
                    currency_name = currency_names.get(self.currency_type, self.currency_type.title())
                    
                    # Footer with navigation and cost info
                    footer_text = f"{currency_emoji} {currency_name}: {self.final_currency} remaining • Cost: {self.total_crystals_spent}"
                    if self.total_daphine_gained > 0:
                        footer_text += f" • 🦋 Daphine Gained: {self.total_daphine_gained}"
                    footer_text += f" • Page {self.page_idx+1}/{self.page_count}"
                    
                    embed.set_footer(text=footer_text)
                    
                    return embed

                async def interaction_check(self, interaction: discord.Interaction) -> bool:
                    return interaction.user == self.ctx.author

                @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.primary, row=0)
                async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.page_idx = (self.page_idx - 1) % self.page_count
                    await interaction.response.edit_message(embed=self.get_embed(), view=self)

                @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.primary, row=0)
                async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.page_idx = (self.page_idx + 1) % self.page_count
                    await interaction.response.edit_message(embed=self.get_embed(), view=self)

                @discord.ui.button(label="🔢 Go to Page", style=discord.ButtonStyle.secondary, row=0)
                async def goto_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                    class PageModal(discord.ui.Modal, title="Go to Page"):
                        page_input = discord.ui.TextInput(
                            label="Page Number",
                            placeholder=f"Enter page number (1-{self.page_count})",
                            min_length=1,
                            max_length=3
                        )

                        def __init__(self, paginator):
                            super().__init__()
                            self.paginator = paginator

                        async def on_submit(self, interaction: discord.Interaction):
                            try:
                                page_num = int(self.page_input.value)
                                if 1 <= page_num <= self.paginator.page_count:
                                    self.paginator.page_idx = page_num - 1
                                    await interaction.response.edit_message(embed=self.paginator.get_embed(), view=self.paginator)
                                else:
                                    await interaction.response.send_message(
                                        f"Invalid page number. Please enter a number between 1 and {self.paginator.page_count}.",
                                        ephemeral=True
                                    )
                            except ValueError:
                                await interaction.response.send_message(
                                    "Please enter a valid number.",
                                    ephemeral=True
                                )

                    await interaction.response.send_modal(PageModal(self))

            # Create special celebration message
            three_star_count = total_rarity_counts.get(3, 0)
            content = ""
            if three_star_count >= 5:
                content = "🌟💫⭐ **MIRACLE SUPER SUMMON!** ⭐💫🌟\n🎆🎇✨ **LEGENDARY BONANZA!** ✨🎇🎆"
            elif three_star_count >= 3:
                content = "🌟💎 **AMAZING SUPER SUMMON!** 💎🌟\n✨ Multiple legendary waifus obtained! ✨"
            elif three_star_count >= 1:
                content = "🌟⭐ **GREAT SUPER SUMMON!** ⭐🌟\n💫 Legendary waifu acquired! 💫"

            # Get currency info from the last multi-summon result
            if last_multi_result:
                currency_type = last_multi_result.get("currency_type", "sakura_crystals")
                currency_remaining = last_multi_result.get("currency_remaining", 0)
            else:
                # Fallback: get fresh user state
                final_user = await self.services.database.get_or_create_user(str(ctx.author.id))
                currency_type = "sakura_crystals"
                currency_remaining = final_user.get("sakura_crystals", 0)

            # Create and send paginated view
            view = SuperSummonPaginator(ctx, sorted_results, total_rarity_counts, total_crystals_spent, currency_remaining, count, currency_type, total_daphine_gained)
            await ctx.send(content=content, embed=view.get_embed(), view=view)

            # Log the super summon results
            self.logger.info(
                f"User {ctx.author} performed x{count} super-summon ({len(all_results)} total pulls): "
                f"3★:{total_rarity_counts.get(3,0)}, 2★:{total_rarity_counts.get(2,0)}, "
                f"1★:{total_rarity_counts.get(1,0)}"
            )

        except Exception as e:
            self.logger.error(f"Error in super summon: {e}")
            embed = discord.Embed(
                title="❌ Super Summon Error",
                description="Something went wrong during super summoning. Please try again later!",
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

            # Add rarity distribution (showing current star levels) and awakened count
            rarity_dist = {}
            upgradeable_count = 0
            total_shards = 0
            awakened_count = 0

            for waifu in collection:
                current_star = waifu.get("current_star_level", waifu["rarity"])
                rarity_dist[current_star] = rarity_dist.get(current_star, 0) + 1
                if waifu.get("is_awakened"):
                    awakened_count += 1
                # Check if upgradeable
                shards = waifu.get("character_shards", 0)
                if current_star < self.services.waifu_service.MAX_STAR_LEVEL:
                    required = self.services.waifu_service.UPGRADE_COSTS.get(current_star + 1, 999)
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
            # Add awakened count field
            embed.add_field(
                name="🦋 Awakened Characters",
                value=f"{awakened_count} awakened waifu(s)",
                inline=True,
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
                if current_star < self.services.waifu_service.MAX_STAR_LEVEL:
                    required = self.services.waifu_service.UPGRADE_COSTS.get(current_star + 1, 999)
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
    @discord.app_commands.describe(
        waifu_name="Name of the waifu to search (optional)",
        series_name="Series name to filter by (optional)"
    )
    @discord.app_commands.autocomplete(waifu_name=waifu_name_autocomplete)
    async def nwnl_profile(self, ctx: commands.Context, *, waifu_name: Optional[str] = None, series_name: Optional[str] = None):
        """Display all matching waifu profiles with star system information, using a paginator. Optionally filter by series name."""
        await ctx.defer()
        try:
            if not waifu_name and not series_name:
                embed = discord.Embed(
                    title="ℹ️ Input Required",
                    description="Please provide at least one of `waifu_name` or `series_name` to view a profile.\nExample: `/nwnl_profile waifu_name:Rem` or `/nwnl_profile series_name:Re:Zero`.",
                    color=0x3498DB,
                )
                await ctx.send(embed=embed)
                return

            # Search for all matching waifus, optionally filtering by series
            search_results = await self.services.database.search_waifus(waifu_name or "", 20, series_name=series_name)
            if not search_results:
                desc = "No waifu found"
                if waifu_name:
                    desc += f" matching '{waifu_name}'"
                if series_name:
                    desc += f" in series '{series_name}'"
                desc += ". Try a different name or check spelling!"
                embed = discord.Embed(
                    title="❌ Waifu Not Found",
                    description=desc,
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
                6: 0xFF1493,  # Deep Pink for 6★ (Transcendent)
            }


            class ProfilePaginator(discord.ui.View):
                def __init__(self, ctx, waifus, collection_dict, waifu_service):
                    super().__init__(timeout=180)
                    self.ctx = ctx
                    self.waifus = waifus
                    self.collection_dict = collection_dict
                    self.waifu_service = waifu_service
                    self.idx = 0
                    self.page = 1  # 1 = main, 2 = stats

                def build_embed(self, waifu, user_waifu, current_star, star_progress=None, combat_stats=None):
                    # Awakened badge and color
                    is_awakened = user_waifu.get('is_awakened', False) if user_waifu else False
                    awakened_badge = " 🦋" if is_awakened else ""
                    awakened_field = None
                    if self.page == 1:
                        description = waifu.get("about") or waifu.get("personality_profile") or "A mysterious character..."
                        embed = discord.Embed(
                            title=f"👤 {waifu['name']}{awakened_badge}",
                            description=description,
                            color=0x00C3FF if is_awakened else rarity_colors.get(current_star, 0x95A5A6),
                        )
                        embed.add_field(name="🎭 Series", value=waifu["series"], inline=True)
                        embed.add_field(name="🏷️ Genre", value=waifu.get("genre", "Unknown"), inline=True)
                        elem_type = waifu.get("elemental_type", "Unknown")
                        if isinstance(elem_type, list):
                            elem_type = ", ".join(elem_type) if elem_type else "Unknown"
                        embed.add_field(name="🔮 Element", value=elem_type, inline=True)
                        embed.add_field(name="⭐ Base Rarity", value="⭐" * waifu["rarity"], inline=True)
                        if waifu.get("mal_id"):
                            embed.add_field(name="🔗 MAL ID", value=str(waifu["mal_id"]), inline=True)
                        if waifu.get("birthday"):
                            embed.add_field(name="🎂 Birthday", value=str(waifu["birthday"]), inline=True)
                        if user_waifu:
                            if is_awakened:
                                embed.add_field(name="🦋 Awakened Status", value="**AWAKENED**\nThis waifu has reached their awakened form!", inline=False)
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
                    else:
                        embed = discord.Embed(
                            title=f"📊 {waifu['name']} — Stats & Details",
                            color=rarity_colors.get(current_star, 0x95A5A6),
                        )
                        if waifu.get("image_url"):
                            embed.set_thumbnail(url=waifu["image_url"])  # Use thumbnail for more compact layout
                        
                        # Top row - rarity, status, and element
                        embed.add_field(name="⭐ Base Rarity", value="⭐" * waifu["rarity"], inline=True)
                        
                        # Status field with star progress
                        if user_waifu:
                            is_awakened = user_waifu.get('is_awakened', False)
                            if not is_awakened:
                                status_value = f"**Owned** ({'⭐' * current_star} {current_star}★)"
                            else:
                                status_value = f"**Owned** ({'<:3532rainbowstar:1423351319510647048>' * current_star} {current_star}★)"
                            if star_progress:
                                # Extract key star progress info for compact display
                                if "READY TO UPGRADE!" in star_progress:
                                    status_value += "\n🔥 **Ready to upgrade!**"
                                elif "MAX STAR" in star_progress:
                                    status_value += "\n✨ **Max Star**"
                                else:
                                    # Show current shards progress
                                    import re
                                    shard_match = re.search(r'(\d+)/(\d+)', star_progress)
                                    if shard_match:
                                        current_shards, required_shards = shard_match.groups()
                                        status_value += f"\n🌟 {current_shards}/{required_shards} shards"
                            if user_waifu.get("custom_nickname"):
                                status_value += f"\n🏷️ {user_waifu['custom_nickname']}"
                        else:
                            status_value = "**Not Collected**\nUse `/nwnl_summon`"
                        embed.add_field(name="❓ Status & Progress", value=status_value, inline=True)
                        
                        # Element type in the third position of top row
                        elem_type = waifu.get("elemental_type")
                        if elem_type:
                            if isinstance(elem_type, list):
                                elem_type = ", ".join(elem_type)
                            embed.add_field(name="🔮 Element", value=elem_type, inline=True)
                        else:
                            embed.add_field(name="🔮 Element", value="Unknown", inline=True)
                        
                        # Second row - compact stats
                        stats = waifu.get("stats")
                        if stats:
                            if isinstance(stats, dict):
                                # Split stats into two columns for square layout
                                stat_items = list(stats.items())
                                half = len(stat_items) // 2 + len(stat_items) % 2
                                left_stats = "\n".join(f"**{k}:** {v}" for k, v in stat_items[:half])
                                right_stats = "\n".join(f"**{k}:** {v}" for k, v in stat_items[half:])
                                embed.add_field(name="📈 Stats (1)", value=left_stats or "None", inline=True)
                                embed.add_field(name="📈 Stats (2)", value=right_stats or "None", inline=True)
                            else:
                                embed.add_field(name="📈 Stats", value=str(stats), inline=True)
                                embed.add_field(name="📈 Stats (2)", value="—", inline=True)  # Empty placeholder
                        else:
                            embed.add_field(name="📈 Stats", value="No stats available", inline=True)
                            embed.add_field(name="📈 Stats (2)", value="—", inline=True)  # Empty placeholder
                        
                        # Third field in second row for spacing
                        embed.add_field(name="⚡ Combat Info", value=combat_stats or "Not available", inline=True)
                        
                        # Third row - potency and resistances  
                        potency = waifu.get("potency")
                        if potency:
                            if isinstance(potency, dict):
                                potency_str = "\n".join(f"**{k}:** {v}" for k, v in potency.items())
                            else:
                                potency_str = str(potency)
                            embed.add_field(name="💥 Potency", value=potency_str, inline=True)
                        
                        resist = waifu.get("elemental_resistances")
                        if resist:
                            if isinstance(resist, dict):
                                resist_str = "\n".join(f"**{k}:** {v}" for k, v in resist.items())
                            else:
                                resist_str = str(resist)
                            embed.add_field(name="🛡️ Resistances", value=resist_str, inline=True)
                        
                        # Third position of third row - gifts
                        gifts = waifu.get("favorite_gifts")
                        if gifts:
                            if isinstance(gifts, list):
                                gifts = ", ".join(gifts)
                            embed.add_field(name="🎁 Gifts", value=gifts, inline=True)
                        
                        # Fourth row - special dialogue (full width if exists)
                        dialogue = waifu.get("special_dialogue")
                        if dialogue:
                            if isinstance(dialogue, dict):
                                # Limit dialogue to prevent overflow
                                dialogue_items = list(dialogue.items())[:3]  # Max 3 dialogue entries
                                dialogue_str = "\n".join(f"**{k}:** {v[:100]}{'...' if len(v) > 100 else ''}" for k, v in dialogue_items)
                            else:
                                dialogue_str = str(dialogue)[:200] + ("..." if len(str(dialogue)) > 200 else "")
                            embed.add_field(name="💬 Special Dialogue", value=dialogue_str, inline=False)
                            
                        archetype = waifu.get("archetype")
                        if archetype:
                            embed.add_field(name="🧩 Archetype", value=archetype, inline=True)


                        embed.set_footer(text=f"ID: {waifu['waifu_id']} • Page 2/2 • Match {self.idx+1}/{len(self.waifus)}")
                        return embed
                @discord.ui.button(label="Switch Page", style=discord.ButtonStyle.secondary, row=0)
                async def switch_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.page = 2 if self.page == 1 else 1
                    embed = await self.get_embed()
                    await interaction.response.edit_message(embed=embed, view=self)

                async def get_embed(self):
                    waifu = self.waifus[self.idx]
                    user_waifu = self.collection_dict.get(waifu["waifu_id"])
                    current_star = user_waifu.get("current_star_level", waifu["rarity"]) if user_waifu else waifu["rarity"]
                    is_awakened = user_waifu.get('is_awakened', False) if user_waifu else False
                    star_progress = None
                    combat_stats = None
                    if user_waifu:
                        shards = await self.waifu_service.get_character_shards(str(self.ctx.author.id), waifu["waifu_id"])
                        is_max_star = current_star >= self.waifu_service.MAX_STAR_LEVEL
                        if not is_awakened:
                            star_info = f"**Current Star Level:** {'⭐' * current_star} ({current_star}★)\n"
                        else:
                            star_info = f"**Current Star Level:** {'<:3532rainbowstar:1423351319510647048>' * current_star} ({current_star}★)\n"
                        star_info += f"**Star Shards:** {shards:,}"
                        if is_max_star:
                            star_info += " (MAX STAR - converts to quartz)"
                        else:
                            next_star = current_star + 1
                            required = self.waifu_service.UPGRADE_COSTS.get(next_star, 999)
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
