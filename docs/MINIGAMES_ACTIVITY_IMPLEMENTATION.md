# Mini-Games Discord Activity - Implementation Plan

> **Scope**: Migrate Guess Anime, Guess Character, and Anidle to a Discord Embedded Activity
> **Priority**: Phase 1 of full NWNL migration

---

## Overview

This document provides step-by-step implementation details for creating a Discord Activity containing the three mini-games. The Activity will coexist with existing bot commands.

---

## Architecture

```
geminya/
├── activity/                     # NEW - Discord Activity project
│   ├── backend/                  # FastAPI backend
│   │   ├── main.py               # FastAPI entry point
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── anidle.py         # Anidle game API
│   │   │   ├── guess_anime.py    # Guess Anime API
│   │   │   └── guess_character.py # Guess Character API
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── jikan_service.py  # Jikan API wrapper
│   │   │   └── shikimori_service.py # Shikimori API wrapper
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── anime.py          # Anime data models
│   │   │   └── game.py           # Game state models
│   │   └── requirements.txt
│   │
│   └── frontend/                 # React frontend
│       ├── package.json
│       ├── vite.config.ts
│       ├── index.html
│       └── src/
│           ├── main.tsx
│           ├── App.tsx
│           ├── discord.ts        # Discord SDK setup
│           ├── api/
│           │   └── client.ts     # API client
│           ├── components/
│           │   ├── common/
│           │   │   ├── Button.tsx
│           │   │   ├── Card.tsx
│           │   │   ├── Timer.tsx
│           │   │   └── DifficultySelector.tsx
│           │   ├── anidle/
│           │   │   ├── AnidleGame.tsx
│           │   │   ├── GuessGrid.tsx
│           │   │   ├── GuessRow.tsx
│           │   │   └── AnimeSearchInput.tsx
│           │   ├── guess-anime/
│           │   │   ├── GuessAnimeGame.tsx
│           │   │   ├── ScreenshotViewer.tsx
│           │   │   └── AnimeGuessInput.tsx
│           │   └── guess-character/
│           │       ├── GuessCharacterGame.tsx
│           │       ├── CharacterImage.tsx
│           │       └── CharacterGuessForm.tsx
│           ├── pages/
│           │   ├── Home.tsx
│           │   ├── Anidle.tsx
│           │   ├── GuessAnime.tsx
│           │   └── GuessCharacter.tsx
│           ├── stores/
│           │   └── gameStore.ts  # Zustand game state
│           └── styles/
│               └── globals.css
│
├── services/                     # EXISTING - Keep
├── cogs/                         # EXISTING - Keep (coexistence)
└── docs/
```

---

## Phase 1: Foundation Setup

### Step 1.1: Create Project Structure

```bash
# Create activity folder structure
mkdir -p activity/backend/routers activity/backend/services activity/backend/models
mkdir -p activity/frontend/src/{api,components,pages,stores,styles}
mkdir -p activity/frontend/src/components/{common,anidle,guess-anime,guess-character}
```

### Step 1.2: Backend Setup (FastAPI)

#### `activity/backend/requirements.txt`
```
fastapi>=0.104.0
uvicorn>=0.24.0
aiohttp>=3.9.0
pydantic>=2.5.0
python-dotenv>=1.0.0
```

#### `activity/backend/main.py`
```python
"""FastAPI backend for Discord Activity mini-games."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import anidle, guess_anime, guess_character

app = FastAPI(
    title="Geminya Mini-Games API",
    version="1.0.0"
)

# CORS for Discord Activity iframe
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Discord Activity origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(anidle.router, prefix="/api/anidle", tags=["anidle"])
app.include_router(guess_anime.router, prefix="/api/guess-anime", tags=["guess-anime"])
app.include_router(guess_character.router, prefix="/api/guess-character", tags=["guess-character"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### Step 1.3: Frontend Setup (Vite + React)

```bash
cd activity/frontend
npm create vite@latest . -- --template react-ts
npm install @discord/embedded-app-sdk zustand @tanstack/react-query axios
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

#### `activity/frontend/src/discord.ts`
```typescript
import { DiscordSDK } from '@discord/embedded-app-sdk';

const CLIENT_ID = import.meta.env.VITE_DISCORD_CLIENT_ID;

export const discordSdk = new DiscordSDK(CLIENT_ID);

export async function setupDiscord() {
  await discordSdk.ready();
  
  // Authorize with Discord
  const { code } = await discordSdk.commands.authorize({
    client_id: CLIENT_ID,
    response_type: 'code',
    state: '',
    prompt: 'none',
    scope: ['identify'],
  });
  
  // Exchange code for access token via your backend
  const response = await fetch('/api/auth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });
  
  const { access_token } = await response.json();
  
  // Authenticate with Discord SDK
  await discordSdk.commands.authenticate({ access_token });
  
  return discordSdk;
}
```

---

