# Geminya Discord Bot

A modern Discord AI chatbot powered by Openrouter and MCP.

## Features

- Seemless AI model switch using OpenRouter API
- State management for models, personas and conversation history for each server.
- SillyTavern-style prompt for personas for better roleplay (if needed)
- Support for MCP servers for better answers (experimental)
- Comprehensive logging and error handling

## Quick Start

1. **Install dependencies:**

```bash
pip install discord.py openai pyyaml mcp
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
python start.py --verbose    # Start bot with more verbose logging
```

## Architecture

```
config/          # Configuration system
services/        # Core services (AI, mcp client, state, error handling)
cogs/            # Commands and events with base classes
utils/           # Utilities and logging
lang/            # Language files and personality
mcp_servers/     # Local MCP servers
```

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

Alternatively, you can also directly change them in the `config.Config` class

All persona related settings are in `lang/<language>.json`. The format is:

```json
{
  "characters": [
    "<character_name>": {
      "personality": "The main personality system prompt for the persona",
      "lorebook (Optional)": {
        "<category_name>": {
          "keywords": ["list", "of", "trigger", "words"],
          "example_user": "An example query from user for this category",
          "example": "The example response from the bot for that query"
        }
      }
    }
  ]
}
```

## Commands

- `/change_model <model>` - Change AI model
- `/change_persona <persona>` - Change the persona of the bot
- `/help` - Show help
- `/nekogif` - Random GIF for various reaction
- `/dad_joke` - Random dad jokes

## Development

- **Tests**: `python test_architecture.py`
- **Logs**: Check `logs/` directory

## Project Structure

```
├── base.py              # Main bot class
├── start.py             # Startup script
├── config/
│   └── config.py        # Configuration management
├── services/
│   ├── container.py     # Dependency injection
│   ├── state_manager.py # State management
│   ├── ai_service.py    # AI operations
│   └── error_handler.py # Error handling
│   └── mcp_client.py    # MCP client manager
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

## Adding New Commands and Event Handlers

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

## Notes

- Deepseek models are good for roleplay, Gemini are super fast and good for normal assistant work.
- All models except for the Claude, Gemini and GPT family are pretty suck at tool calling, especially parallel tool calling.
- Claude is god at tool calling, but it burns your wallet faster than you notice, RIP my wallet.

## TODO

- [ ] guess anime character command
- [ ] anydle command
- [ ] waifu gacha command
- [ ] image input support
- [ ] lorebook but for tool use
