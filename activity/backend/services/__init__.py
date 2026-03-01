"""Services package for external API integrations."""

from .config_service import game_config, GameConfig
from .ids_service import ids_service, IDsService
from .jikan_service import JikanService
from .shikimori_service import ShikimoriService

__all__ = [
    "game_config",
    "GameConfig", 
    "ids_service",
    "IDsService",
    "JikanService",
    "ShikimoriService",
]

