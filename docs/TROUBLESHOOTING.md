# Troubleshooting Guide

## Common Issues and Solutions

This guide covers the most frequent problems you might encounter when running Geminya and how to resolve them.

## Bot Startup Issues

### ❌ "Invalid Bot Token" Error

**Symptoms:**

```
discord.errors.LoginFailure: Improper token has been passed.
```

**Solutions:**

1. **Verify Token Format**: Ensure your Discord bot token is correctly formatted

   ```json
   {
     "DISCORD_BOT_TOKEN": "MTxxx.Gxxx.xxx-xxx"
   }
   ```

2. **Check for Extra Characters**: Remove any trailing spaces or newlines

   ```bash
   # Incorrect (with newline)
   "DISCORD_BOT_TOKEN": "MTxxx.Gxxx.xxx-xxx\n"

   # Correct
   "DISCORD_BOT_TOKEN": "MTxxx.Gxxx.xxx-xxx"
   ```

3. **Regenerate Token**: If token was compromised, regenerate in Discord Developer Portal
   - Go to Discord Developer Portal → Your Application → Bot
   - Click "Reset Token" and update `secrets.json`

### ❌ "ModuleNotFoundError" for Dependencies

**Symptoms:**

```
ModuleNotFoundError: No module named 'discord'
```

**Solutions:**

1. **Install Missing Dependencies**:

   ```bash
   pip install discord.py openai aiohttp pyyaml
   ```

2. **Check Virtual Environment**: Ensure you're in the correct virtual environment

   ```bash
   # Activate virtual environment first
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows

   # Then install dependencies
   pip install -r requirements.txt
   ```

3. **Python Version Compatibility**: Ensure Python 3.8+ is being used
   ```bash
   python --version  # Should be 3.8 or higher
   ```

### ❌ "FileNotFoundError: secrets.json"

**Symptoms:**

```
FileNotFoundError: [Errno 2] No such file or directory: 'secrets.json'
```

**Solutions:**

1. **Create secrets.json** in the project root:

   ```json
   {
     "DISCORD_BOT_TOKEN": "your_token_here",
     "OPENROUTER_API_KEY": "your_api_key_here"
   }
   ```

2. **Check File Location**: Ensure `secrets.json` is in the same directory as `base.py`

3. **File Permissions**: Ensure the file is readable
   ```bash
   chmod 644 secrets.json  # Linux/Mac
   ```

## AI Response Issues

### ❌ "No Response from AI Model"

**Symptoms:**

- Bot receives messages but doesn't respond
- Console shows "No response from model" errors

**Solutions:**

1. **Verify OpenRouter API Key**:

   ```json
   {
     "OPENROUTER_API_KEY": "sk-or-v1-xxxxxxxxxxxx"
   }
   ```

2. **Check API Credits**: Ensure your OpenRouter account has available credits

   - Log into OpenRouter dashboard
   - Check usage and billing status

3. **Test API Connection**:

   ```python
   # Test script
   import asyncio
   from openai import AsyncOpenAI

   async def test_api():
       client = AsyncOpenAI(
           base_url="https://openrouter.ai/api/v1",
           api_key="your_api_key_here"
       )
       try:
           response = await client.chat.completions.create(
               model="deepseek/deepseek-chat-v3-0324:free",
               messages=[{"role": "user", "content": "Hello!"}]
           )
           print("API working:", response.choices[0].message.content)
       except Exception as e:
           print("API error:", e)

   asyncio.run(test_api())
   ```

### ❌ "Rate Limited by AI API"

**Symptoms:**

```
Error getting response from model: HTTP 429 Too Many Requests
```

**Solutions:**

1. **Wait for Rate Limit Reset**: Rate limits typically reset after 1 minute
2. **Reduce Bot Usage**: Limit how frequently users can trigger responses
3. **Upgrade API Plan**: Consider upgrading OpenRouter plan for higher limits

### ❌ AI Responses are Generic/Off-Character

**Symptoms:**

- Responses don't include cat puns or "nya"
- Bot sounds too formal or corporate

**Solutions:**

1. **Check Personality Prompt**: Verify `lang/en.json` contains the correct personality
2. **Verify Prompt Building**: Check `build_prompt()` function in `ai_utils.py`
3. **Model Selection**: Some models may not follow personality instructions well
   ```python
   # Try switching to a different model
   /changemodel  # Use this command in Discord
   ```

## Command Issues

### ❌ Slash Commands Not Appearing

**Symptoms:**

- Commands don't show up in Discord's slash command menu
- Bot appears online but commands are missing

**Solutions:**

1. **Wait for Sync**: Command syncing can take up to 1 hour

   ```
   If syncing commands is taking longer than usual you are being ratelimited
   ```

2. **Check Bot Permissions**: Ensure bot has `applications.commands` scope

   - Re-invite bot with correct permissions if needed

3. **Manual Sync**: Force command sync (development only)

   ```python
   # Add to base.py for testing
   await self.tree.sync(guild=discord.Object(id=YOUR_GUILD_ID))
   ```

4. **Clear Command Cache**: Try using commands in a different server or DM

### ❌ "Missing Permissions" Error

**Symptoms:**

```
discord.errors.Forbidden: 403 Forbidden (error code: 50013): Missing Permissions
```

**Solutions:**

1. **Check Bot Role Permissions**:

   - Send Messages
   - Use Slash Commands
   - Embed Links
   - Read Message History

2. **Role Hierarchy**: Ensure bot role is high enough in server role list

3. **Channel Permissions**: Check channel-specific permission overrides

## Connection Issues

