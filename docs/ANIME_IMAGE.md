# Anime Image Command

## Overview

The `animeimage` command allows users to fetch random images (screenshots) from a specified anime. This command uses the Shikimori API to search for anime and retrieve their available screenshots.

## Usage

```
/animeimage <anime_name>
```

### Parameters

- `anime_name` (required): The name of the anime to get an image from
  - Supports autocomplete with all available titles including synonyms
  - Accepts Japanese, English, Russian names and alternative titles

## Features

### Autocomplete Support
- Real-time search suggestions as you type
- Includes all title variations (Japanese, English, Russian, synonyms)
- Shows release year for disambiguation
- Only suggests anime that have available images
- **Performance Optimized**: 2-second timeout prevents interaction errors
- **Smart Caching**: Results cached for 5 minutes to improve performance
- **Rate Limited**: Respects API limits with optimized request timing

### Image Display
- Fetches a random screenshot from the specified anime
- High-quality images (332px width or original resolution)
- Shows anime information including:
  - English title (if different from primary)
  - Release year
  - Episode count
  - MyAnimeList score
  - Genres (up to 3, with count if more)
  - Studio information (up to 2, with count if more)

### Error Handling
- Clear error messages for:
  - Anime not found
  - No images available
  - Network/API errors
- Helpful suggestions for common issues

## Examples

```
/animeimage Attack on Titan
/animeimage Shingeki no Kyojin
/animeimage 進撃の巨人
```

All variations above will work due to the comprehensive title matching system.

## Technical Details

### Data Source
- Uses Shikimori GraphQL API
- Rate limited to respect API constraints (5 RPS, 90 RPM)
- Fallback to alternative image resolutions if needed

### Image Selection
- Randomly selects from all available screenshots
- Prefers 332px width images for optimal Discord display
- Falls back to original resolution if needed

### Caching
- Autocomplete results cached for 5 minutes to improve performance
- Reduces API calls and improves response time
- Cache automatically cleaned to prevent memory buildup

## Limitations

- Only anime with available screenshots can be used
- Dependent on Shikimori API availability
- Some older or less popular anime may have limited images
- Rate limiting may cause delays during high usage

## Related Commands

- `/guessanime` - Visual anime guessing game using screenshots
- `/anidle` - Anime guessing game with clues

## Troubleshooting

**Anime not found:**
- Try using the autocomplete feature
- Check spelling
- Try alternative titles (English vs Japanese)

**No images available:**
- Some anime don't have screenshots in the database
- Try a different anime

**Command not responding:**
- May be rate limited - wait a moment and try again
- Check internet connection
- Report persistent issues
