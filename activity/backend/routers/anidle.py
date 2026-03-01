"""Anidle game API router.

Uses Jikan API for anime selection (difficulty-based),
then AniList for enriched metadata (tags, etc).
"""

import time
import uuid
import logging
from typing import Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.jikan_service import JikanService
from services.anilist_service import anilist_service
from services.config_service import game_config
from models.game import AnidleGame

router = APIRouter()
jikan = JikanService()
logger = logging.getLogger(__name__)

# In-memory game storage (use Redis in production)
games: Dict[str, AnidleGame] = {}


class StartGameRequest(BaseModel):
    """Request to start a new game."""
    user_id: str
    difficulty: str = "normal"


class GuessRequest(BaseModel):
    """Request to make a guess."""
    anime_name: str


class HintRequest(BaseModel):
    """Request for a hint."""
    hint_type: str


async def enrich_with_anilist(anime_data: Dict) -> Dict:
    """Enrich Jikan anime data with AniList metadata (tags, etc).
    
    If AniList lookup fails, use Jikan data with empty tags.
    """
    mal_id = anime_data.get("mal_id")
    if not mal_id:
        return jikan.format_anime_data(anime_data)
    
    # Get enriched data from AniList
    anilist_data = await anilist_service.get_anime_by_mal_id(mal_id)
    
    if anilist_data:
        # Use AniList data (has tags) but merge with Jikan for completeness
        jikan_formatted = jikan.format_anime_data(anime_data)
        
        # Prefer AniList for these fields (more accurate)
        return {
            "id": mal_id,
            "title": anilist_data.get("title") or jikan_formatted.get("title"),
            "title_english": anilist_data.get("title_english") or jikan_formatted.get("title_english"),
            "title_japanese": anilist_data.get("title_japanese") or jikan_formatted.get("title_japanese"),
            "year": anilist_data.get("year") or jikan_formatted.get("year"),
            "score": anilist_data.get("score") or jikan_formatted.get("score"),
            "episodes": anilist_data.get("episodes") or jikan_formatted.get("episodes"),
            "genres": anilist_data.get("genres") or jikan_formatted.get("genres"),
            "studios": anilist_data.get("studios") or jikan_formatted.get("studios"),
            "source": anilist_data.get("source") or jikan_formatted.get("source"),
            "format": anilist_data.get("format") or jikan_formatted.get("format"),
            "media_type": anilist_data.get("media_type") or anilist_data.get("format") or jikan_formatted.get("format"),
            "season": jikan_formatted.get("season"),  # AniList doesn't have season name
            "primary_tags": anilist_data.get("primary_tags", []),
            "secondary_tags": anilist_data.get("secondary_tags", []),
            "image": anilist_data.get("image") or jikan_formatted.get("image"),
            "synopsis": jikan_formatted.get("synopsis", "")
        }
    
    # Fallback to Jikan only (no tags)
    logger.warning(f"AniList lookup failed for MAL ID {mal_id}, using Jikan data")
    jikan_formatted = jikan.format_anime_data(anime_data)
    jikan_formatted["primary_tags"] = []
    jikan_formatted["secondary_tags"] = []
    jikan_formatted["media_type"] = jikan_formatted.get("format", "Unknown")
    return jikan_formatted


@router.post("/start")
async def start_game(request: StartGameRequest):
    """Start a new Anidle game."""
    max_retries = game_config.max_retries
    
    for attempt in range(max_retries):
        anime_data = await jikan.get_random_anime(request.difficulty)
        if not anime_data:
            continue
        
        # Enrich with AniList data (tags, etc)
        target = await enrich_with_anilist(anime_data)
        
        # Log what we got
        primary_tags = target.get("primary_tags", [])
        logger.info(f"Selected '{target.get('title')}' with {len(primary_tags)} primary tags: {primary_tags[:3]}...")
        
        game_id = f"{request.user_id}_{uuid.uuid4().hex[:8]}"
        game = AnidleGame(
            game_id=game_id,
            user_id=request.user_id,
            target=target,
            difficulty=request.difficulty,
            max_guesses=game_config.anidle_max_guesses
        )
        
        games[game_id] = game
        
        return {
            "game_id": game_id,
            "max_guesses": game.max_guesses,
            "difficulty": request.difficulty
        }
    
    raise HTTPException(status_code=500, detail="Failed to fetch anime from API")


