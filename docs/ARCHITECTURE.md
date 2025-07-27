# Service Architecture Documentation

## Overview

Geminya uses a service-oriented architecture with dependency injection for maintainable, testable code.

## Core Services

### ServiceContainer (`services/container.py`)

Central dependency injection container that manages all services.

```python
services = ServiceContainer(config)
await services.initialize()  # Initialize all services
await services.cleanup()     # Cleanup resources
```

**Available Services:**

- `config`: Configuration management
- `state_manager`: Bot state and history
- `ai_service`: AI operations
- `error_handler`: Error management
- `logger_manager`: Logging system
- `mcp_client`: MCP clients management

### StateManager (`services/state_manager.py`)

Manages conversation history, model preferences, and lore book data.

**Key Methods:**

```python
# Model management
state_manager.set_model(server_id, model_id)
model = state_manager.get_model(server_id)

# History management
state_manager.add_message(channel_id, author_id, name, nick, content)
history = state_manager.get_history(channel_id)

# Lore book
lore_book = state_manager.get_lore_book()
```

### AIService (`services/ai_service.py`)

Handles AI operations and OpenRouter API communication.

**Key Methods:**

```python
# Generate response
response = await ai_service.get_response(message, server_id)

# Check if should respond
should_respond = await ai_service.get_check_response(prompt)
```

### ErrorHandler (`services/error_handler.py`)

Centralized error handling with statistics and rate limiting.

**Key Methods:**

```python
# Handle API errors
message = error_handler.handle_api_error(exception, context)

# Get error statistics
stats = error_handler.get_error_stats()
```

## Base Classes

### BaseCommand (`cogs/base_command.py`)

Base class for all command cogs with service injection.

```python
class MyCommand(BaseCommand):
    def __init__(self, bot, services):
        super().__init__(bot, services)
        # Access: self.config, self.state_manager, self.ai_service, etc.

    @app_commands.command()
    async def my_command(self, interaction):
        # Use services
        model = self.state_manager.get_model(str(interaction.guild_id))
```

### BaseEventHandler (`cogs/base_event.py`)

Base class for all event handlers with service injection.

```python
class MyEvent(BaseEventHandler):
    @commands.Cog.listener()
    async def on_message(self, message):
        # Use services
        await self.state_manager.add_message(...)
```

## Configuration System

### Config (`config/config.py`)

Type-safe configuration with validation and environment variable support.

```python
@dataclass
class Config:
    discord_token: str
    openrouter_api_key: str
    default_model: str = "anthropic/claude-3-haiku"

    @classmethod
    def create(cls) -> 'Config':
        # Loads from config.yml with env var substitution

    def validate(self) -> None:
        # Validates configuration
```

## Logging System

### LoggerManager (`utils/logging.py`)

Centralized logging with multiple loggers and file rotation.

```python
logger_manager = setup_logging(config)

# Get specific loggers
main_logger = logger_manager.get_logger("main")
message_logger = logger_manager.get_message_logger()
ai_logger = logger_manager.get_ai_logger()
error_logger = logger_manager.get_error_logger()
mcp_logger = logger_manager.get_mcp_logger()
```

**Log Files:**

- `logs/geminya.log` - Main application log
- `logs/messages.log` - Message handling
- `logs/ai.log` - AI operations
- `logs/errors.log` - Error tracking
- `logs/mcp.loa` - MCP operation

## Testing

### Architecture Tests (`test_architecture.py`)

Comprehensive test suite validating all components:

```bash
python test_architecture.py  # Run all tests
python test_architecture.py --verbose  # Detailed output
```

**Test Coverage:**

- Configuration loading and validation
- Service container initialization
- State manager functionality
- AI service setup
- Error handler operations
- Base class inheritance
- Logging system
- Backward compatibility
