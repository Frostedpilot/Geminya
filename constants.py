"""
DEPRECATED: This file is being phased out in favor of the new configuration system.

Use the config module instead:
    from config import Config
    config = Config.create()

This file remains for backward compatibility during the transition.
"""

import warnings
from typing import Dict, Tuple

# Issue deprecation warning
warnings.warn(
    "constants.py is deprecated. Use the config module instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Load configuration for backward compatibility
try:
    from config import Config

    _config = Config.create()

    DISCORD_TOKEN = _config.discord_token
    OPENROUTER_API_KEY = _config.openrouter_api_key
    DEFAULT_MODEL = _config.default_model
    CHECK_MODEL = _config.check_model
    SENTENCE_ENDINGS = _config.sentence_endings
    MAX_HISTORY_LENGTH = _config.max_history_length
    ACTIVE_SERVERS = _config.active_servers
    # Import MODEL_INFOS and MODEL_NAMES for model information
    from config.models import MODEL_INFOS, MODEL_NAMES

    AVAILABLE_MODELS = MODEL_NAMES

except Exception as e:
    # Fallback to old behavior if new config fails
    import json

    with open("secrets.json", "r") as f:
        secrets = json.load(f)

    DISCORD_TOKEN = secrets.get("DISCORD_BOT_TOKEN")
    OPENROUTER_API_KEY = secrets.get("OPENROUTER_API_KEY")
    DEFAULT_MODEL = "deepseek/deepseek-chat-v3-0324:free"
    CHECK_MODEL = "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"

    SENTENCE_ENDINGS = (".", "!", "?")
    MAX_HISTORY_LENGTH = 7

    ACTIVE_SERVERS = ("1393258849867272325", "700261922259599420")

    # Use MODEL_NAMES from models.py for consistency
    from config.models import MODEL_NAMES

    AVAILABLE_MODELS = MODEL_NAMES
