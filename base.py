import discord
import asyncio
import sys
from typing import Any

from discord.ext import commands

# Import new configuration and service systems
from config import Config, ConfigError
from config.cogs import get_enabled_cogs
from services.container import ServiceContainer
from cogs import COMMANDS, EVENT_HANDLERS


class GeminyaBot(commands.Bot):
    """Enhanced Geminya bot with dependency injection and service management."""

    def __init__(
        self, config: Config, services: ServiceContainer, *args: Any, **kwargs: Any
    ) -> None:
        self.config = config
        self.services = services
        self.logger = services.get_logger("bot")

        # Initialize Discord bot
        super().__init__(*args, **kwargs)

        self.logger.info("GeminyaBot initialized with new architecture")

    async def setup_hook(self):
        """Setup hook called when the bot is starting."""
        self.logger.info("Starting bot setup...")

        try:
            # Initialize all services
            await self.services.initialize_all()

            # Determine if we are in which mode
            mode = getattr(self.config, 'mode', None)
            skip_cogs = set()

            # if mode == "NIGLER":
            #     skip_cogs = {
            #         "cogs.commands.anidle",
            #         "cogs.commands.guess_anime",
            #         "cogs.commands.anitrace",
            #         "cogs.commands.nekogif",
            #         "cogs.commands.dad_joke",
            #         "cogs.commands.yo_mama",
            #         "cogs.commands.useless_fact",
            #         "cogs.commands.saucenao",
            #     }

            # Filter command cogs
            enabled_commands = get_enabled_cogs(COMMANDS, self.config.mode)
            for cog in enabled_commands:
                cog_name = cog.split(".")[-1]
                try:
                    await self.load_extension(f"{cog}")
                    self.logger.info(f"Loaded command cog: {cog_name}")
                except Exception as e:
                    self.logger.error(f"Failed to load command cog {cog_name}: {e}")
            
            # Log skipped cogs for transparency
            skipped = set(COMMANDS) - set(enabled_commands)
            if skipped:
                self.logger.info(f"Skipped cogs: {', '.join(s.split('.')[-1] for s in skipped)}")

            # Load event handler cogs
            for cog in EVENT_HANDLERS:
                cog_name = cog.split(".")[-1]
                try:
                    await self.load_extension(f"{cog}")
                    self.logger.info(f"Loaded event handler: {cog_name}")
                except Exception as e:
                    self.logger.error(f"Failed to load event handler {cog_name}: {e}")

            # Sync commands (preserve Activity Entry Point commands)
            self.logger.info("Syncing application commands...")
            if len(self.tree.get_commands()) > 0:
                self.logger.info(
                    "Command syncing may take a moment due to Discord rate limits"
                )
                try:
                    # Fetch existing commands to find Entry Point commands (type 4)
                    # that Discord creates for Activities — these must be included
                    # in bulk sync or Discord rejects the request (error 50240)
                    existing = await self.http.get_global_commands(self.application_id)
                    entry_points = [c for c in existing if c.get('type') == 4]

                    if entry_points:
                        # Build payload manually: bot commands + entry point commands
                        payload = [cmd.to_dict(self.tree) for cmd in self.tree.get_commands()]
                        payload.extend(entry_points)
                        await self.http.bulk_upsert_global_commands(self.application_id, payload)
                        self.logger.info(f"Synced commands (preserved {len(entry_points)} Entry Point command(s))")
                    else:
                        await self.tree.sync()
                except discord.HTTPException as e:
                    if e.code == 50240:
                        self.logger.warning("Command sync skipped: Entry Point conflict. Commands from previous sync are still active.")
                    else:
                        raise

            self.logger.info(
                f"Bot setup completed. Loaded {len(self.commands)} commands"
            )

        except Exception as e:
            self.logger.error(f"Critical error during bot setup: {e}")
            await self.services.cleanup_all()
            raise

    async def close(self):
        """Cleanup when the bot is shutting down."""
        self.logger.info("Bot is shutting down...")

        try:
            await self.services.cleanup_all()
        except Exception as e:
            self.logger.error(f"Error during service cleanup: {e}")

        await super().close()
        self.logger.info("Bot shutdown completed")


async def main():
    """Main entry point with proper error handling."""
    try:
        # Load configuration
        config = Config.create()
        config.validate()

        # Create service container
        services = ServiceContainer(config)
        logger = services.get_logger("main")

        logger.info("Starting Geminya bot...")
        logger.info(f"Configuration: {config.to_dict()}")

        # Configure Discord intents
        intents = discord.Intents.default()
        intents.message_content = True

        # Create bot instance
        bot = GeminyaBot(
            config=config,
            services=services,
            command_prefix=[],  # Using slash commands
            intents=intents,
            help_command=None,
        )

        # Start the bot
        async with bot:
            await bot.start(config.discord_token)

    except ConfigError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())
