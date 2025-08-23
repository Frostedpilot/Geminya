# Geminya Discord Bot

A modern Discord AI chatbot with integrated waifu collection system, powered by OpenRouter and MCP.

## Features

- **AI Chatbot:** Seamless AI model switching using OpenRouter API
- **Waifu Collection System:** Complete gacha mechanics with star progression
- **State Management:** Models, personas and conversation history per server
- **MCP Integration:** Model Context Protocol servers for enhanced responses
- **Dual LLM Support:** Separate models for tools and roleplay for optimal performance
- **Advanced Personas:** SillyTavern-style prompts for immersive roleplay
- **Comprehensive Logging:** Detailed error handling and debugging support

## Systems Overview

### 🤖 **AI Chatbot System**
- Multiple AI model support via OpenRouter
- Context-aware conversations with memory
- Personality system with configurable characters
- Tool calling capabilities with specialized models

### 🌸 **NWNL (No Waifu No Laifu) Academy**
- **Gacha System:** 1★-3★ character summoning with pity system
- **Star Progression:** Automatic upgrades to 4★-5★ using duplicate shards
- **Currency System:** Sakura Crystals for summoning, Quartz for premium items
- **Academy Management:** Ranks, daily rewards, collection statistics
- **Data Pipeline:** MAL integration for authentic character data

## Quick Start

1. **Install dependencies:**

```bash
pip install -r requirements.txt
# Saucenao-api require low version of these module although it works just fine with newer version.
pip install --upgrade requests, aiohttp, urllib3
```

2. **Configure secrets:**

```bash
cp secrets.json.example secrets.json
# Edit secrets.json with your API tokens and database credentials
```

