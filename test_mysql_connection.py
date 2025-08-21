#!/usr/bin/env python3
"""Test script to verify MySQL connection for the waifu database."""

import asyncio
import aiomysql
import logging
import json
import os
from pathlib import Path


def load_config():
    """Load configuration from files without circular imports."""
    # Load secrets
    secrets_path = Path("secrets.json")
    if not secrets_path.exists():
        raise FileNotFoundError("secrets.json not found")
        
    with open(secrets_path, "r", encoding="utf-8") as f:
        secrets = json.load(f)
    
    # Load config.yml if available
    config_data = {}
    config_path = Path("config.yml")
    if config_path.exists():
        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
        except ImportError:
            pass  # yaml not available
    
    # Get database configuration
    database_config = config_data.get("database", {})
    database_type = database_config.get("type", "sqlite")
    
    if database_type != "mysql":
        raise ValueError("Database type is not set to 'mysql' in config.yml")
    
    # Return MySQL configuration
    return {
        "host": secrets.get("MYSQL_HOST"),
        "port": secrets.get("MYSQL_PORT", 3306),
        "user": secrets.get("MYSQL_USER"),
        "password": secrets.get("MYSQL_PASSWORD"),
        "database": secrets.get("MYSQL_DATABASE"),
        "charset": "utf8mb4",
    }


async def test_mysql_connection():
    """Test the MySQL connection and create basic tables."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        mysql_config = load_config()
        
        logger.info("Testing MySQL connection...")
        logger.info(f"Host: {mysql_config['host']}")
        logger.info(f"Port: {mysql_config['port']}")
        logger.info(f"Database: {mysql_config['database']}")
        logger.info(f"User: {mysql_config['user']}")
        
        # Test connection
        conn = await aiomysql.connect(
            host=mysql_config["host"],
            port=mysql_config["port"],
            user=mysql_config["user"],
            password=mysql_config["password"],
            db=mysql_config["database"],
            charset=mysql_config.get("charset", "utf8mb4"),
            autocommit=True,
        )
        
        logger.info("✅ Successfully connected to MySQL!")
        
        # Test basic operations
        async with conn.cursor() as cursor:
            # Test creating a simple table
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS connection_test (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    test_message VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            logger.info("✅ Successfully created test table!")
            
            # Test inserting data
            await cursor.execute(
                "INSERT INTO connection_test (test_message) VALUES (%s)",
                ("MySQL connection test successful!",)
            )
            logger.info("✅ Successfully inserted test data!")
            
            # Test reading data
            await cursor.execute("SELECT * FROM connection_test ORDER BY id DESC LIMIT 1")
            result = await cursor.fetchone()
            if result:
                logger.info(f"✅ Successfully read test data: {result}")
            
            # Test JSON support (if available)
            try:
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS json_test (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        json_data JSON
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                
                await cursor.execute(
                    "INSERT INTO json_test (json_data) VALUES (%s)",
                    ('{"test": "json support", "nested": {"value": 123}}',)
                )
                logger.info("✅ Successfully tested JSON column support!")
                json_support = True
                
                # Clean up
                await cursor.execute("DROP TABLE IF EXISTS json_test")
                
            except Exception as json_error:
                logger.warning(f"⚠️ JSON columns not supported: {json_error}")
                logger.info("📝 Will use TEXT columns for JSON data instead")
                json_support = False
            # Clean up test tables
            await cursor.execute("DROP TABLE IF EXISTS connection_test")
            logger.info("✅ Cleaned up test tables!")
        
        conn.close()
        logger.info("✅ MySQL connection test completed successfully!")
        
        print("\n" + "="*50)
        print("🎉 MySQL CONNECTION TEST PASSED! 🎉")
        print("="*50)
        print("Your MySQL database is ready for the waifu system!")
        if not json_support:
            print("⚠️ Note: Your MySQL server doesn't support JSON columns.")
            print("   The system will use TEXT columns for JSON data instead.")
        print("You can now run the migration script if you have existing data.")
        print("Or start the bot directly if this is a fresh setup.")
        
        return True
        
    except aiomysql.Error as e:
        logger.error(f"❌ MySQL error: {e}")
        print("\n" + "="*50)
        print("❌ MySQL CONNECTION TEST FAILED!")
        print("="*50)
        print("Please check your MySQL configuration:")
        print("1. Verify host, port, username, and password in secrets.json")
        print("2. Ensure the database exists on your MySQL server")
        print("3. Check that your MySQL user has proper permissions")
        print("4. Verify network connectivity to your MySQL server")
        return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        print("\n" + "="*50)
        print("❌ CONNECTION TEST FAILED!")
        print("="*50)
        print(f"Error: {e}")
        print("Please check your configuration and try again.")
        return False


if __name__ == "__main__":
    asyncio.run(test_mysql_connection())
