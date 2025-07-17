# API Documentation

## Core Classes

### `GeminyaBot`

The main bot class that extends Discord.py's `commands.Bot`.

```python
class GeminyaBot(commands.Bot):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.model = {}  # Dict[str, str] - Server ID to model mapping
        super().__init__(*args, **kwargs)
```

**Attributes:**

- `model`: Dictionary mapping server IDs to AI model identifiers

**Methods:**

- `setup_hook()`: Async method called during bot initialization to load cogs and sync commands

---

## AI Utilities (`utils/ai_utils.py`)

### `get_response()`

Generates AI responses using the configured model and context.

```python
async def get_response(
    message: discord.Message,
    model: str,
    history: Optional[List[Dict]] = None,
    lore_book: Optional[Dict] = None
) -> str
```

**Parameters:**

- `message`: Discord message object containing the user's input
- `model`: OpenRouter model identifier (e.g., "deepseek/deepseek-chat-v3-0324:free")
- `history`: Optional conversation history list
- `lore_book`: Optional lore book for contextual responses

**Returns:**

- String containing the generated AI response

**Raises:**

- `AssertionError`: If message is not a Discord.Message instance
- Various API exceptions handled internally, returns fallback message

### `build_prompt()`

Constructs the complete prompt for AI generation.

```python
def build_prompt(
    message: discord.Message,
    history: Optional[List[Dict]] = None,
    lore_book: Optional[Dict] = None
) -> str
```

**Parameters:**

- `message`: Discord message object
- `history`: Conversation history entries
- `lore_book`: Lore book data structure

**Returns:**

- Formatted prompt string for AI model

### `get_check_response()`

Determines if the bot should respond to ambiguous mentions.

```python
async def get_check_response(prompt: str) -> str
```

**Parameters:**

- `prompt`: Check prompt asking if response is warranted

**Returns:**

- Lowercase string ("yes" or "no") indicating whether to respond

---

## Configuration Management (`utils/config_load.py`)

### `load_language_file()`

Loads the language configuration file.

```python
def load_language_file() -> Dict[str, Any]
```

**Returns:**

- Dictionary containing language data from JSON file

**Raises:**

- `FileNotFoundError`: If language file doesn't exist

### `lore_book_load()`

Loads and processes the lore book data into the bot instance.

```python
def lore_book_load(bot: GeminyaBot) -> None
```

**Parameters:**

- `bot`: Bot instance to load lore book into

**Side Effects:**

- Sets `bot.lore_book` attribute with processed data structure

**Data Structure Created:**

```python
bot.lore_book = {
    "trigger_words": Dict[str, List[str]],      # Word -> lore keys
    "example_responses": Dict[str, str],        # Lore key -> example
    "quick_trigger_list": Set[str]              # All trigger words
}
```

---

## Utility Functions (`utils/utils.py`)

### `get_sys_prompt()`

Retrieves the system prompt for the AI model.

```python
def get_sys_prompt() -> str
```

**Returns:**

- System prompt string defining Geminya's personality

### `split_response()`

Splits long AI responses into Discord-compatible chunks.

```python
def split_response(response: str, max_len: int = 1999) -> List[str]
```

**Parameters:**

- `response`: Full AI response text
- `max_len`: Maximum length per chunk (default: 1999)

**Returns:**

- List of text chunks, each under the maximum length

**Behavior:**

- Preserves sentence boundaries when possible
- Splits on sentence endings (., !, ?) when exceeding length
- Falls back to hard splits if no sentence boundaries found

---

## Command Classes

### `ChangeModelCog`

Handles AI model selection via interactive dropdown.

```python
class ChangeModelCog(commands.Cog):
    def __init__(self, bot: GeminyaBot):
        self.bot = bot
```

**Commands:**

- `/changemodel`: Displays model selection interface

**Components:**

- `ModelSelect`: Discord UI Select component for model choice
- `ModelView`: Discord UI View container

### `HelpCog`

Provides dynamic help generation.

```python
class HelpCog(commands.Cog):
    def __init__(self, bot: GeminyaBot):
        self.bot = bot
```

**Commands:**

- `/help`: Shows available commands in embed format

### `NekoGifCog`