3. **Install required MCP servers**
   Follow the guide to install [Google-search MCP server](https://github.com/limklister/mcp-google-custom-search-server)

   > [!NOTE]
   > If you use a Windows machine, you will have to apply the fixes in [this reddit comment](https://www.reddit.com/r/ClaudeAI/comments/1i6197n/comment/mff6ian/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button)

4. **Test & Run:**

```bash
python test_architecture.py   # Validate setup
python start_geminya.py       # Start main bot
python start_dev.py           # Start in development mode
python start_dev.py --verbose # Start with more verbose logging
```

## Architecture

```
config/          # Configuration system and models
services/        # Core services (AI, MCP, state management, error handling)
cogs/            # Discord commands and events with base classes
  ├── commands/  # All bot commands (entertainment, utility)
  └── events/    # Event handlers (message processing, error handling)
utils/           # Utilities, logging, and helper functions
lang/            # Language files and character personalities
mcp_servers/     # Local MCP servers
docs/            # Comprehensive documentation
logs/            # Application logs
```

## Configuration

### Character Personalities

All persona settings are in `lang/<language>.json`:

```json
{
  "characters": {
    "<character_name>": {
      "personality": "The main personality system prompt for the persona",
      "lorebook": {
        "<category_name>": {
          "keywords": ["list", "of", "trigger", "words"],
          "example_user": "An example query from user for this category",
          "example": "The example response from the bot for that query"
        }
      }
    }
  }
}
```

### Tool use instructions

You can add some intructions for tool using in `lang/<language>.json`:

```json
{
  "tool_book": {
    "category_name": {
      "keywords": ["list", "of", "trigger", "words"],
      "instruction": "The instruction for the LLM"
    }
  }
}
```

## Commands

### Core Commands

- `/change_model <model>` - Switch AI model for personality roleplay
- `/change_persona <persona>` - Change the bot's personality
- `/change_tool_model <model>` - Change model used for tool calling
- `/help` - Show comprehensive help information
- `/mcp_status` - Check MCP server status

### 🌸 NWNL (Waifu Collection) Commands

**Summoning & Collection:**
- `/nwnl_summon` - Single waifu summon (10 crystals)
- `/nwnl_multi_summon` - 10-pull summon (100 crystals, guaranteed 2★+ on 10th)
- `/nwnl_collection [user]` - View waifu collection with star levels
- `/nwnl_profile <waifu_name>` - View detailed waifu information

**Academy Management:**
- `/nwnl_status` - Check academy rank, currencies, and statistics
- `/nwnl_daily` - Claim daily rewards
- `/nwnl_rename_academy <name>` - Rename your academy
- `/nwnl_reset_account` - Reset all academy data
- `/nwnl_delete_account` - Permanently delete account

**Shop System:**
- `/nwnl_shop` - Browse guarantee tickets
- `/nwnl_buy <item>` - Purchase guarantee tickets
- `/nwnl_inventory` - View purchased items
- `/nwnl_purchase_history` - View purchase history
- `/nwnl_use_item <item>` - Use guarantee tickets

### Entertainment Commands

- `/nekogif` - Random reaction GIFs
- `/dad_joke` - Random dad jokes
- `/yo_mama` - Random "yo mama" jokes
- `/useless_fact` - Random useless facts
- `/saucenao` - Find image source
- `/currency` - Money exchange rate calculator

### Anime & Character Commands

- `/anidle` - Wordle but anime
- `/guess_anime` - Guess an anime from its random screenshot
- `/guess_character` - Character guessing game
- `/anitrace` - Trace anime from images

## Development

### Logs

Check the `logs/` directory for:

- `geminya.log` - Main application logs
- `errors.log` - Error logs
- `messages.log` - Message processing logs
- `mcp.log` - MCP server logs

### Development Scripts

- `start_dev.py` - Start bot in development mode

## Project Structure

```
├── base.py                   # Main bot class and initialization
├── start_geminya.py          # Primary startup script
├── start_dev.py              # Development startup script
├── requirements.txt          # Python dependencies
├── config.yml                # Bot configuration
├── secrets.json              # API keys and credentials
├── config/
│   ├── config.py            # Configuration management
│   └── models.py            # LLM model definitions
├── services/
│   ├── container.py         # Dependency injection container
│   ├── state_manager.py     # Bot state management
│   ├── ai_service.py        # AI service
│   ├── error_handler.py     # Error handling service
│   ├── database.py          # MySQL database service
│   ├── waifu_service.py     # Waifu gacha and collection system
│   ├── command_queue.py     # Command queuing for race condition prevention
│   ├── mal_api.py           # MyAnimeList API integration
│   ├── llm/                 # Abstract module for LLM providers
│   └── mcp/                 # MCP client and server management
├── cogs/
│   ├── base_command.py      # Base class for commands
│   ├── base_event.py        # Base class for events
│   ├── commands/            # Command implementations
│   │   ├── waifu_summon.py  # NWNL summoning commands
│   │   ├── waifu_academy.py # NWNL academy management
│   │   ├── shop.py          # NWNL shop system
│   │   ├── anime_image.py   # Anime image search
│   │   ├── guess_anime.py   # Anime guessing game
│   │   ├── saucenao.py      # Image source finding
│   │   └── ...              # Other commands
│   └── events/              # Event handlers
│       ├── on_message.py    # Message processing
│       ├── on_ready.py      # Bot startup events
│       └── on_command_error.py # Error handling
├── utils/
│   ├── logging.py           # Centralized logging system
│   ├── config_load.py       # Configuration loading utilities
│   ├── model_utils.py       # AI model utilities
│   └── utils.py             # General utilities
├── lang/
│   └── en.json              # Character personalities and responses
├── mcp_servers/             # Local MCP servers
├── data/                    # Character data files (CSV, Excel)
├── docs/                    # Documentation
│   └── WAIFU.md            # Complete NWNL system documentation
├── logs/                    # Application logs
├── pull_from_mal.py         # MAL data extraction script
├── character_edit.py        # Character data processing
├── process_character_final.py # Final character data processing
├── upload_to_mysql.py       # Database upload script
├── initialize_shop.py       # Shop initialization
└── reset_*.py               # Database reset utilities
```

## Service Architecture

The bot uses dependency injection for loose coupling and easy testing:

```python
# Service initialization
config = Config.create()
services = ServiceContainer(config)
await services.initialize()

# Available services
services.state_manager    # Conversation state per server
services.ai_service      # AI model operations and chat
services.error_handler   # Centralized error management
services.logger_manager  # Logging system
services.mcp_manager     # MCP server management
```

## Adding New Features

### Creating Commands

```python
from cogs.base_command import BaseCommand
from discord.ext import commands
from discord import app_commands

class MyCommand(BaseCommand):
    def __init__(self, bot, services):
        super().__init__(bot, services)
        # Access services via self.ai_service, self.state_manager, etc.

    @app_commands.command(name="mycommand", description="My new command")
    async def my_command(self, interaction: discord.Interaction):
        # Command implementation
        await interaction.response.send_message("Hello!")
```

### Creating Event Handlers

```python
from cogs.base_event import BaseEventHandler
from discord.ext import commands

class MyEvent(BaseEventHandler):
    @commands.Cog.listener()
    async def on_my_event(self, data):
        # Event handling with access to all services
        self.logger.info(f"Handling event: {data}")
```

## Model Recommendations

### AI Models by Use Case

**For Roleplay & Character Interaction:**

- `openrouter/deepseek/deepseek-chat-v3-0324:free` - The best free model for role-playing, also has a cheap paid version which is unquantized.
- `openrouter/tngtech/deepseek-r1t2-chimera:free` - Another excelent model with style similar to deepseek V3 but now with thinking capability.

**For Fast Responses & General Chat:**

- `google/gemini-flash-1.5` - Super fast, good for casual conversations with reasonable price.
- `openrouter/moonshotai/kimi-k2` - Also very good model for general chat, but with slower response.

**For Tool Calling & Function Execution:**

- `anthropic/claude-4-sonnet` - The almighty god of tool calling (and wallet burning).
- `openrouter/qwen/qwen3-235b-a22b-2507` - Almost dirt cheap, but still pack quite a punch.
- `openrouter/deepseek/deepseek-chat-v3-0324:free` - Not really strong or consistent, but it's free.

**Cost Considerations:**

- Claude models are excellent but expensive - use wisely!
- Gemini Flash offers the best performance/cost ratio
- Deepseek provides great value for free, although it has been heavily rate limited recently.

**Notes:**

- Most models outside Claude, Gemini, and GPT families struggle with complex tool calling
- Claude excels at parallel tool calling but will burn through your budget quickly
- For production use, consider mixing models based on the task complexity

## Contributing

Please read `CONTRIBUTING.md` for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
