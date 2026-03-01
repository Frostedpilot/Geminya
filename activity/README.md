# Geminya Discord Activity

A Discord Embedded Activity containing anime mini-games: Anidle, Guess Anime, Guess Character, Guess Opening, and Guess Ending.

## Project Structure

```
activity/
├── backend/                 # FastAPI Python backend
│   ├── main.py              # FastAPI entry point
│   ├── config.yml           # Game difficulty & selection config
│   ├── requirements.txt     # Python dependencies
│   ├── routers/             # API route handlers
│   │   ├── anidle.py        # Anidle game API
│   │   ├── guess_anime.py   # Guess Anime API
│   │   ├── guess_character.py # Guess Character API
│   │   ├── guess_theme.py   # Guess OP/ED theme API
│   │   └── media_proxy.py   # Media proxy for Discord CSP
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
├── frontend/                # React TypeScript frontend (hosted on Vercel)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── main.tsx         # React entry
│       ├── App.tsx          # Main app with routing
│       ├── discord.ts       # Discord SDK + OAuth2 setup
│       ├── api/client.ts    # API client
│       ├── pages/           # Game pages
│       │   ├── Home.tsx     # Game selection
│       │   ├── Anidle.tsx   # Wordle-style anime guessing
│       │   ├── GuessAnime.tsx # Screenshot guessing
│       │   ├── GuessCharacter.tsx # Character identification
│       │   ├── GuessOpening.tsx # Opening theme guessing
│       │   └── GuessEnding.tsx # Ending theme guessing
│       └── components/      # Shared components
│           └── common/
│               ├── DifficultySelector.tsx
│               ├── SearchInput.tsx
│               └── Sidebar.tsx
│
└── startgame.bat            # Local dev launcher (backend + tunnel)
```

## Secrets & Configuration

The backend loads secrets in this priority order:
1. `secrets.json` (at repo root — used for local dev)
2. Environment variables (used on Koyeb)

| Secret | Required | Purpose |
|--------|----------|---------|
| `DISCORD_APP_ID` | ✅ | Discord OAuth2 token exchange |
| `DISCORD_CLIENT_SECRET` | ✅ | Discord OAuth2 token exchange |
| `IDS_MOE_API_KEY` | ✅ | Anime ID conversion (Guess Anime needs this) |
| `TMDB_API_KEY` | Optional | TMDB integration |

---

## Deployment Options

### Option A: Koyeb (Production — 24/7)

The backend runs on [Koyeb](https://app.koyeb.com/) free tier. Frontend stays on Vercel.

```
Discord Activity → Vercel (Frontend) → Koyeb (Backend API)
```

**Koyeb Service Config:**

| Setting | Value |
|---------|-------|
| Working directory | `activity/backend` |
| Build command | `pip install -r requirements.txt` |
| Run command | `uvicorn main:app --host 0.0.0.0 --port 8000` |
| Instance | Free ($0.00/mo) |

Set all secrets as **Environment Variables** in Koyeb (no `secrets.json` needed).

**Discord Developer Portal → Activities → URL Mappings:**

| Prefix | Target |
|--------|--------|
| `/api` | `https://your-service.koyeb.app` |

> ⚠️ Free tier sleeps after ~1 hour of inactivity. First request after sleep takes 3–5 seconds.

---

### Option B: Local Dev (Testing)

Run the backend on your PC and expose it via Cloudflare Tunnel.

```
Discord Activity → Vercel (Frontend) → Cloudflare Tunnel → localhost:8080
```

#### Backend

```bash
cd activity/backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

#### Frontend (only needed if developing UI)

```bash
cd activity/frontend
npm install
cp .env.example .env         # Set VITE_DISCORD_CLIENT_ID
npm run dev
```

#### Expose via Tunnel

```bash
cloudflared tunnel run geminya
```

Or use the launcher script:
```bash
startgame.bat                # Starts both backend + tunnel
```

**Discord Developer Portal → Activities → URL Mappings:**

| Prefix | Target |
|--------|--------|
| `/api` | `https://api.geminya.me` (or your tunnel URL) |

#### Switching Between Local and Koyeb

Just change the URL mapping target in Discord Developer Portal:
- **Local:** `https://api.geminya.me` (tunnel)
- **Production:** `https://your-service.koyeb.app` (Koyeb)

---

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

### Guess OP/ED

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/guess-theme/op/start` | POST | Start opening game |
| `/api/guess-theme/ed/start` | POST | Start ending game |
| `/api/guess-theme/{game_id}/guess` | POST | Submit anime guess |
| `/api/guess-theme/{game_id}/reveal` | POST | Reveal video hint |
| `/api/guess-theme/{game_id}/giveup` | POST | Give up |
| `/api/guess-theme/search/anime` | GET | Anime autocomplete |

## Games

### 🎯 Anidle
Wordle-style anime guessing game. You have 21 attempts to guess the anime based on comparison indicators (✅ correct, ⬆️ higher, ⬇️ lower, ❌ wrong).

### 📸 Guess Anime
Identify an anime from screenshots. You get 4 screenshots and 4 attempts. Each wrong guess reveals a new screenshot.

### 🎭 Guess Character
One-shot challenge! Identify 4 characters AND name their anime correctly.

### 🎵 Guess Opening
Listen to an anime opening theme and guess which anime it's from. Stage 1: audio only → Stage 2: full video hint.

### 🎶 Guess Ending
Listen to an anime ending theme and guess which anime it's from. Stage 1: audio only → Stage 2: full video hint.

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

**External APIs:**
- Jikan API v4 (MyAnimeList data with popularity ranking)
- Shikimori GraphQL API (anime screenshots)
- AnimeThemes.moe API (opening/ending themes with videos)
- IDs.moe API (anime ID conversions between MAL, Shikimori, AniList, AniDB, etc.)

## Coexistence with Bot

This Activity coexists with the existing discord.py bot. Both can be run simultaneously:

- Bot commands still work (`/anidle`, `/guessanime`, etc.)
- Activity provides a richer, interactive experience
- No shared database — Activity uses external APIs only
