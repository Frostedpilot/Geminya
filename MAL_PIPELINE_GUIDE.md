# MAL Data Pipeline Documentation

## Overview

The MAL (MyAnimeList) data pipeline has been split into modular components for better maintainability and flexibility. The pipeline consists of 4 main scripts:

## Pipeline Scripts

### 1. `pull_from_mal.py` - Data Extraction
**Purpose**: Pull character and anime data from MAL API and export to CSV files.

**Features**:
- ✅ Removes gender filters (no male/female filtering)
- ✅ Removes bio filters  
- ✅ Only filters out characters with 0 favorites
- ✅ Exports to `data/characters_mal.csv` and `data/anime_mal.csv`
- ✅ Skips existing data for faster subsequent runs
- ✅ Rate limiting for API compliance

**Output Files**:
- `data/characters_mal.csv` - Raw character data from MAL
- `data/anime_mal.csv` - Anime metadata for series lookup

**Usage**:
```bash
python pull_from_mal.py
```

### 2. `character_edit.py` - Data Processing (Placeholder)
**Purpose**: Process and customize character data from `data/characters_mal.csv`.

**Current Status**: 📝 **PLACEHOLDER** - Implement your custom logic here

**Features to Implement**:
- Element determination logic
- Rarity calculation based on favorites
- Birthday extraction from character descriptions
- Base stats generation
- Favorite gifts assignment
- Special dialogue creation

**Input**: `data/characters_mal.csv`
**Output**: `character_sql.csv`

**Usage**:
```bash
python character_edit.py
```

### 3. `upload_to_mysql.py` - Database Upload
**Purpose**: Upload processed character data to MySQL database.

**Features**:
- ✅ Reads from `character_sql.csv`
- ✅ Checks for existing characters by MAL ID
- ✅ Generates missing character attributes
- ✅ Bulk upload with error handling
- ✅ Upload progress tracking

**Input**: `character_sql.csv`
**Output**: MySQL database records

**Usage**:
```bash
python upload_to_mysql.py
```

### 4. `populate_from_mal_orchestrator.py` - Pipeline Orchestrator
**Purpose**: Run the complete pipeline or individual steps.

**Features**:
- ✅ Run full pipeline sequentially
- ✅ Skip to specific script
- ✅ Status checking
- ✅ Error handling and logging

**Usage**:
```bash
# Run full pipeline
python populate_from_mal_orchestrator.py

# Skip to specific script
python populate_from_mal_orchestrator.py --skip-to upload_to_mysql.py

# Show status
python populate_from_mal_orchestrator.py --status
```

## Data Flow

```
MAL API → pull_from_mal.py → data/characters_mal.csv + data/anime_mal.csv
                                      ↓
character_edit.py (PLACEHOLDER) → character_sql.csv
                                      ↓
upload_to_mysql.py → MySQL Database
```

## CSV File Formats

### `data/characters_mal.csv`
```csv
mal_id,name,name_kanji,nicknames,about,image_url,favorites,series_type,series_mal_id
123,Character Name,キャラクター,Nick1|Nick2,Character description,https://...,500,anime,456
```

### `data/anime_mal.csv`
```csv
mal_id,title,title_english,title_japanese,type,episodes,status,aired_from,aired_to,score,scored_by,rank,popularity,members,favorites,synopsis,image_url,genres,studios
456,Anime Title,English Title,日本語タイトル,TV,24,Finished Airing,2023-01-01,2023-06-30,8.5,10000,100,50,50000,1000,Synopsis...,https://...,Action|Drama,Studio Name
```

### `character_sql.csv` (After processing)
```csv
mal_id,name,name_kanji,nicknames,about,image_url,favorites,series_type,series_mal_id,element,rarity,birthday,base_stats,favorite_gifts,special_dialogue
123,Character Name,キャラクター,Nick1|Nick2,Description,https://...,500,anime,456,fire,3,01-15,{...},{...},{...}
```

## Configuration

The pipeline uses the existing configuration system:
- `config.yml` - Main configuration
- `secrets.json` - MAL API credentials
- Database connection settings

## Key Changes from Original

### ✅ Completed Changes
1. **Removed Gender Filtering**: No more male/female character filtering
2. **Removed Bio Filtering**: No substantial description requirements  
3. **Added 0 Favorites Filter**: Only characters with >0 favorites are included
4. **CSV Export System**: Data persistence between runs
5. **Modular Architecture**: Separate concerns for better maintainability
6. **Skip Existing Data**: Faster subsequent runs
7. **Error Recovery**: Individual script failures don't break entire pipeline

### 📝 To Be Implemented
1. **Character Editor Logic**: Implement custom processing in `character_edit.py`
2. **Advanced Filtering**: Add custom character filters if needed
3. **Data Validation**: Add CSV validation and cleanup
4. **Batch Processing**: Handle large datasets efficiently

## Database Schema

The upload script expects these database columns:
- `name` - Character name
- `series` - Series title (from data/anime_mal.csv lookup)
- `genre` - "Anime" or "Manga"
- `element` - Character element (fire, water, earth, etc.)
- `rarity` - 1-5 star rarity
- `image_url` - Character image URL
- `mal_id` - MyAnimeList character ID
- `base_stats` - JSON object with attack, defense, speed, hp
- `birthday` - Character birthday (YYYY-MM-DD or MM-DD)
- `favorite_gifts` - JSON array of gift preferences
- `special_dialogue` - JSON object with dialogue lines

## Error Handling

Each script includes:
- ✅ Comprehensive logging
- ✅ File existence checks
- ✅ API rate limiting
- ✅ Database connection validation
- ✅ Graceful error recovery
- ✅ Progress tracking

## Performance Considerations

- **Rate Limiting**: 1.5s delay between API calls
- **Incremental Updates**: Skip existing data
- **Batch Processing**: Efficient database operations
- **Memory Management**: Process data in chunks

## Troubleshooting

### Common Issues

1. **MAL Authentication Failed**
   - Check `secrets.json` credentials
   - Verify OAuth setup

2. **CSV Files Not Found**
   - Run `pull_from_mal.py` first
   - Check file permissions

3. **Database Connection Failed**
   - Verify MySQL server is running
   - Check database credentials

4. **Character Upload Failures**
   - Check for duplicate MAL IDs
   - Verify required fields are present

### Logs

Check these log files for debugging:
- Console output for real-time progress
- `logs/geminya.log` for application logs
- `logs/errors.log` for error details

## Next Steps

1. **Implement Character Editor**: Add your custom logic to `character_edit.py`
2. **Test Pipeline**: Run full pipeline with small dataset
3. **Customize Filters**: Add additional character filtering if needed
4. **Optimize Performance**: Tune for your dataset size
5. **Add Monitoring**: Set up pipeline monitoring and alerts

---

*Pipeline successfully separates data extraction, processing, and upload for maximum flexibility and maintainability.*
