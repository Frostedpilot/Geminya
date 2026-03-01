"""Guess Anime game API router.

Uses Jikan API for anime selection (config-based rank ranges),
IDs.moe API for ID conversion, and Shikimori API for screenshots.
"""

import uuid
import logging
from typing import Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.jikan_service import JikanService
from services.shikimori_service import ShikimoriService
from services.ids_service import ids_service
from services.config_service import game_config
from models.game import GuessAnimeGame

router = APIRouter()
jikan = JikanService()
shikimori = ShikimoriService()
logger = logging.getLogger(__name__)

games: Dict[str, GuessAnimeGame] = {}


class StartGameRequest(BaseModel):
    user_id: str
    difficulty: str = "normal"


class GuessRequest(BaseModel):
    anime_name: str


async def get_shikimori_screenshots(mal_id: int, min_screenshots: int = 4) -> list:
    """Get Shikimori screenshots using IDs.moe API for ID conversion.
    
    Converts MAL ID to Shikimori ID, then fetches screenshots from Shikimori.
    """
    logger.info(f"🔎 get_shikimori_screenshots called for MAL ID {mal_id}")
    try:
        # Convert MAL ID to Shikimori ID using IDs.moe API
        logger.info(f"📞 Calling ids_service.get_shikimori_id({mal_id})...")
        shikimori_id = await ids_service.get_shikimori_id(mal_id)
        logger.info(f"📬 ids_service.get_shikimori_id returned: {shikimori_id}")
        
        if not shikimori_id:
            logger.warning(f"⚠️ No Shikimori mapping found for MAL ID {mal_id}")
            return []
        
        logger.info(f"🎬 MAL ID {mal_id} → Shikimori ID {shikimori_id}")
        
        # Fetch anime data from Shikimori (includes screenshots)
        screenshots = await shikimori.get_anime_screenshots(shikimori_id, min_screenshots=min_screenshots)
        
        if screenshots:
            logger.info(f"✅ Got {len(screenshots)} screenshots from Shikimori for ID {shikimori_id}")
        else:
            logger.warning(f"⚠️ No screenshots found on Shikimori for ID {shikimori_id}")
        
        return screenshots
    except Exception as e:
        logger.error(f"❌ Error getting Shikimori screenshots for MAL ID {mal_id}: {e}")
        return []



@router.post("/start")
async def start_game(request: StartGameRequest):
    """Start a new Guess Anime game.
    
    Game has 5 stages:
    - Stages 1-4: Screenshots
    - Stage 5: Name hint (first 2 letters)
    - Only 1 guess allowed
    
    Flow:
    1. Get random anime from Jikan (config-based rank difficulty)
    2. Convert MAL ID to Shikimori ID using IDs.moe API
    3. Fetch screenshots from Shikimori
    """
    max_retries = game_config.max_retries
    min_screenshots = game_config.guess_anime_min_screenshots
    
    logger.info(f"Starting Guess Anime game for user {request.user_id} with difficulty {request.difficulty}")
    
    # Check if required services are configured
    if not ids_service._api_key:
        logger.error("❌ IDs.moe API key not configured")
        raise HTTPException(
            status_code=503,
            detail="IDs.moe API key not configured. Add IDS_MOE_API_KEY to secrets.json"
        )
    
    for attempt in range(max_retries):
        # 1. Get random anime from Jikan with config-based difficulty
        anime_data = await jikan.get_random_anime(request.difficulty)
        if not anime_data:
            logger.warning(f"Retry {attempt + 1}/{max_retries}: Failed to fetch anime from Jikan")
            continue
        
        mal_id = anime_data.get("mal_id")
        anime_title = anime_data.get("title", "Unknown")
        
        if not mal_id:
            logger.warning(f"Retry {attempt + 1}/{max_retries}: No MAL ID for anime '{anime_title}'")
            continue
        
        logger.info(f"Retry {attempt + 1}/{max_retries}: Fetched anime '{anime_title}' (MAL ID: {mal_id})")
        
        # 2. Get Shikimori screenshots via IDs.moe mapping
        logger.info(f"⏳ About to call get_shikimori_screenshots for MAL ID {mal_id}...")
        screenshots = await get_shikimori_screenshots(mal_id, min_screenshots=min_screenshots)
        logger.info(f"📦 get_shikimori_screenshots returned {len(screenshots)} screenshots")
        
        if len(screenshots) >= 4:
            logger.info(f"✅ Success on attempt {attempt + 1}: Found {len(screenshots)} screenshots for '{anime_title}' (MAL ID: {mal_id})")
            
            # Randomly select 4 screenshots from available ones
            import random
            selected_screenshots = random.sample(screenshots, min(4, len(screenshots)))
            
            # Format anime data
            target = jikan.format_anime_data(anime_data)
            target["screenshots"] = selected_screenshots
            
            game_id = f"{request.user_id}_{uuid.uuid4().hex[:8]}"
            game = GuessAnimeGame(
                game_id=game_id,
                user_id=request.user_id,
                target=target,
                screenshots=selected_screenshots,
                difficulty=request.difficulty,
                max_guesses=game_config.guess_anime_max_guesses
            )
            
            games[game_id] = game
            first_screenshot = game.get_current_screenshot()
            
            return {
                "game_id": game_id,
                "max_guesses": game.max_guesses,
                "difficulty": request.difficulty,
                "total_stages": 5,  # 4 screenshots + 1 name hint
                "revealed_stages": game.revealed_stages,
                "current_stage": game.current_stage,
                "current_screenshot": first_screenshot.get("medium") or first_screenshot.get("original"),
                "name_hint_revealed": game.name_hint_revealed,
                "name_hint": game.get_name_hint() if game.name_hint_revealed else None,
                "attempts_remaining": game.get_attempts_remaining()
            }

        
        logger.warning(f"Retry {attempt + 1}/{max_retries}: Only {len(screenshots)} screenshots for '{anime_title}' (MAL ID {mal_id}), need {min_screenshots}")
    
    logger.error(f"❌ Failed to start game after {max_retries} retries - unable to find anime with sufficient screenshots")
    raise HTTPException(
        status_code=500, 
        detail="Unable to start game.")


