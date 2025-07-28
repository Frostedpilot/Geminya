# Anime Wordle Command Documentation

## Overview
A Discord bot command that implements a Wordle-like game using anime data from the Jikan API (MyAnimeList). Players must guess an anime title based on its properties.

## Game Mechanics

### Properties Compared:
- **Title**: ✅/❌ - Exact match
- **Year**: ⬆️/⬇️/✅ - Higher/Lower/Exact
- **Score**: ⬆️/⬇️/✅ - Higher/Lower/Exact (MyAnimeList's 1-10 scale)
- **Episodes**: ⬆️/⬇️/✅ - Higher/Lower/Exact
- **Genres**: ✅/🟡/❌ - Full match/Partial match/No match
- **Studio**: ✅/❌ - Any studio match
- **Source**: ✅/❌ - Exact match (Manga, Light Novel, Original, etc.)
- **Format**: ✅/❌ - Exact match (TV, Movie, OVA, etc.)

### Game Rules:
- 21 attempts maximum
- One game per channel at a time
- Target anime is randomly selected using weighted difficulty-based selection
- Case-insensitive anime search
- Multiple difficulty levels: Easy, Normal, Hard, Expert

## Commands

### `/animewordle start [difficulty]`
Starts a new anime Wordle game in the current channel.
- **difficulty** (optional): Choose from `easy`, `normal`, `hard`, or `expert`
- Default difficulty is `normal`

### `/animewordle guess <anime_name>`
Make a guess by providing an anime title. The bot will search MyAnimeList and compare properties.

**Example**: `/animewordle guess Attack on Titan`

### `/animewordle hint`
Get a random hint about the target anime (ephemeral message).
**Note**: Using hints adds +2 to your guess count as a penalty.

**Possible hints**:
- One random genre
- Studio name
- Decade
- Format (TV/Movie/OVA)
- Source (Manga/Light Novel/etc.)
- Score range

### `/animewordle giveup`
Reveal the answer and end the current game.

## Difficulty Levels

### Easy 🟢
- Focuses on extremely popular and acclaimed anime
- Higher chance of well-known titles (85-100 score range)

### Normal 🟡 (Default)
- Balanced mix of popular and good anime
- Moderate difficulty with variety of score ranges

### Hard 🟠
- Emphasizes good but lesser-known anime
- Lower chance of extremely popular titles

### Expert 🔴
- Focuses on obscure and unknown anime
- Highest chance of difficult-to-guess titles
- Very challenging for anime enthusiasts

## Data Source
Uses Jikan API v4 (https://api.jikan.moe/v4) for MyAnimeList data:
- No authentication required
- Rate limited to respect API guidelines
- Comprehensive anime database with detailed metadata
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
