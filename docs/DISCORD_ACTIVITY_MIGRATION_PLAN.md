# Discord Activity Migration Plan

> **Scope**: Convert all NWNL gamemodes + mini-games (guess anime, guess character, anidle) into a Discord Embedded Activity

---

## Executive Summary

This document outlines the complete transformation of the Geminya Discord bot from a **command-based bot** to a **Discord Embedded Activity** (interactive web application running inside Discord).

### What Changes

| Current State | Future State |
|--------------|--------------|
| Python discord.py bot | JavaScript/TypeScript web app + Python API backend |
| Slash commands + embeds | Full interactive web UI |
| Per-channel game instances | Real-time multiplayer sessions |
| Text-based interaction | Mouse/touch/keyboard interaction |

---

## High-Level Architecture

### Current Architecture
```
┌─────────────────────────────────────────────────────┐
│                    Discord Client                    │
│   ┌─────────────────────────────────────────────┐   │
│   │           Slash Commands / Embeds            │   │
│   └─────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│              Python Bot (discord.py)                 │
│   ┌───────────┐  ┌───────────┐  ┌───────────────┐   │
│   │   Cogs    │→ │ Services  │→ │   Database    │   │
│   └───────────┘  └───────────┘  └───────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Target Architecture
```
┌─────────────────────────────────────────────────────┐
│                    Discord Client                    │
│   ┌─────────────────────────────────────────────┐   │
│   │       Discord Activity (iframe)              │   │
│   │   ┌─────────────────────────────────────┐   │   │
│   │   │     React/Vue Web Application        │   │   │
│   │   │   (HTML/CSS/JS + Embedded App SDK)   │   │   │
│   │   └─────────────────────────────────────┘   │   │
│   └─────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        │ REST + WebSocket
                        ▼
┌─────────────────────────────────────────────────────┐
│              Python API Backend (FastAPI)            │
│   ┌───────────┐  ┌───────────┐  ┌───────────────┐   │
│   │ REST API  │→ │ Services  │→ │   Database    │   │
│   │ WebSocket │  │  (reuse)  │  │    (reuse)    │   │
│   └───────────┘  └───────────┘  └───────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## Component Inventory

### Games to Migrate

| Game | Source File | Lines | Complexity | Multiplayer? |
|------|-------------|-------|------------|--------------|
| **NWNL Gacha** | `waifu_summon.py` | 2061 | High | No (solo) |
| **Academy Management** | `waifu_academy.py` | 720 | Medium | No (solo) |
| **Shop System** | `shop.py` | 1610 | High | No (solo) |
| **Expeditions** | `expeditions.py` | 4754 | Very High | Team-based |
| **World Threat** | `world_threat.py` | 1866 | High | Coop |
| **Guess Anime** | `guess_anime.py` | 863 | Medium | Channel-shared |
| **Guess Character** | `guess_character.py` | 1195 | Medium | Channel-shared |
| **Anidle** | `anidle.py` | 1274 | Medium | Channel-shared |

### Services to Preserve

| Service | File | Can Reuse? | Notes |
|---------|------|------------|-------|
| `DatabaseService` | `database.py` | ✅ Full | Just add API layer |
| `WaifuService` | `waifu_service.py` | ✅ Full | Core gacha logic |
| `ExpeditionService` | `expedition_service.py` | ✅ Full | Expedition logic |
| `WorldThreatService` | `world_threat_service.py` | ✅ Full | World Threat logic |
| `AIService` | `ai_service.py` | ✅ Full | AI interactions |

### External APIs Used

| API | Used By | Purpose |
|-----|---------|---------|
| Jikan (MAL) | anidle, guess_character | Anime/character data |
| Shikimori | guess_anime | Screenshots, anime info |

---

## Technology Stack

### Frontend (New)
| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | **React + TypeScript** | UI components |
| Build Tool | **Vite** | Fast development |
| State Management | **Zustand** or **Redux Toolkit** | Global state |
| Styling | **Tailwind CSS** or **CSS Modules** | Styling |
| Discord SDK | `@discord/embedded-app-sdk` | Discord integration |
| Game Engine (optional) | **PixiJS** or **Phaser** | Mini-game graphics |
| WebSocket | **Socket.io Client** | Real-time sync |

