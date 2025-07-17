# Development Guide

## Getting Started with Development

This guide covers how to extend and modify Geminya's functionality, from adding new commands to customizing the personality system.

## Project Architecture

### Bot Structure

```
GeminyaBot (commands.Bot)
├── Model Management (per-server AI model selection)
├── History Management (conversation context)
├── Lore Book System (trigger-based responses)
└── Cog System (modular commands and events)
```

### Key Design Patterns

1. **Cog-based Architecture**: Commands and events are organized into Discord.py cogs for modularity
2. **Async/Await**: All I/O operations use async patterns for performance
3. **Context Management**: Conversation history and server-specific settings maintained in memory
4. **Fallback Handling**: Graceful degradation when services are unavailable

## Adding New Commands

### Basic Command Structure

Create a new file in `cogs/commands/` (e.g., `my_command.py`):

```python
import discord
from discord.ext import commands


class MyCommandCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="mycommand",
        description="Description of what the command does"
    )
    async def my_command(self, ctx, parameter: str = None):
        """Command implementation with optional parameters."""

        # Access bot instance
        server_id = str(ctx.guild.id)
        current_model = self.bot.model.get(server_id, "default")

        # Respond with Geminya's personality
        await ctx.send(f"Nya! You used my command with: {parameter} ✨")


async def setup(bot):
    await bot.add_cog(MyCommandCog(bot))
```

### Command Best Practices

1. **Personality Integration**: Always respond in Geminya's voice with cat puns
2. **Error Handling**: Use try/catch blocks for external API calls
3. **Permissions**: Check user permissions when appropriate
4. **Rate Limiting**: Be mindful of Discord's rate limits

### Advanced Command Example

```python
from discord.ui import View, Select
import aiohttp


class CategorySelect(Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            discord.SelectOption(label="Option 1", value="opt1"),
            discord.SelectOption(label="Option 2", value="opt2"),
        ]
        super().__init__(placeholder="Choose...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        await interaction.response.send_message(
            f"You selected {selected}, nya! (◕‿◕)✨"
        )


class InteractiveView(View):
    def __init__(self, bot):
        super().__init__(timeout=300)  # 5 minute timeout
        self.add_item(CategorySelect(bot))


class AdvancedCommandCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="interactive")
    async def interactive_command(self, ctx):
        """Example of interactive command with UI components."""
        view = InteractiveView(self.bot)
        await ctx.send("Pick an option, nya! ✨", view=view)

    @commands.hybrid_command(name="api")
    async def api_command(self, ctx, query: str):
        """Example of command that calls external API."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"https://api.example.com/{query}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        await ctx.send(f"Found data: {data}, nya! ✨")
                    else:
                        await ctx.send("API request failed, nya! Try again later.")
            except Exception as e:
                await ctx.send("Something went wrong, nya! (╥﹏╥)")
                print(f"API error: {e}")


async def setup(bot):
    await bot.add_cog(AdvancedCommandCog(bot))
```

## Adding Event Handlers

### Basic Event Handler

Create a new file in `cogs/events/` (e.g., `my_event.py`):

```python
import discord
from discord.ext import commands


class MyEventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle when a new member joins the server."""
        # Get a default channel to send welcome message
        channel = member.guild.system_channel
        if channel:
            await channel.send(
                f"Welcome to the server, {member.mention}! "
                f"Nya! I'm Geminya, your friendly catgirl assistant! ✨"
            )

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle when someone adds a reaction."""
        if user == self.bot.user:
            return  # Ignore bot's own reactions

        # Example: React with cat emojis to specific reactions
        if str(reaction.emoji) == "❤️":
            await reaction.message.add_reaction("🐱")


async def setup(bot):
    await bot.add_cog(MyEventCog(bot))
```

### Available Events

Common Discord.py events you can handle:

