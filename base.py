import discord
from typing import Any

from discord.ext import commands
from constants import DISCORD_TOKEN
from cogs import COMMANDS, EVENT_HANDLERS


class GeminyaBot(commands.Bot):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.model = {}
        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        for cog in COMMANDS:
            cog_name = cog.split(".")[-1]
            discord.client._log.info(f"Loaded Command {cog_name}")
            await self.load_extension(f"{cog}")
        for cog in EVENT_HANDLERS:
            cog_name = cog.split(".")[-1]
            discord.client._log.info(f"Loaded Event Handler {cog_name}")
            await self.load_extension(f"{cog}")
        print(
            "If syncing commands is taking longer than usual you are being ratelimited"
        )
        await self.tree.sync()
        discord.client._log.info(f"Loaded {len(self.commands)} commands")


intents = discord.Intents.default()
intents.message_content = True
bot = GeminyaBot(command_prefix=[], intents=intents, help_command=None)

if DISCORD_TOKEN is None:
    raise ValueError("DISCORD_BOT_TOKEN is not set in secrets.json")

bot.run(DISCORD_TOKEN, reconnect=True)
