# Guess the Anime Command Documentation

## Overview
A Discord bot command that implements a visual anime guessing game using screenshot data from the Shikimori GraphQL API. Players must guess an anime title based on 1-4 progressive screenshot reveals.

## Game Mechanics

### Visual Progression System:
- **4 Random Screenshots**: Selected from the target anime's screenshot collection
- **Progressive Reveal**: Wrong guesses reveal additional screenshots
- **Screenshot Quality**: Uses Shikimori's high-quality screenshot database
- **No Manipulation**: Screenshots shown as-is, no cropping or blurring

### Game Rules

- 4 attempts maximum (one for each screenshot)
- One game per channel at a time
- Target anime is randomly selected using difficulty-based filtering
- Case-insensitive anime search with partial matching
- Multiple difficulty levels: Easy, Normal, Hard, Expert

### Scoring & Progression

- **Screenshot 1**: Revealed immediately at game start
- **Screenshots 2-4**: Revealed after each wrong guess
- **Hints Available**: Progressive hints after each guess
- **Time Tracking**: Game duration measured for completion stats
- **Simple Logic**: 4 screenshots = 4 chances to win

## Commands

### `/guessanime start [difficulty]`
Starts a new visual anime guessing game in the current channel.
- **difficulty** (optional): Choose from `easy`, `normal`, `hard`, or `expert`
- Default difficulty is `normal`
- Displays first screenshot with game instructions

### `/guessanime guess <anime_name>`
Make a guess by providing an anime title.
- **anime_name** (required): Your guess for the anime title
- Supports partial matching for alternative names
- Wrong guesses reveal additional screenshots

**Example**: `/guessanime guess Attack on Titan`

### `/guessanime hint`
Get progressive hints about the target anime (ephemeral message).
- **Progressive Unlocking**: More hints available after more wrong guesses
- Available hints: year, episodes, format, genres, score, studios
- Does not count against guess limit

### `/guessanime giveup`
Reveal the answer and end the current game.
- Shows the correct anime with full details
- Displays all remaining screenshots
- Shows game statistics (attempts, duration)

## Difficulty Levels

### Easy 🟢
- Focuses on highly popular anime (score ≥ 8.0)
- Well-known titles with extensive screenshot collections
- Higher chance of recognizable scenes

### Normal 🟡 (Default)
- Balanced mix of popular and good anime (score ≥ 7.0)
- Moderate difficulty with variety of genres and years

### Hard 🟠
- Emphasizes good but lesser-known anime (score ≥ 6.5)
- More challenging to recognize from screenshots alone
- Broader range of anime types and years

### Expert 🔴
- Includes obscure and niche anime (score ≥ 6.0)
- Most challenging for anime enthusiasts
- May include older or very specialized anime

## Data Source
Uses Shikimori GraphQL API (https://shikimori.one/api/graphql):
- OAuth2 authentication not required for public data
- Rate limited: 5 requests/second, 90 requests/minute
- High-quality screenshot database with multiple resolutions
- Comprehensive anime metadata including MAL cross-references

### Screenshot Quality Options:
- `originalUrl`: Full resolution screenshots
- `x332Url`: Medium resolution (332px width)
- `x166Url`: Thumbnail resolution (166px width)

## Game State Management

### GuessAnimeGame Class:
```python
class GuessAnimeGame:
    target: ShikimoriAnimeData           # Target anime to guess
    guesses: List[str]                   # Player guess history
    max_guesses: int = 4                 # Exactly 4 attempts (one per screenshot)
    game_screenshots: List[ScreenshotData] # 4 selected screenshots
    revealed_screenshots: List[ScreenshotData] # Currently visible screenshots
    current_screenshot_index: int        # Next screenshot to reveal
    difficulty: str                      # Game difficulty level
    start_time: float                   # Game start timestamp
```

### Screenshot Selection:
- Randomly selects 4 screenshots from available collection
- Ensures minimum 4 screenshots available before starting game
- Falls back gracefully if fewer screenshots available

### Matching Algorithm:
- **Exact Match**: Direct title comparison (case-insensitive)
- **Partial Match**: Substring matching for alternative names
- **Multi-language**: Supports English, Russian, and Japanese titles
- **Synonyms**: Includes alternative titles and romanizations

## Error Handling
- Network errors gracefully handled with retries
- Rate limiting automatically managed with delays
- Anime with insufficient screenshots filtered out
- Invalid commands provide clear error messages
- Game state cleanup on completion or timeout

## Example Game Flow

1. **Start**: `/guessanime start`
   - Bot queries Shikimori for anime with screenshots
   - Selects target based on difficulty
   - Shows first screenshot with game instructions

2. **Guess**: `/guessanime guess Death Note`
   - Bot checks guess against target anime titles
   - If wrong, reveals next screenshot
   - Shows attempts remaining and current progress

3. **Hint**: `/guessanime hint`
   - Shows available hints based on guess count
   - Information revealed progressively (year → episodes → genres → etc.)

4. **Continue**: Make more guesses based on visual clues
   - Each wrong guess reveals another screenshot
   - Hints become more detailed with more attempts

5. **Win/Lose**: Game ends when correct or out of attempts
   - Shows full anime details and statistics
   - Displays all screenshots and game duration

## Technical Implementation
- Uses `aiohttp` for Shikimori GraphQL requests
- Game state stored in memory per channel with cleanup
- Rate limiting compliance with Shikimori API guidelines
- Screenshot progression logic with random selection
- Follows the bot's service architecture pattern
- Comprehensive error logging and user feedback

## GraphQL Query Structure
```graphql
query GetAnimeWithScreenshots($limit: PositiveInt!, $score: Int, $censored: Boolean) {
  animes(limit: $limit, score: $score, censored: $censored, order: random) {
    id name english russian synonyms malId score episodes kind
    airedOn { year }
    genres { name }
    studios { name }
    poster { originalUrl }
    screenshots { id originalUrl x332Url x166Url }
    statusesStats { status count }
  }
}
```

## Performance Considerations
- Screenshot loading optimized with appropriate resolutions
- Memory management with automatic game cleanup
- Efficient caching of anime data during active games
- Rate limiting prevents API overuse
- Timeout handling for long-running games