### Backend (Modified)
| Component | Technology | Purpose |
|-----------|------------|---------|
| API Framework | **FastAPI** | REST + WebSocket API |
| WebSocket | **FastAPI WebSockets** or **Socket.io** | Real-time events |
| Auth | Discord OAuth2 (via SDK) | User authentication |
| Database | PostgreSQL (existing) | Data persistence |

---

## Module Migration Details

### 1. NWNL Gacha System (`waifu_summon.py`)

#### Current Flow
```
/nwnl_summon → WaifuSummonCog → WaifuService → Database
                    ↓
            Discord Embed (result)
```

#### New Flow
```
[Click Summon Button] → Frontend State → API Call
                                            ↓
                        ← JSON Response ← WaifuService
                            ↓
                    Animated Summon UI (reveals card)
```

#### Frontend Components
```
src/
├── components/
│   ├── gacha/
│   │   ├── SummonButton.tsx      # Main summon button
│   │   ├── SummonAnimation.tsx   # Pull animation
│   │   ├── WaifuCard.tsx         # Character card display
│   │   ├── MultiPullResults.tsx  # 10-pull grid view
│   │   └── PityCounter.tsx       # Pity display
│   ├── collection/
│   │   ├── CollectionGrid.tsx    # Waifu grid view
│   │   ├── WaifuProfile.tsx      # Detail view
│   │   └── FilterBar.tsx         # Search/filter
```

#### API Endpoints (New)
```python
# api/gacha.py
@router.post("/summon")
async def summon(discord_id: str, banner_id: Optional[int] = None):
    return await waifu_service.perform_summon(discord_id, banner_id)

@router.post("/multi-summon")
async def multi_summon(discord_id: str, banner_id: Optional[int] = None):
    results = []
    for _ in range(10):
        results.append(await waifu_service.perform_summon(discord_id, banner_id))
    return results

@router.get("/collection/{discord_id}")
async def get_collection(discord_id: str, page: int = 1, limit: int = 20):
    return await database.get_user_waifus(discord_id, page, limit)
```

---

### 2. Academy Management (`waifu_academy.py`)

#### Frontend Components
```
src/
├── components/
│   ├── academy/
│   │   ├── StatusPanel.tsx       # Academy status overview
│   │   ├── CurrencyBar.tsx       # Crystals, coins display
│   │   ├── DailyRewards.tsx      # Daily claim button
│   │   ├── MissionList.tsx       # Daily missions
│   │   └── AcademySettings.tsx   # Rename, reset options
```

#### API Endpoints
```python
@router.get("/academy/status/{discord_id}")
@router.post("/academy/claim-daily/{discord_id}")
@router.get("/academy/missions/{discord_id}")
@router.post("/academy/rename/{discord_id}")
```

---

### 3. Shop System (`shop.py`)

#### Frontend Components
```
src/
├── components/
│   ├── shop/
│   │   ├── ShopGrid.tsx          # Item grid
│   │   ├── ShopItem.tsx          # Individual item card
│   │   ├── CartSidebar.tsx       # Purchase cart
│   │   ├── InventoryDrawer.tsx   # User inventory
│   │   └── PurchaseModal.tsx     # Confirm purchase
```

---

### 4. Expeditions (`expeditions.py`)

#### Complexity Note
Expeditions is the most complex module (4754 lines). Requires:
- Team selection UI (drag & drop)
- Progress visualization
- Equipment management
- Reward animations

#### Frontend Components
```
src/
├── components/
│   ├── expeditions/
│   │   ├── ExpeditionList.tsx    # Available expeditions
│   │   ├── ExpeditionCard.tsx    # Single expedition
│   │   ├── TeamBuilder.tsx       # Character selection grid
│   │   ├── CharacterSlot.tsx     # Draggable slot
│   │   ├── ProgressTracker.tsx   # Real-time progress
│   │   ├── EquipmentPanel.tsx    # Equipment selection
│   │   └── RewardsModal.tsx      # Completion rewards
```

---

### 5. World Threat (`world_threat.py`)

#### Multiplayer Requirement
World Threat requires **real-time multiplayer** - multiple users collaborate against a boss.

#### WebSocket Events
```javascript
// Client → Server
socket.emit('join_world_threat', { bossId, discordId });
socket.emit('select_team', { characters: [...] });
socket.emit('start_fight', {});

// Server → Client
socket.on('player_joined', (data) => {});
socket.on('fight_update', (data) => {});
socket.on('boss_defeated', (rewards) => {});
```

