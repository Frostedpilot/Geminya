"""Configuration management for the Geminya Discord bot.

This module provides a centralized configuration system that supports
both environment variables and file-based configuration with validation.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class ConfigError(Exception):
    """Custom exception for configuration-related errors."""

    pass


@dataclass
class Config:
    """Configuration class for the Geminya bot.

    Supports loading from environment variables, secrets.json, and provides
    sensible defaults for all configuration options.
    """

    # Core API credentials
    discord_token: str
    openrouter_api_key: str
    saucenao_api_key: str

    # Bot behavior settings
    language: str = "en"
    max_history_length: int = 7
    debug: bool = False

    # Model configuration
    default_model: str = "deepseek/deepseek-chat-v3-0324:free"
    check_model: str = "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"

    default_persona: str = "Geminya_Exp"

    # Response configuration
    sentence_endings: tuple = (".", "!", "?")
    max_response_length: int = 1999

    # MCP configuration
    max_tool_iterations: int = 10  # Maximum number of tool calling iterations

    # Server restrictions (empty tuple means no restrictions)
    active_servers: tuple = ()

    # Available models mapping
    available_models: Dict[str, str] = field(
        default_factory=lambda: {
            "DeepSeek V3 0324": "deepseek/deepseek-chat-v3-0324:free",
            "Kimi K2": "moonshotai/kimi-k2:free",
            "DeepSeek Chimera": "tngtech/deepseek-r1t2-chimera:free",
            "DeepSeek R1 0528": "deepseek/deepseek-r1-0528:free",
            "Gemini 2.5 Flash": "google/gemini-2.5-flash",
        }
    )

    # Reverse mapping for quick access
    quick_models_reverse: Dict[str, str] = field(init=False)

    # MCP server folders
    mcp_server_instruction: Dict = field(
        default_factory=lambda: {
            "duckduckgo": {
                "command": "python",
                "args": ["mcp_servers/duckduckgo.py"],
                "env": None,
                "blacklist": [],  # No tools blacklisted for duckduckgo
            },
            "anilist": {
                "command": "npx",
                "args": ["-y", "anilist-mcp"],
                "env": None,
                "blacklist": [
                    # Example: Blacklist user management and posting tools
                    "delete_activity",
                    "post_message_activity",
                    "post_text_activity",
                    "delete_thread",
                    "follow_user",
                    "update_user",
                    "add_list_entry",
                    "get_authorized_user",
                    "remove_list_entry",
                    "update_list_entry",
                    "favourite_anime",
                    "favourite_manga",
                    "favourite_character",
                    "favourite_staff",
                    "favourite_studio",
                ],
            },
        }
    )

    def __post_init__(self):
        """Initialize reverse mapping for available models."""
        self.quick_models_reverse = {v: k for k, v in self.available_models.items()}

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Returns:
            Config: Configuration instance with values from environment

        Raises:
            ConfigError: If required environment variables are missing
        """
        discord_token = os.getenv("DISCORD_BOT_TOKEN", "")
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        saucenao_key = os.getenv("SAUCENAO_API_KEY", "")

        if not discord_token:
            raise ConfigError("DISCORD_BOT_TOKEN environment variable is required")
        if not openrouter_key:
            raise ConfigError("OPENROUTER_API_KEY environment variable is required")

        # Parse active servers from environment (comma-separated)
        active_servers_str = os.getenv("ACTIVE_SERVERS", "")
        active_servers = tuple(
            s.strip() for s in active_servers_str.split(",") if s.strip()
        )

        return cls(
            discord_token=discord_token,
            openrouter_api_key=openrouter_key,
            saucenao_api_key=saucenao_key,
            language=os.getenv("LANGUAGE", "en"),
            max_history_length=int(os.getenv("MAX_HISTORY_LENGTH", "7")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            default_model=os.getenv(
                "DEFAULT_MODEL", "deepseek/deepseek-chat-v3-0324:free"
            ),
            check_model=os.getenv(
                "CHECK_MODEL",
                "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            ),
            max_response_length=int(os.getenv("MAX_RESPONSE_LENGTH", "1999")),
            active_servers=active_servers,
        )

    @classmethod
    def from_file(
        cls, secrets_path: Optional[Path] = None, config_path: Optional[Path] = None
    ) -> "Config":
        """Load configuration from files.

        Args:
            secrets_path: Path to secrets.json file (default: ./secrets.json)
            config_path: Path to config.yml file (default: ./config.yml)

        Returns:
            Config: Configuration instance with values from files

        Raises:
            ConfigError: If required files are missing or invalid
        """
        if secrets_path is None:
            secrets_path = Path("secrets.json")
        if config_path is None:
            config_path = Path("config.yml")

        # Load secrets
        try:
            with open(secrets_path, "r", encoding="utf-8") as f:
                secrets = json.load(f)
        except FileNotFoundError:
            raise ConfigError(f"Secrets file not found: {secrets_path}")
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in secrets file {secrets_path}: {e}")

        discord_token = secrets.get("DISCORD_BOT_TOKEN")
        openrouter_key = secrets.get("OPENROUTER_API_KEY")
        saucenao_key = secrets.get("SAUCENAO_API_KEY")

        if not discord_token:
            raise ConfigError("DISCORD_BOT_TOKEN not found in secrets file")
        if not openrouter_key:
            raise ConfigError("OPENROUTER_API_KEY not found in secrets file")

        # Load config.yml if it exists
        config_data = {}
        if config_path.exists():
            try:
                import yaml

                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}
            except ImportError:
                # yaml not available, skip config file
                pass
            except Exception as e:
                raise ConfigError(f"Error loading config file {config_path}: {e}")

        # Parse active servers
        active_servers = config_data.get("active_servers", [])
        if isinstance(active_servers, str):
            active_servers = [s.strip() for s in active_servers.split(",") if s.strip()]
        active_servers = tuple(str(s) for s in active_servers)

        return cls(
            discord_token=discord_token,
            openrouter_api_key=openrouter_key,
            saucenao_api_key=saucenao_key,
            language=config_data.get("language", "en"),
            max_history_length=config_data.get("max_history_length", 7),
            debug=config_data.get("debug", False),
            default_model=config_data.get(
                "default_model", "deepseek/deepseek-chat-v3-0324:free"
            ),
            check_model=config_data.get(
                "check_model",
                "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            ),
            max_response_length=config_data.get("max_response_length", 1999),
            active_servers=active_servers,
        )

    @classmethod
    def create(cls, prefer_env: bool = False) -> "Config":
        """Create configuration using the best available method.

        Args:
            prefer_env: If True, prefer environment variables over files

        Returns:
            Config: Configuration instance

        Raises:
            ConfigError: If configuration cannot be loaded
        """
        errors = []

        if prefer_env:
            try:
                return cls.from_env()
            except ConfigError as e:
                errors.append(f"Environment: {e}")

        try:
            return cls.from_file()
        except ConfigError as e:
            errors.append(f"Files: {e}")

        if not prefer_env:
            try:
                return cls.from_env()
            except ConfigError as e:
                errors.append(f"Environment: {e}")

        raise ConfigError(f"Could not load configuration. Errors: {'; '.join(errors)}")

    def validate(self) -> None:
        """Validate the configuration values.

        Raises:
            ConfigError: If any configuration values are invalid
        """
        if not self.discord_token.strip():
            raise ConfigError("Discord token cannot be empty")
        if not self.openrouter_api_key.strip():
            raise ConfigError("OpenRouter API key cannot be empty")
        if self.max_history_length < 1:
            raise ConfigError("Max history length must be at least 1")
        if self.max_response_length < 100:
            raise ConfigError("Max response length must be at least 100")
        if not self.language.strip():
            raise ConfigError("Language cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data).

        Returns:
            Dict[str, Any]: Configuration as dictionary with secrets masked
        """
        data = {
            "language": self.language,
            "max_history_length": self.max_history_length,
            "debug": self.debug,
            "default_model": self.default_model,
            "check_model": self.check_model,
            "sentence_endings": self.sentence_endings,
            "max_response_length": self.max_response_length,
            "active_servers": self.active_servers,
            "available_models": self.available_models,
            "discord_token": "***HIDDEN***",
            "openrouter_api_key": "***HIDDEN***",
        }
        return data