- `on_message`: Message received
- `on_member_join/leave`: Member joins/leaves server
- `on_reaction_add/remove`: Reactions added/removed
- `on_voice_state_update`: Voice channel changes
- `on_guild_join/remove`: Bot added/removed from server

## Customizing AI Responses

### Modifying Personality

Edit `lang/en.json` to change Geminya's personality:

```json
{
  "personality": {
    "Geminya_Exp": "Your updated system prompt here..."
  }
}
```

### Adding Lore Book Entries

Add new trigger-based responses:

```json
{
  "lorebook": {
    "your_category": {
      "keywords": ["trigger", "words", "here"],
      "example_user": "Example user message",
      "example": "Geminya's example response with personality, nya! ✨"
    }
  }
}
```

### Custom Response Logic

Modify `utils/ai_utils.py` to change how responses are generated:

```python
def build_prompt(message, history=None, lore_book=None):
    # Your custom prompt building logic
    personality_prompt = get_sys_prompt()

    # Add custom context based on message content
    if "programming" in message.content.lower():
        personality_prompt += "\nYou're especially excited about coding today!"

    # Rest of prompt building...
    return final_prompt
```

## Working with Models

### Adding New AI Models

Update `constants.py`:

```python
AVAILABLE_MODELS = {
    "Your Model Name": "provider/model-id:variant",
    "Another Model": "different-provider/model:free",
    # ... existing models
}
```

### Model-Specific Logic

You can add conditional logic based on the selected model:

```python
async def get_response(message, model, history=None, lore_book=None):
    # Model-specific adjustments
    if "gpt" in model.lower():
        # Adjust for GPT models
        temperature = 0.8
    elif "deepseek" in model.lower():
        # Adjust for DeepSeek models
        temperature = 0.7

    # Use in API call...
```

## Database Integration

### Adding Persistent Storage

For features requiring data persistence, you can add database support:

```python
import sqlite3
import aiosqlite


class DatabaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "geminya.db"

    async def setup_db(self):
        """Initialize database tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    preferred_model TEXT,
                    custom_setting TEXT
                )
            """)
            await db.commit()

    @commands.hybrid_command(name="setpref")
    async def set_preference(self, ctx, setting: str):
        """Save user preference to database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO user_preferences (user_id, custom_setting) VALUES (?, ?)",
                (ctx.author.id, setting)
            )
            await db.commit()
        await ctx.send("Preference saved, nya! ✨")


async def setup(bot):
    cog = DatabaseCog(bot)
    await cog.setup_db()
    await bot.add_cog(cog)
```

## Testing Your Code

### Unit Testing

Create test files in a `tests/` directory:

```python
import unittest
from unittest.mock import Mock, AsyncMock
from utils.utils import split_response


class TestUtils(unittest.TestCase):
    def test_split_response_short(self):
        """Test that short responses aren't split."""
        response = "Short response nya!"
        result = split_response(response)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], response)

    def test_split_response_long(self):
        """Test that long responses are split properly."""
        response = "Very long response. " * 100  # Over 1999 chars
        result = split_response(response)
        self.assertGreater(len(result), 1)
        for chunk in result:
            self.assertLessEqual(len(chunk), 1999)


if __name__ == "__main__":
    unittest.main()
```

### Integration Testing

Test bot commands manually:

```python
# test_bot.py
import asyncio
from base import GeminyaBot
import discord

async def test_commands():
    """Test bot commands in isolation."""
    intents = discord.Intents.default()
    intents.message_content = True
    bot = GeminyaBot(command_prefix=[], intents=intents)

    # Test model switching
    bot.model["123456789"] = "test-model"
    assert bot.model["123456789"] == "test-model"

    print("Basic tests passed!")

if __name__ == "__main__":
    asyncio.run(test_commands())
```

## Performance Optimization

### Caching Responses

Implement response caching to reduce API calls:

