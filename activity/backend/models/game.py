"""Game state models for mini-games."""

import time
import random
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class AnidleGame(BaseModel):
    """Game state for Anidle (Wordle-style anime guessing)."""
    
    game_id: str
    user_id: str
    target: Dict[str, Any]
    guesses: List[Dict[str, Any]] = []
    max_guesses: int = 21
    hint_penalty: int = 0
    is_complete: bool = False
    is_won: bool = False
    difficulty: str = "normal"
    start_time: float = Field(default_factory=time.time)
    
    def add_guess(self, guess: Dict[str, Any], comparison: Dict[str, str]) -> bool:
        self.guesses.append({"anime": guess, "comparison": comparison})
        
        if guess.get("id") == self.target.get("id"):
            self.is_complete = True
            self.is_won = True
            return True
        
        if len(self.guesses) + self.hint_penalty >= self.max_guesses:
            self.is_complete = True
            self.is_won = False
        
        return False
    
    def get_guesses_remaining(self) -> int:
        return max(0, self.max_guesses - len(self.guesses) - self.hint_penalty)
    
    def get_duration(self) -> int:
        return int(time.time() - self.start_time)
    
    @staticmethod
    def compare_anime(guess: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Any]:
        """Compare guess anime with target anime.
        
        Returns comparison dict with status for each field:
        - Simple fields: "value status" string
        - Tags: list of {name, status} where status is "correct", "secondary", or "wrong"
        """
        comparison = {}
        
        guess_title = guess.get("title", "Unknown")
        target_title = target.get("title", "Unknown")
        comparison["title"] = f"{guess_title} {'✅' if guess_title.lower() == target_title.lower() else '❌'}"
        
        guess_year = guess.get("year", 0) or 0
        target_year = target.get("year", 0) or 0
        if guess_year == target_year:
            comparison["year"] = f"{guess_year} ✅"
        elif guess_year < target_year:
            comparison["year"] = f"{guess_year} ⬆️"
        else:
            comparison["year"] = f"{guess_year} ⬇️"
        
        guess_score = guess.get("score", 0) or 0
        target_score = target.get("score", 0) or 0
        # Round to 1 decimal for comparison
        guess_score_rounded = round(float(guess_score), 1)
        target_score_rounded = round(float(target_score), 1)
        if guess_score_rounded == target_score_rounded:
            comparison["score"] = f"{guess_score_rounded} ✅"
        elif guess_score_rounded < target_score_rounded:
            comparison["score"] = f"{guess_score_rounded} ⬆️"
        else:
            comparison["score"] = f"{guess_score_rounded} ⬇️"
        
        guess_eps = guess.get("episodes", 0) or 0
        target_eps = target.get("episodes", 0) or 0
        if guess_eps == target_eps:
            comparison["episodes"] = f"{guess_eps} ✅"
        elif guess_eps < target_eps:
            comparison["episodes"] = f"{guess_eps} ⬆️"
        else:
            comparison["episodes"] = f"{guess_eps} ⬇️"
        
        guess_genres = guess.get("genres", [])
        target_genres = set(target.get("genres", []))
        # Return individual status for each genre (like tags)
        genres_result = []
        for genre in guess_genres:
            if genre in target_genres:
                genres_result.append({"name": genre, "status": "correct"})
            else:
                genres_result.append({"name": genre, "status": "wrong"})
        comparison["genres"] = genres_result
        
        guess_studios = set(guess.get("studios", []))
        target_studios = set(target.get("studios", []))
        if guess_studios == target_studios:
            comparison["studio"] = f"{', '.join(sorted(guess_studios))} ✅"
        else:
            studio_matches = [f"{s} {'✅' if s in target_studios else '❌'}" for s in guess.get("studios", [])]
            comparison["studio"] = ", ".join(studio_matches) if studio_matches else "❌"
        
        guess_source = guess.get("source", "Unknown")
        target_source = target.get("source", "Unknown")
        comparison["source"] = f"{guess_source} {'✅' if guess_source == target_source else '❌'}"
        
        guess_format = guess.get("format", "Unknown")
        target_format = target.get("format", "Unknown")
        comparison["format"] = f"{guess_format} {'✅' if guess_format == target_format else '❌'}"
        
        # Media type (same as format, but separate field for UI)
        guess_media_type = guess.get("media_type", guess.get("format", "Unknown"))
        target_media_type = target.get("media_type", target.get("format", "Unknown"))
        comparison["media_type"] = f"{guess_media_type} {'✅' if guess_media_type == target_media_type else '❌'}"
        
        guess_season = guess.get("season", "Unknown")
        target_season = target.get("season", "Unknown")
        comparison["season"] = f"{guess_season} {'✅' if guess_season == target_season else '❌'}"
        
        # Tags comparison with 3 states: correct (primary), secondary, wrong
        # Target has primary_tags (first 5) and secondary_tags (next 5)
        target_primary = set(target.get("primary_tags", []))
        target_secondary = set(target.get("secondary_tags", []))
        guess_primary = guess.get("primary_tags", [])
        
        tags_result = []
        for tag in guess_primary:
            if tag in target_primary:
                tags_result.append({"name": tag, "status": "correct"})
            elif tag in target_secondary:
                tags_result.append({"name": tag, "status": "secondary"})
            else:
                tags_result.append({"name": tag, "status": "wrong"})
        
        comparison["tags"] = tags_result
        
        return comparison


