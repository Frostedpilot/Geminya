"""Configuration for cog and service loading."""
import re
from typing import List, Dict, Set

# Regex patterns for cog grouping
REGEX_GAME = r"cogs\.commands\.(waifu_.*|expeditions|shop|world_threat|anidle|guess_.*|anitrace|currency|banner|giftcode)"
REGEX_MUSIC = r"cogs\.commands\.spotify"
REGEX_FUN = r"cogs\.commands\.(nekogif|dad_joke|yo_mama|useless_fact)"

# Cog loading rules per mode
# Format: "MODE": {"include": [pattern1, ...], "exclude": [pattern1, ...]}
# Exclude takes priority over include
COG_RULES = {
    "GEMINYA": {
        "include": [r".*"],  # meaningful default
        "exclude": [
            REGEX_GAME,
        ],
    },
    "NIGLER": {
        "include": [r".*"],
        "exclude": [
            REGEX_MUSIC, # Assuming Geminya is the AI chat bot and doesn't need music/game
            r"cogs\.commands\.saucenao",  # Maybe exclude tools?
        ],  # Loads everything
    },
    "DEV": {
        "include": [r".*"],
        "exclude": [],
    },
}

# Service dependencies
# Service Name -> List of Cog Regex patterns that require this service
# The service will load if ANY of the enabled cogs match ANY of the patterns
SERVICE_DEPENDENCIES: Dict[str, List[str]] = {
    "WaifuService": [r"cogs\.commands\.waifu_.*", r"cogs\.commands\.shop"],
    "ExpeditionService": [r"cogs\.commands\.expeditions"],
    "WorldThreatService": [r"cogs\.commands\.world_threat"],
    "MusicService": [REGEX_MUSIC],
    "SpotifyService": [REGEX_MUSIC],
    # DatabaseService is core for state management, so we don't conditionalize it based on cogs usually,
    # but if valid use case arises, add it here.
}


def get_enabled_cogs(all_cogs: List[str], mode: str) -> List[str]:
    """
    Get list of enabled cogs for the given mode based on COG_RULES.
    
    Exclusion takes priority over inclusion.
    """
    rules = COG_RULES.get(mode, COG_RULES.get("GEMINYA")) # Fallback to Geminya if unknown
    
    enabled_cogs = []
    
    for cog in all_cogs:
        # Check inclusion
        included = False
        for pattern in rules["include"]:
            if re.match(pattern, cog):
                included = True
                break
        
        if not included:
            continue
            
        # Check exclusion
        excluded = False
        for pattern in rules["exclude"]:
            if re.match(pattern, cog):
                excluded = True
                break
        
        if not excluded:
            enabled_cogs.append(cog)
            
    return enabled_cogs


def should_load_service(service_name: str, mode: str, enabled_cogs: List[str]) -> bool:
    """
    Determine if a service should be loaded based on enabled cogs.
    
    A service should load if:
    1. It has no dependencies defined (assumed core service)
    2. OR at least one of its dependent cogs is present in enabled_cogs
    """
    dependencies = SERVICE_DEPENDENCIES.get(service_name)
    
    # If no dependencies listed, assume it's a core service and should load
    # (Unless we want strict opt-in, but safer to assume core)
    # However, for this specific refactor, we are focusing on conditionally loading
    # the optional services.
    if not dependencies:
        return True
        
    for cog in enabled_cogs:
        for pattern in dependencies:
            if re.match(pattern, cog):
                return True
                
    return False
