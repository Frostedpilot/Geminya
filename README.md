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

## Commands

- `/changemodel` - Change AI model
- `/changepersona` - Change AI personality

## Documentation

See [PROJECT.md](PROJECT.md) for complete project documentation including:
- Architecture overview and design principles
- Service system and dependency injection
- Configuration and environment setup
- Development guide and best practices
- API reference and examples
- Troubleshooting and migration guide