### ❌ Bot Frequently Disconnecting

**Symptoms:**

- Bot goes offline periodically
- "Connection closed" errors in console

**Solutions:**

1. **Check Network Stability**: Ensure stable internet connection
2. **Firewall Settings**: Allow Discord connections through firewall
3. **Enable Reconnection**: Bot should auto-reconnect (built into discord.py)

### ❌ "Cannot Connect to Discord" Error

**Symptoms:**

```
aiohttp.ClientConnectorError: Cannot connect to host discord.com
```

**Solutions:**

1. **Check Internet Connection**: Verify connectivity to Discord

   ```bash
   ping discord.com
   ```

2. **Proxy/VPN Issues**: If using proxy/VPN, ensure Discord isn't blocked

3. **DNS Issues**: Try using different DNS servers (8.8.8.8, 1.1.1.1)

## Performance Issues

### ❌ High Memory Usage

**Symptoms:**

- Bot uses excessive RAM
- System becomes slow over time

**Solutions:**

1. **Reduce History Length**: Lower `MAX_HISTORY_LENGTH` in `constants.py`

   ```python
   MAX_HISTORY_LENGTH = 5  # Reduce from default 7
   ```

2. **Monitor Memory**: Add memory monitoring

   ```python
   import psutil
   process = psutil.Process()
   print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB")
   ```

3. **Restart Periodically**: Set up automatic restarts for long-running deployments

### ❌ Slow Response Times

**Symptoms:**

- Long delays between user messages and bot responses
- Timeout errors

**Solutions:**

1. **Check AI API Latency**: Test different models for speed
2. **Optimize History Processing**: Reduce context sent to AI
3. **Server Location**: Use servers closer to AI API endpoints

## Configuration Issues

### ❌ "Language File Not Found"

**Symptoms:**

```
FileNotFoundError: Language file 'lang/en.json' does not exist.
```

**Solutions:**

1. **Verify File Exists**: Check that `lang/en.json` is present
2. **Check config.yml**: Ensure language setting matches existing file

   ```yaml
   LANGUAGE: en # Must match lang/en.json
   ```

3. **File Encoding**: Ensure JSON file is UTF-8 encoded

### ❌ "Lore Book Data Missing"

**Symptoms:**

```
ValueError: Lore book data is missing or empty in the language file.
```

**Solutions:**

1. **Check JSON Structure**: Verify `lang/en.json` has `lorebook` section
2. **Validate JSON**: Use JSON validator to check for syntax errors
3. **Restore from Backup**: Use git to restore original language file

## Development Issues

### ❌ Code Changes Not Taking Effect

**Solutions:**

1. **Restart Bot**: Stop and start the bot process
2. **Check File Paths**: Ensure editing correct files
3. **Import Caching**: Clear Python import cache
   ```bash
   # Remove __pycache__ directories
   find . -name "__pycache__" -type d -exec rm -rf {} +
   ```

### ❌ Cog Loading Errors

**Symptoms:**

```
discord.ext.commands.errors.ExtensionFailed: Extension 'cogs.commands.my_command' failed to load.
```

**Solutions:**

1. **Check Syntax**: Verify Python syntax in cog files
2. **Import Errors**: Ensure all imports are available
3. **Setup Function**: Verify `async def setup(bot):` function exists

## Logging and Debugging

### Enable Debug Logging

Add to `base.py` for more detailed logs:

```python
import logging

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Discord-specific debugging
discord.utils.setup_logging(level=logging.DEBUG)
```

### Check Log Files

Monitor log files for errors:

```bash
# Real-time log monitoring
tail -f logs/on_message.log

# Search for errors
grep -i error logs/on_message.log
```

### Console Output Analysis

Common console messages and their meanings:

**Normal Operation:**

```
Loaded Command change_model        # ✅ Commands loading correctly
Bot is ready to receive messages!  # ✅ Bot connected successfully
```

**Warning Signs:**

```
Failed to fetch the image.        # ⚠️ External API issues
No response from model            # ⚠️ AI API problems
High memory usage: 250.0MB       # ⚠️ Memory concerns
```

**Error Indicators:**

```
Error getting response from model  # ❌ AI API failure
Missing Permissions               # ❌ Discord permission issues
Connection lost                   # ❌ Network problems
```

## Emergency Recovery

### Quick Fixes

1. **Restart Bot**: Solves most temporary issues

   ```bash
   # Kill and restart
   pkill -f "python base.py"
   python base.py
   ```

2. **Reset Configuration**: Restore default settings

   ```bash
   git checkout -- constants.py config.yml
   ```

3. **Clear Cache**: Remove temporary files
   ```bash
   rm -rf __pycache__ logs/*.log
   ```

### Recovery Checklist

When bot is completely broken:

- [ ] Check `secrets.json` exists and is valid
- [ ] Verify all dependencies are installed
- [ ] Confirm Discord bot token is working
- [ ] Test OpenRouter API key separately
- [ ] Check file permissions
- [ ] Verify Python version compatibility
- [ ] Review recent code changes
- [ ] Check system resources (RAM, disk space)

### Getting Help

If issues persist:

1. **Check GitHub Issues**: Search for similar problems
2. **Create Issue**: Provide error logs and system information
3. **Discord Communities**: Ask in Discord.py or AI bot communities
4. **Stack Overflow**: Search for specific error messages

Include this information when asking for help:

- Operating system and Python version
- Complete error message and stack trace
- Steps to reproduce the problem
- Recent changes to code or configuration
- Log file contents (remove sensitive information)

Remember to never share your actual API keys or tokens when asking for help!
