import discord
from discord.ext import commands
from discord.ui import Select, View, Button
from typing import Dict, List

from cogs.base_command import BaseCommand
from cogs.commands import change_model
from services.container import ServiceContainer
from services.llm.types import ModelInfo
from utils.model_utils import (
    get_model_name_by_id,
    get_models_by_provider,
    get_all_providers,
)


class ProviderSelect(Select):
    """Select menu for choosing a provider."""

    def __init__(self, services: ServiceContainer):
        self.services = services
        self.config = services.config

        # Get available providers from MODEL_INFOS
        providers = get_all_providers()

        options = []
        for provider in providers:
            models = get_models_by_provider(provider)

            filtered_models = self.filter_out_non_tool_models(models)

            if not filtered_models:
                continue

            tool_count = sum(
                1 for model in filtered_models.values() if model.supports_tools
            )

            options.append(
                discord.SelectOption(
                    label=provider.title(),
                    value=provider,
                    description=f"{len(models)} models ({tool_count} with tools)",
                    emoji="🤖" if provider == "openrouter" else "⚙️",
                )
            )

        super().__init__(
            placeholder="Choose a provider to see its models...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="provider_select",
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle provider selection."""
        selected_provider = self.values[0]

        # Create new view with model selection for this provider
        view = ModelSelectionView(self.services, selected_provider)

        # Update the message with the model selection
        embed = self._create_provider_embed(selected_provider)
        await interaction.response.edit_message(embed=embed, view=view)

    def filter_out_non_tool_models(
        self, models: Dict[str, "ModelInfo"]
    ) -> Dict[str, "ModelInfo"]:
        """Filter out models that do not support tools."""
        return {name: info for name, info in models.items() if info.supports_tools}

    def _create_provider_embed(self, provider: str) -> discord.Embed:
        """Create embed showing provider information."""
        models = get_models_by_provider(provider)

        embed = discord.Embed(
            title=f"🤖 {provider.title()} Models",
            description=f"Choose from {len(models)} available models:",
            color=0x00FF88,
        )

        # Add model information with better formatting
        model_list = []
        for display_name, model_info in models.items():
            # Format like "AI21: Jamba Mini 1.7 • 17.3M tokens • $0.20/M • Tools"
            info_parts = []

            # Context length with proper formatting
            if model_info.context_length:
                if model_info.context_length >= 1_000_000:
                    context_display = (
                        f"{model_info.context_length/1_000_000:.1f}M tokens"
                    )
                elif model_info.context_length >= 1_000:
                    context_display = f"{model_info.context_length/1_000:.0f}K tokens"
                else:
                    context_display = f"{model_info.context_length} tokens"
                info_parts.append(context_display)

            # Pricing with both input and output costs
            if model_info.cost_per_million_tokens:
                input_cost = model_info.cost_per_million_tokens.get("in", 0)
                output_cost = model_info.cost_per_million_tokens.get("out", 0)
                if input_cost == 0 and output_cost == 0:
                    info_parts.append("Free")
                else:
                    pricing_parts = []
                    if input_cost > 0:
                        pricing_parts.append(f"${input_cost:.2f}/M in")
                    if output_cost > 0:
                        pricing_parts.append(f"${output_cost:.2f}/M out")
                    if pricing_parts:
                        info_parts.append(" | ".join(pricing_parts))

            # Create emoji combination
            emoji_parts = []

            # Add cost emoji first
            if (
                model_info.cost_per_million_tokens
                and model_info.cost_per_million_tokens.get("in", 0) == 0
                and model_info.cost_per_million_tokens.get("out", 0) == 0
            ):
                emoji_parts.append("🆓")  # Free
            else:
                emoji_parts.append("💰")  # Paid

            # Add tool support emoji
            if model_info.supports_tools:
                emoji_parts.append("🛠️")  # Has tools
            else:
                emoji_parts.append("💬")  # Chat only

            tools_emoji = "".join(emoji_parts)

            # Combine info
            info_text = " • ".join(info_parts) if info_parts else "No details available"
            model_list.append(f"{tools_emoji} **{display_name}**\n   └ {info_text}")

        # Split into chunks if too many models
        if len(model_list) <= 8:
            embed.add_field(
                name="Available Models", value="\n".join(model_list), inline=False
            )
        else:
            # Split into multiple fields
            mid = len(model_list) // 2
            embed.add_field(
                name="Available Models (Part 1)",
                value="\n".join(model_list[:mid]),
                inline=True,
            )
            embed.add_field(
                name="Available Models (Part 2)",
                value="\n".join(model_list[mid:]),
                inline=True,
            )

        embed.set_footer(text="🆓 = Free | 💰 = Paid | 🛠️ = Tools | 💬 = Chat only")
        return embed


class ModelSelect(Select):
    """Select menu for choosing a specific model."""

    def __init__(self, services: ServiceContainer, provider: str):
        self.services = services
        self.config = services.config
        self.provider = provider

        # Get models for this provider
        models = get_models_by_provider(provider)

        filtered_models = self.filter_out_non_tool_models(models)

        options = []
        for display_name, model_info in filtered_models.items():
            # Create rich description with key info like in the AI21 example
            description_parts = []

            # Add context length (like "17.3M tokens")
            if model_info.context_length:
                if model_info.context_length >= 1_000_000:
                    context_display = (
                        f"{model_info.context_length/1_000_000:.1f}M tokens"
                    )
                elif model_info.context_length >= 1_000:
                    context_display = f"{model_info.context_length/1_000:.0f}K tokens"
                else:
                    context_display = f"{model_info.context_length} tokens"
                description_parts.append(context_display)

            # Add pricing info with both input and output prices
            if model_info.cost_per_million_tokens:
                input_cost = model_info.cost_per_million_tokens.get("in", 0)
                output_cost = model_info.cost_per_million_tokens.get("out", 0)
                if input_cost == 0 and output_cost == 0:
                    description_parts.append("Free")
                else:
                    pricing_parts = []
                    if input_cost > 0:
                        pricing_parts.append(f"${input_cost:.2f}/M in")
                    if output_cost > 0:
                        pricing_parts.append(f"${output_cost:.2f}/M out")
                    if pricing_parts:
                        description_parts.append(" | ".join(pricing_parts))

            # Add tool support
            if model_info.supports_tools:
                description_parts.append("Tools")

            # Join parts with bullet separator for cleaner look
            description = " • ".join(
                description_parts[:2]
            )  # Limit to 2 parts for space

            # Create single emoji for select option (Discord limitation)
            if model_info.supports_tools:
                emoji = "🛠️"  # Prioritize tools if available
            elif (
                model_info.cost_per_million_tokens
                and model_info.cost_per_million_tokens.get("in", 0) == 0
                and model_info.cost_per_million_tokens.get("out", 0) == 0
            ):
                emoji = "🆓"  # Free models
            else:
                emoji = "💰"  # Paid models without tools

            options.append(
                discord.SelectOption(
                    label=display_name,
                    value=model_info.id,
                    description=description,
                    emoji=emoji,
                )
            )

        # Sort options by name
        options.sort(key=lambda x: x.label)

        super().__init__(
            placeholder="Select a model...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="model_select",
        )

    def filter_out_non_tool_models(
        self, models: Dict[str, "ModelInfo"]
    ) -> Dict[str, "ModelInfo"]:
        """Filter out models that do not support tools."""
        return {name: info for name, info in models.items() if info.supports_tools}

    async def callback(self, interaction: discord.Interaction):
        """Handle model selection."""
        selected_model_id = self.values[0]
        selected_model_name = get_model_name_by_id(selected_model_id)
        server_id = str(interaction.guild.id)

        # Update the server's model
        self.services.state_manager.set_tool_model(server_id, selected_model_id)

        # Create success embed
        embed = discord.Embed(
            title="✅ Model Changed Successfully!",
            description=f"The server model has been changed to **{selected_model_name}**",
            color=0x00FF88,
        )

        # Add model details
        models = get_models_by_provider(self.provider)
        model_info = None
        for info in models.values():
            if info.id == selected_model_id:
                model_info = info
                break

        if model_info:
            # Format details similar to the AI21 example
            details_lines = []

            # Provider info
            details_lines.append(f"**Provider:** {model_info.provider.title()}")

            # Context length with proper formatting
            if model_info.context_length:
                if model_info.context_length >= 1_000_000:
                    context_display = (
                        f"{model_info.context_length/1_000_000:.1f}M tokens"
                    )
                elif model_info.context_length >= 1_000:
                    context_display = f"{model_info.context_length/1_000:.0f}K tokens"
                else:
                    context_display = f"{model_info.context_length:,} tokens"
                details_lines.append(f"**Context:** {context_display}")

            # Pricing information
            if model_info.cost_per_million_tokens:
                input_cost = model_info.cost_per_million_tokens.get("in", 0)
                output_cost = model_info.cost_per_million_tokens.get("out", 0)
                if input_cost == 0 and output_cost == 0:
                    details_lines.append("**Pricing:** Free")
                else:
                    pricing_parts = []
                    if input_cost > 0:
                        pricing_parts.append(f"${input_cost:.2f}/M input")
                    if output_cost > 0:
                        pricing_parts.append(f"${output_cost:.2f}/M output")
                    details_lines.append(f"**Pricing:** {' • '.join(pricing_parts)}")

            # Tool support
            details_lines.append(
                f"**Tool Support:** {'✅ Yes' if model_info.supports_tools else '❌ No'}"
            )

            embed.add_field(
                name="Model Details", value="\n".join(details_lines), inline=False
            )

            if model_info.description:
                embed.add_field(
                    name="Description",
                    value=model_info.description[:200]
                    + ("..." if len(model_info.description) > 200 else ""),
                    inline=False,
                )

        embed.set_footer(text="Changes take effect immediately for new conversations.")

        # Create a simple view with just a "Change Again" button
        view = ChangeAgainView(self.services)

        await interaction.response.edit_message(embed=embed, view=view)


class ChangeAgainButton(Button):
    """Button to restart the model selection process."""

    def __init__(self, services: ServiceContainer):
        self.services = services
        super().__init__(
            label="Change Again",
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            custom_id="change_again",
        )

    async def callback(self, interaction: discord.Interaction):
        """Restart the model selection process."""
        # Create initial view
        view = InitialSelectionView(self.services)
        embed = view._create_initial_embed(interaction.guild.id)

        await interaction.response.edit_message(embed=embed, view=view)


class ChangeAgainView(View):
    """View with just a change again button."""

    def __init__(self, services: ServiceContainer):
        super().__init__(timeout=300.0)
        self.add_item(ChangeAgainButton(services))


class ModelSelectionView(View):
    """View for selecting a specific model from a provider."""

    def __init__(self, services: ServiceContainer, provider: str):
        super().__init__(timeout=300.0)
        self.add_item(ModelSelect(services, provider))
        # Add back button
        back_button = Button(
            label="← Back to Providers",
            style=discord.ButtonStyle.secondary,
            custom_id="back_to_providers",
        )
        back_button.callback = self._back_callback
        self.add_item(back_button)
        self.services = services

    async def _back_callback(self, interaction: discord.Interaction):
        """Go back to provider selection."""
        view = InitialSelectionView(self.services)
        embed = view._create_initial_embed(interaction.guild.id)
        await interaction.response.edit_message(embed=embed, view=view)


class InitialSelectionView(View):
    """Initial view for provider selection."""

    def __init__(self, services: ServiceContainer):
        super().__init__(timeout=300.0)
        self.services = services
        self.add_item(ProviderSelect(services))

    def _create_initial_embed(self, guild_id: int) -> discord.Embed:
        """Create the initial embed showing current model and provider options."""
        server_id = str(guild_id)
        current_model_id = self.services.state_manager.get_model(server_id)
        current_model_name = get_model_name_by_id(current_model_id) or "Unknown Model"

        embed = discord.Embed(
            title="🤖 Change AI Model",
            description=f"**Current Model:** {current_model_name}\n\nChoose a provider to see available models:",
            color=0x5865F2,
        )

        # Add provider statistics
        providers = get_all_providers()
        provider_info = []
        for provider in providers:
            models = get_models_by_provider(provider)
            tool_count = sum(1 for model in models.values() if model.supports_tools)
            provider_info.append(
                f"**{provider.title()}:** {len(models)} models ({tool_count} with tools)"
            )

        embed.add_field(
            name="Available Providers", value="\n".join(provider_info), inline=False
        )

        embed.set_footer(
            text="Select a provider below to see its models | Timeout: 5 minutes"
        )
        return embed


class ChangeToolModelCog(BaseCommand):
    """Cog for changing AI tool models with modern UI components."""

    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

    @commands.hybrid_command(
        name="changetoolmodel",
        description="Change the AI tool model used by the bot in this server.",
    )
    async def change_tool_model(self, ctx: commands.Context):
        """Change the AI tool model used by the bot."""
        if not ctx.guild:
            await ctx.send("This command can only be used in servers, nya!")
            return

        # Create initial view and embed
        view = InitialSelectionView(self.services)
        embed = view._create_initial_embed(ctx.guild.id)

        await ctx.send(embed=embed, view=view)

    @change_tool_model.error
    async def change_tool_model_error(self, ctx: commands.Context, error: Exception):
        """Handle errors in the change_tool_model command."""
        self.logger.error(f"Error in change_tool_model command: {error}")
        await ctx.send(
            "❌ An error occurred while changing the model. Please try again later, nya!",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    """Set up the cog."""
    services = getattr(bot, "services", None)
    if services:
        await bot.add_cog(ChangeToolModelCog(bot, services))