#### Frontend Components
```
src/
├── components/
│   ├── world-threat/
│   │   ├── BossDisplay.tsx       # Boss HP, stats
│   │   ├── PlayerList.tsx        # Active players
│   │   ├── TeamSelection.tsx     # 6-character picker
│   │   ├── FightAnimation.tsx    # Battle visualization
│   │   ├── DamageNumbers.tsx     # Floating damage
│   │   └── LeaderboardPanel.tsx  # Rankings
```

---

### 6. Mini-Games

#### Guess Anime (`guess_anime.py`)
Currently uses Shikimori API for screenshots. 

**Frontend Features:**
- Full-screen screenshot display
- Animated reveal (blur → clear)
- Answer input with autocomplete
- Score/streak tracking

#### Guess Character (`guess_character.py`)
Uses Jikan API for character images.

**Frontend Features:**
- Character portrait display
- Two-input form (character name + anime)
- Timer visualization
- Difficulty selector

#### Anidle (`anidle.py`)
Wordle-style anime guessing game.

**Frontend Features:**
- Wordle-style grid (21 rows × 7 columns)
- Color-coded comparison indicators
- Anime search autocomplete
- Category hints (genre, year, studio, etc.)

---

## Directory Structure (New)

```
geminya/
├── api/                          # FastAPI backend
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry
│   ├── routers/
│   │   ├── gacha.py              # Gacha endpoints
│   │   ├── academy.py            # Academy endpoints
│   │   ├── shop.py               # Shop endpoints
│   │   ├── expeditions.py        # Expedition endpoints
│   │   ├── world_threat.py       # World Threat endpoints
│   │   └── minigames.py          # Mini-game endpoints
│   ├── websocket/
│   │   ├── manager.py            # WebSocket connection manager
│   │   └── handlers.py           # Event handlers
│   └── middleware/
│       └── discord_auth.py       # Discord OAuth validation
│
├── frontend/                     # React frontend (NEW)
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── discord.ts            # Discord SDK setup
│   │   ├── api/                  # API client
│   │   │   └── client.ts
│   │   ├── components/           # UI components
│   │   │   ├── gacha/
│   │   │   ├── academy/
│   │   │   ├── shop/
│   │   │   ├── expeditions/
│   │   │   ├── world-threat/
│   │   │   └── minigames/
│   │   ├── pages/                # Route pages
│   │   │   ├── Home.tsx
│   │   │   ├── Gacha.tsx
│   │   │   ├── Collection.tsx
│   │   │   ├── Expeditions.tsx
│   │   │   ├── WorldThreat.tsx
│   │   │   └── MiniGames.tsx
│   │   ├── hooks/                # Custom hooks
│   │   ├── stores/               # State management
│   │   └── styles/               # CSS/Tailwind
│   └── public/
│       └── assets/
│
├── services/                     # EXISTING - Keep & reuse
│   ├── database.py
│   ├── waifu_service.py
│   ├── expedition_service.py
│   └── world_threat_service.py
│
├── src/wanderer_game/            # EXISTING - Keep & reuse
│   ├── models/
│   ├── systems/
│   └── registries/
│
└── cogs/                         # DEPRECATED - Replace with API
    └── commands/                 # (Can remove after migration)
```

---

## Migration Phases

### Phase 1: Foundation (2-3 weeks)
- [ ] Set up FastAPI backend alongside existing bot
- [ ] Create Discord Application with Activity enabled
- [ ] Set up React + Vite frontend project
- [ ] Implement Discord Embedded App SDK integration
- [ ] Create basic navigation/routing structure
- [ ] Implement Discord OAuth flow

**Deliverable:** Empty Activity shell that loads inside Discord

---

### Phase 2: Core Systems (3-4 weeks)
- [ ] Migrate gacha/summon to Activity
  - [ ] Summon button + animation
  - [ ] Result card display
  - [ ] Multi-pull grid
- [ ] Migrate collection viewer
  - [ ] Grid view with pagination
  - [ ] Filter/search
  - [ ] Profile modal
- [ ] Migrate academy status
  - [ ] Status dashboard
  - [ ] Daily rewards claim
  - [ ] Mission tracker

**Deliverable:** Playable gacha system in Activity

---

### Phase 3: Economy Systems (2-3 weeks)
- [ ] Migrate shop
  - [ ] Shop grid UI
  - [ ] Purchase flow
  - [ ] Inventory management
