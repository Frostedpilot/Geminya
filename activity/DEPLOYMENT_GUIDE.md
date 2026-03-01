# Discord Activity Deployment Guide

This guide covers deploying the Geminya Activity games (including Guess Opening/Ending) on Discord Activities for PUBLIC USE.

## Prerequisites

- Discord Developer Account
- Discord Application created
- Node.js 18+ and Python 3.9+
- Cloudflare account (for backend tunnel) OR other hosting solution
- Domain/subdomain (optional but recommended)

## Step 1: Discord Developer Portal Setup

### 1.1 Create/Configure Application

1. Go to https://discord.com/developers/applications
2. Select your existing "Geminya" application (or create new)
3. Note your **Application ID** (CLIENT_ID)

### 1.2 Enable Activities

1. In your application, go to **Activities** section in left sidebar
2. Click **Enable Activities**
3. Accept the terms

### 1.3 Configure OAuth2

1. Go to **OAuth2** section
2. Add redirect URL: `http://localhost:5173/.proxy`
3. In **URL Generator**, select scopes: `applications.commands`, `identify`

## Step 2: Backend Setup

### 2.1 Install Dependencies

```bash
cd activity/backend
python -m venv venv

# Windows
venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2.2 Configure Secrets

Backend uses the root-level `secrets.json` for API keys:

```json
{
  "IDS_MOE_API_KEY": "your_ids_moe_api_key_here"
}
```

Get your IDs.moe API key from: https://ids.moe

### 2.3 Start Backend Server

```bash
# From activity/backend
uvicorn main:app --reload --port 8080 --host 0.0.0.0
```

Backend will be available at: `http://localhost:8080`

**Test it locally:** Open http://localhost:8080/docs to see the API documentation.

## Step 4: Expose Backend Publicly

Since you're running the backend on your local device, you need to expose it so Discord and other users can access it.

### Option A: Cloudflare Tunnel (Recommended - Free & Easy)

**Install cloudflared:**
```bash
# Windows (with winget)
winget install --id Cloudflare.cloudflared

# Or download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
```

**Create tunnel:**
```bash
# Login to Cloudflare
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create geminya-backend

# Note the tunnel ID that's displayed
```

**Configure tunnel:**

Create `config.yml` in `C:\Users\<YourUser>\.cloudflared\` (Windows) or `~/.cloudflared/` (Linux/Mac):

```yaml
url: http://localhost:8080
tunnel: <your-tunnel-id>
credentials-file: C:\Users\<YourUser>\.cloudflared\<tunnel-id>.json
```

**Run tunnel:**
```bash
cloudflared tunnel run geminya-backend
```

**Get public URL:**
```bash
cloudflared tunnel route dns geminya-backend <subdomain>.yourdomain.com
# Or use the auto-generated trycloudflare.com URL for testing
```

Your backend will be accessible at: `https://<subdomain>.yourdomain.com` or `https://<random>.trycloudflare.com`

### Option B: ngrok (Alternative)

```bash
# Install ngrok: https://ngrok.com/download

# Run ngrok
ngrok http 8080

# Note the HTTPS URL provided (e.g., https://abc123.ngrok.io)
```

### Option C: Hosting Service

Deploy to a proper hosting service:
- **Railway.app** - Easy Python deployment
- **Heroku** - Classic PaaS
- **DigitalOcean/AWS/Azure** - VPS with more control

For this guide, we'll assume you're using **Cloudflare Tunnel**.

**Important:** Keep the tunnel running! Your backend must be accessible for the activity to work.

## Step 5: Build and Deploy Frontend

### 3.1 Install Dependencies

```bash
cd activity/frontend
npm install
```

### 3.2 Configure Environment

Create `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and add your Discord Application ID:

```env
VITE_DISCORD_CLIENT_ID=your_application_id_here
```

### 3.3 Start Frontend Dev Server

```bash
# From activity/frontend
npm run dev
```

Frontend will be available at: `http://localhost:5173`

## Step 4: Discord Activity URL Mappings (Development Mode)

### 4.1 Configure URL Mappings

In Discord Developer Portal → Your Application → Activities:

**Add URL Mappings:**

| Prefix | Target |
|--------|--------|
| `/.proxy/api` | `http://localhost:8080` |
| `/` | `http://localhost:5173` |

These mappings tell Discord where to proxy requests in the Activity iframe.

### 4.2 Understanding the Proxy

