"""Configuration loader for the activity backend.

Loads settings from config.yml for game difficulty, anime selection, etc.
"""

import os
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


class GameConfig:
    """Configuration manager for activity backend games."""
    
    _instance: Optional["GameConfig"] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self) -> None:
        """Load configuration from config.yml."""
        config_path = Path(__file__).parent.parent / "config.yml"
        
        if not config_path.exists():
            print(f"⚠️ Config file not found at {config_path}, using defaults")
            self._config = self._get_defaults()
            return
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
            print(f"✅ Loaded config from {config_path}")
        except Exception as e:
            print(f"⚠️ Failed to load config: {e}, using defaults")
            self._config = self._get_defaults()
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "global": {
                "min_members": 7500,
                "search_limit": 25,
                "max_retries": 5
            },
            "anime_selection": {
                "rank_ranges": {
                    "easy": {"1-500": 10, "501-1000": 2},
                    "normal": {"500-1500": 10, "1501-2500": 5},
                    "hard": {"2000-3500": 10, "3501-4500": 5},
                    "expert": {"3500-5000": 10, "5001-6000": 5},
                    "crazy": {"5000-6500": 10, "6501-7500": 3},
                    "insanity": {"6500-8000": 10, "7500-8000": 2}
                }
            },
            "games": {
                "anidle": {"max_guesses": 21, "hint_penalty": 3},
                "guess_anime": {"max_guesses": 4, "min_screenshots": 4},
                "guess_character": {"max_guesses": 1}
            }
        }
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()
    
    # === Global Settings ===
    
    @property
    def min_members(self) -> int:
        """Get global minimum member count."""
        return self._config.get("global", {}).get("min_members", 7500)
    
    @property
    def search_limit(self) -> int:
        """Get default search limit."""
        return self._config.get("global", {}).get("search_limit", 25)
    
    @property
    def max_retries(self) -> int:
        """Get max retries for game initialization."""
        return self._config.get("global", {}).get("max_retries", 5)
    
    # === Anime Selection ===
    
    def get_rank_ranges(self, difficulty: str, source: str = "anime_selection") -> Dict[str, int]:
        """Get popularity rank ranges for a difficulty level.
        
        Args:
            difficulty: Difficulty level (easy, normal, hard, etc.)
            source: Config source ("anime_selection" or "theme_anime_selection")
        
        Returns:
            Dict mapping "min-max" strings to weights
        """
        ranges = self._config.get(source, {}).get("rank_ranges", {})
        return ranges.get(difficulty, ranges.get("normal", {}))
    
    def select_rank_range(self, difficulty: str, source: str = "anime_selection") -> Tuple[int, int]:
        """Select a random popularity rank range based on difficulty weights.
        
        Args:
            difficulty: Difficulty level (easy, normal, hard, etc.)
            source: Config source ("anime_selection" or "theme_anime_selection")
        
        Returns:
            Tuple of (min_rank, max_rank) where 1 = most popular
        """
        ranges = self.get_rank_ranges(difficulty, source)
        
        if not ranges:
            # Fallback to normal range
            return (500, 2500)
        
        # Create weighted list of ranges
        weighted_ranges: List[Tuple[int, int]] = []
        for range_str, weight in ranges.items():
            min_val, max_val = map(int, range_str.split("-"))
            weighted_ranges.extend([(min_val, max_val)] * weight)
        
        # Randomly select based on weights
        selected = random.choice(weighted_ranges)
        return selected
    
    def select_character_params(self, difficulty: str) -> Tuple[str, str]:
        """Select anime difficulty and character role based on weighted config.
        
        Returns:
            Tuple of (anime_difficulty, role) e.g. ("easy", "Main")
        """
        char_config = self._config.get("character_selection", {})
        weights = char_config.get(difficulty, char_config.get("normal", {}))
        
        if not weights:
            # Fallback: same difficulty, main character
            return (difficulty, "Main")
        
        # Create weighted list of (anime_difficulty, role) tuples
        weighted_choices: List[Tuple[str, str]] = []
        for combo, weight in weights.items():
            parts = combo.split(":")
            if len(parts) == 2:
                anime_diff = parts[0]
                role = "Main" if parts[1].lower() == "main" else "Supporting"
                weighted_choices.extend([(anime_diff, role)] * weight)
        
        if not weighted_choices:
            return (difficulty, "Main")
        
        selected = random.choice(weighted_choices)
        return selected
    
    # === Game Settings ===
    
    def get_game_setting(self, game: str, setting: str, default: Any = None) -> Any:
        """Get a specific game setting."""
        return self._config.get("games", {}).get(game, {}).get(setting, default)
    
    @property
    def anidle_max_guesses(self) -> int:
        """Get max guesses for Anidle."""
        return self.get_game_setting("anidle", "max_guesses", 21)
    
    @property
    def anidle_hint_penalty(self) -> int:
        """Get hint penalty for Anidle."""
        return self.get_game_setting("anidle", "hint_penalty", 3)
    
    @property
    def guess_anime_max_guesses(self) -> int:
        """Get max guesses for Guess Anime."""
        return self.get_game_setting("guess_anime", "max_guesses", 4)
    
    @property
    def guess_anime_min_screenshots(self) -> int:
        """Get minimum screenshots required for Guess Anime."""
        return self.get_game_setting("guess_anime", "min_screenshots", 4)
    
    @property
    def guess_character_max_guesses(self) -> int:
        """Get max guesses for Guess Character."""
        return self.get_game_setting("guess_character", "max_guesses", 1)


# Global instance
game_config = GameConfig()
