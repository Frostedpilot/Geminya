# Guess Character Command

The `guess_character` command is a single-guess character identification game that challenges players to identify both a character and their anime from just a character portrait.

## Commands

### `/guess_character action: [action]`

Main command with different actions for the character guessing game.

**Actions:**

- `Start New Game` - Begin a new character guessing game
- `Make a Guess` - Submit your character and anime guess
- `Give Up` - End the current game and reveal the answer

**Parameters:**

- `action` (required): The action to perform
- `character` (required for "Make a Guess"): Your guess for the character's name
- `anime` (required for "Make a Guess"): Your guess for the anime title
- `difficulty` (optional, for "Start New Game"): Game difficulty level
  - `easy`: Characters from very popular anime (popularity rank 1-1050)
  - `normal`: Characters from moderately popular anime (popularity rank 1-3400)
  - `hard`: Characters from less popular anime (popularity rank 501-25000)
  - `expert`: Characters from obscure anime (popularity rank 1051-25000)

**Default difficulty:** `normal`

**Examples:**

- `/guess_character action:Start New Game difficulty:Normal`
- `/guess_character action:Make a Guess character:Spike Spiegel anime:Cowboy Bebop`
- `/guess_character action:Give Up`

## Game Rules

1. **Single Guess**: You only get one attempt to guess both the character and anime
2. **Portrait Hint**: The only hint is the character's portrait image from MyAnimeList
3. **Dual Requirements**: You must correctly identify both:
   - The character's name (including accepted nicknames)
   - The anime title (including accepted alternative titles)
4. **Scoring**:
   - **Win**: Both character and anime correct
   - **Partial**: Only character OR anime correct  
   - **Loss**: Neither correct

## Difficulty System

The game reuses the Anidle popularity ranges from `config.yml`:

- **Easy**: Focus on extremely popular anime characters that most anime fans know
- **Normal**: Mix of popular and moderately known anime characters
- **Hard**: Characters from less mainstream anime
- **Expert**: Obscure characters from niche anime

## Character Selection Process

1. Select a random anime based on the difficulty's popularity range
2. Fetch all characters from that anime via Jikan API
3. Filter for Main and Supporting characters (excludes background characters)
4. Randomly select one character that has an available portrait image

## API Usage

- **Primary API**: [Jikan API v4](https://jikan.moe/) for anime and character data
- **Endpoints Used**:
  - `/anime` - Get anime list by popularity/score
  - `/anime/{id}/characters` - Get characters for specific anime
- **Rate Limiting**: 1 second delay between API calls to respect Jikan's limits

## Configuration

The command uses the existing `anidle` configuration in `config.yml`:

- `selection_ranges.popularity` - Defines popularity ranges for each difficulty
- `selection_method` - Determines whether to use popularity or score-based selection

No additional configuration is required.
