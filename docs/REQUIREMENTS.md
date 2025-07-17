# Requirements and Dependencies

## Python Version

- **Minimum**: Python 3.8
- **Recommended**: Python 3.12+
- **Tested**: Python 3.12.x

## Core Dependencies

### Discord Integration

```
discord.py >= 2.3.0
```

**Purpose**: Discord bot framework and API wrapper
**Features Used**:

- Slash commands (`hybrid_command`)
- Event handling (`Cog.listener`)
- UI components (`View`, `Select`)
- Message processing and embeds

### AI Model Integration

```
openai >= 1.0.0
```

**Purpose**: OpenAI-compatible API client for OpenRouter
**Features Used**:

- Async chat completions
- Custom base URL support
- Error handling and retries

### HTTP Client

```
aiohttp >= 3.8.0
```

**Purpose**: Async HTTP requests for external APIs
**Features Used**:

- nekos.best API integration
- Async context managers
- JSON response handling

### Configuration Management

```
PyYAML >= 6.0
```

**Purpose**: YAML configuration file parsing
**Features Used**:

- Loading `config.yml`
- Safe YAML loading
- Error handling for malformed files

## Development Dependencies

### Code Quality

```
black >= 23.0.0          # Code formatting
flake8 >= 6.0.0          # Linting
mypy >= 1.0.0            # Type checking
```

### Testing

```
pytest >= 7.0.0         # Testing framework
pytest-asyncio >= 0.20.0 # Async test support
pytest-cov >= 4.0.0     # Coverage reporting
```

## Installation Methods

### Using pip (Recommended)

```bash
# Install core dependencies
pip install discord.py openai aiohttp pyyaml

# Or install everything at once
pip install discord.py==2.3.2 openai==1.12.0 aiohttp==3.9.1 PyYAML==6.0.1
```

### Using requirements.txt

Create `requirements.txt`:

```txt
discord.py>=2.3.0,<3.0.0
openai>=1.0.0,<2.0.0
aiohttp>=3.8.0,<4.0.0
PyYAML>=6.0,<7.0

# Development dependencies (optional)
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0
pytest>=7.0.0
pytest-asyncio>=0.20.0
pytest-cov>=4.0.0
```

Then install:

```bash
pip install -r requirements.txt
```

### Using Poetry

Create `pyproject.toml`:

```toml
[tool.poetry]
name = "geminya"
version = "1.0.0"
description = "Discord AI Catgirl Bot"
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.8"
"discord.py" = "^2.3.0"
openai = "^1.0.0"
aiohttp = "^3.8.0"
PyYAML = "^6.0"

[tool.poetry.group.dev.dependencies]
black = "^23.0.0"
flake8 = "^6.0.0"
mypy = "^1.0.0"
pytest = "^7.0.0"
pytest-asyncio = "^0.20.0"
pytest-cov = "^4.0.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

Then install:

```bash
poetry install
```

### Using Conda

Create `environment.yml`:

```yaml
name: geminya
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.12
  - pip
  - pip:
      - discord.py>=2.3.0
      - openai>=1.0.0
      - aiohttp>=3.8.0
      - PyYAML>=6.0
