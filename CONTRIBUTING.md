# Contributing to Geminya

Thank you for your interest in contributing to Geminya! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

### Our Pledge

We are committed to making participation in this project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Expected Behavior

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate

## Getting Started

### Ways to Contribute

1. **Bug Reports**: Found a bug? Report it!
2. **Feature Requests**: Have an idea? Share it!
3. **Code Contributions**: Fix bugs or implement features
4. **Documentation**: Improve or add documentation
5. **Testing**: Help test new features and releases
6. **Community Support**: Help other users in discussions

### Before You Start

1. Check existing [issues](https://github.com/your-repo/issues) and [pull requests](https://github.com/your-repo/pulls)
2. Join our community discussions
3. Read the [development documentation](docs/DEVELOPMENT.md)

## Development Setup

### Prerequisites

- Python 3.8+
- Git
- Discord Bot Token (for testing)
- OpenRouter API Key (for AI features)

### Local Development Setup

1. **Fork and Clone**

   ```bash
   git clone https://github.com/your-username/Geminya.git
   cd Geminya
   ```

2. **Create Virtual Environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt

   # Install development dependencies
   pip install black flake8 mypy pytest pytest-asyncio pytest-cov
   ```

4. **Set Up Configuration**

   ```bash
   cp secrets.json.example secrets.json
   # Edit secrets.json with your tokens
   ```

5. **Run Tests**

   ```bash
   pytest
   ```

6. **Start Development Bot**
   ```bash
   python base.py
   ```

## Contributing Guidelines

### Issue Reporting

When reporting bugs, please include:

- **Description**: Clear description of the issue
- **Steps to Reproduce**: Exact steps to recreate the bug
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: OS, Python version, dependencies
- **Logs**: Relevant error messages or logs

**Bug Report Template:**

```markdown
## Description

Brief description of the bug

## Steps to Reproduce

1. Step one
2. Step two
3. Step three

## Expected Behavior

What you expected to happen

## Actual Behavior

What actually happened

## Environment

- OS: [e.g., Windows 10, Ubuntu 20.04]
- Python: [e.g., 3.12.0]
- discord.py: [e.g., 2.3.2]

## Additional Context

Any other relevant information
```

### Feature Requests

When suggesting features, please include:

- **Problem Statement**: What problem does this solve?
- **Proposed Solution**: How would you like it to work?
- **Alternatives**: Other solutions you've considered
- **Use Cases**: When would this be useful?

### Code Contributions

1. **Start Small**: Begin with small improvements or bug fixes
2. **Discuss First**: For major changes, open an issue first
3. **Follow Standards**: Adhere to our coding standards
4. **Test Your Code**: Ensure tests pass and add new tests
5. **Update Documentation**: Update relevant documentation

## Pull Request Process

### Before Submitting

1. **Branch from `main`**: Create a feature branch

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**: Implement your changes
3. **Test**: Run tests and ensure they pass
4. **Lint**: Run code quality checks

   ```bash
   black . --check
   flake8 .
   mypy .
   ```

5. **Commit**: Use clear, descriptive commit messages

   ```bash
   git commit -m "Add: new command for user preferences

   - Implement /setpref command for user settings
   - Add database integration for preferences
   - Include tests for preference storage"
   ```

### Pull Request Template

```markdown
## Description

Brief description of changes

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing

- [ ] Tests pass locally
- [ ] New tests added (if applicable)
- [ ] Manual testing completed

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Changes generate no new warnings
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests
2. **Code Review**: Maintainers review changes
3. **Feedback**: Address any requested changes
4. **Approval**: Once approved, changes are merged

## Coding Standards

### Python Style

- **PEP 8**: Follow Python style guidelines
- **Black**: Use Black code formatter
- **Type Hints**: Add type hints for function parameters and returns
- **Docstrings**: Document all public functions and classes

### Code Organization

```python
"""Module docstring describing purpose."""

import standard_library
import third_party
import local_modules

from typing import Optional, List, Dict
import discord
from discord.ext import commands

from utils.ai_utils import get_response


class ExampleCog(commands.Cog):
    """Example cog demonstrating coding standards."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="example")
    async def example_command(
        self,
        ctx: commands.Context,
        parameter: Optional[str] = None
    ) -> None:
        """
        Example command demonstrating proper documentation.

        Args:
            ctx: Discord command context
            parameter: Optional parameter description
        """
        # Implementation with clear comments
        if parameter:
            await ctx.send(f"Parameter provided: {parameter}")
        else:
            await ctx.send("No parameter provided")


async def setup(bot: commands.Bot) -> None:
    """Setup function for cog loading."""
    await bot.add_cog(ExampleCog(bot))
```

### Naming Conventions

- **Functions/Variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Files**: `snake_case.py`
- **Cogs**: `descriptive_name.py`

### Comments and Documentation

```python
def complex_function(data: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Process complex data structure and return summary.

    Args:
        data: List of dictionaries containing user data

    Returns:
        Dictionary with processed statistics

    Raises:
        ValueError: If data format is invalid
    """
    # Process each entry
    result = {}
    for entry in data:
        # Validate required fields
        if 'id' not in entry:
            raise ValueError("Missing required 'id' field")

        # Update statistics
        result[entry['id']] = len(entry.get('messages', []))

    return result
```

## Testing

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest configuration
├── test_commands/           # Command tests
│   ├── test_change_model.py
│   └── test_help.py
├── test_events/             # Event tests
│   └── test_on_message.py
└── test_utils/              # Utility tests
    ├── test_ai_utils.py
    └── test_utils.py
```

### Writing Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from discord.ext import commands

from cogs.commands.example import ExampleCog


class TestExampleCog:
    """Test suite for ExampleCog."""

    @pytest.fixture
    def bot(self):
        """Create mock bot for testing."""
        return AsyncMock(spec=commands.Bot)

    @pytest.fixture
    def cog(self, bot):
        """Create cog instance for testing."""
        return ExampleCog(bot)

    @pytest.mark.asyncio
    async def test_example_command(self, cog):
        """Test example command functionality."""
        # Create mock context
        ctx = AsyncMock()

        # Test command execution
        await cog.example_command(ctx, "test_parameter")

        # Verify expected behavior
        ctx.send.assert_called_once_with("Parameter provided: test_parameter")
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_commands/test_example.py

# Run tests matching pattern
pytest -k "test_example"
```

## Documentation

### Types of Documentation

1. **Code Documentation**: Docstrings and comments
2. **API Documentation**: Function and class documentation
3. **User Documentation**: Setup and usage guides
4. **Developer Documentation**: Architecture and development guides

### Documentation Standards

- **Clear and Concise**: Use simple, clear language
- **Examples**: Include code examples where helpful
- **Up to Date**: Keep documentation current with code changes
- **Comprehensive**: Cover all public APIs and features

### Updating Documentation

When making changes:

1. Update relevant docstrings
2. Update API documentation if needed
3. Update user guides for new features
4. Update README if necessary

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and community chat
- **Pull Requests**: Code review and collaboration

### Getting Help

- **Documentation**: Check existing documentation first
- **Search Issues**: Look for similar problems/questions
- **Ask Questions**: Open a discussion or issue
- **Discord Community**: Join Discord.py community for general help

### Recognition

Contributors are recognized through:

- **Contributors List**: Listed in README and CHANGELOG
- **Commit Attribution**: Git history preserves contributions
- **Release Notes**: Major contributions highlighted in releases

## Development Workflow

### Feature Development

```bash
# 1. Create feature branch
git checkout -b feature/awesome-feature

# 2. Make changes
# ... edit files ...

# 3. Test changes
pytest
black . --check
flake8 .

# 4. Commit changes
git add .
git commit -m "Add awesome feature"

# 5. Push and create PR
git push origin feature/awesome-feature
# Create pull request on GitHub
```

### Bug Fixes

```bash
# 1. Create bug fix branch
git checkout -b fix/bug-description

# 2. Fix the bug
# ... edit files ...

# 3. Add test for the bug
# ... create test ...

# 4. Verify fix
pytest tests/test_specific_bug.py

# 5. Commit and push
git add .
git commit -m "Fix: description of bug fix"
git push origin fix/bug-description
```

## License

By contributing to Geminya, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Questions?

If you have questions about contributing, please:

1. Check existing documentation
2. Search GitHub issues
3. Open a new discussion
4. Reach out to maintainers

Thank you for contributing to Geminya! Your help makes this project better for everyone. 🐱✨