- Frontend makes requests to `/api/...`
- Discord's iframe proxies to `/.proxy/api/...`
- Which maps to your local backend at `http://localhost:8080`

## Step 5: Test the Activity

### 5.1 Get Test URL

In Discord Developer Portal → Activities → **Test Mode**:

1. Click **Copy Link**
2. This gives you a special test URL like:
   ```
   https://discord.com/activities/<app_id>/<launch_id>
   ```

### 5.2 Open in Discord

1. **Desktop Discord (recommended)**: Open Discord app
2. Paste the test URL in any server channel
3. Click the activity link
4. Activity opens in an iframe

### 5.3 Testing Flow

The activity should:
1. ✅ Load the game selection screen
2. ✅ Show all 5 games (Anidle, Guess Anime, Guess Character, Guess OP, Guess ED)
3. ✅ Let you start any game
4. ✅ Connect to backend APIs successfully

**Debug console:** Press `Ctrl+Shift+I` in Discord to open DevTools

## Step 6: Verify New Games

### Test Guess Opening

1. Click "Guess OP" card
2. Select difficulty
3. Start game
4. Should see: Audio player with opening theme
5. Test "Show Video" hint button
6. Test guessing anime name

### Test Guess Ending

1. Click "Guess ED" card
2. Same flow as Guess Opening but with ending themes

### Common Issues

**"No themes found after 5 attempts"**
- Backend is trying popular anime but AnimeThemes.moe may not have themes
- Check backend console logs to see which anime were tried
- The `theme_anime_selection` config favors popular anime (rank 1-3000)

**API errors:**
- Check backend logs: `activity/backend/` terminal
- Verify IDs.moe API key is set
- Rate limiting: AnimeThemes has 2.5s delay between requests

**Discord "Activity not responding"**
- Verify both servers are running (frontend :5173, backend :8080)
- Check URL mappings are correct
- Try refreshing Discord (Ctrl+R)

## Step 7: Production Deployment (Optional)

For production deployment outside of local development:

### Backend Options

**Option A: Railway**
```bash
# Install Railway CLI
npm i -g @railway/cli

# From activity/backend
railway login
railway init
railway up
```

**Option B: Heroku**
```bash
# From activity/backend
heroku create geminya-activity-backend
git push heroku main
```

**Option C: VPS (DigitalOcean, AWS, etc.)**
- Use systemd service
- Nginx reverse proxy
- Let's Encrypt SSL

### Frontend Deployment

```bash
cd activity/frontend
npm run build

# Deploy dist/ folder to:
# - Vercel: vercel deploy
# - Netlify: netlify deploy
# - Cloudflare Pages
```

### Update Discord Mappings

Change from localhost to production URLs:

| Prefix | Target |
|--------|--------|
| `/.proxy/api` | `https://your-backend.com` |
| `/` | `https://your-frontend.com` |

## Architecture Overview

```
Discord Client
    ↓
Activity Iframe (https://discord.com/activities/...)
    ↓
Frontend (localhost:5173 or production)
    ↓
API calls (proxied through /.proxy/api)
    ↓
Backend (localhost:8080 or production)
    ↓
External APIs (Jikan, Shikimori, AnimeThemes, IDs.moe)
```

## Files Checklist

Before deploying, ensure these are configured:

- [ ] `secrets.json` - IDS_MOE_API_KEY set
- [ ] `activity/frontend/.env` - VITE_DISCORD_CLIENT_ID set
- [ ] Discord Developer Portal - Activities enabled
- [ ] Discord Developer Portal - URL mappings configured
- [ ] Backend running on port 8080
- [ ] Frontend running on port 5173

## Monitoring

**Backend Health Check:**
```bash
curl http://localhost:8080/health
```

Should return:
```json
{
  "status": "healthy",
  "apis": {
    "jikan": "configured",
    "shikimori": "configured",
    "ids_moe": "configured"
  }
}
```

**Backend Logs:**
Watch for:
- `✅ Selected 'Anime Name'` - Random anime selection working
- `✅ Found in AnimeThemes: ...` - Theme data found
- `🎲 Attempt X: Trying ...` - Game initialization attempts

## Support

If you encounter issues:

1. Check both server logs (backend terminal + frontend terminal)
2. Open Discord DevTools (Ctrl+Shift+I)
3. Verify URL mappings in Discord Developer Portal
4. Test APIs individually via `/docs` endpoint

## Next Steps

- Add more games to the activity
- Implement Redis for persistent game state
- Add leaderboards
- Deploy to production with proper hosting