## Phase 2: Anidle Migration

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/anidle/start` | POST | Start new game |
| `/api/anidle/guess` | POST | Submit guess |
| `/api/anidle/hint` | POST | Request hint |
| `/api/anidle/giveup` | POST | Give up game |
| `/api/anidle/search` | GET | Anime autocomplete |

#### `activity/backend/routers/anidle.py`
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
from services.jikan_service import JikanService

router = APIRouter()
jikan = JikanService()

# In-memory game storage (for MVP - use Redis in production)
games: Dict[str, dict] = {}

class StartGameRequest(BaseModel):
    user_id: str
    difficulty: str = "normal"

class GuessRequest(BaseModel):
    user_id: str
    anime_name: str

class GameState(BaseModel):
    game_id: str
    guesses: List[dict]
    max_guesses: int
    is_complete: bool
    is_won: bool
    hint_penalty: int

@router.post("/start")
async def start_game(request: StartGameRequest):
    """Start a new Anidle game."""
    target = await jikan.get_random_anime(request.difficulty)
    if not target:
        raise HTTPException(status_code=500, detail="Failed to fetch anime")
    
    game_id = f"{request.user_id}_{int(time.time())}"
    games[game_id] = {
        "target": target,
        "guesses": [],
        "max_guesses": 21,
        "is_complete": False,
        "is_won": False,
        "hint_penalty": 0,
        "difficulty": request.difficulty
    }
    
    return {"game_id": game_id, "max_guesses": 21}

@router.post("/guess")
async def make_guess(request: GuessRequest, game_id: str):
    """Submit a guess for Anidle."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    guess = await jikan.search_anime(request.anime_name)
    
    if not guess:
        raise HTTPException(status_code=400, detail="Anime not found")
    
    # Compare guess with target
    comparison = compare_anime(guess, game["target"])
    game["guesses"].append({"guess": guess, "comparison": comparison})
    
    # Check win/lose
    if guess["id"] == game["target"]["id"]:
        game["is_won"] = True
        game["is_complete"] = True
    elif len(game["guesses"]) + game["hint_penalty"] >= game["max_guesses"]:
        game["is_complete"] = True
    
    return {
        "comparison": comparison,
        "is_won": game["is_won"],
        "is_complete": game["is_complete"],
        "guesses_remaining": game["max_guesses"] - len(game["guesses"]) - game["hint_penalty"]
    }

@router.get("/search")
async def search_anime(q: str, limit: int = 25):
    """Search anime for autocomplete."""
    results = await jikan.search_multiple_anime(q, limit)
    return results
```

### Frontend Components

#### `activity/frontend/src/pages/Anidle.tsx`
```tsx
import { useState, useEffect } from 'react';
import { DifficultySelector } from '../components/common/DifficultySelector';
import { AnidleGame } from '../components/anidle/AnidleGame';
import { api } from '../api/client';

export function Anidle() {
  const [gameId, setGameId] = useState<string | null>(null);
  const [difficulty, setDifficulty] = useState('normal');
  const [isLoading, setIsLoading] = useState(false);

  const startGame = async () => {
    setIsLoading(true);
    try {
      const { game_id } = await api.post('/anidle/start', {
        user_id: window.discordUser.id,
        difficulty
      });
      setGameId(game_id);
    } finally {
      setIsLoading(false);
    }
  };

  if (!gameId) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-6">
        <h1 className="text-4xl font-bold text-white">Anidle</h1>
        <p className="text-gray-300">Guess the anime in 21 tries!</p>
        <DifficultySelector value={difficulty} onChange={setDifficulty} />
        <button
          onClick={startGame}
          disabled={isLoading}
          className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          {isLoading ? 'Starting...' : 'Start Game'}
        </button>
      </div>
    );
  }

  return <AnidleGame gameId={gameId} onExit={() => setGameId(null)} />;
}
```

#### `activity/frontend/src/components/anidle/GuessRow.tsx`
```tsx
interface GuessRowProps {
  comparison: {
    title: string;
    year: string;
    score: string;
    episodes: string;
    genres: string;
    studio: string;
    source: string;
    format: string;
    season: string;
  };
}

export function GuessRow({ comparison }: GuessRowProps) {
  const getIndicator = (value: string) => {
    if (value.includes('✅')) return 'bg-green-500';
    if (value.includes('⬆️') || value.includes('⬇️')) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="grid grid-cols-7 gap-1 text-sm">
      <Cell value={comparison.title} color={getIndicator(comparison.title)} />
      <Cell value={comparison.year} color={getIndicator(comparison.year)} />
      <Cell value={comparison.score} color={getIndicator(comparison.score)} />
      <Cell value={comparison.episodes} color={getIndicator(comparison.episodes)} />
      <Cell value={comparison.genres} color={getIndicator(comparison.genres)} />
      <Cell value={comparison.studio} color={getIndicator(comparison.studio)} />
      <Cell value={comparison.season} color={getIndicator(comparison.season)} />
    </div>
  );
}

function Cell({ value, color }: { value: string; color: string }) {
  // Extract text without emoji
  const text = value.replace(/[✅❌⬆️⬇️]/g, '').trim();
  return (
    <div className={`${color} p-2 rounded text-white text-center truncate`}>
      {text}
    </div>
  );
}
```

---

