"""
Logging configuration for Geminya project with comprehensive expedition system logging.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Add color to level name
        record.levelname = f"{color}{record.levelname}{reset}"
        
        return super().format(record)


def setup_logging(debug_mode: bool = False):
    """Set up comprehensive logging configuration."""
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Determine log level
    log_level = logging.DEBUG if debug_mode else logging.INFO
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    expedition_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Main application log file (rotating)
    main_log_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "geminya.log",
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=5
    )
    main_log_handler.setLevel(log_level)
    main_log_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(main_log_handler)
    
    # Expedition-specific log file (for detailed expedition debugging)
    expedition_log_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "expeditions.log",
        maxBytes=20 * 1024 * 1024,  # 20MB
        backupCount=3
    )
    expedition_log_handler.setLevel(logging.DEBUG)  # Always debug for expeditions
    expedition_log_handler.setFormatter(expedition_formatter)
    
    # Add expedition filter
    expedition_log_handler.addFilter(ExpeditionLogFilter())
    root_logger.addHandler(expedition_log_handler)
    
    # Discord bot log file
    discord_log_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "discord.log",
        maxBytes=20 * 1024 * 1024,  # 20MB
        backupCount=3
    )
    discord_log_handler.setLevel(logging.INFO)
    discord_log_handler.setFormatter(detailed_formatter)
    
    # Add discord filter
    discord_log_handler.addFilter(DiscordLogFilter())
    root_logger.addHandler(discord_log_handler)
    
    # Database log file
    db_log_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "database.log",
        maxBytes=20 * 1024 * 1024,  # 20MB
        backupCount=3
    )
    db_log_handler.setLevel(logging.INFO)
    db_log_handler.setFormatter(detailed_formatter)
    
    # Add database filter
    db_log_handler.addFilter(DatabaseLogFilter())
    root_logger.addHandler(db_log_handler)
    
    # Error log file (errors and critical only)
    error_log_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "errors.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_log_handler.setLevel(logging.ERROR)
    error_log_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_log_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Log startup
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("🚀 Geminya logging system initialized")
    logger.info(f"📊 Log level: {logging.getLevelName(log_level)}")
    logger.info(f"📁 Logs directory: {logs_dir.absolute()}")
    logger.info("="*60)


class ExpeditionLogFilter(logging.Filter):
    """Filter to capture expedition-related log messages."""
    
    def filter(self, record):
        message = record.getMessage()
        return any(keyword in message for keyword in [
            '[EXPEDITION_', 'expedition', 'EXPEDITION', 
            '[DB_EXPEDITION_', 'DISCORD_EXPEDITION'
        ])


class DiscordLogFilter(logging.Filter):
    """Filter to capture Discord-related log messages."""
    
    def filter(self, record):
        message = record.getMessage()
        return any(keyword in message for keyword in [
            '[DISCORD_', 'discord', 'DISCORD', 'interaction',
            'slash command', 'command', 'guild'
        ]) or record.name.startswith('cogs')


class DatabaseLogFilter(logging.Filter):
    """Filter to capture database-related log messages."""
    
    def filter(self, record):
        message = record.getMessage()
        return any(keyword in message for keyword in [
            '[DB_', 'database', 'DATABASE', 'query', 'transaction',
            'connection', 'postgresql'
        ]) or record.name.startswith('services.database')


def get_expedition_logger(name: str) -> logging.Logger:
    """Get a logger specifically configured for expedition operations."""
    logger = logging.getLogger(f"expedition.{name}")
    return logger


def get_discord_logger(name: str) -> logging.Logger:
    """Get a logger specifically configured for Discord operations."""
    logger = logging.getLogger(f"discord.{name}")
    return logger


def get_database_logger(name: str) -> logging.Logger:
    """Get a logger specifically configured for database operations."""
    logger = logging.getLogger(f"database.{name}")
    return logger