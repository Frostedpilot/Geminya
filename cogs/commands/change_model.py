import discord
from discord.ext import commands
from discord.ui import Select, View

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


class ModelSelect(Select):
    def __init__(self, services: ServiceContainer):
        self.services = services
        self.config = services.config

        options = [
            discord.SelectOption(label=name)
            for name in self.config.available_models.keys()
        ]
        super().__init__(
            placeholder="Choose a model...", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_model_name = self.values[0]
        model_id = self.config.available_models[selected_model_name]
        server_id = str(interaction.guild.id)

        # Use state manager to update model
        self.services.state_manager.set_model(server_id, model_id)

        await interaction.response.send_message(
            f"I've set the model to **{selected_model_name}**, nya! (´｡• ω •｡`)",
            ephemeral=True,
        )
        self.view.stop()


class ModelView(View):
    def __init__(self, services: ServiceContainer):
        super().__init__(timeout=60.0)
        self.add_item(ModelSelect(services))


class ChangeModelCog(BaseCommand):
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

    @commands.hybrid_command(
        name="changemodel",
        description="Change the AI model used by the bot in this server.",
    )
    async def change_model(self, ctx: commands.Context):
        """Change the AI model used by the bot."""
        if not ctx.guild:
            await ctx.send("This command can only be used in servers, nya!")
            return

        server_id = str(ctx.guild.id)
        current_model_id = self.state_manager.get_model(server_id)

        # Find current model name
        current_model_name = "Unknown"
        for name, model_id in self.config.available_models.items():
            if model_id == current_model_id:
                current_model_name = name
                break

        view = ModelView(self.services)
        await ctx.send(
            f"The current model is **{current_model_name}**, nya! "
            f"Please choose a new one from the list below, nya! (o^▽^o)",
            view=view,
        )

        self.logger.info(f"Model selection sent to {ctx.guild.name} ({server_id})")


async def setup(bot: commands.Bot):
    # Get services from bot instance
    if hasattr(bot, "services"):
        await bot.add_cog(ChangeModelCog(bot, bot.services))
    else:
        # Fallback for old architecture during transition
        from constants import AVAILABLE_MODELS

        class LegacyChangeModelCog(commands.Cog):
            def __init__(self, bot):
                self.bot = bot

            @commands.hybrid_command(
                name="changemodel", description="Change the model used by the bot."
            )
            async def change_model(self, ctx):
                await ctx.send(
                    "Model changing is temporarily unavailable during system upgrade, nya!"
                )

        await bot.add_cog(LegacyChangeModelCog(bot))
