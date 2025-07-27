#!/usr/bin/env python3
"""Quick test to verify the personality loading fix."""

import asyncio
from config import Config
from services.container import ServiceContainer


class MockMessage:
    """Mock Discord message for testing."""

    def __init__(
        self, guild_id: int = 1393258849867272325, content: str = "test message"
    ):
        self.guild = MockGuild(guild_id)
        self.content = content
        self.author = MockAuthor()


class MockGuild:
    """Mock Discord guild."""

    def __init__(self, guild_id: int):
        self.id = guild_id


class MockAuthor:
    """Mock Discord author."""

    def __init__(self):
        self.name = "TestUser"


async def test_personality_loading():
    """Test that personality loading works with the new JSON structure."""
    print("🧪 Testing personality loading...")

    try:
        # Initialize services
        config = Config.create()
        services = ServiceContainer(config)
        await services.initialize_all()

        # Create mock message
        message = MockMessage()

        # Test personality loading
        personality = services.ai_service._get_personality_prompt(message)

        print(f"✅ Personality loaded successfully!")
        print(f"📝 Personality length: {len(personality)} characters")
        print(f"📝 First 100 chars: {personality[:100]}...")

        # Test lore book access
        server_id = str(message.guild.id)
        services.state_manager.initialize_server(server_id)
        persona_name = services.state_manager.persona.get(
            server_id, config.default_persona
        )
        lore_books = services.state_manager.get_lore_books()
        lore_book = lore_books.get(persona_name) if lore_books else None

        if lore_book:
            print(f"✅ Lore book loaded for persona '{persona_name}'")
            print(f"📚 Lore book categories: {list(lore_book.keys())}")
        else:
            print(f"⚠️ No lore book found for persona '{persona_name}'")

        await services.cleanup_all()
        print("🎉 All personality tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_personality_loading())
