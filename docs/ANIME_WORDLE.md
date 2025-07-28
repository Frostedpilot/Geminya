# Anime Wordle Command Documentation

## Overview
A Discord bot command that implements a Wordle-like game using anime data from the AniList API. Players must guess an anime title based on its properties.

## Game Mechanics

### Properties Compared:
- **Title**: ✅/❌ - Exact match
- **Year**: ⬆️/⬇️/✅ - Higher/Lower/Exact
- **Score**: ⬆️/⬇️/✅ - Higher/Lower/Exact (0-100 scale)
- **Episodes**: ⬆️/⬇️/✅ - Higher/Lower/Exact
- **Genres**: ✅/🟡/❌ - Full match/Partial match/No match
- **Studio**: ✅/❌ - Any studio match
- **Source**: ✅/❌ - Exact match (Manga, Light Novel, Original, etc.)
- **Format**: ✅/❌ - Exact match (TV, Movie, OVA, etc.)

### Game Rules:
- 6 attempts maximum
- One game per channel at a time
- Target anime is randomly selected from popular anime (top 500)
- Case-insensitive anime search

## Commands

### `/animewordle start`
Starts a new anime Wordle game in the current channel.

### `/animewordle guess <anime_name>`
Make a guess by providing an anime title. The bot will search AniList and compare properties.

**Example**: `/animewordle guess Attack on Titan`

### `/animewordle hint`
Get a random hint about the target anime (ephemeral message).

**Possible hints**:
- One random genre
- Studio name
- Decade
- Format (TV/Movie/OVA)
- Source (Manga/Light Novel/etc.)
- Score range

### `/animewordle giveup`
Reveal the answer and end the current game.

## Data Source
Uses AniList GraphQL API (https://graphql.anilist.co) for anime data:
- No authentication required for basic queries
- Rate limit: Reasonable for Discord bot usage
- Comprehensive anime database with detailed metadata

## Error Handling
- Network errors are gracefully handled
- Anime not found provides helpful feedback
- Game state is properly managed per channel
- Invalid commands provide clear error messages

## Example Game Flow

1. **Start**: `/animewordle start`
   - Bot selects random popular anime
   - Shows game instructions

2. **Guess**: `/animewordle guess Demon Slayer`
   - Bot searches for "Demon Slayer" on AniList
   - Compares all properties with target
   - Shows results with indicators

3. **Continue**: Make more guesses based on the feedback
   - ⬆️ means target value is higher
   - ⬇️ means target value is lower
   - ✅ means exact match
   - 🟡 means partial match (genres only)

4. **Win/Lose**: Game ends when you guess correctly or run out of attempts

## Technical Implementation
- Uses `aiohttp` for AniList API requests
- Game state stored in memory per channel
- Automatic cleanup when games complete
- Follows the bot's service architecture pattern
- Proper error logging and user feedback
