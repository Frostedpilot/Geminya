#!/usr/bin/env python3
"""Startup script for the Geminya Discord bot.

This script provides a convenient way to start the bot with proper error handling,
configuration validation, and environment setup.
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path
from config import Config, ConfigError
from config.logging_config import setup_logging


def setup_environment():
    """Set up the environment for running the bot."""
    # Add current directory to Python path
    current_dir = Path(__file__).parent.absolute()
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))

    # Create necessary directories
    logs_dir = current_dir / "logs"
    logs_dir.mkdir(exist_ok=True)


def check_dependencies():
    """Check if all required dependencies are installed."""
    required_packages = [
        "discord.py",
        "openai",
        "yaml",
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package.replace(".py", "").replace("-", "_"))
        except ImportError:
            missing.append(package)

    if missing:
        print("❌ Missing required packages:")
        for package in missing:
            print(f"  • {package}")
        print("\nInstall them with: pip install " + " ".join(missing))
        return False

    return True


def check_configuration():
    """Check if configuration is valid."""
    try:
        from config import Config, ConfigError

        config = Config.create()
        config.set_mode("GEMINYA")  # Set default mode
        config.validate()

        return True, config
    except ConfigError as e:
        print(f"❌ Configuration error: {e}")
        return False, None
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return False, None


async def run_bot(config, test_mode=False):
    """Run the bot with the given configuration."""
    import discord
    from services.container import ServiceContainer
    from base import GeminyaBot

    try:
        # Create service container
        services = ServiceContainer(config)
        logger = services.get_logger("startup")

        logger.info("Starting Geminya bot...")
        if test_mode:
            logger.info(
                "Running in test mode - bot will start but not connect to Discord"
            )

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

        if test_mode:
            # In test mode, just initialize services and exit
            logger.info("Test mode: initializing services...")
            await services.initialize_all()
            logger.info("Test mode: services initialized successfully")
            await services.cleanup_all()
            logger.info("Test mode completed successfully")
            return

        # Start the bot
        async with bot:
            await bot.start(config.discord_token)

    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested by user")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Geminya Discord Bot")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (don't connect to Discord)",
    )
    parser.add_argument(
        "--check-config", action="store_true", help="Check configuration and exit"
    )
    parser.add_argument(
        "--check-deps", action="store_true", help="Check dependencies and exit"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    print("🐱 Geminya Discord Bot Startup")
    print("=" * 40)

    # Set up environment
    setup_environment()
    
    # Set up logging before doing anything else
    debug_mode = args.verbose
    setup_logging(debug_mode=debug_mode)
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Geminya bot startup initiated")

    # Check dependencies
    if args.check_deps or args.verbose:
        logger.info("Checking dependencies...")
        if not check_dependencies():
            logger.error("Dependency check failed")
            sys.exit(1)
        print("✅ All dependencies found")

    # Check configuration
    if args.check_config or args.verbose:
        print("🔍 Checking configuration...")
        config_valid, config = check_configuration()
        if not config_valid:
            sys.exit(1)
        print("✅ Configuration is valid")

        if args.check_config:
            print("\n📋 Configuration Summary:")
            print(f"  Language: {config.language}")
            print(f"  Max History: {config.max_history_length}")
            print(f"  Debug Mode: {config.debug}")
            print(f"  Default Model: {config.default_model}")
            print(
                f"  Active Servers: {len(config.active_servers) if config.active_servers else 'All'}"
            )
            sys.exit(0)
    else:
        config_valid, config = check_configuration()
        if not config_valid:
            sys.exit(1)

    # Run architecture tests if in test mode
    if args.test:
        print("🧪 Running architecture tests...")
        test_script = Path(__file__).parent / "test_architecture.py"
        if test_script.exists():
            import subprocess

            result = subprocess.run(
                [sys.executable, str(test_script)], capture_output=True, text=True
            )
            if result.returncode != 0:
                print("❌ Architecture tests failed:")
                print(result.stdout)
                print(result.stderr)
                sys.exit(1)
            print("✅ Architecture tests passed")

    # Start the bot
    try:
        print("🚀 Starting bot...")
        asyncio.run(run_bot(config, test_mode=args.test))
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
