# Development Guide

## Quick Start

1. **Test architecture**: `python test_architecture.py`
2. **Start development**: `python start.py`
3. **Check logs**: `logs/` directory

## Project Structure

```
├── config/config.py         # Configuration system
├── services/                # Core services
│   ├── container.py         # Dependency injection
│   ├── state_manager.py     # State management
│   ├── ai_service.py        # AI operations
│   └── error_handler.py     # Error handling
├── cogs/                    # Discord cogs
│   ├── base_command.py      # Command base class
│   ├── base_event.py        # Event base class
│   ├── commands/            # Command implementations
│   └── events/              # Event handlers
├── utils/                   # Utilities
│   ├── logging.py           # Centralized logging
│   └── utils.py             # General utilities
└── lang/en.json             # Personality & responses
```

## Creating New Features

### Adding Commands

1. **Create command file** in `cogs/commands/`:

```python
# cogs/commands/my_command.py
import discord
from discord import app_commands
from discord.ext import commands
from cogs.base_command import BaseCommand

class MyCommand(BaseCommand):
    def __init__(self, bot, services):
        super().__init__(bot, services)

    @app_commands.command(name="mycommand", description="My new command")
    async def my_command(self, interaction: discord.Interaction):
        # Access services via self.ai_service, self.state_manager, etc.
        model = self.state_manager.get_model(str(interaction.guild_id))

        await interaction.response.send_message(f"Using model: {model}")

async def setup(bot):
    services = getattr(bot, 'services', None)
    if services:
        await bot.add_cog(MyCommand(bot, services))
```

2. **Auto-loading**: Commands in `cogs/commands/` are loaded automatically.

### Adding Events

1. **Create event file** in `cogs/events/`:

```python
# cogs/events/my_event.py
import discord
from discord.ext import commands
from cogs.base_event import BaseEventHandler

class MyEvent(BaseEventHandler):
    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Access services
        self.logger.info(f"Member joined: {member.name}")

        # Use state manager
        self.state_manager.initialize_server(str(member.guild.id))

async def setup(bot):
    services = getattr(bot, 'services', None)
    if services:
        await bot.add_cog(MyEvent(bot, services))
```

### Adding Services

1. **Create service** in `services/`:

```python
# services/my_service.py
import logging
from config import Config

class MyService:
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger

    async def initialize(self) -> None:
        self.logger.info("My service initialized")

    async def cleanup(self) -> None:
        self.logger.info("My service cleanup completed")
```

2. **Add to container**:

```python
# services/container.py
from services.my_service import MyService

class ServiceContainer:
    def __init__(self, config: Config):
        # ... existing services
        self.my_service = MyService(config, logger_manager.get_logger("my_service"))

    async def initialize(self) -> None:
        # ... existing initialization
        await self.my_service.initialize()
```

## Testing

### Running Tests

```bash
# Run all tests
python test_architecture.py

# Verbose output
python test_architecture.py --verbose
```

### Writing Tests

Add test methods to `ArchitectureTest` class:

```python
@test("My new feature")
async def test_my_feature(self):
    """Test my new feature."""
    from services.my_service import MyService

    config = Config.create()
    my_service = MyService(config, logging.getLogger("test"))

    await my_service.initialize()
    # Test functionality
    assert my_service.some_method() == expected_result
    await my_service.cleanup()
```

## Debugging

### Logging

Use appropriate logger for context:

```python
class MyCommand(BaseCommand):
    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.logger = services.logger_manager.get_logger("commands")

    async def my_command(self, interaction):
        self.logger.info(f"Command executed by {interaction.user}")
        self.logger.debug(f"Command data: {interaction.data}")
```

### Error Handling

Use the error handler service:

```python
class MyCommand(BaseCommand):
    async def my_command(self, interaction):
        try:
            # Risky operation
            result = await some_api_call()
        except Exception as e:
            error_msg = self.error_handler.handle_api_error(e, "my_command")
            await interaction.response.send_message(error_msg, ephemeral=True)
```

### Debug Mode

Enable debug logging in config:

```yaml
discord:
  debug: true
logging:
  level: "DEBUG"
```

## Best Practices

### Service Usage

**DO:**

```python
class MyCommand(BaseCommand):
    async def my_command(self, interaction):
        # Use injected services
        model = self.state_manager.get_model(str(interaction.guild_id))
        response = await self.ai_service.get_response(message, str(interaction.guild_id))
```

**DON'T:**

```python
# Avoid direct imports of legacy code
from constants import DEFAULT_MODEL  # Deprecated
from utils.ai_utils import get_response  # Use ai_service instead
```

### Error Handling

**DO:**

```python
async def my_operation(self):
    try:
        result = await risky_operation()
        return result
    except SpecificException as e:
        self.logger.error(f"Specific error: {e}")
        raise
    except Exception as e:
        self.logger.error(f"Unexpected error: {e}")
        return self.error_handler.handle_api_error(e, "my_operation")
```

**DON'T:**

```python
async def my_operation(self):
    try:
        return await risky_operation()
    except:  # Too broad
        pass  # Silent failure
```

### Configuration

**DO:**

```python
class MyService:
    def __init__(self, config: Config):
        self.api_key = config.my_api_key  # Type-safe access
        self.timeout = config.timeout if config.timeout > 0 else 30
```

**DON'T:**

```python
# Avoid global configuration access
from constants import MY_API_KEY  # Use dependency injection instead
```

## Migration from Legacy

### Gradual Migration

1. **Keep legacy code working** with deprecation warnings
2. **Create new features** using service architecture
3. **Migrate existing features** one at a time
4. **Remove deprecated code** after full migration

### Common Patterns

**Legacy Pattern:**

```python
# Old command style
class OldCommand(commands.Cog):
    @commands.command()
    async def old_cmd(self, ctx):
        from utils.ai_utils import get_response
        response = await get_response(ctx.message, DEFAULT_MODEL)
```

**New Pattern:**

```python
# New service-based style
class NewCommand(BaseCommand):
    @app_commands.command()
    async def new_cmd(self, interaction):
        response = await self.ai_service.get_response(
            interaction.message,
            str(interaction.guild_id)
        )
```

## Performance

### Service Initialization

Services are initialized once at startup:

```python
# Heavy operations in initialize()
async def initialize(self):
    self.expensive_resource = await load_expensive_data()

# Quick operations in methods
async def get_data(self):
    return self.expensive_resource.query(...)
```

### Memory Management

Clean up resources properly:

```python
async def cleanup(self):
    if self.connection:
        await self.connection.close()
    self.cache.clear()
```

### Caching

Use state manager for persistent data:

```python
# Cache in state manager
self.state_manager.set_cached_data(key, value)
cached = self.state_manager.get_cached_data(key)
```