class GuessAnimeGame(BaseModel):
    """Game state for Guess Anime (screenshot-based guessing).
    
    5 stages total:
    - Stages 1-4: Screenshots
    - Stage 5: Name hint (first 2 letters of JP/EN names)
    """
    
    game_id: str
    user_id: str
    target: Dict[str, Any]
    screenshots: List[Dict[str, str]] = []
    revealed_stages: int = 1  # Tracks how many stages are revealed (1-5)
    current_stage: int = 1  # Currently viewing stage (1-5)
    name_hint_revealed: bool = False
    guesses: List[str] = []
    max_guesses: int = 1  # Only 1 guess allowed
    is_complete: bool = False
    is_won: bool = False
    difficulty: str = "normal"
    start_time: float = Field(default_factory=time.time)
    
    def get_current_screenshot(self) -> Optional[Dict[str, str]]:
        """Get the screenshot for the current stage (stages 1-4 only)."""
        if 1 <= self.current_stage <= 4 and self.screenshots:
            idx = min(self.current_stage - 1, len(self.screenshots) - 1)
            return self.screenshots[idx]
        return None
    
    def reveal_next_stage(self) -> bool:
        """Reveal the next stage (up to 5 total)."""
        if self.revealed_stages < 5:
            self.revealed_stages += 1
            if self.revealed_stages == 5:
                self.name_hint_revealed = True
            return True
        return False
    
    def set_current_stage(self, stage: int) -> bool:
        """Navigate to a specific revealed stage."""
        if 1 <= stage <= self.revealed_stages:
            self.current_stage = stage
            return True
        return False
    
    def get_name_hint(self) -> Dict[str, str]:
        """Generate name hint with dashes for hidden chars and spaces preserved."""
        def format_hint(text: str) -> str:
            """Format text showing first 2 chars, spaces preserved, remaining as dashes."""
            if len(text) <= 2:
                return text
            
            result = []
            for i, char in enumerate(text):
                if i < 2:
                    result.append(char)
                elif char == ' ':
                    result.append(' ')
                else:
                    result.append('-')
            
            return ''.join(result)
        
        hint = {}
        if self.target.get("title"):
            hint["title"] = format_hint(self.target["title"])
        if self.target.get("title_english"):
            hint["title_english"] = format_hint(self.target["title_english"])
        if self.target.get("title_japanese"):
            hint["title_japanese"] = format_hint(self.target["title_japanese"])
        return hint
    
    def add_guess(self, guess_name: str, target_titles: List[str]) -> bool:
        """Add a guess. Only 1 guess allowed - wrong guess ends the game."""
        self.guesses.append(guess_name)
        guess_lower = guess_name.lower().strip()
        
        for target_title in target_titles:
            target_lower = target_title.lower().strip()
            if guess_lower == target_lower or (len(guess_lower) > 3 and guess_lower in target_lower):
                self.is_complete = True
                self.is_won = True
                return True
        
        # Wrong guess - game over
        self.is_complete = True
        self.is_won = False
        return False
    
    def get_attempts_remaining(self) -> int:
        return max(0, self.max_guesses - len(self.guesses))
    
    def get_duration(self) -> int:
        return int(time.time() - self.start_time)
    
    @staticmethod
    def select_screenshots(all_screenshots: List[Dict], count: int = 4) -> List[Dict]:
        if len(all_screenshots) <= count:
            return all_screenshots
        return random.sample(all_screenshots, count)


class GuessCharacterGame(BaseModel):
    """Game state for Guess Character."""
    
    game_id: str
    user_id: str
    target_character: Dict[str, Any]
    target_anime: Dict[str, Any]
    guesses_made: int = 0
    max_guesses: int = 1
    character_guess: str = ""
    anime_guess: str = ""
    is_complete: bool = False
    is_won: bool = False
    difficulty: str = "normal"
    start_time: float = Field(default_factory=time.time)
    
    def make_guess(self, character_name: str, anime_name: str, target_char_names: List[str], target_anime_titles: List[str]) -> Dict[str, bool]:
        self.character_guess = character_name
        self.anime_guess = anime_name
        self.guesses_made += 1
        
        char_correct = any(character_name.lower().strip() == name.lower().strip() for name in target_char_names)
        anime_correct = any(anime_name.lower().strip() == title.lower().strip() for title in target_anime_titles)
        
        self.is_won = char_correct and anime_correct
        self.is_complete = True
        
        return {"character_correct": char_correct, "anime_correct": anime_correct, "is_won": self.is_won}
    
    def get_duration(self) -> int:
        return int(time.time() - self.start_time)


class GuessThemeGame(BaseModel):
    """Game state for Guess OP/ED (Opening/Ending theme guessing)."""
    
    game_id: str
    user_id: str
    target_anime: Dict[str, Any]  # Anime info
    theme: Dict[str, Any]  # Theme info (slug, title, url)
    theme_type: str  # "op" or "ed"
    current_stage: int = 1  # 1 = audio only, 2 = video
    max_stage: int = 2
    is_complete: bool = False
    is_won: bool = False
    difficulty: str = "normal"
    start_time: float = Field(default_factory=time.time)
    
    def reveal_next_stage(self) -> bool:
        """Reveal the next stage. Returns True if there are more stages."""
        if self.current_stage < self.max_stage:
            self.current_stage += 1
            return True
        return False
    
    def make_guess(self, anime_name: str, target_titles: List[str]) -> bool:
        """Make a guess. Returns True if correct."""
        self.is_complete = True
        self.is_won = any(
            anime_name.lower().strip() == title.lower().strip() 
            for title in target_titles
        )
        return self.is_won
    
    def get_duration(self) -> int:
        return int(time.time() - self.start_time)