## Phase 3: Guess Anime Migration

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/guess-anime/start` | POST | Start new game |
| `/api/guess-anime/guess` | POST | Submit guess |
| `/api/guess-anime/giveup` | POST | Give up game |
| `/api/guess-anime/search` | GET | Anime autocomplete |

### Frontend Components

#### `activity/frontend/src/components/guess-anime/ScreenshotViewer.tsx`
```tsx
interface ScreenshotViewerProps {
  screenshots: string[];
  currentIndex: number;
}

export function ScreenshotViewer({ screenshots, currentIndex }: ScreenshotViewerProps) {
  return (
    <div className="relative w-full max-w-2xl mx-auto">
      <img
        src={screenshots[currentIndex]}
        alt="Anime screenshot"
        className="w-full rounded-lg shadow-lg"
      />
      <div className="absolute bottom-4 right-4 bg-black/70 px-3 py-1 rounded-full text-white">
        {currentIndex + 1} / {screenshots.length}
      </div>
    </div>
  );
}
```

---

## Phase 4: Guess Character Migration

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/guess-character/start` | POST | Start new game |
| `/api/guess-character/guess` | POST | Submit guess |
| `/api/guess-character/giveup` | POST | Give up game |
| `/api/guess-character/search-character` | GET | Character autocomplete |
| `/api/guess-character/search-anime` | GET | Anime autocomplete |

### Frontend Components

#### `activity/frontend/src/components/guess-character/CharacterGuessForm.tsx`
```tsx
interface CharacterGuessFormProps {
  onSubmit: (characterName: string, animeName: string) => void;
  isSubmitting: boolean;
}

export function CharacterGuessForm({ onSubmit, isSubmitting }: CharacterGuessFormProps) {
  const [characterName, setCharacterName] = useState('');
  const [animeName, setAnimeName] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(characterName, animeName);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-white mb-2">Character Name</label>
        <SearchInput
          value={characterName}
          onChange={setCharacterName}
          searchEndpoint="/api/guess-character/search-character"
          placeholder="Enter character name..."
        />
      </div>
      <div>
        <label className="block text-white mb-2">From Anime</label>
        <SearchInput
          value={animeName}
          onChange={setAnimeName}
          searchEndpoint="/api/guess-character/search-anime"
          placeholder="Enter anime name..."
        />
      </div>
      <button
        type="submit"
        disabled={isSubmitting || !characterName || !animeName}
        className="w-full py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
      >
        {isSubmitting ? 'Checking...' : 'Submit Guess'}
      </button>
    </form>
  );
}
```

---

## Phase 5: Shared Components

### `activity/frontend/src/components/common/DifficultySelector.tsx`
```tsx
interface DifficultySelectorProps {
  value: string;
  onChange: (difficulty: string) => void;
}

const difficulties = [
  { value: 'easy', label: 'Easy', color: 'bg-green-500', emoji: '🟢' },
  { value: 'normal', label: 'Normal', color: 'bg-yellow-500', emoji: '🟡' },
  { value: 'hard', label: 'Hard', color: 'bg-orange-500', emoji: '🟠' },
  { value: 'expert', label: 'Expert', color: 'bg-red-500', emoji: '🔴' },
  { value: 'crazy', label: 'Crazy', color: 'bg-purple-500', emoji: '🟣' },
  { value: 'insanity', label: 'Insanity', color: 'bg-gray-800', emoji: '⚫' },
];

export function DifficultySelector({ value, onChange }: DifficultySelectorProps) {
  return (
    <div className="flex flex-wrap justify-center gap-2">
      {difficulties.map((d) => (
        <button
          key={d.value}
          onClick={() => onChange(d.value)}
          className={`px-4 py-2 rounded-lg font-medium transition-all
            ${value === d.value 
              ? `${d.color} text-white scale-105` 
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
        >
          {d.emoji} {d.label}
        </button>
      ))}
    </div>
  );
}
```

---

## Deployment

### Discord Developer Portal Setup

1. Go to https://discord.com/developers/applications
2. Select your Geminya application
3. Enable "Activities" in the app settings
4. Configure URL mappings:
   - `/.proxy/api` → Your FastAPI backend URL
   - `/` → Your React frontend URL

### Running Locally

```bash
# Terminal 1: Backend
cd activity/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8080

# Terminal 2: Frontend
cd activity/frontend
npm install
npm run dev

# Terminal 3: Discord tunnel (for local testing)
npx @anthropic/discord-activity-tunnel
```

---

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Foundation | 3-4 days | Project setup, Discord SDK integration |
| Anidle | 4-5 days | Full Anidle game in Activity |
| Guess Anime | 3-4 days | Full Guess Anime in Activity |
| Guess Character | 3-4 days | Full Guess Character in Activity |
| Polish | 2-3 days | UI polish, testing, bug fixes |
| **Total** | **~3 weeks** | All 3 mini-games in Activity |

---

## Next Steps

1. Create the `activity/` directory structure
2. Set up FastAPI backend with health check
3. Set up Vite + React frontend
4. Implement Discord SDK integration
5. Begin Anidle migration (simplest game first)
