# 🌸 Waifu Academy Setup Guide

## Overview

The Waifu Academy is a gacha-style collection game where users can summon, collect, and interact with characters from anime series. The system integrates with the MyAnimeList (MAL) API via Jikan to populate character data.

## Installation

### 1. Install Dependencies

```bash
pip install jikanpy-v4 aiosqlite
```

### 2. Initialize Database

Run the initialization script to set up the database and populate it with initial character data:

```bash
python init_waifu_database.py
```

This will:

- Create the SQLite database schema
- Populate with characters from popular anime series
- Set up sample data for testing

## Database Schema

The system uses SQLite with the following main tables:

- **users**: User accounts and academy information
- **waifus**: Character database with stats and metadata
- **user_waifus**: User's collection with bond levels and customization
- **conversations**: Chat history between users and waifus
- **daily_missions**: Daily tasks and rewards
- **events**: Special events and rate-up periods

## Commands

### Core Commands

- `/nwnl_summon [type]` - Summon new waifus (10 crystals per summon)
- `/nwnl_collection [user]` - View waifu collection
- `/nwnl_profile <name>` - View detailed waifu information
- `/nwnl_status` - Check academy status and statistics

### Academy Management

- `/nwnl_daily` - Claim daily Sakura Crystal rewards
- `/nwnl_shop` - Browse academy shop with quartzs items
- `/nwnl_buy` - Purchase items from the shop
- `/nwnl_inventory` - View your purchased items
- `/nwnl_use_item` - Use items from your inventory
- `/nwnl_purchase_history` - View your purchase history
- `/nwnl_rename_academy <name>` - Rename your academy

## Gacha System

### Rarity Rates

- ⭐⭐⭐⭐⭐ (5-Star): 0.6%
- ⭐⭐⭐⭐ (4-Star): 8.5%
- ⭐⭐⭐ (3-Star): 25.0%
- ⭐⭐ (2-Star): 35.0%
- ⭐ (1-Star): 30.9%

### Pity System

- Guaranteed 4-star every 10 pulls
- Guaranteed 5-star every 90 pulls
- Soft pity starts at 75 pulls (increased 5-star rate)

### Constellation System

- Duplicate waifus increase constellation levels
- Higher constellations unlock special abilities
- Constellation levels affect bond progression

## Character Data Sources

### MyAnimeList Integration

The system uses the Jikan API (v4) to fetch character data:

1. **Anime Selection**: Currently uses a curated list of popular series
2. **Character Import**: Fetches main and supporting characters
3. **Rarity Assignment**: Based on character role and popularity (favorites)
4. **Image Integration**: Uses official MAL character images

### Future Enhancements

- Integration with user's MAL account
- Import from user's completed anime list
- Custom character addition system
- Community voting for new additions

## Configuration

### Environment Variables

Currently no special environment variables required. The system uses:

- SQLite database stored in `data/waifu_academy.db`
- Jikan API (public, no authentication required)

### Customization

You can modify the following in `services/waifu_service.py`:

```python
# Gacha rates
GACHA_RATES = {
    5: 0.6,   # 5-star rate
    4: 8.5,   # 4-star rate
    # ... etc
}

# Costs
SUMMON_COST = 10  # Crystals per summon

# Pity thresholds
PITY_5_STAR = 90  # Only 5* pity - guaranteed 5* every 90 pulls

# Multi-summon guarantees
- Multi-summon always performs exactly 10 rolls
- 10th roll guarantees at least 4* rarity if none were pulled in the first 9
```

## Adding New Anime Series

To add more anime series to the database:

1. Find the MAL ID for the anime
2. Add it to the `popular_series` list in `populate_initial_waifus()`
3. Run the initialization script again

Example:

```python
{"mal_id": 16498, "title": "Attack on Titan"}
```

## Development Roadmap

### Phase 1 (Current)

- [x] Basic gacha system
- [x] Character collection
- [x] Database schema
- [x] Core commands

### Phase 2 (Next)

- [ ] Chat system with AI personality
- [ ] Bond level progression
- [ ] Daily missions system
- [ ] Academy customization

### Phase 3 (Future)

- [ ] Events and rate-up banners
- [ ] Trading system
- [ ] Guild features
- [ ] Advanced AI interactions

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `jikanpy-v4` and `aiosqlite` are installed
2. **Database Errors**: Check if `data/` directory exists and is writable
3. **API Rate Limits**: Jikan API has rate limits; initialization adds delays
4. **Missing Characters**: Some anime may not have character data available

### Logging

The system uses Python's logging module. Check logs for:

- Database operations
- API calls to Jikan
- Gacha summon results
- Error details

### Performance

- Database uses indexes for common queries
- Character images are loaded on-demand
- API calls are rate-limited to respect Jikan's limits

## Contributing

When adding new features:

1. Update database schema in `services/database.py`
2. Add business logic to `services/waifu_service.py`
3. Create commands in `cogs/commands/`
4. Update documentation

### Code Style

- Use async/await for all database operations
- Include proper error handling and logging
- Follow Discord.py embed styling conventions
- Document new functions with docstrings

## Support

For issues or questions:

1. Check the logs for error details
2. Verify database integrity
3. Test with a fresh database initialization
4. Report bugs with full error traces
