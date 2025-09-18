# 📊 Geminya Expedition System Logging Guide

## Overview
Comprehensive logging has been added throughout the expedition system to help with debugging and monitoring. The logging system creates multiple log files with different purposes and filtering.

## Log Files Created

### 📁 `logs/` Directory Structure
- **`geminya.log`** - Main application log (rotating, 50MB max)
- **`expeditions.log`** - Expedition-specific operations (rotating, 20MB max)
- **`discord.log`** - Discord bot interactions (rotating, 20MB max)
- **`database.log`** - Database operations (rotating, 20MB max)
- **`errors.log`** - Errors and critical issues only (rotating, 10MB max)

## Logging Tags Added

### 🗺️ Expedition Service Logs
- **`[EXPEDITION_START]`** - Starting new expeditions
- **`[EXPEDITION_COMPLETE]`** - Completing expeditions
- **`[EXPEDITION_GET]`** - Getting user expeditions

### 💬 Discord Command Logs
- **`[DISCORD_EXPEDITION_LIST]`** - `/nwnl_expeditions_list` command
- **`[DISCORD_EXPEDITION_STATUS]`** - `/nwnl_expeditions_status` command
- **`[DISCORD_EXPEDITION_COMPLETE]`** - `/nwnl_expeditions_complete` command
- **`[DISCORD_EXPEDITION_LOGS]`** - `/nwnl_expeditions_logs` command

### 🗃️ Database Operation Logs
- **`[DB_EXPEDITION_GET]`** - Getting expeditions from database
- **`[DB_EXPEDITION_CREATE]`** - Creating new expeditions
- **`[DB_EXPEDITION_UPDATE]`** - Updating expedition status

## Log Levels Used

### 🐛 DEBUG
- Detailed parameter logging
- Step-by-step operation tracking
- Internal state information

### ℹ️ INFO
- Important operation completions
- User action summaries
- System state changes

### ⚠️ WARNING
- Expedition limit reached
- User attempting invalid operations
- Non-critical issues

### ❌ ERROR
- Failed operations
- Missing data/templates
- Database errors
- Exception details with stack traces

## Example Log Output

```
2025-09-18 16:34:09 | INFO | [EXPEDITION_START] User 506341727821365258 attempting to start expedition forest_scout with 1 participants
2025-09-18 16:34:09 | DEBUG | [EXPEDITION_START] Checking expedition limit for user 506341727821365258
2025-09-18 16:34:09 | DEBUG | [EXPEDITION_START] User 506341727821365258 has 3 active expeditions
2025-09-18 16:34:09 | WARNING | [EXPEDITION_START] User 506341727821365258 at expedition limit (3/3)
```

## How to Use for Debugging

### 📋 When a Bug Occurs:
1. **Check `expeditions.log`** for expedition-specific issues
2. **Check `discord.log`** for Discord command problems
3. **Check `database.log`** for database-related errors
4. **Check `errors.log`** for critical failures

### 🔍 Log Analysis:
- All logs include timestamps, log levels, and tagged operations
- User IDs are logged for tracking specific user issues
- Database operation counts are logged for performance monitoring
- Full exception traces are captured for debugging

### 🚀 Performance Monitoring:
- Track expedition creation/completion rates
- Monitor database query performance
- Identify bottlenecks in the expedition flow

## Configuration

### Enable Debug Logging:
```python
from config.logging_config import setup_logging
setup_logging(debug_mode=True)  # More detailed logs
```

### Production Logging:
```python
setup_logging(debug_mode=False)  # INFO level and above
```

## Benefits for Bug Fixing

1. **🎯 Pinpoint Issues**: Exact location where problems occur
2. **📈 Track User Flows**: Complete user interaction traces  
3. **⚡ Performance Insights**: Database and service operation timing
4. **🔄 State Tracking**: Expedition states and transitions
5. **📊 Usage Analytics**: User behavior patterns

## Future Enhancements

- **Metrics Integration**: Export logs to monitoring systems
- **Alert System**: Automatic notifications for critical errors
- **Log Aggregation**: Centralized logging for multiple bot instances
- **User Session Tracking**: Complete user journey mapping

---

**Usage**: When reporting bugs, include relevant log sections from the appropriate log files. The tagged format makes it easy to filter and find specific operations.