```python
import time
from functools import lru_cache


class ResponseCache:
    def __init__(self, max_age=300):  # 5 minutes
        self.cache = {}
        self.max_age = max_age

    def get(self, key):
        if key in self.cache:
            response, timestamp = self.cache[key]
            if time.time() - timestamp < self.max_age:
                return response
            else:
                del self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = (value, time.time())


# Use in AI utils
response_cache = ResponseCache()

async def get_response(message, model, history=None, lore_book=None):
    # Create cache key from message content and recent history
    cache_key = f"{message.content[:100]}_{model}"

    cached = response_cache.get(cache_key)
    if cached:
        return cached

    # Generate new response
    response = await generate_ai_response(...)
    response_cache.set(cache_key, response)
    return response
```

### Memory Management

Monitor memory usage for long-running bots:

```python
import psutil
import gc
from discord.ext import tasks


class MemoryMonitorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.memory_monitor.start()

    @tasks.loop(hours=1)
    async def memory_monitor(self):
        """Monitor memory usage and cleanup if needed."""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        if memory_mb > 500:  # If using more than 500MB
            print(f"High memory usage: {memory_mb:.1f}MB, running cleanup...")

            # Cleanup old history entries
            for channel_id in list(self.bot.history.keys()):
                if len(self.bot.history[channel_id]) > 10:
                    self.bot.history[channel_id] = self.bot.history[channel_id][-5:]

            gc.collect()
```

## Debugging Tips

### Logging Best Practices

```python
import logging

# Set up logger for your module
logger = logging.getLogger(__name__)

class MyCommandCog(commands.Cog):
    @commands.hybrid_command(name="debug")
    async def debug_command(self, ctx):
        try:
            # Your command logic
            logger.info(f"Debug command used by {ctx.author}")
            result = some_operation()
            logger.debug(f"Operation result: {result}")

        except Exception as e:
            logger.error(f"Error in debug command: {e}", exc_info=True)
            await ctx.send("Something went wrong, nya! Check the logs.")
```

### Error Handling Patterns

```python
async def safe_api_call(url):
    """Example of robust API call with proper error handling."""
    max_retries = 3
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:  # Rate limited
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    else:
                        logger.warning(f"API returned status {response.status}")
                        return None

        except asyncio.TimeoutError:
            logger.warning(f"Timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

    return None  # All retries failed
```

## Contributing Guidelines

### Code Style

1. **Follow PEP 8**: Use tools like `black` and `flake8`
2. **Type Hints**: Add type hints for function parameters and returns
3. **Docstrings**: Document all public functions and classes
4. **Comments**: Explain complex logic with inline comments

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-command

# Make your changes
# ... code changes ...

# Commit with descriptive message
git commit -m "Add new interactive command with dropdown UI"

# Push and create pull request
git push origin feature/new-command
```

### Pull Request Template

When submitting changes:

1. **Description**: What does this change do?
2. **Testing**: How was this tested?
3. **Breaking Changes**: Any backwards compatibility issues?
4. **Screenshots**: For UI changes, include screenshots

## Deployment Considerations

### Environment Variables

For production, use environment variables instead of `secrets.json`:

```python
import os

DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
```

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "base.py"]
```

### Monitoring and Health Checks

```python
from discord.ext import tasks
import aiohttp

class HealthCheckCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.health_check.start()

    @tasks.loop(minutes=5)
    async def health_check(self):
        """Report bot status to monitoring service."""
        try:
            # Check if bot is responsive
            latency = self.bot.latency * 1000  # Convert to ms

            # Report to monitoring service
            async with aiohttp.ClientSession() as session:
                await session.post('http://monitoring-service/health', json={
                    'status': 'healthy',
                    'latency': latency,
                    'guilds': len(self.bot.guilds),
                    'users': len(self.bot.users)
                })
        except Exception as e:
            logger.error(f"Health check failed: {e}")
```

This development guide should help you extend Geminya's functionality while maintaining code quality and the bot's personality. Remember to test thoroughly and follow the established patterns for consistency!
