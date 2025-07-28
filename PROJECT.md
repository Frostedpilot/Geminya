# Geminya Discord Bot - Project Documentation

## Overview

Geminya is a Discord bot with AI conversation capabilities built using a service-oriented architecture with dependency injection. The bot provides AI-powered conversations through OpenRouter API integration and supports model/persona switching.

## Architecture

### Core Design Principles
- **Service-Oriented Architecture**: Loose coupling via dependency injection
- **Type-Safe Configuration**: YAML with environment variable support  
- **Centralized Logging**: Multi-logger system with file rotation
- **Error Handling**: Unified error management and statistics
- **Backward Compatibility**: Legacy code support with deprecation warnings

### Project Structure
```
├── base.py                 # Main bot entry point with new architecture
├── start.py               # Production startup script with CLI options
├── test_architecture.py   # Architecture validation tests
├── config.yml             # Main configuration file
├── secrets.json           # Secret tokens (not in version control)
├── requirements.txt       # Python dependencies
├── config/
│   ├── __init__.py
│   └── config.py          # Type-safe configuration management
├── services/
│   ├── __init__.py
│   ├── container.py       # Dependency injection container
│   ├── state_manager.py   # Bot state and conversation history
│   ├── ai_service.py      # AI operations and OpenRouter integration
│   ├── error_handler.py   # Error handling and statistics
│   └── mcp_client.py      # Model Context Protocol client
├── cogs/
│   ├── __init__.py
│   ├── base_command.py    # Base class for all commands
│   ├── base_event.py      # Base class for all events
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── change_model.py     # AI model selection command
│   │   └── change_persona.py   # AI persona selection command
│   └── events/
│       ├── __init__.py
│       ├── on_ready.py         # Bot initialization
│       ├── on_message.py       # Message processing
│       └── on_command_error.py # Error handling
├── utils/
│   ├── __init__.py
│   ├── logging.py         # Centralized logging setup
│   ├── config_load.py     # Legacy configuration support
│   └── utils.py           # General utilities
├── lang/
│   └── en.json            # Personality definitions and responses
├── logs/                  # Log files (created at runtime)
│   ├── geminya.log        # Main application log
│   ├── messages.log       # Message handling log
│   └── errors.log         # Error tracking log
├── personalities/         # Personality files directory
└── mcp_servers/           # MCP server implementations
    └── duckduckgo.py
```

## Configuration

### Environment Setup
Required environment variables:
```bash
DISCORD_TOKEN=your_discord_bot_token
OPENROUTER_API_KEY=your_openrouter_api_key
```

### config.yml Structure
```yaml
discord:
  token: "${DISCORD_TOKEN}"
  prefix: "!"
  debug: false

openrouter:
  api_key: "${OPENROUTER_API_KEY}"
  base_url: "https://openrouter.ai/api/v1"

models:
  default: "anthropic/claude-3-haiku"
  check: "anthropic/claude-3-haiku"
  available:
    "Claude 3 Haiku": "anthropic/claude-3-haiku"
    "Claude 3.5 Sonnet": "anthropic/claude-3-5-sonnet-20241022"
    "DeepSeek V3": "deepseek/deepseek-chat"
    "GPT-4o Mini": "openai/gpt-4o-mini"

bot:
  max_history_length: 10
  language: "en"
  active_servers: []

logging:
  level: "INFO"
  max_file_size: 10485760
  backup_count: 5
  format: "%Y-%m-%d %H:%M:%S | %8s | %s | %s"
```

### secrets.json (Legacy Support)
```json
{
  "DISCORD_BOT_TOKEN": "your_token",
  "OPENROUTER_API_KEY": "your_key"
}
```

## Core Services

### ServiceContainer (`services/container.py`)
Central dependency injection container managing all services:
```python
services = ServiceContainer(config)
await services.initialize_all()  # Initialize all services
await services.cleanup_all()     # Cleanup resources
```

Available services:
- `config`: Configuration management
- `state_manager`: Bot state and history  
- `ai_service`: AI operations
- `error_handler`: Error management
- `logger_manager`: Logging system

### StateManager (`services/state_manager.py`)
Manages conversation history, model preferences, and lore book data:
```python
# Model management
state_manager.set_model(server_id, model_id)
model = state_manager.get_model(server_id)

# History management  
state_manager.add_message(channel_id, author_id, name, nick, content)
history = state_manager.get_history(channel_id)

# Persona management
state_manager.set_persona(server_id, persona_name)
persona = state_manager.get_persona(server_id)
```

### AIService (`services/ai_service.py`)
Handles AI operations and OpenRouter API communication:
```python
# Generate response
response = await ai_service.get_response(message, server_id)

# Check if should respond
should_respond = await ai_service.get_check_response(prompt)
```

### ErrorHandler (`services/error_handler.py`)
Centralized error handling with statistics and rate limiting:
```python
# Handle API errors
message = error_handler.handle_api_error(exception, context)

# Get error statistics
stats = error_handler.get_error_stats()
```

## Commands

### Available Commands
- `/changemodel` - Interactive AI model selection via dropdown
- `/changepersona` - Change the bot's personality

### Base Classes

#### BaseCommand (`cogs/base_command.py`)
Base class for all command cogs with service injection:
```python
class MyCommand(BaseCommand):
    def __init__(self, bot, services):
        super().__init__(bot, services)
        # Access: self.config, self.state_manager, self.ai_service, etc.

    @app_commands.command()
    async def my_command(self, interaction):
        model = self.state_manager.get_model(str(interaction.guild_id))
```

