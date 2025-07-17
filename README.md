# Geminya - Discord AI Catgirl Bot 🐱✨

Geminya is a Discord bot powered by AI models that embodies a playful, chaotic catgirl personality. She responds to messages with cat puns, generates AI responses using various language models, and provides interactive commands for users.

## 🌟 Features

- **AI-Powered Conversations**: Uses OpenRouter API to access multiple AI models (DeepSeek, Kimi, etc.)
- **Catgirl Personality**: Responds with cat puns, playful actions, and enthusiastic energy
- **Model Switching**: Users can change AI models per server using slash commands
- **Context-Aware Responses**: Maintains conversation history and responds contextually
- **Lore Book System**: Trigger-based responses for specific keywords
- **Smart Response Detection**: Responds when mentioned or when "geminya" appears in messages
- **Multi-language Support**: Configurable language system (currently supports English)

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Discord Bot Token
- OpenRouter API Key
- Required Python packages (see [Requirements](#requirements))

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd Geminya
   ```

2. **Install dependencies**

   ```bash
   pip install discord.py openai aiohttp pyyaml
   ```

3. **Create secrets.json**

   ```json
   {
     "DISCORD_BOT_TOKEN": "your_discord_bot_token_here",
     "OPENROUTER_API_KEY": "your_openrouter_api_key_here"
   }
   ```

4. **Run the bot**
   ```bash
   python base.py
   ```

## 📁 Project Structure

```
Geminya/
├── base.py                 # Main bot entry point
├── constants.py            # Configuration constants
├── config.yml              # Bot configuration
├── secrets.json            # API keys (create this)
├── test.py                 # Testing utilities
├── cogs/                   # Discord.py cogs
│   ├── __init__.py
│   ├── commands/           # Slash commands
│   │   ├── __init__.py
│   │   ├── change_model.py # Model selection command
│   │   ├── help.py         # Help command
│   │   └── nekogif.py      # Random neko gif command
│   └── events/             # Event handlers
│       ├── __init__.py
│       ├── on_message.py   # Message processing
│       ├── on_ready.py     # Bot initialization
│       └── on_command_error.py # Error handling
├── lang/                   # Language files
│   └── en.json             # English personality & responses
├── utils/                  # Utility modules
│   ├── __init__.py
│   ├── ai_utils.py         # AI response generation
│   ├── config_load.py      # Configuration loading
│   └── utils.py            # General utilities
└── logs/                   # Log files
    └── on_message.log      # Message handling logs
```

## 🎯 Core Components

### Main Bot Class (`base.py`)

- **GeminyaBot**: Custom Discord bot class that inherits from `commands.Bot`
- **Model Management**: Stores AI model preferences per server
- **Cog Loading**: Automatically loads command and event handler cogs
- **Command Tree Syncing**: Syncs slash commands with Discord

### AI Integration (`utils/ai_utils.py`)

- **Response Generation**: Creates contextual AI responses using OpenRouter
- **Prompt Building**: Constructs prompts with personality, history, and lore
- **Model Selection**: Supports multiple AI models with fallback handling
- **Check Response**: Determines if bot should respond to ambiguous mentions

### Event Handling (`cogs/events/`)

- **Message Processing**: Handles incoming messages and maintains conversation history
- **Bot Initialization**: Sets up default models and initializes data structures
- **Error Handling**: Graceful error handling for commands and interactions

### Commands (`cogs/commands/`)

- **Model Changing**: Interactive dropdown for selecting AI models
- **Help System**: Dynamic help generation based on available commands
- **Fun Commands**: Neko gif fetching and other entertainment features

## 🔧 Configuration

### Available Models

Configure available AI models in `constants.py`:

```python
AVAILABLE_MODELS = {
    "DeepSeek V3 0324": "deepseek/deepseek-chat-v3-0324:free",
    "Kimi K2": "moonshotai/kimi-k2:free",
    "DeepSeek Chimera": "tngtech/deepseek-r1t2-chimera:free",
    "DeepSeek R1 0528": "deepseek/deepseek-r1-0528:free",
}
```

### Bot Settings

Modify settings in `constants.py`:

- `MAX_HISTORY_LENGTH`: Number of messages to remember (default: 7)
- `DEFAULT_MODEL`: Default AI model for new servers
- `ACTIVE_SERVERS`: List of server IDs where bot is active

### Language Configuration

Edit `config.yml` to change language:

```yaml
LANGUAGE: en # Currently only 'en' supported
```

## 🎭 Personality System

Geminya's personality is defined in `lang/en.json` with multiple persona variants:

- **Core Traits**: Chaotic, playful, flirty, enthusiastic
- **Speech Patterns**: Cat puns, "nya!" endings, kaomojis
- **Behavioral Quirks**: Impulsive, attention-seeking, dramatic
- **Interaction Style**: Responds to headpats, gets excited about cat-related topics

### Lore Book System

The lore book in `lang/en.json` contains trigger-based responses:

- **Keywords**: Words that trigger special responses
- **Examples**: Sample conversations for context
- **Categories**: Programming help, proofreading, personality interactions

## 🤖 AI Model Features

### Response Generation

- **Context Awareness**: Uses conversation history for coherent responses
- **Personality Integration**: All responses maintain Geminya's catgirl persona
- **Error Handling**: Graceful fallbacks when AI services are unavailable
- **Rate Limiting**: Built-in handling for API rate limits

### Model Management

- **Per-Server Settings**: Each Discord server can have its own preferred model
- **Interactive Selection**: Users can change models via dropdown menu
- **Real-time Switching**: Model changes take effect immediately

## 📝 API Documentation

### Key Classes

#### `GeminyaBot`

Main bot class with model management capabilities.

```python
class GeminyaBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.model = {}  # Server-specific model storage
        super().__init__(*args, **kwargs)
```

#### AI Utilities

```python
async def get_response(message, model, history=None, lore_book=None):
    """Generate AI response with context and personality"""

def build_prompt(message, history=None, lore_book=None):
    """Build complete prompt with personality and context"""
```

### Event Handlers

- `on_ready`: Initialize bot data structures
- `on_message`: Process messages and generate responses
- `on_command_error`: Handle command errors gracefully

## 🛠️ Development

### Adding New Commands

1. Create new file in `cogs/commands/`
2. Implement command class inheriting from `commands.Cog`
3. Add `async def setup(bot)` function
4. The command will be auto-loaded on bot startup

### Adding New Events

1. Create new file in `cogs/events/`
2. Implement event handler class
3. Use `@commands.Cog.listener()` decorator
4. Add `async def setup(bot)` function

### Extending Personality

1. Edit `lang/en.json` to add new personality traits
2. Add new lore book entries with keywords and examples
3. Modify prompt building in `ai_utils.py` if needed

## 🔍 Troubleshooting

### Common Issues

**Bot not responding to commands:**

- Check if bot has necessary permissions in Discord server
- Verify `DISCORD_BOT_TOKEN` in `secrets.json`
- Ensure slash commands are synced (happens automatically on startup)

**AI responses not generating:**

- Verify `OPENROUTER_API_KEY` in `secrets.json`
- Check network connectivity to OpenRouter API
- Review logs in `logs/on_message.log` for error details

**Model switching not working:**

- Ensure user has appropriate permissions
- Check that guild ID is properly set in bot's model dictionary
- Verify selected model is available in `AVAILABLE_MODELS`

### Logging

- Message handling: `logs/on_message.log`
- Bot events: Console output with Discord.py logging
- AI API calls: Console output in `ai_utils.py`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Discord.py library for Discord bot framework
- OpenRouter for AI model access
- nekos.best API for neko gifs
- The catgirl community for inspiration ✨

---

_Made with 💖 and lots of cat puns by the Geminya development team!_
