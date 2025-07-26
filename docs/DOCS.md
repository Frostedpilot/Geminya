# Geminya Documentation Index

## Quick Links

- **[README.md](README.md)** - Main project overview and quick start
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Service architecture and design patterns
- **[CONFIG.md](CONFIG.md)** - Configuration system and environment setup
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development guide and best practices

## Documentation Structure

### Getting Started

1. **Setup**: Follow README.md for installation and configuration
2. **Testing**: Run `python test_architecture.py` to validate setup
3. **Development**: Read DEVELOPMENT.md for coding guidelines

### Architecture Overview

- **Service-Oriented Design**: Loose coupling via dependency injection
- **Type-Safe Configuration**: YAML with environment variable support
- **Centralized Logging**: Multi-logger system with file rotation
- **Error Handling**: Unified error management and statistics
- **Backward Compatibility**: Legacy code support with deprecation warnings

### Key Components

#### Core Services (`services/`)

- `ServiceContainer` - Dependency injection container
- `StateManager` - Conversation history and bot state
- `AIService` - OpenRouter API integration
- `ErrorHandler` - Error management and statistics

#### Configuration (`config/`)

- `Config` - Type-safe configuration with validation
- Environment variable substitution
- YAML-based configuration files

#### Base Classes (`cogs/`)

- `BaseCommand` - Inherited by all command cogs
- `BaseEventHandler` - Inherited by all event handlers
- Automatic service injection

#### Utilities (`utils/`)

- `LoggerManager` - Centralized logging setup
- Legacy compatibility layer
- General utility functions

### File Organization

```
Documentation/
├── README.md           # Project overview
├── ARCHITECTURE.md     # Technical architecture
├── CONFIG.md          # Configuration guide
├── DEVELOPMENT.md     # Developer guide
└── DOCS.md            # This index file

Code/
├── base.py            # Main bot entry point
├── start.py           # Production startup script
├── test_architecture.py # Architecture validation
├── config/            # Configuration system
├── services/          # Core services
├── cogs/              # Discord bot components
├── utils/             # Utilities and helpers
└── lang/              # Language and personality
```

### Testing

- **Architecture Tests**: `python test_architecture.py`
- **Manual Testing**: `python start.py` with test Discord server
- **Continuous Validation**: Tests validate service initialization, dependency injection, and component integration

### Migration Notes

The refactored architecture maintains backward compatibility:

- **Legacy imports work** with deprecation warnings
- **Old configuration methods** still function
- **Gradual migration path** from monolithic to service-oriented design

### Performance Considerations

- **Lazy initialization** of services
- **Resource cleanup** on shutdown
- **Memory-efficient** conversation history management
- **Optimized logging** with file rotation

### Security

- **Environment variable** protection for sensitive data
- **Configuration validation** prevents invalid setups
- **Error handling** avoids information leakage
- **API key management** through secure configuration

## Quick Reference

### Start Development

```bash
git clone <repo>
cd Geminya
python test_architecture.py
python start.py
```

### Add New Command

```python
from cogs.base_command import BaseCommand

class MyCommand(BaseCommand):
    @app_commands.command()
    async def my_cmd(self, interaction):
        # Use self.ai_service, self.state_manager, etc.
```

### Add New Service

```python
class MyService:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

    async def initialize(self): pass
    async def cleanup(self): pass
```

### Configuration

```yaml
# config.yml
discord:
  token: "${DISCORD_TOKEN}"
openrouter:
  api_key: "${OPENROUTER_API_KEY}"
```

---

_Updated for the refactored service-oriented architecture_