- [ ] Currency display
- [ ] Purchase history

**Deliverable:** Complete economy loop

---

### Phase 4: Complex Gamemodes (4-5 weeks)
- [ ] Migrate Expeditions
  - [ ] Team builder (drag & drop)
  - [ ] Equipment system
  - [ ] Progress tracking
  - [ ] Reward claiming
- [ ] Migrate World Threat
  - [ ] WebSocket multiplayer
  - [ ] Boss fight visualization
  - [ ] Team selection
  - [ ] Real-time damage sync

**Deliverable:** All main gamemodes functional

---

### Phase 5: Mini-Games (3-4 weeks)
- [ ] Migrate Guess Anime
  - [ ] Screenshot reveal mechanic
  - [ ] Answer autocomplete
- [ ] Migrate Guess Character
  - [ ] Character image display
  - [ ] Two-input guessing
- [ ] Migrate Anidle
  - [ ] Wordle-style grid
  - [ ] Comparison indicators
  - [ ] Anime search

**Deliverable:** All mini-games playable

---

### Phase 6: Polish & Launch (2-3 weeks)
- [ ] Performance optimization
- [ ] Mobile responsiveness
- [ ] Accessibility improvements
- [ ] Error handling
- [ ] Analytics integration
- [ ] Beta testing
- [ ] Discord Activity store submission

**Deliverable:** Production-ready Activity

---

## Effort Estimates

| Phase | Duration | Developers Needed |
|-------|----------|-------------------|
| Foundation | 2-3 weeks | 1-2 |
| Core Systems | 3-4 weeks | 2-3 |
| Economy | 2-3 weeks | 1-2 |
| Complex Gamemodes | 4-5 weeks | 2-3 |
| Mini-Games | 3-4 weeks | 1-2 |
| Polish & Launch | 2-3 weeks | 1-2 |
| **Total** | **16-22 weeks** | **~3-4 months** |

---

## Technical Considerations

### Discord Activity Limitations
- **Max iframe size**: Activities run in an iframe, limited screen real estate
- **Rate limits**: Discord SDK has rate limits on certain operations
- **Server count during development**: Activities in development only work in servers with <25 members

### API Authentication
```typescript
// Frontend: Get Discord user from SDK
const sdk = new DiscordSDK(CLIENT_ID);
await sdk.ready();
const { access_token } = await sdk.commands.authenticate({ scope: ['identify'] });

// Send token to backend with each request
const response = await fetch('/api/summon', {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
```

### WebSocket Architecture (for World Threat)
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Player 1  │────▶│             │◀────│   Player 2  │
│   (Client)  │     │  WebSocket  │     │   (Client)  │
└─────────────┘     │   Server    │     └─────────────┘
                    │  (FastAPI)  │
┌─────────────┐     │             │     ┌─────────────┐
│   Player 3  │────▶│             │◀────│   Player 4  │
│   (Client)  │     └─────────────┘     │   (Client)  │
└─────────────┘                         └─────────────┘
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Long development time | High | Phase-based rollout, parallel development |
| Learning curve (React/TS) | Medium | Use templates, component libraries |
| Discord SDK breaking changes | Medium | Pin SDK version, monitor changelog |
| Performance on low-end devices | Medium | Lazy loading, code splitting |
| Data migration issues | Low | Keep existing database, only add API |
| External API rate limits | Low | Implement caching, proxy through backend |

---

## Decision Points for User

Before proceeding, please consider:

1. **Hybrid approach?** Keep bot commands for basic functions, Activity for rich experiences?

2. **Priority order?** Which games should be migrated first?

3. **Design style?** Anime-themed UI, minimalist, gaming-style?

4. **Mobile support?** Activities can run on mobile Discord - prioritize touch controls?

5. **Sound effects?** Add audio for summons, wins, etc.?

---

## Next Steps

1. **Create Discord Application** with Activity feature enabled
2. **Set up development environment** (Node.js, Vite, FastAPI)
3. **Build proof-of-concept** with single gacha summon
4. **Validate with Discord** (review Activity guidelines)
5. **Begin Phase 1 implementation**

---

## References

- [Discord Embedded App SDK](https://discord.com/developers/docs/activities/overview)
- [Discord Activities Examples](https://github.com/discord/embedded-app-sdk-examples)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Vite + React Setup](https://vitejs.dev/guide/)
- [PixiJS](https://pixijs.com/) (for game animations)
