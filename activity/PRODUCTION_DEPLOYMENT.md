# Discord Activity Production Deployment Guide

Deploy Geminya Activity games (Anidle, Guess Anime, Guess Character, Guess Opening, Guess Ending) for PUBLIC USE on Discord Activities.

## Architecture Overview

```
Discord Users
    ↓
Discord Activity (iframe)
    ↓
Frontend (Vercel/Cloudflare Pages)
    ↓ API calls via /.proxy/api
Discord Proxy
    ↓
Backend (Your device via Cloudflare Tunnel)
    ↓
External APIs (Jikan, Shikimori, AnimeThemes, IDs.moe)
```

## Prerequisites

- ✅ Discord Application created
- ✅ Node.js 18+ and Python 3.9+ installed
- ✅ Cloudflare account (free)
- ✅ Vercel/Netlify account (free) OR Cloudflare Pages
- ✅ Git/GitHub account

---

## Part 1: Backend Setup & Exposure

### Step 1: Configure Backend

```bash
cd activity/backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Add API Keys

Edit root `secrets.json`:
```json
{
  "IDS_MOE_API_KEY": "your_key_from_https://ids.moe"
}
```

### Step 3: Start Backend

```bash
# From activity/backend (with venv activated)
uvicorn main:app --reload --port 8080 --host 0.0.0.0
```

Test locally: http://localhost:8080/docs

### Step 4: Expose Backend with Cloudflare Tunnel

**Install cloudflared:**
```bash
# Windows
winget install Cloudflare.cloudflared

# Linux/Mac
brew install cloudflared
```

**Quick expose (no account needed):**
```bash
cloudflared tunnel --url http://localhost:8080
```

This gives you a temporary URL like: `https://random-words-123.trycloudflare.com`

**Permanent tunnel (recommended for production):**

```bash
# Login
cloudflared tunnel login

# Create named tunnel
cloudflared tunnel create geminya-backend

# Note the tunnel ID
# Create config file at ~/.cloudflared/config.yml
```

Config file (`~/.cloudflared/config.yml` or `C:\Users\<You>\.cloudflared\config.yml`):
```yaml
url: http://localhost:8080
tunnel: <your-tunnel-id>
credentials-file: /path/to/.cloudflared/<tunnel-id>.json
```

**Start tunnel:**
```bash
cloudflared tunnel run geminya-backend
```

**Get your backend URL:**
- Quick method: Uses `trycloudflare.com` domain (shown in terminal)
- Permanent: Route to your domain: `cloudflared tunnel route dns geminya-backend api.yourdomain.com`

**Example backend URL:** `https://geminya-api.trycloudflare.com`

✅ **Keep this terminal running!** Your backend must stay online.

---

## Part 2: Frontend Deployment

### Step 5: Prepare Frontend

```bash
cd activity/frontend
npm install
```

### Step 6: Configure Environment

Create `.env.production`:
```env
VITE_DISCORD_CLIENT_ID=<your_discord_app_id>
VITE_API_URL=/.proxy/api
```

Get your Discord Application ID from: https://discord.com/developers/applications

### Step 7: Deploy Frontend

**Option A: Vercel (Recommended)**

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd activity/frontend
vercel --prod
```

Follow prompts:
- Project name: `geminya-activity`
- Framework: `Vite`
- Environment variables: Add `VITE_DISCORD_CLIENT_ID=your_app_id`

**You'll get a URL like:** `https://geminya-activity.vercel.app`

**Option B: Netlify**

```bash
npm i -g netlify-cli
cd activity/frontend
npm run build
netlify deploy --prod --dir=dist
```

**Option C: Cloudflare Pages**

1. Push to GitHub
2. Go to Cloudflare Pages
3. Connect repo
4. Build settings:
   - Build command: `npm run build`
   - Output: `dist`
   - Environment: `VITE_DISCORD_CLIENT_ID=your_app_id`

**Frontend URL example:** `https://geminya-activity.vercel.app`

---

## Part 3: Discord Activity Configuration

### Step 8: Configure URL Mappings

Go to: **Discord Developer Portal** → Your App → **Activities** → **URL Mappings**

Add these mappings:

| Prefix | Target |
|--------|--------|
| `/.proxy/api` | `https://your-cloudflare-tunnel-url.com` |
| `/` | `https://your-frontend-url.vercel.app` |

**Example:**
```
/.proxy/api  →  https://geminya-api.trycloudflare.com
/            →  https://geminya-activity.vercel.app
```