```

Then install:

```bash
conda env create -f environment.yml
conda activate geminya
```

## System Dependencies

### Operating System Support

- **Windows**: Windows 10/11 (PowerShell support)
- **macOS**: macOS 10.15+ (Catalina and newer)
- **Linux**: Ubuntu 20.04+, Debian 11+, CentOS 8+, Alpine Linux

### Network Requirements

**Outbound Connections:**

- Discord API: `discord.com` (port 443)
- OpenRouter API: `openrouter.ai` (port 443)
- nekos.best API: `nekos.best` (port 443)

**Firewall Configuration:**

```bash
# Allow outbound HTTPS connections
sudo ufw allow out 443
```

## Optional Dependencies

### Enhanced Logging

```
coloredlogs >= 15.0      # Colored console logs
structlog >= 23.0        # Structured logging
```

### Performance Monitoring

```
psutil >= 5.9.0          # System resource monitoring
memory-profiler >= 0.60  # Memory usage profiling
```

### Database Support (Future)

```
asyncpg >= 0.28.0        # PostgreSQL async driver
redis >= 4.5.0           # Redis caching
```

### Configuration Validation

```
pydantic >= 2.0.0        # Data validation
python-dotenv >= 1.0.0   # Environment file support
```

## Version Compatibility

### Python Version Matrix

| Python Version | Compatibility | Status              |
| -------------- | ------------- | ------------------- |
| 3.7            | ❌            | Not supported (EOL) |
| 3.8            | ✅            | Minimum supported   |
| 3.9            | ✅            | Fully supported     |
| 3.10           | ✅            | Fully supported     |
| 3.11           | ✅            | Fully supported     |
| 3.12           | ✅            | Recommended         |
| 3.13           | ⚠️            | Beta support        |

### Discord.py Compatibility

| discord.py Version | Features         | Compatibility      |
| ------------------ | ---------------- | ------------------ |
| 1.x                | Legacy commands  | ❌ Not supported   |
| 2.0-2.2            | Slash commands   | ⚠️ Limited support |
| 2.3+               | Full feature set | ✅ Recommended     |

### OpenAI Library Compatibility

| openai Version | API Version   | Status            |
| -------------- | ------------- | ----------------- |
| 0.x            | Legacy API    | ❌ Not compatible |
| 1.0-1.11       | New API       | ⚠️ Basic support  |
| 1.12+          | Full features | ✅ Recommended    |

## Platform-Specific Notes

### Windows

**PowerShell Support**: Bot includes PowerShell-specific command examples
**Encoding**: Ensure UTF-8 encoding for JSON files
**Path Separators**: Code handles Windows path separators correctly

```powershell
# Windows installation
python -m pip install --upgrade pip
pip install discord.py openai aiohttp pyyaml
```

### macOS

**Homebrew Python**: Avoid system Python, use Homebrew

```bash
brew install python@3.12
python3.12 -m pip install discord.py openai aiohttp pyyaml
```

### Linux

**Package Manager**: Install Python dev packages

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.12 python3.12-dev python3.12-venv python3-pip

# CentOS/RHEL
sudo dnf install python3.12 python3.12-devel python3-pip

# Alpine
sudo apk add python3 python3-dev py3-pip
```

## Docker Support

### Base Image Requirements

```dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

### Multi-stage Build

```dockerfile
# Build stage
FROM python:3.12-slim as builder
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.12-slim
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
```

## Memory Requirements

### Minimum System Requirements

- **RAM**: 256MB (basic operation)
- **Disk**: 100MB (code + dependencies)
- **CPU**: 1 core (minimal load)

### Recommended System Requirements

- **RAM**: 512MB (comfortable operation)
- **Disk**: 500MB (logs + cache)
- **CPU**: 2 cores (responsive performance)

### Scaling Considerations

**Per Guild Memory Usage:**

- Base: ~1MB per connected guild
- History: ~1KB per stored message
- Cache: ~500KB per active conversation

**Example Calculation:**

```
Base Usage: 50MB
Guilds (10): 10MB
Messages (1000): 1MB
Cache (20 channels): 10MB
Total: ~71MB
```

## Troubleshooting Dependencies

### Common Installation Issues

**SSL Certificate Errors:**

```bash
pip install --trusted-host pypi.org --trusted-host pypi.python.org discord.py
```

**Permission Errors:**

```bash
# Use user installation
pip install --user discord.py openai aiohttp pyyaml

# Or use virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install discord.py openai aiohttp pyyaml
```

**Compiler Errors (Linux):**

```bash
# Install build tools
sudo apt install build-essential python3-dev
```

### Dependency Conflicts

**Check Installed Versions:**

```bash
pip list | grep -E "(discord|openai|aiohttp|yaml)"
```

**Force Reinstall:**

```bash
pip install --force-reinstall discord.py
```

**Clean Installation:**

```bash
pip uninstall discord.py openai aiohttp pyyaml
pip cache purge
pip install discord.py openai aiohttp pyyaml
```

## Security Considerations

### Dependency Security

**Regular Updates:**

```bash
pip list --outdated
pip install --upgrade discord.py openai aiohttp pyyaml
```

**Security Scanning:**

```bash
pip install safety
safety check
```

**Vulnerability Monitoring:**

```bash
pip install pip-audit
pip-audit
```

### Pinned Versions (Production)

For production deployments, pin exact versions:

```txt
discord.py==2.3.2
openai==1.12.0
aiohttp==3.9.1
PyYAML==6.0.1
```

This ensures reproducible builds and prevents breaking changes from automatic updates.