@router.post("/{game_id}/guess")
async def make_guess(game_id: str, request: GuessRequest):
    """Submit a guess for the game."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    
    if game.is_complete:
        raise HTTPException(status_code=400, detail="Game is already complete")
    
    # Search for anime using Jikan
    guess_data = await jikan.search_anime(request.anime_name)
    if not guess_data:
        raise HTTPException(status_code=400, detail="Anime not found")
    
    # Enrich guess with AniList data for tags comparison
    guess = await enrich_with_anilist(guess_data)
    comparison = AnidleGame.compare_anime(guess, game.target)
    is_correct = game.add_guess(guess, comparison)
    
    response = {
        "guess": {
            "title": guess["title"], 
            "year": guess["year"], 
            "score": guess["score"], 
            "image": guess.get("image"),
            "media_type": guess.get("media_type"),
            "primary_tags": guess.get("primary_tags", [])
        },
        "comparison": comparison,
        "is_correct": is_correct,
        "is_complete": game.is_complete,
        "is_won": game.is_won,
        "guesses_remaining": game.get_guesses_remaining(),
        "guess_count": len(game.guesses)
    }
    
    if game.is_complete:
        response["target"] = game.target
        response["duration"] = game.get_duration()
    
    return response


@router.post("/{game_id}/hint")
async def get_hint(game_id: str, request: HintRequest):
    """Get a hint (costs guesses)."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    if game.is_complete:
        raise HTTPException(status_code=400, detail="Game is already complete")
    
    game.hint_penalty += game_config.anidle_hint_penalty
    target = game.target
    hint_value = None
    
    if request.hint_type == "genre":
        hint_value = target["genres"][0] if target["genres"] else "Unknown"
    elif request.hint_type == "year":
        year = target["year"]
        hint_value = f"{(year // 10) * 10}s" if year else "Unknown"
    elif request.hint_type == "studio":
        hint_value = target["studios"][0] if target["studios"] else "Unknown"
    elif request.hint_type == "media_type":
        hint_value = target.get("media_type", "Unknown")
    elif request.hint_type == "tag":
        primary_tags = target.get("primary_tags", [])
        hint_value = primary_tags[0] if primary_tags else "Unknown"
    else:
        raise HTTPException(status_code=400, detail="Invalid hint type")
    
    return {"hint_type": request.hint_type, "hint_value": hint_value, "guesses_remaining": game.get_guesses_remaining()}


@router.post("/{game_id}/giveup")
async def give_up(game_id: str):
    """Give up the current game."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    game.is_complete = True
    game.is_won = False
    
    return {"target": game.target, "guess_count": len(game.guesses), "duration": game.get_duration()}


@router.get("/{game_id}/status")
async def get_status(game_id: str):
    """Get current game status."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    return {
        "game_id": game_id,
        "guess_count": len(game.guesses),
        "guesses_remaining": game.get_guesses_remaining(),
        "is_complete": game.is_complete,
        "is_won": game.is_won,
        "difficulty": game.difficulty,
        "duration": game.get_duration()
    }


@router.get("/search")
async def search_anime(q: str, limit: int = None):
    """Search anime for autocomplete."""
    if not q or len(q.strip()) < 2:
        return []
    limit = limit or game_config.search_limit
    return await jikan.search_multiple_anime(q, limit)


@router.get("/config")
async def get_config():
    """Get current difficulty configuration."""
    try:
        from services.config_service import game_config
        return {
            "min_members": game_config.min_members,
            "difficulty_ranges": {
                diff: game_config.get_member_ranges(diff)
                for diff in ["easy", "normal", "hard", "expert", "crazy", "insanity"]
            }
        }
    except Exception as e:
        return {"error": str(e)}