Fetches random neko gifs from nekos.best API.

```python
class NekoGifCog(commands.Cog):
    def __init__(self, bot: GeminyaBot):
        self.bot = bot
```

**Commands:**

- `/nekogif`: Fetches and displays random neko gif with metadata

---

## Event Handler Classes

### `OnMessage`

Processes incoming messages and generates AI responses.

```python
class OnMessage(commands.Cog):
    def __init__(self, bot: GeminyaBot):
        self.bot = bot
        self.max_history_length = MAX_HISTORY_LENGTH
```

**Events:**

- `on_message`: Main message processing logic

**Methods:**

- `get_response()`: Generates and sends AI response for a message

**Response Triggers:**

1. Direct mentions (`@Geminya`)
2. "geminya" keyword in message (with confirmation check)

**History Management:**

- Maintains per-channel conversation history
- Combines consecutive messages from same user
- Trims history to configured maximum length
- Replaces Discord mentions with readable names

### `OnReady`

Handles bot initialization when connecting to Discord.

```python
class OnReady(commands.Cog):
    def __init__(self, bot: GeminyaBot):
        self.bot = bot
```

**Events:**

- `on_ready`: Bot startup initialization

**Initialization Tasks:**

1. Create empty history dictionaries for all text channels
2. Set default AI model for all guilds
3. Load lore book data
4. Log startup information and invite link

### `OnError`

Handles command errors gracefully.

```python
class OnError(commands.Cog):
    def __init__(self, bot: GeminyaBot):
        self.bot = bot
```

**Events:**

- `on_command_error`: Error handling for slash commands

**Handled Errors:**

- `MissingPermissions`: User lacks required permissions
- `NotOwner`: Command restricted to bot owner

---

## Constants (`constants.py`)

### Configuration Variables

```python
# API Keys (loaded from secrets.json)
DISCORD_TOKEN: str
OPENROUTER_API_KEY: str

# AI Model Configuration
DEFAULT_MODEL: str = "deepseek/deepseek-chat-v3-0324:free"
CHECK_MODEL: str = "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
AVAILABLE_MODELS: Dict[str, str]

# Bot Behavior
SENTENCE_ENDINGS: Tuple[str, ...] = (".", "!", "?")
MAX_HISTORY_LENGTH: int = 7
ACTIVE_SERVERS: Tuple[str, ...] = ("1393258849867272325", "700261922259599420")
```

### Model Definitions

```python
AVAILABLE_MODELS = {
    "DeepSeek V3 0324": "deepseek/deepseek-chat-v3-0324:free",
    "Kimi K2": "moonshotai/kimi-k2:free",
    "DeepSeek Chimera": "tngtech/deepseek-r1t2-chimera:free",
    "DeepSeek R1 0528": "deepseek/deepseek-r1-0528:free",
}
```

---

## Data Structures

### Message History Entry

```python
{
    "author": int,           # Discord user ID
    "name": str,            # Username#discriminator format
    "nick": Optional[str],   # Server nickname if available
    "content": str          # Message content with mentions resolved
}
```

### Lore Book Structure

```python
{
    "trigger_words": {
        "word": ["lore_key1", "lore_key2"]  # Mapping words to lore entries
    },
    "example_responses": {
        "lore_key": "formatted_example_text"  # Example interactions
    },
    "quick_trigger_list": set(...)  # All trigger words for fast lookup
}
```

### Language File Format

```json
{
  "personality": {
    "Geminya_Exp": "system_prompt_text"
  },
  "lorebook": {
    "category_name": {
      "keywords": ["trigger", "words"],
      "example_user": "example user message",
      "example": "example bot response"
    }
  }
}
```

---

## Error Handling

### API Errors

- OpenRouter API failures return fallback message: "Nya! Something went wrong, please try again later."
- Rate limiting handled with exponential backoff in check responses
- Network errors logged to console

### Discord Errors

- Missing permissions handled with user-friendly messages
- Unknown commands ignored gracefully
- Malformed data handled with logging and fallbacks

### Configuration Errors

- Missing secrets.json raises ValueError with clear message
- Invalid language files raise FileNotFoundError
- Missing lore book data raises ValueError
