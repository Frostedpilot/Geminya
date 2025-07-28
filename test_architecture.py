#!/usr/bin/env python3
"""Test script for the refactored Geminya bot architecture.

This script validates that all components work correctly after the refactoring.
Run this before starting the bot to ensure everything is properly configured.
"""

import asyncio
import sys
import traceback
from pathlib import Path


class ArchitectureTest:
    """Test suite for the new bot architecture."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def test(name: str):
        """Decorator for test methods."""

        def decorator(func):
            async def wrapper(self, *args, **kwargs):
                try:
                    print(f"Testing {name}... ", end="")
                    await func(self, *args, **kwargs)
                    print("✅ PASSED")
                    self.passed += 1
                except Exception as e:
                    print(f"❌ FAILED: {e}")
                    self.failed += 1
                    self.errors.append(f"{name}: {e}")
                    if "--verbose" in sys.argv:
                        print(f"  Error details: {traceback.format_exc()}")

            return wrapper

        return decorator

    @test("Configuration system")
    async def test_config(self):
        """Test configuration loading."""
        from config import Config, ConfigError

        # Test file-based config
        config = Config.create()
        assert config is not None
        assert hasattr(config, "discord_token")
        assert hasattr(config, "openrouter_api_key")

        # Test validation
        config.validate()

    @test("Service container initialization")
    async def test_service_container(self):
        """Test service container creation."""
        from config import Config
        from services.container import ServiceContainer

        config = Config.create()
        services = ServiceContainer(config)

        assert services.config is not None
        assert services.state_manager is not None
        assert services.ai_service is not None
        assert services.error_handler is not None
        assert services.logger_manager is not None

    @test("State manager")
    async def test_state_manager(self):
        """Test state manager functionality."""
        from config import Config
        from services.state_manager import StateManager
        from utils.logging import setup_logging

        config = Config.create()
        logger_manager = setup_logging(config)
        state_manager = StateManager(config, logger_manager.get_logger("test"))

        await state_manager.initialize()

        # Test model management
        state_manager.set_model("test_server", "test_model")
        assert state_manager.get_model("test_server") == "test_model"

        # Test history management
        state_manager.add_message(
            channel_id=456,
            author_id=123,
            author_name="TestUser",
            nick=None,
            content="Test message",
        )
        history = state_manager.get_history(456)
        assert len(history) == 1
        assert history[0]["content"] == "Test message"

        await state_manager.cleanup()

    @test("AI service initialization")
    async def test_ai_service(self):
        """Test AI service setup."""
        from config import Config
        from services.state_manager import StateManager
        from services.ai_service import AIService
        from services.mcp_client import MCPClientManager
        from utils.logging import setup_logging

        config = Config.create()
        logger_manager = setup_logging(config)
        state_manager = StateManager(config, logger_manager.get_logger("test"))
        mcp_client = MCPClientManager(config, state_manager, logger_manager.get_logger("test"))
        ai_service = AIService(config, state_manager, logger_manager.get_ai_logger(), mcp_client)

        await state_manager.initialize()
        await ai_service.initialize()

        assert ai_service.client is not None

        await ai_service.cleanup()
        await state_manager.cleanup()

    @test("Error handler")
    async def test_error_handler(self):
        """Test error handling functionality."""
        from config import Config
        from services.error_handler import ErrorHandler
        from utils.logging import setup_logging

        config = Config.create()
        logger_manager = setup_logging(config)
        error_handler = ErrorHandler(config, logger_manager.get_error_logger())

        # Test API error handling
        test_error = Exception("Test error")
        message = error_handler.handle_api_error(test_error, "test context")
        assert "Something went wrong" in message

        # Test error stats
        stats = error_handler.get_error_stats()
        assert stats["total_errors"] > 0

        error_handler.reset_error_count()
        stats = error_handler.get_error_stats()
        assert stats["total_errors"] == 0

    @test("Base command class")
    async def test_base_command(self):
        """Test base command functionality."""
        from discord.ext import commands
        from config import Config
        from services.container import ServiceContainer
        from cogs.base_command import BaseCommand

        config = Config.create()
        services = ServiceContainer(config)

        # Create a mock bot
        class MockBot(commands.Bot):
            def __init__(self):
                # Mock bot for testing purposes
                pass

        bot = MockBot()

        # Test base command initialization
        base_cmd = BaseCommand(bot, services)
        assert base_cmd.bot is bot
        assert base_cmd.services is services
        assert base_cmd.config is config
        assert base_cmd.state_manager is services.state_manager
        assert base_cmd.ai_service is services.ai_service

    @test("Base event handler class")
    async def test_base_event(self):
        """Test base event handler functionality."""
        from discord.ext import commands
        from config import Config
        from services.container import ServiceContainer
        from cogs.base_event import BaseEventHandler

        config = Config.create()
        services = ServiceContainer(config)

        # Create a mock bot
        class MockBot(commands.Bot):
            def __init__(self):
                # Mock bot for testing purposes
                pass

        bot = MockBot()

        # Test base event handler initialization
        base_event = BaseEventHandler(bot, services)
        assert base_event.bot is bot
        assert base_event.services is services
        assert base_event.config is config
        assert base_event.state_manager is services.state_manager
        assert base_event.ai_service is services.ai_service

    @test("Logging system")
    async def test_logging(self):
        """Test logging configuration."""
        from config import Config
        from utils.logging import setup_logging

        config = Config.create()
        logger_manager = setup_logging(config)

        # Test logger creation
        main_logger = logger_manager.get_logger("main")
        assert main_logger is not None

        message_logger = logger_manager.get_message_logger()
        assert message_logger is not None

        ai_logger = logger_manager.get_ai_logger()
        assert ai_logger is not None

        error_logger = logger_manager.get_error_logger()
        assert error_logger is not None

    @test("Backward compatibility")
    async def test_backward_compatibility(self):
        """Test that old imports still work with deprecation warnings."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # This should work but issue deprecation warnings
            from constants import DISCORD_TOKEN, DEFAULT_MODEL
            from utils.utils import split_response

            # Check that warnings were issued
            assert len(w) > 0
            assert any("deprecated" in str(warning.message).lower() for warning in w)

            # Check that values are accessible
            assert DISCORD_TOKEN is not None
            assert DEFAULT_MODEL is not None

            # Test utility function
            result = split_response("Short message")
            assert len(result) == 1

    @test("Configuration validation")
    async def test_config_validation(self):
        """Test configuration validation."""
        from config import Config, ConfigError

        # Test invalid configuration
        try:
            invalid_config = Config(
                discord_token="",  # Empty token should fail validation
                openrouter_api_key="",
            )
            invalid_config.validate()
            assert False, "Should have raised ConfigError"
        except ConfigError:
            pass  # Expected

    async def run_tests(self):
        """Run all tests."""
        print("🧪 Running Geminya Architecture Tests\n")

        # Run all test methods
        test_methods = [
            self.test_config,
            self.test_service_container,
            self.test_state_manager,
            self.test_ai_service,
            self.test_error_handler,
            self.test_base_command,
            self.test_base_event,
            self.test_logging,
            self.test_backward_compatibility,
            self.test_config_validation,
        ]

        for test_method in test_methods:
            await test_method()

        # Print results
        print("\n📊 Test Results:")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(
            f"📈 Success Rate: {(self.passed / (self.passed + self.failed)) * 100:.1f}%"
        )

        if self.errors:
            print("\n🔍 Errors:")
            for error in self.errors:
                print(f"  • {error}")

        if self.failed == 0:
            print(
                "\n🎉 All tests passed! The refactored architecture is working correctly."
            )
        else:
            print("\n⚠️  Some tests failed. Please review the errors above.")
            sys.exit(1)


async def main():
    """Main test runner."""
    test_runner = ArchitectureTest()
    await test_runner.run_tests()


if __name__ == "__main__":
    print("Geminya Bot Architecture Test Suite")
    print("=" * 40)

    # Check if required files exist
    required_files = [
        "config/config.py",
        "services/container.py",
        "services/state_manager.py",
        "services/ai_service.py",
        "services/error_handler.py",
        "utils/logging.py",
        "cogs/base_command.py",
        "cogs/base_event.py",
    ]

    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print("❌ Missing required files:")
        for file_path in missing_files:
            print(f"  • {file_path}")
        print("\nPlease ensure all refactored components are in place.")
        sys.exit(1)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Test runner failed: {e}")
        if "--verbose" in sys.argv:
            traceback.print_exc()
        sys.exit(1)
