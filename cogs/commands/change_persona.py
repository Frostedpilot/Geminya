import discord
from discord.ext import commands
from discord.ui import Select, View, Button
from typing import Dict, List

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


class PersonaSelect(Select):
    """Select menu for choosing a persona."""

    def __init__(self, services: ServiceContainer):
        self.services = services
        self.config = services.config

        # Get available personas
        personas = self.config.personas

        options = []
        for persona_name, persona_data in personas.items():
            # Create description from persona data
            description = "Custom persona"
            if isinstance(persona_data, dict):
                if "description" in persona_data:
                    description = persona_data["description"][
                        :100
                    ]  # Limit description length
                elif "system_prompt" in persona_data:
                    # Use first part of system prompt as description
                    prompt = persona_data["system_prompt"]
                    description = (
                        prompt.split(".")[0][:100] if prompt else "Custom persona"
                    )

            options.append(
                discord.SelectOption(
                    label=persona_name,
                    value=persona_name,
                    description=description,
                    emoji="🎭",
                )
            )

        # Sort options alphabetically
        options.sort(key=lambda x: x.label.lower())

        super().__init__(
            placeholder="Select a persona...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="persona_select",
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle persona selection."""
        selected_persona_name = self.values[0]
        server_id = str(interaction.guild.id)

        # Update the server's persona
        self.services.state_manager.set_persona(server_id, selected_persona_name)

        # Update bot nickname if possible
        try:
            bot_member = interaction.guild.get_member(interaction.client.user.id)
            if bot_member and bot_member.guild_permissions.change_nickname:
                await bot_member.edit(nick=selected_persona_name)
        except discord.Forbidden:
            pass  # Ignore if we can't change nickname

        # Create success embed
        embed = discord.Embed(
            title="✅ Persona Changed Successfully!",
            description=f"The server persona has been changed to **{selected_persona_name}**",
            color=0x00FF88,
        )

        # Add persona details
        persona_data = self.config.personas.get(selected_persona_name)
        if persona_data and isinstance(persona_data, dict):
            details = []

            if "description" in persona_data:
                details.append(f"**Description:** {persona_data['description']}")

            if "system_prompt" in persona_data:
                system_prompt = persona_data["system_prompt"]
                if len(system_prompt) > 300:
                    system_prompt = system_prompt[:300] + "..."
                details.append(f"**System Prompt:** {system_prompt}")

            if details:
                embed.add_field(
                    name="Persona Details", value="\n".join(details), inline=False
                )

        embed.set_footer(text="Changes take effect immediately for new conversations.")

        # Create a simple view with just a "Change Again" button
        view = ChangeAgainView(self.services)

        await interaction.response.edit_message(embed=embed, view=view)


class ChangeAgainButton(Button):
    """Button to restart the persona selection process."""

    def __init__(self, services: ServiceContainer):
        self.services = services
        super().__init__(
            label="Change Again",
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            custom_id="change_again_persona",
        )

    async def callback(self, interaction: discord.Interaction):
        """Restart the persona selection process."""
        # Create initial view
        view = PersonaSelectionView(self.services)
        embed = view._create_initial_embed(interaction.guild.id)

        await interaction.response.edit_message(embed=embed, view=view)


class ChangeAgainView(View):
    """View with just a change again button."""

    def __init__(self, services: ServiceContainer):
        super().__init__(timeout=300.0)
        self.add_item(ChangeAgainButton(services))


class PersonaSelectionView(View):
    """Initial view for persona selection."""

    def __init__(self, services: ServiceContainer):
        super().__init__(timeout=300.0)
        self.services = services
        self.config = services.config
        self.add_item(PersonaSelect(services))

    def _create_initial_embed(self, guild_id: int) -> discord.Embed:
        """Create the initial embed showing current persona and available options."""
        server_id = str(guild_id)
        # Initialize server if needed
        self.services.state_manager.initialize_server(server_id)
        current_persona_name = self.services.state_manager.get_persona(server_id)

        embed = discord.Embed(
            title="🎭 Change AI Persona",
            description=f"**Current Persona:** {current_persona_name}\n\nChoose a new persona from the available options:",
            color=0x9B59B6,
        )

        # Add persona statistics
        personas = self.config.personas
        persona_count = len(personas)

        embed.add_field(
            name="Available Personas",
            value=f"**Total Personas:** {persona_count}\n\nSelect from the dropdown below to see persona details and switch.",
            inline=False,
        )

        # Show current persona details if available
        current_persona_data = personas.get(current_persona_name)
        if current_persona_data and isinstance(current_persona_data, dict):
            if "description" in current_persona_data:
                embed.add_field(
                    name="Current Persona Description",
                    value=current_persona_data["description"][:200]
                    + ("..." if len(current_persona_data["description"]) > 200 else ""),
                    inline=False,
                )

        embed.set_footer(text="Select a persona below | Timeout: 5 minutes")
        return embed


class ChangePersonaCog(BaseCommand):
    """Cog for changing AI personas with modern UI components."""

    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

    @commands.hybrid_command(
        name="changepersona",
        description="Change the AI persona used by the bot in this server.",
    )
    async def change_persona(self, ctx: commands.Context):
        """Change the AI persona used by the bot."""
        if not ctx.guild:
            await ctx.send("This command can only be used in servers, nya!")
            return

        # Create initial view and embed
        view = PersonaSelectionView(self.services)
        embed = view._create_initial_embed(ctx.guild.id)

        await ctx.send(embed=embed, view=view)

    @change_persona.error
    async def change_persona_error(self, ctx: commands.Context, error: Exception):
        """Handle errors in the change_persona command."""
        self.logger.error(f"Error in change_persona command: {error}")
        await ctx.send(
            "❌ An error occurred while changing the persona. Please try again later, nya!",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    """Set up the cog."""
    services = getattr(bot, "services", None)
    if services:
        await bot.add_cog(ChangePersonaCog(bot, services))
