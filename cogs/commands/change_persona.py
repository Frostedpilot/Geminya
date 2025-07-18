import discord
from discord.ext import commands
from discord.ui import Select, View

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


class PersonaSelect(Select):
    def __init__(self, services: ServiceContainer):
        self.services = services
        self.config = services.config

        options = [
            discord.SelectOption(label=name)
            for name in set(self.config.personas.keys())
        ]
        super().__init__(
            placeholder="Choose a persona...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        selected_persona_name = self.values[0]
        server_id = str(interaction.guild.id)

        # Use state manager to update persona
        self.services.state_manager.set_persona(server_id, selected_persona_name)

        self.view.stop()


class PersonaView(View):
    def __init__(self, services: ServiceContainer):
        super().__init__(timeout=60.0)
        self.add_item(PersonaSelect(services))


class ChangePersonaCog(BaseCommand):
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

        server_id = str(ctx.guild.id)

        # Find current persona name
        # Make sure server is initialized
        self.state_manager.initialize_server(server_id)
        current_persona_name = self.state_manager.get_persona(server_id)

        view = PersonaView(self.services)

        msg = await ctx.send(
            f"The current persona is **{current_persona_name}**, nya! "
            f"Please choose a new one from the list below, nya! (o^▽^o)",
            view=view,
        )

        await view.wait()

        await msg.edit(
            content=f"I've set the persona to **{self.state_manager.get_persona(server_id)}**, nya! (´｡• ω •｡`)",
            view=None,  # Remove the view after selection
        )

        self.logger.info(f"Persona selection sent to {ctx.guild.name} ({server_id})")


async def setup(bot: commands.Bot):
    # Get services from bot instance
    await bot.add_cog(ChangePersonaCog(bot, bot.services))
