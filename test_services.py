#!/usr/bin/env python3
"""Test script to verify service container initialization."""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.container import ServiceContainer
from config import Config


async def test_services():
    """Test that all services can be initialized."""
    try:
        # Create minimal config for testing
        config = Config(
            discord_token="test_token",
            discord_tokens=["test_token"],
            openrouter_api_key="test_key",
            saucenao_api_key="test_key",
            tavily_api_key="test_key",
            google_console_api_key="test_key",
            google_search_engine_id="test_id",
        )
        container = ServiceContainer(config)
        await container.initialize_all()
        print("✅ Service container initialized successfully")

        # Test waifu service access
        container.waifu_service
        print("✅ Waifu service accessible")

        await container.cleanup_all()
        print("✅ Service container cleaned up successfully")

    except Exception as e:
        print(f"❌ Error initializing services: {e}")
        return False

    return True


if __name__ == "__main__":
    result = asyncio.run(test_services())
    sys.exit(0 if result else 1)
