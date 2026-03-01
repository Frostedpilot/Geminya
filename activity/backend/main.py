"""FastAPI backend for Discord Activity mini-games."""

import os
import json
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import anidle, guess_anime, guess_character, guess_theme
from services.ids_service import ids_service

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def load_secrets():
    """Load secrets from secrets.json."""
    secrets_path = Path(__file__).parent.parent.parent / "secrets.json"
    if secrets_path.exists():
        with open(secrets_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("🚀 Starting Geminya Mini-Games API...")
    
    # Load secrets
    secrets = load_secrets()
    
    # Initialize IDs.moe
    ids_api_key = secrets.get("IDS_MOE_API_KEY", os.environ.get("IDS_MOE_API_KEY", ""))
    if ids_api_key:
        ids_service.set_api_key(ids_api_key)
        logger.info("✅ IDs.moe API configured")
    else:
        logger.warning("⚠️ IDS_MOE_API_KEY not found - Guess Anime ID conversion disabled")
        logger.warning("   Get your API key at: https://ids.moe")
        logger.warning("⚠️ Guess Anime game will not work without IDS_MOE_API_KEY!")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Geminya Mini-Games API...")



app = FastAPI(
    title="Geminya Mini-Games API",
    description="Backend API for Discord Activity mini-games (Anidle, Guess Anime, Guess Character)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for Discord Activity iframe
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Discord Activity will use proxy
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(anidle.router, prefix="/api/anidle", tags=["anidle"])
app.include_router(guess_anime.router, prefix="/api/guess-anime", tags=["guess-anime"])
app.include_router(guess_character.router, prefix="/api/guess-character", tags=["guess-character"])
app.include_router(guess_theme.router, prefix="/api/guess-theme", tags=["guess-theme"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Geminya Mini-Games API",
        "version": "1.0.0",
        "games": ["anidle", "guess-anime", "guess-character", "guess-op", "guess-ed"]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "apis": {
            "jikan": "configured",
            "shikimori": "configured",
            "ids_moe": "configured" if ids_service._api_key else "not configured"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

