"""Guess Theme (OP/ED) game API router.

Uses AnimeThemes API for OP/ED videos, Jikan API for anime selection.
"""

import uuid
from typing import Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.jikan_service import JikanService
from services.animethemes_service import AnimeThemesService
from services.config_service import game_config
from models.game import GuessThemeGame

router = APIRouter()
jikan = JikanService()
animethemes = AnimeThemesService()

games: Dict[str, GuessThemeGame] = {}


class StartGameRequest(BaseModel):
    user_id: str
    difficulty: str = "normal"


class GuessRequest(BaseModel):
    anime_name: str


async def _start_theme_game(request: StartGameRequest, theme_type: str):
    """Start a new Guess OP/ED game.
    
    Args:
        request: Start game request with user_id and difficulty
        theme_type: "op" or "ed"
    """
    max_attempts = game_config.max_retries
    
    for attempt in range(max_attempts):
        # Get random anime using theme-specific config (favors anime with theme data)
        anime = await jikan.get_random_anime(request.difficulty, source="theme_anime_selection")
        if not anime:
            print(f"❌ Attempt {attempt + 1}: No anime returned from Jikan")
            continue
        
        mal_id = anime.get("mal_id")
        anime_title = anime.get("title", "Unknown")
        print(f"🎲 Attempt {attempt + 1}: Trying {anime_title} (MAL ID: {mal_id})")
        
        if not mal_id:
            print(f"❌ No MAL ID found for {anime_title}")
            continue
        
        # Check if anime has themes
        themes = await animethemes.get_themes_by_mal_id(mal_id)
        if not themes:
            print(f"❌ No themes found for {anime_title} (MAL ID: {mal_id})")
            continue
        
        # Get random OP or ED
        ops_count = len(themes.get("ops", []))
        eds_count = len(themes.get("eds", []))
        print(f"📊 {anime.get('title')}: {ops_count} OPs, {eds_count} EDs")
        
        if theme_type == "op":
            theme_list = themes.get("ops", [])
        else:
            theme_list = themes.get("eds", [])
        
        if not theme_list:
            print(f"❌ No {theme_type.upper()}s found, continuing...")
            continue
        
        import random
        theme = random.choice(theme_list)
        
        # Create game
        game_id = f"{request.user_id}_{uuid.uuid4().hex[:8]}"
        game = GuessThemeGame(
            game_id=game_id,
            user_id=request.user_id,
            target_anime={
                "id": mal_id,
                "title": anime.get("title", "Unknown"),
                "title_english": anime.get("title_english"),
                "title_japanese": anime.get("title_japanese"),
                "year": jikan._extract_year(anime),
                "image": jikan._extract_image(anime)
            },
            theme=theme,
            theme_type=theme_type,
            difficulty=request.difficulty
        )
        
        games[game_id] = game
        
        print(f"✅ Theme game: {anime.get('title')} - {theme.get('slug')} ({theme_type.upper()})")
        
        return {
            "game_id": game_id,
            "difficulty": request.difficulty,
            "theme_type": theme_type,
            "theme_slug": theme.get("slug"),
            "theme_url": theme.get("url"),
            "current_stage": 1,
            "max_stage": 2
        }
    
    raise HTTPException(
        status_code=500, 
        detail=f"Failed to find anime with {theme_type.upper()} after {max_attempts} attempts"
    )


@router.post("/op/start")
async def start_op_game(request: StartGameRequest):
    """Start a new Guess Opening game."""
    return await _start_theme_game(request, "op")


@router.post("/ed/start")
async def start_ed_game(request: StartGameRequest):
    """Start a new Guess Ending game."""
    return await _start_theme_game(request, "ed")


@router.post("/{game_id}/guess")
async def make_guess(game_id: str, request: GuessRequest):
    """Submit a guess for the anime."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    if game.is_complete:
        raise HTTPException(status_code=400, detail="Game is already complete")
    
    # Build list of valid titles
    target = game.target_anime
    valid_titles = [target.get("title", "")]
    if target.get("title_english"):
        valid_titles.append(target["title_english"])
    if target.get("title_japanese"):
        valid_titles.append(target["title_japanese"])
    
    is_correct = game.make_guess(request.anime_name, valid_titles)
    
    return {
        "is_correct": is_correct,
        "is_won": game.is_won,
        "is_complete": game.is_complete,
        "target": {
            "title": target.get("title"),
            "title_english": target.get("title_english"),
            "year": target.get("year"),
            "image": target.get("image")
        },
        "theme": {
            "slug": game.theme.get("slug"),
            "title": game.theme.get("title"),
            "artist": game.theme.get("artist")
        },
        "duration": game.get_duration()
    }


@router.post("/{game_id}/reveal")
async def reveal_stage(game_id: str):
    """Reveal the next stage (video)."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    if game.is_complete:
        raise HTTPException(status_code=400, detail="Game is already complete")
    
    has_more = game.reveal_next_stage()
    
    return {
        "current_stage": game.current_stage,
        "max_stage": game.max_stage,
        "has_more_stages": has_more,
        "theme_url": game.theme.get("url")
    }


@router.post("/{game_id}/giveup")
async def give_up(game_id: str):
    """Give up the current game."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    game.is_complete = True
    game.is_won = False
    
    target = game.target_anime
    
    return {
        "target": {
            "title": target.get("title"),
            "title_english": target.get("title_english"),
            "year": target.get("year"),
            "image": target.get("image")
        },
        "theme": {
            "slug": game.theme.get("slug"),
            "title": game.theme.get("title"),
            "artist": game.theme.get("artist"),
            "url": game.theme.get("url")
        },
        "duration": game.get_duration()
    }


@router.get("/search/anime")
async def search_anime(q: str, limit: int = None):
    """Search anime for autocomplete."""
    if not q or len(q.strip()) < 2:
        return []
    limit = limit or game_config.search_limit
    return await jikan.search_multiple_anime(q, limit)