#### BaseEventHandler (`cogs/base_event.py`)
Base class for all event handlers with service injection:
```python
class MyEvent(BaseEventHandler):
    @commands.Cog.listener()
    async def on_message(self, message):
        await self.state_manager.add_message(...)
```

## Events

### Message Processing (`cogs/events/on_message.py`)
- Handles AI response generation
- Manages conversation history
- Detects mentions and keywords
- Processes lore book triggers

### Bot Initialization (`cogs/events/on_ready.py`)
- Initializes server states
- Sets bot status and activity
- Logs startup information

### Error Handling (`cogs/events/on_command_error.py`)
- Graceful command error handling
- User-friendly error messages
- Error logging and statistics

## Development

### Installation & Setup
1. **Install dependencies:**
   ```bash
   pip install discord.py openai pyyaml aiohttp
   ```

2. **Configure environment:**
   ```bash
   # Copy and edit configuration
   cp config.yml.example config.yml
   
   # Set environment variables
   export DISCORD_TOKEN="your_token"
   export OPENROUTER_API_KEY="your_key"
   ```

3. **Test & Run:**
   ```bash
   python test_architecture.py  # Validate setup
   python start.py              # Start bot
   ```

### Testing
Architecture validation test suite:
```bash
python test_architecture.py          # Run all tests
python test_architecture.py --verbose # Detailed output
```

Test coverage includes:
- Configuration loading and validation
- Service container initialization
- State manager functionality
- AI service setup
- Error handler operations
- Base class inheritance
- Logging system
- Backward compatibility

### Adding New Features

**New Command:**
```python
# cogs/commands/my_command.py
from cogs.base_command import BaseCommand

class MyCommand(BaseCommand):
    def __init__(self, bot, services):
        super().__init__(bot, services)

    @app_commands.command(name="mycommand", description="My new command")
    async def my_command(self, interaction: discord.Interaction):
        # Use services: self.ai_service, self.state_manager, etc.
        pass

async def setup(bot):
    services = getattr(bot, 'services', None)
    await bot.add_cog(MyCommand(bot, services))
```

**New Event:**
```python
# cogs/events/my_event.py
from cogs.base_event import BaseEventHandler

class MyEvent(BaseEventHandler):
    @commands.Cog.listener()
    async def on_my_event(self, data):
        # Handle event with service access
        pass

async def setup(bot):
    services = getattr(bot, 'services', None)
    await bot.add_cog(MyEvent(bot, services))
```

### Logging System
Multiple specialized loggers with file rotation:
```python
logger_manager = services.get_logger_manager()

# Get specific loggers
main_logger = logger_manager.get_logger("main")
message_logger = logger_manager.get_message_logger()
ai_logger = logger_manager.get_ai_logger()
error_logger = logger_manager.get_error_logger()
```

Log files:
- `logs/geminya.log` - Main application log
- `logs/messages.log` - Message handling
- `logs/errors.log` - Error tracking

## Legacy Migration

### Backward Compatibility
Old imports continue working with deprecation warnings:
```python
from constants import DISCORD_TOKEN      # Still works, shows warning
from utils.utils import split_response   # Still works, shows warning
```

### Migration Patterns
**Legacy Pattern:**
```python
# Old command style
class OldCommand(commands.Cog):
    @commands.command()
    async def old_cmd(self, ctx):
        from constants import DEFAULT_MODEL
        # Direct utility imports
```

**New Pattern:**
```python
# New service-based style
class NewCommand(BaseCommand):
    @app_commands.command()
    async def new_cmd(self, interaction):
        model = self.state_manager.get_model(server_id)
        response = await self.ai_service.get_response(...)
```

## Dependencies

### Core Requirements
- Python 3.8+ (3.12+ recommended)
- discord.py >= 2.3.0
- openai >= 1.0.0
- aiohttp >= 3.8.0
- PyYAML >= 6.0

### Optional Dependencies
- coloredlogs >= 15.0 (enhanced logging)
- psutil >= 5.9.0 (system monitoring)
- pytest >= 7.0.0 (testing)

## Troubleshooting

### Common Issues

**Bot Token Error:**
- Verify `DISCORD_TOKEN` environment variable
- Check token format and validity
- Ensure bot has proper permissions

**AI API Issues:**
- Verify `OPENROUTER_API_KEY` environment variable
- Check API credits and rate limits
- Test different models for compatibility

**Permission Errors:**
- Ensure bot has required Discord permissions:
  - Send Messages
  - Use Slash Commands  
  - Read Message History
  - Embed Links

**Module Import Errors:**
- Install all required dependencies
- Check Python version compatibility
- Verify virtual environment activation

### Performance Optimization
- Adjust `max_history_length` for memory usage
- Monitor log file sizes and rotation
- Use background tasks for long operations
- Implement caching for frequently accessed data

## Security Considerations

- Never commit `secrets.json` to version control
- Use environment variables for sensitive data
- Implement rate limiting for API calls
- Validate all user inputs
- Monitor error logs for potential issues
- Keep dependencies updated for security patches

## Version History

### Current Features
- AI-powered conversations via OpenRouter
- Interactive model and persona selection
- Service-oriented architecture with DI
- Comprehensive error handling and logging
- Backward compatibility with legacy code
- Automatic command and event loading

### Planned Features
- Database persistence for conversation history
- Web dashboard for configuration
- Plugin system for custom commands
- Voice channel integration
- Metrics and monitoring dashboard
- Enhanced caching system
