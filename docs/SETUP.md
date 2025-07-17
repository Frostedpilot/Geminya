# Installation & Setup Guide

## Prerequisites

Before installing Geminya, ensure you have the following:

- **Python 3.12+** (recommended)
- **Git** for cloning the repository
- **Discord Bot Token** from Discord Developer Portal
- **OpenRouter API Key** for AI model access

## Step 1: Discord Bot Setup

### Create Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name (e.g., "Geminya")
3. Go to the "Bot" section in the left sidebar
4. Click "Add Bot" or "Create Bot"
5. Copy the bot token (you'll need this later)

### Set Bot Permissions

In the "OAuth2" > "URL Generator" section:

**Scopes:**

- ✅ `bot`
- ✅ `applications.commands`

**Bot Permissions:**

- ✅ `Send Messages`
- ✅ `Use Slash Commands`
- ✅ `Read Message History`
- ✅ `Embed Links`
- ✅ `Attach Files`
- ✅ `Use External Emojis`
- ✅ `Add Reactions`

Copy the generated URL and use it to invite the bot to your server.

## Step 2: OpenRouter API Setup

1. Visit [OpenRouter](https://openrouter.ai/)
2. Create an account or sign in
3. Go to your API keys section
4. Generate a new API key
5. Copy the key (you'll need this for configuration)

## Step 3: Project Installation

### Clone Repository

```bash
git clone <repository-url>
cd Geminya
```

### Install Python Dependencies

Using pip:

```bash
pip install discord.py openai aiohttp pyyaml
```

Or if you have a requirements.txt:

```bash
pip install -r requirements.txt
```

### Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv geminya-env

# Activate virtual environment
# Windows:
geminya-env\Scripts\activate
# macOS/Linux:
source geminya-env/bin/activate

# Install dependencies
pip install discord.py openai aiohttp pyyaml
```

## Step 4: Configuration

### Create Secrets File

Create `secrets.json` in the project root:

```json
{
  "DISCORD_BOT_TOKEN": "your_discord_bot_token_here",
  "OPENROUTER_API_KEY": "your_openrouter_api_key_here"
}
```

⚠️ **Important**: Never commit `secrets.json` to version control. Add it to `.gitignore`.

### Configure Bot Settings

Edit `constants.py` to customize bot behavior:

```python
# Default AI model for new servers
DEFAULT_MODEL = "deepseek/deepseek-chat-v3-0324:free"

# Maximum conversation history length
MAX_HISTORY_LENGTH = 7

# Add your server IDs if you want to restrict the bot
ACTIVE_SERVERS = ("your_server_id_here",)

# Available AI models for users to choose from
AVAILABLE_MODELS = {
    "DeepSeek V3 0324": "deepseek/deepseek-chat-v3-0324:free",
    "Kimi K2": "moonshotai/kimi-k2:free",
    "DeepSeek Chimera": "tngtech/deepseek-r1t2-chimera:free",
    "DeepSeek R1 0528": "deepseek/deepseek-r1-0528:free",
}
```

### Language Configuration

Edit `config.yml` if needed:

```yaml
LANGUAGE: en # Currently only English is supported
```

## Step 5: Running the Bot

### First Run

```bash
python base.py
```

You should see output like:

```
Loaded Command change_model
Loaded Command help
Loaded Command nekogif
Loaded Event Handler on_command_error
Loaded Event Handler on_message
Loaded Event Handler on_ready
If syncing commands is taking longer than usual you are being ratelimited
Loaded 3 commands
Geminya#1234 aka Geminya has connected to Discord!
Bot is ready to receive messages!
```

### Background Running

For production deployment, consider using process managers:

**Using screen:**

```bash
screen -S geminya
python base.py
# Press Ctrl+A, then D to detach
```

**Using nohup:**

```bash
nohup python base.py > bot.log 2>&1 &
```

**Using systemd (Linux):**
Create `/etc/systemd/system/geminya.service`:

```ini
[Unit]
Description=Geminya Discord Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/Geminya
ExecStart=/path/to/python base.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable geminya
sudo systemctl start geminya
```

## Step 6: Verification

### Test Bot Functionality

1. **Basic Response**: Mention the bot in a channel: `@Geminya hello!`
2. **Slash Commands**: Try `/help` to see available commands
3. **Model Switching**: Use `/changemodel` to test the model selection interface
4. **Fun Commands**: Try `/nekogif` for a random neko gif

### Check Logs

Monitor the console output or log files for any errors:

- Console output for general bot activity
- `logs/on_message.log` for message processing details

## Troubleshooting

### Common Issues

**"Invalid Bot Token" Error:**

- Verify the token in `secrets.json` is correct
- Ensure no extra spaces or characters in the token
- Check that the bot wasn't regenerated in Discord Developer Portal

**"Missing Permissions" Error:**

- Verify bot has necessary permissions in Discord server
- Check that bot role is high enough in the role hierarchy
- Ensure bot was invited with correct permission scopes

**"API Key Error" for OpenRouter:**

- Verify OpenRouter API key in `secrets.json`
- Check your OpenRouter account credits/limits
- Ensure key hasn't expired

**Commands Not Appearing:**

- Wait a few minutes for Discord to sync slash commands
- Try the slash commands in a different server
- Check console for rate limiting messages

**Bot Not Responding:**

- Verify bot is online in Discord
- Check that `ACTIVE_SERVERS` includes your server ID (or remove this restriction)
- Ensure message content intent is enabled if using Discord.py 2.0+

### Debug Mode

Enable debug logging by modifying `base.py`:

```python
import logging

# Add after imports
logging.basicConfig(level=logging.DEBUG)

# Or for Discord.py specific debugging
discord.utils.setup_logging(level=logging.DEBUG)
```

### Network Issues

If you're behind a firewall or proxy:

- Ensure Discord's IPs are whitelisted
- Check that ports 443 and 80 are accessible
- Consider using a VPN if corporate firewalls block Discord

## Optional Enhancements

### Auto-restart on Crash

Create a simple restart script `run.sh`:

```bash
#!/bin/bash
while true; do
    python base.py
    echo "Bot crashed. Restarting in 5 seconds..."
    sleep 5
done
```

### Log Rotation

For long-term deployment, set up log rotation:

```bash
# Add to crontab (crontab -e)
0 0 * * * /usr/sbin/logrotate /path/to/logrotate.conf
```

Logrotate config (`logrotate.conf`):

```
/path/to/Geminya/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### Monitoring

Consider setting up monitoring with tools like:

- **Uptime Kuma** for service monitoring
- **Grafana + Prometheus** for metrics
- **Discord webhooks** for crash notifications

## Next Steps

Once your bot is running successfully:

1. **Customize Personality**: Edit `lang/en.json` to modify Geminya's responses
2. **Add Commands**: Create new cogs in `cogs/commands/`
3. **Extend Events**: Add new event handlers in `cogs/events/`
4. **Configure Lore Book**: Add custom trigger responses in the language file
5. **Set Up Monitoring**: Implement health checks and restart mechanisms

## Security Notes

- Keep `secrets.json` secure and never commit it to version control
- Regularly rotate your API keys
- Monitor bot usage and API costs
- Use proper file permissions on configuration files
- Consider using environment variables instead of files for sensitive data

For additional help, check the [Troubleshooting Guide](TROUBLESHOOTING.md) or consult the [API Documentation](API.md).
