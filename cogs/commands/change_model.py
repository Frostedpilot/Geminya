import discord
from discord.ext import commands
from discord.ui import Select, View

from constants import AVAILABLE_MODELS


class ModelSelect(Select):
    def __init__(self, bot):
        self.bot = bot
        options = [discord.SelectOption(label=name) for name in AVAILABLE_MODELS.keys()]
        super().__init__(
            placeholder="Choose a model...", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_model_name = self.values[0]
        model_id = AVAILABLE_MODELS[selected_model_name]
        server_id = str(interaction.guild.id)

        self.bot.model[server_id] = model_id
        discord.client._log.info(f"Set model for server {server_id} to {model_id}")

        # await interaction.response.send_message(
        #     f"I've set the model to **{selected_model_name}**, nya! (´｡• ω •｡`)"
        # )
        self.view.stop()


class ModelView(View):
    def __init__(self, bot):
        super().__init__()
        self.add_item(ModelSelect(bot))


class ChangeModelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="changemodel", description="Change the model used by the bot."
    )
    async def change_model(self, ctx):
        """Change the model used by the bot."""
        server_id = str(ctx.guild.id)
        current_model_id = self.bot.model.get(server_id, "default_model")

        current_model_name = self.bot.model
        for name, model_id in AVAILABLE_MODELS.items():
            if model_id == current_model_id:
                current_model_name = name
                break

        view = ModelView(self.bot)
        msg = await ctx.send(
            f"The current model is **{current_model_name}**, nya! Please choose a new one from the list below, nya! (o^▽^o)",
            view=view,
        )

        # Wait for the view to be stopped
        await view.wait()
        discord.client._log.info(
            f"Model change interaction sent to {ctx.guild.name} ({server_id})"
        )

        current_model_id = self.bot.model.get(server_id, "default_model")
        for name, model_id in AVAILABLE_MODELS.items():
            if model_id == current_model_id:
                current_model_name = name
                break

        await msg.edit(
            content=f"Model changed to **{current_model_name}** for {ctx.guild.name}, nya! (o^▽^o)",
            view=None,
        )


async def setup(bot):
    await bot.add_cog(ChangeModelCog(bot))
