"""Guess Character game API router."""

import uuid
from typing import Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.jikan_service import JikanService
from services.config_service import game_config
from models.game import GuessCharacterGame

router = APIRouter()
jikan = JikanService()

games: Dict[str, GuessCharacterGame] = {}


class StartGameRequest(BaseModel):
    user_id: str
    difficulty: str = "normal"


class GuessRequest(BaseModel):
    character_name: str
    anime_name: str


def _extract_character_image(char_data: Dict) -> str:
    images = char_data.get("images", {})
    jpg = images.get("jpg", {})
    return jpg.get("image_url") or ""


@router.post("/start")
async def start_game(request: StartGameRequest):
    """Start a new Guess Character game with 4 characters."""
    characters = []
    
    # Fetch 4 characters for batch mode
    for i in range(4):
        char_data = await jikan.get_random_character(request.difficulty)
        
        if not char_data:
            continue
        
        character = {
            "id": char_data.get("mal_id"),
            "name": char_data.get("name", "Unknown"),
            "name_kanji": char_data.get("name_kanji"),
            "nicknames": char_data.get("nicknames", []),
            "image": _extract_character_image(char_data)
        }
        
        anime_info = char_data.get("anime", {})
        anime = {
            "id": anime_info.get("mal_id"),
            "title": anime_info.get("title", "Unknown"),
            "title_english": anime_info.get("title_english"),
            "title_japanese": anime_info.get("title_japanese"),
            "year": jikan._extract_year(anime_info) if anime_info else None
        }
        
        sub_game_id = f"{request.user_id}_{uuid.uuid4().hex[:8]}"
        game = GuessCharacterGame(
            game_id=sub_game_id,
            user_id=request.user_id,
            target_character=character,
            target_anime=anime,
            difficulty=request.difficulty,
            max_guesses=game_config.guess_character_max_guesses
        )
        
        games[sub_game_id] = game
        
        characters.append({
            "game_id": sub_game_id,
            "character_image": character["image"]
        })
    
    if not characters:
        raise HTTPException(status_code=500, detail="Failed to fetch characters")
    
    return {
        "difficulty": request.difficulty,
        "characters": characters
    }


@router.post("/{game_id}/guess")
async def make_guess(game_id: str, request: GuessRequest):
    """Submit a guess for the game."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    if game.is_complete:
        raise HTTPException(status_code=400, detail="Game is already complete")
    
    target_char = game.target_character
    target_anime = game.target_anime
    
    char_names = [target_char["name"]]
    if target_char.get("name_kanji"):
        char_names.append(target_char["name_kanji"])
    char_names.extend(target_char.get("nicknames", []))
    
    anime_titles = [target_anime["title"]]
    if target_anime.get("title_english"):
        anime_titles.append(target_anime["title_english"])
    if target_anime.get("title_japanese"):
        anime_titles.append(target_anime["title_japanese"])
    
    result = game.make_guess(request.character_name, request.anime_name, char_names, anime_titles)
    
    return {
        "character_guess": request.character_name,
        "anime_guess": request.anime_name,
        "character_correct": result["character_correct"],
        "anime_correct": result["anime_correct"],
        "is_won": game.is_won,
        "is_complete": game.is_complete,
        "target": {
            "characterName": target_char["name"],
            "characterImage": target_char.get("image", ""),
            "animeTitle": target_anime["title"],
            "animeYear": target_anime.get("year")
        },
        "duration": game.get_duration()
    }


@router.post("/{game_id}/giveup")
async def give_up(game_id: str):
    """Give up the current game."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    game.is_complete = True
    game.is_won = False
    
    return {
        "target": {
            "characterName": game.target_character["name"],
            "characterImage": game.target_character.get("image", ""),
            "animeTitle": game.target_anime["title"],
            "animeYear": game.target_anime.get("year")
        },
        "duration": game.get_duration()
    }


@router.get("/search-character")
async def search_character(q: str, limit: int = None):
    """Search characters for autocomplete."""
    if not q or len(q.strip()) < 2:
        return []
    limit = limit or game_config.search_limit
    return await jikan.search_multiple_characters(q, limit)


@router.get("/search/anime")
async def search_anime(q: str, limit: int = None):
    """Search anime for autocomplete."""
    if not q or len(q.strip()) < 2:
        return []
    limit = limit or game_config.search_limit
    return await jikan.search_multiple_anime(q, limit)
