# Geminya Discord Activity

A Discord Embedded Activity containing anime mini-games: Anidle, Guess Anime, Guess Character, Guess Opening, and Guess Ending.

## Project Structure

```
activity/
├── backend/                 # FastAPI Python backend
│   ├── main.py              # FastAPI entry point
│   ├── requirements.txt     # Python dependencies
│   ├── routers/             # API route handlers
│   │   ├── anidle.py        # Anidle game API
│   │   ├── guess_anime.py   # Guess Anime API
│   │   ├── guess_character.py # Guess Character API
│   │   └── guess_theme.py   # Guess OP/ED theme API
│   ├── services/            # External API services
│   │   ├── jikan_service.py # Jikan (MAL) API wrapper
│   │   ├── shikimori_service.py # Shikimori API wrapper
│   │   ├── animethemes_service.py # AnimeThemes.moe API wrapper
│   │   ├── ids_service.py   # IDs.moe API wrapper
│   │   └── config_service.py # Config management
│   └── models/              # Data models
│       ├── anime.py         # Anime/Character models
│       └── game.py          # Game state models
│
└── frontend/                # React TypeScript frontend
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    └── src/
        ├── main.tsx         # React entry
        ├── App.tsx          # Main app with routing
        ├── discord.ts       # Discord SDK setup
        ├── api/client.ts    # API client
        ├── pages/           # Game pages
        │   ├── Home.tsx     # Game selection
        │   ├── Anidle.tsx   # Wordle-style anime guessing
        │   ├── GuessAnime.tsx # Screenshot guessing
        │   ├── GuessCharacter.tsx # Character identification
        │   ├── GuessOpening.tsx # Opening theme guessing
        │   └── GuessEnding.tsx # Ending theme guessing
        └── components/      # Shared components
            └── common/
                ├── DifficultySelector.tsx
                └── SearchInput.tsx
```

## Quick Start

### Backend

```bash
cd activity/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload --port 8080
```

### Frontend

```bash
cd activity/frontend

# Install dependencies
npm install

# Copy environment file and configure
cp .env.example .env
# Edit .env and add your Discord Client ID

# Run development server
npm run dev
```

### Discord Developer Portal Setup

1. Go to https://discord.com/developers/applications
2. Select your application (or create one)
3. Enable **Activities** in the app settings
4. Add URL mappings:
   - `/.proxy/api` → `http://localhost:8080`
   - `/` → `http://localhost:5173`

### Local Testing with Discord

For local development with Discord's Activity iframe, you need to expose your local servers:

```bash
# Install cloudflared or use Discord's recommended tunnel
npx @anthropic/discord-activity-tunnel
```

## API Endpoints

### Anidle

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/anidle/start` | POST | Start new game |
| `/api/anidle/{game_id}/guess` | POST | Submit guess |
| `/api/anidle/{game_id}/hint` | POST | Get hint (costs attempts) |
| `/api/anidle/{game_id}/giveup` | POST | Give up |
| `/api/anidle/search` | GET | Anime autocomplete |

### Guess Anime

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/guess-anime/start` | POST | Start new game |
| `/api/guess-anime/{game_id}/guess` | POST | Submit guess |
| `/api/guess-anime/{game_id}/giveup` | POST | Give up |
| `/api/guess-anime/search` | GET | Anime autocomplete |

### Guess Character

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/guess-character/start` | POST | Start new game |
| `/api/guess-character/{game_id}/guess` | POST | Submit guess |
| `/api/guess-character/{game_id}/giveup` | POST | Give up |
| `/api/guess-character/search-character` | GET | Character autocomplete |
| `/api/guess-character/search-anime` | GET | Anime autocomplete |

### Guess Opening

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/guess-theme/op/start` | POST | Start new opening game |
| `/api/guess-theme/{game_id}/guess` | POST | Submit anime guess |
| `/api/guess-theme/{game_id}/reveal` | POST | Reveal next stage (audio → video) |
| `/api/guess-theme/{game_id}/giveup` | POST | Give up |
| `/api/guess-theme/search/anime` | GET | Anime autocomplete |

### Guess Ending

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/guess-theme/ed/start` | POST | Start new ending game |
| `/api/guess-theme/{game_id}/guess` | POST | Submit anime guess |
| `/api/guess-theme/{game_id}/reveal` | POST | Reveal next stage (audio → video) |
| `/api/guess-theme/{game_id}/giveup` | POST | Give up |
| `/api/guess-theme/search/anime` | GET | Anime autocomplete |

## Games

### 🎯 Anidle
Wordle-style anime guessing game. You have 21 attempts to guess the anime based on comparison indicators:
- ✅ Correct match
- ⬆️ Target is higher
- ⬇️ Target is lower
- ❌ Incorrect

### 📸 Guess Anime
Identify an anime from screenshots. You get 4 screenshots and 4 attempts. Each wrong guess reveals a new screenshot.

### 🎭 Guess Character
One-shot challenge! Identify the character AND name their anime correctly. Both must be right to win.

### 🎵 Guess Opening
Listen to an anime opening theme and guess which anime it's from! Start with audio only, then reveal the video as a hint.

### 🎶 Guess Ending
Listen to an anime ending theme and guess which anime it's from! Start with audio only, then reveal the video as a hint.

## Tech Stack

**Backend:**
- FastAPI (Python)
- aiohttp (async HTTP client)
- Pydantic (data validation)

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- Tailwind CSS (styling)
- Discord Embedded App SDK
- React Query (data fetching)
- Zustand (state management)

**External APIs:**
- Jikan API v4 (MyAnimeList data with popularity ranking)
- Shikimori GraphQL API (anime screenshots)
- AnimeThemes.moe API (opening/ending themes with videos)
- IDs.moe API (anime ID conversions between MAL, Shikimori, AniList, AniDB, etc.)

## Coexistence with Bot

This Activity coexists with the existing discord.py bot. Both can be run simultaneously:

- Bot commands still work (`/anidle`, `/guessanime`, etc.)
- Activity provides a richer, interactive experience
- No shared database - Activity uses external APIs only

## Production Deployment

For production deployment where other users can play:

**Quick Start:** See [QUICK_DEPLOY.md](QUICK_DEPLOY.md)  
**Full Guide:** See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)  
**Checklist:** See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

**Summary:**
1. Run backend locally (or deploy to Railway/Heroku)
2. Expose backend via Cloudflare Tunnel
3. Deploy frontend to Vercel/Netlify
4. Configure Discord URL mappings
5. Test and launch!

The frontend uses `@discord/embedded-app-sdk` for Discord integration (already configured).
