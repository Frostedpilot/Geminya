# Configuration Guide

## Overview

Geminya uses a flexible configuration system with YAML files and environment variable support.

## Configuration File

### config.yml

Main configuration file with environment variable substitution:

```yaml
discord:
  token: "${DISCORD_TOKEN}" # Environment variable
  prefix: "!"
  debug: false

openrouter:
  api_key: "${OPENROUTER_API_KEY}" # Environment variable
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
  active_servers: [] # Empty = all servers

logging:
  level: "INFO"
  max_file_size: 10485760 # 10MB
  backup_count: 5
  format: "%Y-%m-%d %H:%M:%S | %8s | %s | %s"
```

### Environment Variables

Set environment variables for sensitive data:

**Windows:**

```cmd
set DISCORD_TOKEN=your_discord_token_here
set OPENROUTER_API_KEY=your_openrouter_key_here
```

**Linux/Mac:**

```bash
export DISCORD_TOKEN=your_discord_token_here
export OPENROUTER_API_KEY=your_openrouter_key_here
```

**Or create `.env` file:**

```env
DISCORD_TOKEN=your_discord_token_here
OPENROUTER_API_KEY=your_openrouter_key_here
```

## Configuration Class

### Type-Safe Configuration

The `Config` class provides type safety and validation:

```python
from config import Config

# Load configuration
config = Config.create()

# Access values
print(config.discord_token)
print(config.default_model)
print(config.max_history_length)

# Validate configuration
config.validate()  # Raises ConfigError if invalid
```

### Configuration Fields

```python
@dataclass
class Config:
    # Required fields
    discord_token: str
    openrouter_api_key: str

    # Optional with defaults
    discord_prefix: str = "!"
    discord_debug: bool = False
    default_model: str = "anthropic/claude-3-haiku"
    check_model: str = "anthropic/claude-3-haiku"
    max_history_length: int = 10
    language: str = "en"
    active_servers: List[str] = field(default_factory=list)
    # ... logging settings
```

## Legacy Support

### secrets.json (Deprecated)

Old `secrets.json` format still works but shows deprecation warnings:

```json
{
  "DISCORD_BOT_TOKEN": "your_token",
  "OPENROUTER_API_KEY": "your_key"
}
```

**Migration:** Move to `config.yml` with environment variables.

### constants.py (Deprecated)

Old constant imports still work:

```python
from constants import DISCORD_TOKEN  # Deprecated
```

**Migration:** Use `Config.create().discord_token`

## Best Practices

### Security

- Never commit tokens to version control
- Use environment variables for sensitive data
- Consider using a secrets management service

### Development vs Production

- Use different config files: `config.dev.yml`, `config.prod.yml`
- Override with environment variables in production
- Set `debug: true` for development

### Validation

- Always call `config.validate()` on startup
- Handle `ConfigError` exceptions gracefully
- Provide helpful error messages for missing configuration

## Example Configurations

### Development

```yaml
discord:
  token: "${DISCORD_TOKEN}"
  debug: true

logging:
  level: "DEBUG"

bot:
  active_servers: ["123456789"] # Test server only
```

### Production

```yaml
discord:
  token: "${DISCORD_TOKEN}"
  debug: false

logging:
  level: "INFO"
  max_file_size: 52428800 # 50MB
  backup_count: 10

bot:
  active_servers: [] # All servers
```

### Docker

```yaml
discord:
  token: "${DISCORD_TOKEN}"

openrouter:
  api_key: "${OPENROUTER_API_KEY}"

logging:
  level: "${LOG_LEVEL:-INFO}"
```

## Troubleshooting

### Common Issues

**ConfigError: Missing required field**

- Check environment variables are set
- Verify config.yml syntax

**Environment variable not substituted**

- Ensure variable is exported/set before running
- Check variable name matches exactly (case-sensitive)

**Invalid YAML syntax**

- Use YAML validator
- Check indentation (spaces, not tabs)
- Quote strings with special characters

### Debugging Configuration

```python
from config import Config

try:
    config = Config.create()
    config.validate()
    print("✅ Configuration valid")
except Exception as e:
    print(f"❌ Configuration error: {e}")
```
