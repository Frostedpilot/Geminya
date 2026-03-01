"""Anime and Character data models."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel


class AnimeData(BaseModel):
    """Data structure for anime information from Jikan."""
    
    id: int
    title: str
    title_english: Optional[str] = None
    title_japanese: Optional[str] = None
    synonyms: List[str] = []
    year: Optional[int] = None
    score: float = 0.0
    episodes: int = 0
    genres: List[str] = []
    studios: List[str] = []
    source: str = "Unknown"
    format: str = "Unknown"
    season: str = "Unknown"
    themes: List[str] = []
    image: Optional[str] = None
    synopsis: Optional[str] = None
    
    def get_all_titles(self) -> List[str]:
        """Get all possible titles for matching."""
        titles = [self.title]
        if self.title_english:
            titles.append(self.title_english)
        if self.title_japanese:
            titles.append(self.title_japanese)
        titles.extend(self.synonyms)
        return [t.strip() for t in titles if t and t.strip()]


class ShikimoriAnimeData(BaseModel):
    """Data structure for anime information from Shikimori."""
    
    id: str
    mal_id: Optional[int] = None
    name: str
    english: Optional[str] = None
    russian: Optional[str] = None
    synonyms: List[str] = []
    score: float = 0.0
    episodes: int = 0
    kind: str = "Unknown"
    status: str = "Unknown"
    year: Optional[int] = None
    genres: List[str] = []
    studios: List[str] = []
    franchise: Optional[str] = None
    poster_url: Optional[str] = None
    screenshots: List[Dict[str, str]] = []
    
    def get_all_titles(self) -> List[str]:
        """Get all possible titles for matching."""
        titles = [self.name]
        if self.english:
            titles.append(self.english)
        if self.russian:
            titles.append(self.russian)
        titles.extend(self.synonyms)
        return [t.strip() for t in titles if t and t.strip()]
    
    def has_sufficient_screenshots(self, min_count: int = 4) -> bool:
        """Check if anime has enough screenshots."""
        return len(self.screenshots) >= min_count


class CharacterData(BaseModel):
    """Data structure for character information."""
    
    id: int
    name: str
    name_kanji: Optional[str] = None
    nicknames: List[str] = []
    image: Optional[str] = None
    anime_appearances: List[Dict[str, Any]] = []
    
    def get_all_names(self) -> List[str]:
        """Get all possible names for matching."""
        names = [self.name]
        if self.name_kanji:
            names.append(self.name_kanji)
        names.extend(self.nicknames)
        return [n.strip() for n in names if n and n.strip()]
    
    def get_primary_anime_title(self) -> str:
        """Get the primary anime this character is from."""
        if self.anime_appearances:
            first_anime = self.anime_appearances[0]
            return first_anime.get("title", "Unknown")
        return "Unknown"


class ComparisonResult(BaseModel):
    """Result of comparing a guess with the target."""
    
    title: str
    year: str
    score: str
    episodes: str
    genres: str
    studio: str
    source: str
    format: str
    season: str
    themes: Optional[str] = None
