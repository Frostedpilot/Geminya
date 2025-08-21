# Waifu Gacha System: SQLite to MySQL Migration Guide

This guide will help you migrate your waifu gacha system from SQLite to MySQL.

## Prerequisites

1. **MySQL Database**: You need an online MySQL database with the following:
   - Host address
   - Port (usually 3306)
   - Username and password
   - Database name

2. **Python Dependencies**: Install the required package:
   ```bash
   pip install aiomysql
   ```

## Step-by-Step Migration

### 1. Update Your Secrets Configuration

Add your MySQL credentials to `secrets.json`:

```json
{
    "DISCORD_BOT_TOKEN": "your_discord_bot_token_here",
    "OPENROUTER_API_KEY": "your_openrouter_api_key_here",
    "SAUCENAO_API_KEY": "your_saucenao_api_key_here",
    "TAVILY_API_KEY": "your_tavily_api_key_here",
    "GEMINI_API_KEY_1": "your_gemini_api_key_1_here",
    "GEMINI_API_KEY_2": "your_gemini_api_key_2_here",
    "MYSQL_HOST": "your.mysql.host.com",
    "MYSQL_PORT": 3306,
    "MYSQL_USER": "your_mysql_username",
    "MYSQL_PASSWORD": "your_mysql_password",
    "MYSQL_DATABASE": "geminya_waifu"
}
```

### 2. Test MySQL Connection

Before migrating, test your MySQL connection:

```bash
python test_mysql_connection.py
```

### 3. Create MySQL Tables

The migration script will automatically create the required tables in your MySQL database.

### 4. Run Data Migration

If you have existing SQLite data to migrate:

```bash
python migrate_waifu_to_mysql.py
```

This will:
- Connect to both your SQLite and MySQL databases
- Create all necessary tables in MySQL
- Transfer all existing data (users, waifus, collections, etc.)
- Preserve relationships and maintain data integrity

### 5. Switch to MySQL

Once migration is complete, update your `config.yml`:

```yaml
# Database Configuration
database:
  # Change from "sqlite" to "mysql"
  type: "mysql"
  
  # SQLite configuration (kept for fallback)
  sqlite:
    path: "data/waifu_academy.db"
  
  # MySQL configuration (will use values from secrets.json)
  mysql:
    host: "${MYSQL_HOST}"
    port: "${MYSQL_PORT:3306}"
    user: "${MYSQL_USER}"
    password: "${MYSQL_PASSWORD}"
    database: "${MYSQL_DATABASE}"
    charset: "utf8mb4"
    autocommit: true
```

### 6. Test the Bot

Start your bot and test the waifu commands:
- `/nwnl_summon` - Test summoning
- `/nwnl_collection` - Test collection viewing
- `/nwnl_academy` - Test academy info

## Features

### What's New with MySQL:

1. **Better Performance**: MySQL handles concurrent users better than SQLite
2. **Scalability**: Can handle much larger datasets and user bases
3. **Remote Access**: Database can be hosted separately from the bot
4. **Better JSON Support**: Native JSON column types for complex data
5. **Improved Reliability**: Better crash recovery and data integrity

### Database Schema Changes:

- **JSON Fields**: `base_stats`, `favorite_gifts`, `special_dialogue`, `room_decorations`, and `bonus_conditions` are now proper JSON columns in MySQL
- **Better Indexing**: Optimized indexes for faster queries
- **Foreign Key Constraints**: Proper cascade deletes for data integrity
- **Unicode Support**: Full UTF8MB4 support for emoji and international characters

## Troubleshooting

### Common Issues:

1. **Connection Failed**: 
   - Check your MySQL credentials in `secrets.json`
   - Ensure your MySQL server is accessible
   - Verify firewall settings

2. **Migration Errors**:
   - Ensure the MySQL database exists
   - Check that the MySQL user has CREATE and INSERT permissions
   - Verify the SQLite database path is correct

3. **Bot Startup Issues**:
   - Check the logs for specific error messages
   - Ensure `aiomysql` is installed
   - Verify the config.yml database type is set to "mysql"

### Rollback to SQLite:

If you need to rollback to SQLite:
1. Change `database.type` back to `"sqlite"` in `config.yml`
2. Restart the bot
3. Your original SQLite data will still be intact

## Performance Tips

1. **Connection Pooling**: The MySQL implementation uses connection pooling for better performance
2. **Indexes**: All frequently queried columns have proper indexes
3. **JSON Queries**: Use MySQL's JSON functions for complex queries on JSON fields
4. **Monitoring**: Monitor your MySQL server performance and adjust pool sizes if needed

## Support

If you encounter issues:
1. Check the bot logs in `logs/geminya.log`
2. Verify your MySQL server is running and accessible
3. Test the connection using the provided test script
4. Ensure all credentials are correct in `secrets.json`
