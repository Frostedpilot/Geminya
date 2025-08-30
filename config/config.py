"""Configuration management for the Geminya Discord bot.

This module provides a centralized configuration system that supports
both environment variables and file-based configuration with validation.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import os
import json
from pathlib import Path
from dotenv import load_dotenv

from services.llm.types import ProviderConfig, ModelInfo
from .models import (
    MODEL_NAMES,
    MODEL_INFOS,
    DEEPSEEK_V3_0324,
    DEEPSEEK_V3_0324_PAID,
    QWEN_3_235B_A22B_2507,
    DOLPHIN_MISTRAL_24B,
    MISTRAL_NEMO,
    ZAI_GLM_4_5_AIR,
    GEMINI_2_5_FLASH_LITE_GG,
)

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
    discord_tokens: Dict[str, str]
    openrouter_api_key: str
    saucenao_api_key: str
    tavily_api_key: str
    google_console_api_key: str
    google_search_engine_id: str
    aistudio_api_key: str

    # Spotify credentials
    spotify_username: str = ""
    spotify_password: str = ""
    spotify_client_id: str = ""
    spotify_client_secret: str = ""

    # MyAnimeList API credentials
    mal_client_id: str = ""
    mal_client_secret: str = ""

    # Database configuration (PostgreSQL only)
    postgres_host: str = ""
    postgres_port: int = 5432
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_database: str = ""

    # Bot behavior settings
    language: str = "en"
    max_history_length: int = 7
    debug: bool = False

    # Model configuration
    default_model: str = DEEPSEEK_V3_0324
    default_models: Dict[str, str] = field(
        default_factory=lambda: {
            "GEMINYA": DEEPSEEK_V3_0324,
            "NIGLER": DOLPHIN_MISTRAL_24B,
            "DEV": GEMINI_2_5_FLASH_LITE_GG,
        }
    )
    default_tool_model: str = ZAI_GLM_4_5_AIR
    fall_back_models: Dict[str, str] = field(
        default_factory=lambda: {
            "GEMINYA": DEEPSEEK_V3_0324_PAID,
            "NIGLER": MISTRAL_NEMO,
            "DEV": DEEPSEEK_V3_0324_PAID,
        }
    )
    fall_back_model: str = DEEPSEEK_V3_0324_PAID
    fall_back_tool_model: str = QWEN_3_235B_A22B_2507
    check_model: str = DOLPHIN_MISTRAL_24B

    default_personas: Dict[str, str] = field(
        default_factory=lambda: {
            "GEMINYA": "Geminya_Exp",
            "NIGLER": "Nigler",
            "DEV": "Iris",
        }
    )
    default_persona: str = "Geminya_Exp"

    # Response configuration
    sentence_endings: tuple = (".", "!", "?")
    max_response_length: int = 1999

    # MCP configuration
    max_tool_iterations: int = 10  # Maximum number of tool calling iterations

    # Server restrictions (empty tuple means no restrictions)
    active_servers: tuple = ()

    # Anidle game configuration
    anidle: Dict[str, Any] = field(default_factory=dict)

    # Character guessing game configuration
    guess_character: Dict[str, Any] = field(default_factory=dict)

    # LLM Providers specific configs
    available_providers: List[str] = field(
        default_factory=lambda: ["openrouter", "aistudio"]
    )
    llm_providers: Dict[str, ProviderConfig] = field(default_factory=dict)

    openrouter_config: ProviderConfig = field(
        default_factory=lambda: ProviderConfig(
            api_key="",
            base_url="https://openrouter.ai/api/v1",
            timeout=30,
            model_infos=MODEL_INFOS.copy(),
        )
    )

    aistudio_config: ProviderConfig = field(
        default_factory=lambda: ProviderConfig(
            api_key="",
            base_url=None,
            timeout=30,
            model_infos=MODEL_INFOS.copy(),
        )
    )

    # MCP server folders
    mcp_server_instruction: Dict = field(
        default_factory=lambda: {
            # "duckduckgo": {
            #     "command": "python",
            #     "args": ["mcp_servers/duckduckgo.py"],
            #     "env": None,
            #     "blacklist": [],  # No tools blacklisted for duckduckgo
            # },
            "anilist": {
                "command": "npx.cmd",
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
            "sequential-thinking": {
                "command": "npx.cmd",
                "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
            },
            "tavily-remote-mcp": {
                "command": "npx.cmd",
                "args": [
                    "-y",
                    "mcp-remote",
                    "https://mcp.tavily.com/mcp/",  # URL will be updated in __post_init__
                ],
                "env": {},
            },
            "google-search": {
                "command": "node",
                "args": [
                    "C:\\python\\personal\\Geminya\\mcp_servers\\mcp-google-custom-search-server\\build\\index.js"
                ],
                "env": {
                    "GOOGLE_API_KEY": "",  # Will be set in __post_init__
                    "GOOGLE_SEARCH_ENGINE_ID": "",  # Will be set in __post_init__
                },
            },
            "fetch-mcp": {
                "command": "python",
                "args": ["-m", "mcp_server_fetch", "--ignore-robots-txt"],
                "env": None,
                "blacklist": [],
            },
        }
    )

    def __post_init__(self):
        """Initialize post-configuration setup."""
        # Safely construct Tavily MCP URL if API key is available
        if self.tavily_api_key:
            tavily_url = (
                f"https://mcp.tavily.com/mcp/?tavilyApiKey={self.tavily_api_key}"
            )
            self.mcp_server_instruction["tavily-remote-mcp"]["args"][-1] = tavily_url

            assert (
                self.mcp_server_instruction["tavily-remote-mcp"]["args"][-1]
                != "https://mcp.tavily.com/mcp/"
            )  # Ensure URL is not empty

        else:
            # If no API key, remove Tavily MCP from instructions
            self.mcp_server_instruction.pop("tavily-remote-mcp", None)

        # Set Google API keys in the MCP server instructions
        if self.google_console_api_key and self.google_search_engine_id:
            self.mcp_server_instruction["google-search"]["env"][
                "GOOGLE_API_KEY"
            ] = self.google_console_api_key
            self.mcp_server_instruction["google-search"]["env"][
                "GOOGLE_SEARCH_ENGINE_ID"
            ] = self.google_search_engine_id

            assert (
                self.mcp_server_instruction["google-search"]["env"]["GOOGLE_API_KEY"]
                != ""
            )  # Ensure API key is not empty
            assert (
                self.mcp_server_instruction["google-search"]["env"][
                    "GOOGLE_SEARCH_ENGINE_ID"
                ]
                != ""
            )  # Ensure search engine ID is not empty
        else:
            # If no Google API keys, remove Google Search MCP from instructions
            self.mcp_server_instruction.pop("google-search", None)

        # Set up api key for each provider
        for provider in self.available_providers:
            api_key_attr_name = provider + "_api_key"
            config_attr_name = provider + "_config"
            if hasattr(self, api_key_attr_name):
                self.__getattribute__(config_attr_name).api_key = self.__getattribute__(
                    api_key_attr_name
                )
            else:
                raise ConfigError(f"API key for provider '{provider}' is missing")

        # Set up provider config
        for provider in self.available_providers:
            self.llm_providers[provider] = self.__getattribute__(provider + "_config")

    def set_mode(self, mode: str):
        """Set the mode for the configuration."""

        assert mode in self.discord_tokens, "Invalid mode specified"

        self.mode = mode
        self.discord_token = self.discord_tokens[mode]
        self.default_model = self.default_models.get(mode, self.default_model)
        self.fall_back_model = self.fall_back_models.get(mode, self.fall_back_model)
        self.default_persona = self.default_personas.get(mode, self.default_persona)

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Returns:
            Config: Configuration instance with values from environment

        Raises:
            ConfigError: If required environment variables are missing
        """
        discord_token_geminya = os.getenv("DISCORD_BOT_TOKEN_GEMINYA", "")
        discord_token_nigler = os.getenv("DISCORD_BOT_TOKEN_NIGLER", "")
        discord_token_dev = os.getenv("DISCORD_BOT_TOKEN_DEV", "")
        discord_tokens = {
            "GEMINYA": discord_token_geminya,
            "NIGLER": discord_token_nigler,
            "DEV": discord_token_dev,
        }
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        saucenao_key = os.getenv("SAUCENAO_API_KEY", "")
        tavily_key = os.getenv("TAVILY_API_KEY", "")
        google_console_api_key = os.getenv("GOOGLE_CONSOLE_API_KEY", "")
        google_search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "")
        aistudio_key = os.getenv("GOOGLE_API_KEY", "")

        if not discord_tokens:
            raise ConfigError("DISCORD_BOT_TOKEN environment variable is required")
        if not openrouter_key:
            raise ConfigError("OPENROUTER_API_KEY environment variable is required")

        # Parse active servers from environment (comma-separated)
        active_servers_str = os.getenv("ACTIVE_SERVERS", "")
        active_servers = tuple(
            s.strip() for s in active_servers_str.split(",") if s.strip()
        )

        return cls(
            discord_token=discord_token_dev,
            discord_tokens=discord_tokens,
            openrouter_api_key=openrouter_key,
            saucenao_api_key=saucenao_key,
            tavily_api_key=tavily_key,
            google_console_api_key=google_console_api_key,
            google_search_engine_id=google_search_engine_id,
            aistudio_api_key=aistudio_key,
            mal_client_id=os.getenv("MAL_CLIENT_ID", ""),
            mal_client_secret=os.getenv("MAL_CLIENT_SECRET", ""),
            spotify_username=os.getenv("SPOTIFY_USERNAME", ""),
            spotify_password=os.getenv("SPOTIFY_PASSWORD", ""),
            spotify_client_id=os.getenv("SPOTIFY_CLIENT_ID", ""),
            spotify_client_secret=os.getenv("SPOTIFY_CLIENT_SECRET", ""),
            language=os.getenv("LANGUAGE", "en"),
            max_history_length=int(os.getenv("MAX_HISTORY_LENGTH", "7")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            default_model=os.getenv(
                "DEFAULT_MODEL", "openrouter/deepseek/deepseek-chat-v3-0324:free"
            ),
            check_model=os.getenv(
                "CHECK_MODEL",
                "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            ),
            max_response_length=int(os.getenv("MAX_RESPONSE_LENGTH", "1999")),
            active_servers=active_servers,
            postgres_host=os.getenv("POSTGRES_HOST", ""),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            postgres_user=os.getenv("POSTGRES_USER", ""),
            postgres_password=os.getenv("POSTGRES_PASSWORD", ""),
            postgres_database=os.getenv("POSTGRES_DB", ""),
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

        discord_token_geminya = secrets.get("DISCORD_BOT_TOKEN_GEMINYA", "")
        discord_token_nigler = secrets.get("DISCORD_BOT_TOKEN_NIGLER", "")
        discord_token_dev = secrets.get("DISCORD_BOT_TOKEN_DEV", "")
        discord_tokens = {
            "GEMINYA": discord_token_geminya,
            "NIGLER": discord_token_nigler,
            "DEV": discord_token_dev,
        }
        openrouter_key = secrets.get("OPENROUTER_API_KEY")
        saucenao_key = secrets.get("SAUCENAO_API_KEY")
        tavily_key = secrets.get("TAVILY_API_KEY", "")
        google_console_api_key = secrets.get("GOOGLE_CONSOLE_API_KEY", "")
        google_search_engine_id = secrets.get("GOOGLE_SEARCH_ENGINE_ID", "")
        aistudio_key = secrets.get("GOOGLE_API_KEY", "")

        # MAL API credentials
        mal_client_id = secrets.get("MAL_CLIENT_ID", "")
        mal_client_secret = secrets.get("MAL_CLIENT_SECRET", "")

        # Spotify credentials
        spotify_username = secrets.get("SPOTIFY_USERNAME", "")
        spotify_password = secrets.get("SPOTIFY_PASSWORD", "")
        spotify_client_id = secrets.get("SPOTIFY_CLIENT_ID", "")
        spotify_client_secret = secrets.get("SPOTIFY_CLIENT_SECRET", "")

        # Database credentials from secrets (PostgreSQL only)
        postgres_host = secrets.get("POSTGRES_HOST", "")
        postgres_port = secrets.get("POSTGRES_PORT", 5432)
        postgres_user = secrets.get("POSTGRES_USER", "")
        postgres_password = secrets.get("POSTGRES_PASSWORD", "")
        postgres_database = secrets.get("POSTGRES_DB", "")

        if not discord_tokens:
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

        # Database configuration from config file and secrets (PostgreSQL only)
        database_config = config_data.get("database", {})

        return cls(
            discord_token=discord_token_dev,
            discord_tokens=discord_tokens,
            openrouter_api_key=openrouter_key,
            saucenao_api_key=saucenao_key,
            tavily_api_key=tavily_key,
            google_console_api_key=google_console_api_key,
            google_search_engine_id=google_search_engine_id,
            aistudio_api_key=aistudio_key,
            mal_client_id=mal_client_id,
            mal_client_secret=mal_client_secret,
            spotify_username=spotify_username,
            spotify_password=spotify_password,
            spotify_client_id=spotify_client_id,
            spotify_client_secret=spotify_client_secret,
            language=config_data.get("language", "en"),
            max_history_length=config_data.get("max_history_length", 7),
            debug=config_data.get("debug", False),
            default_model=config_data.get(
                "default_model", "openrouter/deepseek/deepseek-chat-v3-0324:free"
            ),
            check_model=config_data.get(
                "check_model",
                "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            ),
            max_response_length=config_data.get("max_response_length", 1999),
            active_servers=active_servers,
            anidle=config_data.get("anidle", {}),
            guess_character=config_data.get("guess_character", {}),
            postgres_host=postgres_host,
            postgres_port=postgres_port,
            postgres_user=postgres_user,
            postgres_password=postgres_password,
            postgres_database=postgres_database,
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

    def get_postgres_config(self) -> Dict[str, Any]:
        """Get PostgreSQL configuration dictionary."""
        return {
            "host": self.postgres_host,
            "port": self.postgres_port,
            "user": self.postgres_user,
            "password": self.postgres_password,
            "database": self.postgres_database,
        }

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
            "available_providers": self.available_providers,
            "llm_providers": {
                name: {
                    "api_key": "***HIDDEN***",
                    "base_url": provider.base_url,
                    "timeout": provider.timeout,
                    "model_count": len(provider.model_infos),
                }
                for name, provider in self.llm_providers.items()
            },
            "discord_token": "***HIDDEN***",
            "openrouter_api_key": "***HIDDEN***",
        }
        return data