⚠️ **Important:**
- Use HTTPS only
- No trailing slashes
- Exact URLs, no paths

### Step 9: Enable Activity

In Discord Developer Portal → Activities:

1. ✅ Activities enabled
2. ✅ URL mappings configured
3. ✅ Test mode link copied

---

## Part 4: Testing & Launch

### Step 10: Test Activity

**Get test URL from Discord Portal:**
```
https://discord.com/activities/<your_app_id>/<launch_id>
```

**Test in Discord:**
1. Open Discord desktop app
2. Paste test URL in any server/DM
3. Click the activity
4. Should open in iframe

**Test all games:**
- 🎯 Anidle
- 📸 Guess Anime
- 🎭 Guess Character
- 🎵 Guess Opening ← NEW!
- 🎶 Guess Ending ← NEW!

### Step 11: Debugging

**Open DevTools in Discord:** `Ctrl+Shift+I`

**Check:**
- ✅ Frontend loads
- ✅ API calls go to `/.proxy/api/...`
- ✅ Backend responds (check Network tab)
- ✅ No CORS errors
- ✅ Discord SDK initialized

**Common issues:**

**"Activity not responding"**
- Check both backend and tunnel are running
- Verify URL mappings are exact
- Test backend URL in browser: `https://your-tunnel-url.com/health`

**"No themes found"**
- Check backend logs
- Verify AnimeThemes API is accessible
- Config uses `theme_anime_selection` (rank 1-3000)

**CORS errors**
- Backend already has CORS enabled for all origins
- Make sure requests go through `/.proxy/api` not direct

---

## Part 5: Production Checklist

### Before Going Live

- [ ] Backend tunnel is permanent (not quick temp URL)
- [ ] Frontend deployed to production (not dev mode)
- [ ] Environment variables set correctly
- [ ] Discord URL mappings point to production URLs
- [ ] All 5 games tested and working
- [ ] Backend logs show no errors
- [ ] Test with multiple users

### Keeping Backend Online

**Option 1: Run as Windows Service**
Use `nssm` or create a scheduled task to auto-start backend + tunnel

**Option 2: Docker**
Containerize backend for easier management

**Option 3: Cloud Hosting**
Deploy backend to Railway/Heroku instead of local hosting

---

## Discord Embedded App SDK

Your frontend already uses `@discord/embedded-app-sdk`! Check [discord.ts](frontend/src/discord.ts):

```typescript
import { DiscordSDK } from '@discord/embedded-app-sdk'

const CLIENT_ID = import.meta.env.VITE_DISCORD_CLIENT_ID

// SDK initialization
discordSdk = new DiscordSDK(CLIENT_ID)
await discordSdk.ready()

// OAuth authentication
const { code } = await discordSdk.commands.authorize({
    client_id: CLIENT_ID,
    response_type: 'code',
    scope: ['identify']
})
```

The SDK handles:
- ✅ Discord iframe integration
- ✅ User authentication
- ✅ Activity lifecycle

---

## URLs Quick Reference

**Your Setup:**
```
Discord App ID:    <from Discord portal>
Backend (local):   http://localhost:8080
Backend (public):  https://<tunnel>.trycloudflare.com
Frontend (public): https://<app>.vercel.app
Activity URL:      https://discord.com/activities/<app_id>/<launch_id>
```

**Discord URL Mappings:**
```
/.proxy/api → Backend public URL
/           → Frontend public URL
```

---

## Commands Summary

**Start backend:**
```bash
cd activity/backend
venv\Scripts\activate
uvicorn main:app --port 8080 --host 0.0.0.0
```

**Expose backend:**
```bash
# New terminal
cloudflared tunnel --url http://localhost:8080
# OR for permanent:
cloudflared tunnel run geminya-backend
```

**Deploy frontend:**
```bash
cd activity/frontend
npm run build
vercel --prod
```

---

## Need Help?

**Check backend health:**
```bash
curl https://your-backend-url.com/health
```

**Check backend logs:**
Look for:
- `✅ Loaded config`
- `✅ IDs.moe API configured`
- `✅ Selected 'Anime Name'`
- `✅ Found in AnimeThemes: ...`

**Check Discord DevTools:**
- Console tab for errors
- Network tab for API calls
- Make sure `/.proxy/api` calls work

---

## 🎉 You're Live!

Once everything is configured:
1. Backend running with Cloudflare tunnel
2. Frontend deployed to Vercel
3. Discord URL mappings set
4. Activity tested successfully

**Users can now play your games in Discord!**

Share the activity URL with friends or publish to Discord Activity Shelf.