@router.post("/{game_id}/guess")
async def make_guess(game_id: str, request: GuessRequest):
    """Submit a guess for the game. Only 1 guess allowed - wrong = game over."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    if game.is_complete:
        raise HTTPException(status_code=400, detail="Game is already complete")
    
    # Get all possible title variations for matching
    target_titles = _get_all_titles(game.target)
    is_correct = game.add_guess(request.anime_name, target_titles)
    
    response = {
        "guess": request.anime_name,
        "is_correct": is_correct,
        "is_complete": game.is_complete,
        "is_won": game.is_won,
        "attempts_remaining": game.get_attempts_remaining(),
        "revealed_stages": game.revealed_stages,
        "current_stage": game.current_stage,
        "guess_count": len(game.guesses)
    }
    
    if game.is_complete:
        response["target"] = game.target
        response["duration"] = game.get_duration()
        response["all_screenshots"] = [
            ss.get("medium") or ss.get("original") 
            for ss in game.screenshots[:4]
        ]
        response["name_hint"] = game.get_name_hint()
    
    return response


@router.post("/{game_id}/reveal_stage")
async def reveal_stage(game_id: str):
    """Reveal the next stage or navigate to an existing stage."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    if game.is_complete:
        raise HTTPException(status_code=400, detail="Game is already complete")
    
    # Reveal next stage
    if game.revealed_stages < 5:
        game.reveal_next_stage()
        game.current_stage = game.revealed_stages  # Auto-navigate to newly revealed stage
    
    response = {
        "revealed_stages": game.revealed_stages,
        "current_stage": game.current_stage,
        "name_hint_revealed": game.name_hint_revealed,
    }
    
    # Return current screenshot if in stages 1-4
    if 1 <= game.current_stage <= 4:
        current_ss = game.get_current_screenshot()
        if current_ss:
            response["current_screenshot"] = current_ss.get("medium") or current_ss.get("original")
    
    # Return name hint if stage 5
    if game.name_hint_revealed:
        response["name_hint"] = game.get_name_hint()
    
    return response


@router.post("/{game_id}/navigate_stage/{stage}")
async def navigate_stage(game_id: str, stage: int):
    """Navigate to a specific revealed stage."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    
    if not (1 <= stage <= game.revealed_stages):
        raise HTTPException(status_code=400, detail="Stage not yet revealed")
    
    game.set_current_stage(stage)
    
    response = {
        "current_stage": game.current_stage,
        "revealed_stages": game.revealed_stages,
        "name_hint_revealed": game.name_hint_revealed,
    }
    
    # Return current screenshot if in stages 1-4
    if 1 <= game.current_stage <= 4:
        current_ss = game.get_current_screenshot()
        if current_ss:
            response["current_screenshot"] = current_ss.get("medium") or current_ss.get("original")
    
    # Return name hint if stage 5 and revealed
    if game.name_hint_revealed:
        response["name_hint"] = game.get_name_hint()
    
    return response


@router.post("/{game_id}/giveup")
async def give_up(game_id: str):
    """Give up the current game."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    game.is_complete = True
    game.is_won = False
    
    return {
        "target": game.target,
        "guess_count": len(game.guesses),
        "duration": game.get_duration(),
        "all_screenshots": [
            ss.get("medium") or ss.get("original") 
            for ss in game.screenshots[:4]
        ]
    }


@router.get("/search")
async def search_anime(q: str, limit: int = None):
    """Search anime for autocomplete using Jikan."""
    if not q or len(q.strip()) < 2:
        return []
    limit = limit or game_config.search_limit
    return await jikan.search_multiple_anime(q, limit)


def _get_all_titles(anime: Dict) -> list:
    """Get all possible titles for matching."""
    titles = []
    if anime.get("title"):
        titles.append(anime["title"])
    if anime.get("title_english"):
        titles.append(anime["title_english"])
    if anime.get("title_japanese"):
        titles.append(anime["title_japanese"])
    return titles
