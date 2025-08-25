# Spotify Integration Setup Guide

This guide explains how to set up and use the Spotify integration in Geminya bot using librespot-python for direct streaming.

## ⚠️ Important Disclaimers

### Legal and ToS Considerations

- **This integration uses librespot-python, which is NOT officially approved by Spotify**
- **Using this may violate Spotify's Terms of Service**
- **There is a risk of your Spotify account being banned**
- **Use at your own risk**
- **Only works with Spotify Premium accounts**

### Technical Limitations

- librespot-python is in alpha and may have bugs
- Audio quality may vary
- Some tracks may not be available
- No official support from Spotify

## 🛠️ Setup Instructions

### 1. Spotify Application Setup

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account
3. Click "Create App"
4. Fill in the details:
   - **App Name**: Geminya Music Bot (or any name)
   - **App Description**: Discord bot for music playback
   - **Website**: Your website (can be placeholder)
   - **Redirect URI**: `http://localhost:8080/callback` (not used but required)
5. Check the boxes for Terms of Service
6. Click "Save"
7. Note down your **Client ID** and **Client Secret**

### 2. Configuration

Add the following credentials to your `secrets.json` file:

```json
{
  "SPOTIFY_USERNAME": "your_spotify_username",
  "SPOTIFY_PASSWORD": "your_spotify_password",
  "SPOTIFY_CLIENT_ID": "your_spotify_client_id",
  "SPOTIFY_CLIENT_SECRET": "your_spotify_client_secret"
}
```

**Important Notes:**

- Use your actual Spotify username and password
- **DO NOT use Facebook login** - librespot doesn't support it
- Must be a **Spotify Premium account**
- Keep your credentials secure and never commit them to version control

### 3. Bot Permissions

Ensure your Discord bot has the following permissions:

- `Connect` - To join voice channels
- `Speak` - To play audio
- `Use Voice Activity` - For voice functionality
- `Send Messages` - To respond to commands
- `Use Slash Commands` - For slash command support

## 🎵 Usage Commands

### Basic Commands

- `/spotify_join` - Make the bot join your voice channel for Spotify playback
- `/spotify_leave` - Make the bot leave the voice channel and stop Spotify playback
- `/spotify_search <query>` - Search for tracks and select from results
- `/spotify_play <query>` - Search and play the first result immediately
- `/spotify_playlist <query>` - Search and queue an entire Spotify playlist

### Playback Controls

- `/spotify_pause` - Pause the current track
- `/spotify_resume` - Resume paused playback
- `/spotify_skip` - Skip the current track
- `/spotify_stop` - Stop playback and clear the queue
- `/spotify_volume <0-100>` - Set playback volume

### Queue Management

- `/spotify_queue` - Show the current music queue
- `/spotify_now` - Show currently playing track information

## 🎯 How It Works

### Architecture Overview

```
Discord User → Bot Commands → Spotify Search → librespot Stream → Discord Voice
```

1. **Search Phase**: Bot uses Spotify Web API (spotipy) to search for tracks
2. **Selection Phase**: User selects from search results via Discord buttons
3. **Streaming Phase**: Bot uses librespot-python to create audio stream
4. **Playback Phase**: Bot plays audio through Discord voice connection

### Technical Details

- **Search**: Uses official Spotify Web API for metadata
- **Streaming**: Uses librespot-python for direct audio streaming
- **Queue**: Bot manages its own queue system
- **Voice**: Uses Discord.py voice functionality with PyNaCl

## 🔧 Troubleshooting

### Common Issues

#### "Spotify services not available"

- Check that all 4 Spotify credentials are in `secrets.json`
- Verify credentials are correct
- Ensure you have Spotify Premium

#### "Failed to create librespot session"

- Check username/password are correct
- Ensure you're not using Facebook login
- Try restarting the bot
- Check if Spotify account is active

#### "No audio in voice channel"

- Ensure bot has proper voice permissions
- Check that you're in the same voice channel
- Verify volume is not at 0
- Try rejoining the voice channel

#### "Failed to create audio source"

- Track may not be available in your region
- Track may be premium-only content
- librespot session may have expired - restart bot

### Audio Quality Issues

The bot supports different quality levels:

- **NORMAL**: 96 kbps
- **HIGH**: 160 kbps (default)
- **VERY_HIGH**: 320 kbps

Quality is set in the SpotifyService initialization and affects bandwidth usage.

### Rate Limiting

- Spotify Web API has rate limits for searches
- librespot may have connection limits
- If you encounter issues, wait a few minutes before retrying

## 🚀 Features

### Currently Supported

- ✅ Track search and playback
- ✅ Playlist search and queueing
- ✅ Queue management
- ✅ Basic playback controls (play, pause, skip, stop)
- ✅ Volume control
- ✅ Auto-disconnect when queue is empty
- ✅ Multiple guild support

### Planned Features

- 🔄 Loop modes (track, queue)
- 🔀 Shuffle mode
- ⏭️ Seek functionality
- 📊 Advanced queue management
- 🎚️ Audio filters and effects

## 🛡️ Security Considerations

### Protecting Your Credentials

- Never commit `secrets.json` to version control
- Use environment variables in production
- Rotate credentials periodically
- Monitor your Spotify account for unusual activity

### Account Safety

- Use a separate Spotify account if possible
- Monitor for any ToS violation warnings
- Keep backups of your playlists
- Be prepared for potential account suspension

## 🆘 Support

If you encounter issues:

1. Check the bot logs for error messages
2. Verify all credentials are correct
3. Ensure you have Spotify Premium
4. Try restarting the bot
5. Check Discord permissions

For technical issues with librespot-python, refer to:

- [librespot-python GitHub](https://github.com/kokarare1212/librespot-python)
- [librespot documentation](https://librespot-python.readthedocs.io/)

## ⚖️ Legal Notice

This integration is provided for educational purposes only. Users are responsible for ensuring compliance with Spotify's Terms of Service and applicable laws. The developers of this bot are not responsible for any account suspensions or legal issues arising from the use of this integration.

Use this feature responsibly and at your own risk.
