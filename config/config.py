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
    tavily_api_key: str
    google_console_api_key: str
    google_search_engine_id: str

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
            "DeepSeek V3 0324": "openrouter/deepseek/deepseek-chat-v3-0324:free",
            "Kimi K2": "openrouter/moonshotai/kimi-k2:free",
            "DeepSeek Chimera": "openrouter/tngtech/deepseek-r1t2-chimera:free",
            "DeepSeek R1 0528": "openrouter/deepseek/deepseek-r1-0528:free",
            "Gemini 2.5 Flash": "openrouter/google/gemini-2.5-flash",
            "Qwen 3 235B A22B Instruct 2507": "openrouter/qwen/qwen3-235b-a22b-2507",
        }
    )

    # Reverse mapping for quick access
    quick_models_reverse: Dict[str, str] = field(init=False)

    # LLM Providers specific configs
    available_providers: List[str] = field(default_factory=["openrouter"])
    llm_providers: Dict[str, ProviderConfig] = field(default_factory=dict)

    openrouter_config: ProviderConfig = ProviderConfig(
        api_key=openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        timeout=30,
        available_models={
            "DeepSeek V3 0324": "openrouter/deepseek/deepseek-chat-v3-0324:free",
            "Kimi K2": "openrouter/moonshotai/kimi-k2:free",
            "DeepSeek Chimera": "openrouter/tngtech/deepseek-r1t2-chimera:free",
            "DeepSeek R1 0528": "openrouter/deepseek/deepseek-r1-0528:free",
            "Gemini 2.5 Flash": "openrouter/google/gemini-2.5-flash",
            "Qwen 3 235B A22B Instruct 2507": "openrouter/qwen/qwen3-235b-a22b-2507",
        },
        model_infos={
            "DeepSeek V3 0324": ModelInfo(
                id="openrouter/deepseek/deepseek-chat-v3-0324:free",
                name="DeepSeek V3 0324 (free)",
                provider="openrouter",
                context_length=163840,
                supports_tools=True,
                cost_per_million_tokens={"in": 0, "out": 0},
                description="DeepSeek V3, a 685B-parameter, mixture-of-experts model, is the latest iteration of the flagship chat model family from the DeepSeek team. It succeeds the DeepSeek V3 model and performs really well on a variety of tasks.",
            ),
            "Kimi K2": ModelInfo(
                id="openrouter/moonshotai/kimi-k2:free",
                name="Kimi K2 (free)",
                provider="openrouter",
                context_length=32768,
                supports_tools=True,
                cost_per_million_tokens={"in": 0, "out": 0},
                description="Kimi K2 Instruct is a large-scale Mixture-of-Experts (MoE) language model developed by Moonshot AI, featuring 1 trillion total parameters with 32 billion active per forward pass. It is optimized for agentic capabilities, including advanced tool use, reasoning, and code synthesis. Kimi K2 excels across a broad range of benchmarks, particularly in coding (LiveCodeBench, SWE-bench), reasoning (ZebraLogic, GPQA), and tool-use (Tau2, AceBench) tasks. It supports long-context inference up to 128K tokens and is designed with a novel training stack that includes the MuonClip optimizer for stable large-scale MoE training.",
            ),
            "DeepSeek Chimera": ModelInfo(
                id="openrouter/tngtech/deepseek-r1t2-chimera:free",
                name="DeepSeek R1T2 Chimera (free)",
                provider="openrouter",
                context_length=163840,
                supports_tools=False,
                cost_per_million_tokens={"in": 0, "out": 0},
                description="DeepSeek-TNG-R1T2-Chimera is the second-generation Chimera model from TNG Tech. It is a 671 B-parameter mixture-of-experts text-generation model assembled from DeepSeek-AI’s R1-0528, R1, and V3-0324 checkpoints with an Assembly-of-Experts merge. The tri-parent design yields strong reasoning performance while running roughly 20 % faster than the original R1 and more than 2× faster than R1-0528 under vLLM, giving a favorable cost-to-intelligence trade-off. The checkpoint supports contexts up to 60 k tokens in standard use (tested to ~130 k) and maintains consistent <think> token behaviour, making it suitable for long-context analysis, dialogue and other open-ended generation tasks.",
            ),
            "DeepSeek R1 0528": ModelInfo(
                id="openrouter/deepseek/deepseek-r1-0528:free",
                name="DeepSeek R1 0528 (free)",
                provider="openrouter",
                context_length=163840,
                supports_tools=False,
                cost_per_million_tokens={"in": 0, "out": 0},
                description="May 28th update to the original DeepSeek R1 Performance on par with OpenAI o1, but open-sourced and with fully open reasoning tokens. It's 671B parameters in size, with 37B active in an inference pass. Fully open-source model.",
            ),
            "Gemini 2.5 Flash": ModelInfo(
                id="openrouter/google/gemini-2.5-flash",
                name="Gemini 2.5 Flash",
                provider="openrouter",
                context_length=1048576,
                supports_tools=True,
                cost_per_million_tokens={"in": 0.30, "out": 2.50, "image": 1.238},
                description='Gemini 2.5 Flash is Google\'s state-of-the-art workhorse model, specifically designed for advanced reasoning, coding, mathematics, and scientific tasks. It includes built-in "thinking" capabilities, enabling it to provide responses with greater accuracy and nuanced context handling. Additionally, Gemini 2.5 Flash is configurable through the "max tokens for reasoning" parameter, as described in the documentation ',
            ),
            "Qwen 3 235B A22B Instruct 2507": ModelInfo(
                id="openrouter/qwen/qwen3-235b-a22b-2507",
                name="Qwen 3 235B A22B Instruct 2507",
                provider="openrouter",
                context_length=262144,
                supports_tools=True,
                cost_per_million_tokens={"in": 0.078, "out": 0.312},
                description='Qwen3-235B-A22B-Instruct-2507 is a multilingual, instruction-tuned mixture-of-experts language model based on the Qwen3-235B architecture, with 22B active parameters per forward pass. It is optimized for general-purpose text generation, including instruction following, logical reasoning, math, code, and tool usage. The model supports a native 262K context length and does not implement "thinking mode" (<think> blocks). Compared to its base variant, this version delivers significant gains in knowledge coverage, long-context reasoning, coding benchmarks, and alignment with open-ended tasks. It is particularly strong on multilingual understanding, math reasoning (e.g., AIME, HMMT), and alignment evaluations like Arena-Hard and WritingBench.',
            ),
        },
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
            "sequential-thinking": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
            },
            "tavily-remote-mcp": {
                "command": "npx",
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
        }
    )

    def __post_init__(self):
        """Initialize reverse mapping for available models."""
        self.quick_models_reverse = {v: k for k, v in self.available_models.items()}

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

        # Set up provider config
        for provider in self.available_providers:
            self.llm_providers[provider] = self.__getattribute__(provider + "_config")

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
        tavily_key = os.getenv("TAVILY_API_KEY", "")
        google_console_api_key = os.getenv("GOOGLE_CONSOLE_API_KEY", "")
        google_search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "")

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
            tavily_api_key=tavily_key,
            google_console_api_key=google_console_api_key,
            google_search_engine_id=google_search_engine_id,
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
        tavily_key = secrets.get("TAVILY_API_KEY", "")
        google_console_api_key = secrets.get("GOOGLE_CONSOLE_API_KEY", "")
        google_search_engine_id = secrets.get("GOOGLE_SEARCH_ENGINE_ID", "")

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
            tavily_api_key=tavily_key,
            google_console_api_key=google_console_api_key,
            google_search_engine_id=google_search_engine_id,
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
