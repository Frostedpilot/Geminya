# Geminya Discord Bot

A modern Discord bot with AI conversation capabilities, built with service-oriented architecture and dependency injection.

## Features

- 🤖 AI conversations via OpenRouter API
- 🏗️ Service-oriented architecture with dependency injection
- 📊 State management for models and conversation history
- 🎯 Lore book integration for contextual responses
- 📝 Comprehensive logging and error handling
- 🔄 Backward compatibility with legacy code
- ✅ Full test suite for architecture validation

## Quick Start

1. **Install dependencies:**

```bash
pip install discord.py openai pyyaml
```

2. **Configure:**

```bash
cp config.yml.example config.yml
# Edit config.yml with your tokens
```

3. **Test & Run:**

```bash
python test_architecture.py  # Validate setup
python start.py              # Start bot
```

## Architecture

```
config/          # Configuration system with validation
services/        # Core services (AI, state, error handling)
cogs/            # Commands and events with base classes
utils/           # Utilities and logging
lang/            # Language files and personality
```

**Key Components:**

- `ServiceContainer`: Dependency injection container
- `StateManager`: Conversation history and model preferences
- `AIService`: OpenRouter API integration
- `ErrorHandler`: Centralized error management
- `BaseCommand`/`BaseEventHandler`: Inheritance for cogs

## Configuration

`config.yml` supports environment variable substitution:

```yaml
discord:
  token: "${DISCORD_TOKEN}"

openrouter:
  api_key: "${OPENROUTER_API_KEY}"

models:
  default: "anthropic/claude-3-haiku"
  check: "anthropic/claude-3-haiku"
```

## Commands

- `/change_model <model>` - Change AI model
- `/help` - Show help
- `/nekogif` - Random cat GIF

## Development

- **Tests**: `python test_architecture.py`
- **Logs**: Check `logs/` directory
- **Legacy**: Old imports work with deprecation warnings

## Project Structure

```
├── base.py              # Main bot with new architecture
├── start.py             # Production startup script
├── config/
│   └── config.py        # Configuration management
├── services/
│   ├── container.py     # Dependency injection
│   ├── state_manager.py # State management
│   ├── ai_service.py    # AI operations
│   └── error_handler.py # Error handling
├── cogs/
│   ├── base_command.py  # Base class for commands
│   ├── base_event.py    # Base class for events
│   ├── commands/        # Command implementations
│   └── events/          # Event handlers
├── utils/
│   ├── logging.py       # Centralized logging
│   ├── config_load.py   # Legacy config support
│   └── utils.py         # General utilities
└── lang/
    └── en.json          # Personality and responses
```

## Service Architecture

The bot uses dependency injection for loose coupling:

```python
# Service initialization
config = Config.create()
services = ServiceContainer(config)
await services.initialize()

# Services available to all cogs
services.state_manager    # Conversation state
services.ai_service      # AI operations
services.error_handler   # Error management
services.logger_manager  # Logging system
```

## Adding New Features

**Commands:**

```python
from cogs.base_command import BaseCommand

class MyCommand(BaseCommand):
    def __init__(self, bot, services):
        super().__init__(bot, services)
        # Access services via self.ai_service, self.state_manager, etc.
```

**Events:**

```python
from cogs.base_event import BaseEventHandler

class MyEvent(BaseEventHandler):
    @commands.Cog.listener()
    async def on_my_event(self, data):
        # Handle event with access to all services
```

## Legacy Support

Old imports continue working with deprecation warnings:

```python
from constants import DISCORD_TOKEN  # Still works
from utils.utils import split_response  # Still works
```

Migrate to new patterns:

```python
from config import Config
config = Config.create()
token = config.discord_token
```
