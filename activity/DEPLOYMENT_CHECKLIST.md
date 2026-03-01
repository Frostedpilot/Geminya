# Discord Activity Production Deployment Checklist

Deploy Guess Opening/Ending and all games for PUBLIC USE.

## ☐ Discord Setup

- [ ] Application created at https://discord.com/developers/applications
- [ ] Application ID (Client ID) copied
- [ ] Activities enabled in app settings
- [ ] `@discord/embedded-app-sdk` installed in frontend (already done ✅)

## ☐ Backend Preparation

- [ ] IDs.moe API key obtained from https://ids.moe
- [ ] API key added to root `secrets.json`
- [ ] Python venv created and activated
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Backend starts successfully: `uvicorn main:app --port 8080 --host 0.0.0.0`
- [ ] Health check works: http://localhost:8080/health

## ☐ Backend Exposure (Choose One)

### Cloudflare Tunnel (Recommended)
- [ ] cloudflared installed
- [ ] Tunnel created: `cloudflared tunnel create geminya-backend`
- [ ] Config file created in `~/.cloudflared/config.yml`
- [ ] Tunnel running: `cloudflared tunnel run geminya-backend`
- [ ] Public URL obtained (e.g., `https://abc.trycloudflare.com`)
- [ ] Backend accessible via public URL

### OR ngrok
- [ ] ngrok installed
- [ ] Running: `ngrok http 8080`
- [ ] HTTPS URL obtained

### OR Cloud Hosting
- [ ] Deployed to Railway/Heroku/VPS
- [ ] Public HTTPS URL obtained

**Backend Public URL:** `https://________________.com`

## ☐ Frontend Deployment

### Build Configuration
- [ ] Node modules installed: `npm install`
- [ ] `.env` or `.env.production` created
- [ ] `VITE_DISCORD_CLIENT_ID` set to your Application ID
- [ ] Build works locally: `npm run build`

### Deployment (Choose One)

#### Vercel (Recommended)
- [ ] Vercel CLI installed: `npm i -g vercel`
- [ ] Deployed: `vercel --prod`
- [ ] Environment variable `VITE_DISCORD_CLIENT_ID` set in Vercel dashboard
- [ ] Build successful

#### OR Netlify
- [ ] Netlify CLI installed
- [ ] Built and deployed: `netlify deploy --prod --dir=dist`
- [ ] Environment variables set

#### OR Cloudflare Pages
- [ ] Repository connected
- [ ] Build command: `npm run build`
- [ ] Output directory: `dist`
- [ ] Environment variable set
- [ ] Build successful

**Frontend Public URL:** `https://________________.com`

## ☐ Discord URL Mappings

In Discord Developer Portal → Your App → Activities → URL Mappings:

- [ ] Mapping 1: `/.proxy/api` → `<your-backend-public-url>`
- [ ] Mapping 2: `/` → `<your-frontend-public-url>`
- [ ] Both URLs use HTTPS
- [ ] No trailing slashes
- [ ] Mappings saved

**Example:**
```
/.proxy/api  →  https://geminya-api.trycloudflare.com
/            →  https://geminya-activity.vercel.app
```

## ☐ Production Testing

### Get Activity URL
- [ ] Test URL copied from Discord Portal Activities → Test Mode
- [ ] Format: `https://discord.com/activities/<app_id>/<launch_id>`

### Test in Discord
- [ ] Discord desktop app opened
- [ ] Test URL pasted in server/DM
- [ ] Activity iframe opens
- [ ] DevTools opened (Ctrl+Shift+I)

### Verify Discord SDK
- [ ] No SDK errors in console
- [ ] User authentication works
- [ ] `window.discordUser` populated

### Test All Games
- [ ] **Anidle** - Starts, accepts guesses, autocomplete works
- [ ] **Guess Anime** - Screenshots load, guessing works
- [ ] **Guess Character** - Character image loads, dual input works
- [ ] **Guess Opening** - Audio plays, video reveal works, guessing works
- [ ] **Guess Ending** - Audio plays, video reveal works, guessing works

### Verify Backend Connection
- [ ] API calls visible in Network tab
- [ ] Calls go to `/.proxy/api/...` (not direct backend URL)
- [ ] Status 200 responses
- [ ] No CORS errors

## ☐ Multi-User Testing

- [ ] Invite friend to test
- [ ] Activity works for other users
- [ ] Multiple concurrent games work
- [ ] No conflicts between users

## ☐ Production Stability

### Backend
- [ ] Backend terminal running
- [ ] Tunnel terminal running
- [ ] Backend logs show no errors
- [ ] All external APIs working (Jikan, AnimeThemes, IDs.moe)

### Frontend
- [ ] Deployed frontend loads quickly
- [ ] No console errors
- [ ] Mobile responsive (test in Discord mobile if possible)

### Performance
- [ ] Games load within 3 seconds
- [ ] API responses under 2 seconds
- [ ] Media (images/audio/video) loads properly
- [ ] No memory leaks after extended play

## ☐ Monitoring Setup

### Backend Logs
Watch for:
- [ ] `✅ Loaded config`
- [ ] `✅ IDs.moe API configured`
- [ ] `✅ Selected 'Anime Name' (rank #XXX)`
- [ ] `✅ Found in AnimeThemes: ...`
- [ ] `🎲 Attempt X: Trying ...`
- [ ] No error stack traces

### Health Check
- [ ] Backend health endpoint accessible: `<backend-url>/health`
- [ ] Returns: `{"status": "healthy", "apis": {...}}`

### Rate Limits
- [ ] Jikan: 1 req/sec (1s delay configured)
- [ ] AnimeThemes: 2.5s delay configured
- [ ] No 429 errors in logs

## ☐ Documentation

- [ ] Backend URL documented
- [ ] Frontend URL documented
- [ ] Discord App ID documented
- [ ] Tunnel command saved
- [ ] Restart procedures documented

## ☐ Long-term Maintenance

### Auto-start (Optional)
- [ ] Backend auto-starts on system boot
- [ ] Tunnel auto-starts on system boot
- [ ] OR deployed to always-on hosting

### Backup Plans
- [ ] Alternative tunnel service (ngrok) available
- [ ] Frontend redeployment command saved
- [ ] Backend restart command saved

### Updates
- [ ] Git repository up to date
- [ ] Changes tested locally before deploying
- [ ] Rollback plan if issues occur

## ☐ Optional: Public Launch

### Activity Shelf
- [ ] Activity submitted to Discord
- [ ] Description and screenshots provided
- [ ] Activity reviewed and approved
- [ ] Live on Discord Activity Shelf

### Promotion
- [ ] Shared in Discord servers
- [ ] Social media posts
- [ ] Community feedback gathered

## ✅ Deployment Complete!

Your Geminya Activity is LIVE and accessible to all Discord users!

**Summary:**
- ✅ Backend running on: `_________________`
- ✅ Frontend deployed to: `_________________`
- ✅ Discord Activity URL: `_________________`
- ✅ All 5 games working
- ✅ Multi-user capable
- ✅ Production stable

**Next Steps:**
- Monitor backend logs for issues
- Gather user feedback
- Plan new features (leaderboards, stats, more games)
- Consider moving to dedicated hosting for stability

### Backend Configuration
- [ ] IDs.moe API key obtained from https://ids.moe
- [ ] API key added to root `secrets.json`:
  ```json
  {
    "IDS_MOE_API_KEY": "your_key_here"
  }
  ```
- [ ] Python virtual environment created (`python -m venv venv`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Backend tested: `http://localhost:8080/docs` loads successfully

### Frontend Configuration
- [ ] Node modules installed (`npm install`)
- [ ] `.env` file created from `.env.example`
- [ ] Discord Client ID added to `.env`:
  ```env
  VITE_DISCORD_CLIENT_ID=your_app_id_here
  ```
- [ ] Frontend tested: `http://localhost:5173` loads successfully

## ☐ Discord Activity Configuration

### URL Mappings (Development Mode)
In Discord Developer Portal → Your App → Activities → URL Mappings:

- [ ] Mapping 1:
  - Prefix: `/.proxy/api`
  - Target: `http://localhost:8080`
  
- [ ] Mapping 2:
  - Prefix: `/`
  - Target: `http://localhost:5173`

### Test Mode Setup
- [ ] Test link copied from Activities → Test Mode
- [ ] Test URL format: `https://discord.com/activities/<app_id>/<launch_id>`

## ☐ Server Startup

### Start Both Servers

**Option A: Using start script (Windows)**
```bash
cd activity
start_dev.bat
```

**Option B: Manual startup**

Terminal 1 - Backend:
```bash
cd activity/backend
venv\Scripts\activate  # Windows
# OR: source venv/bin/activate  # Linux/Mac
uvicorn main:app --reload --port 8080 --host 0.0.0.0
```

Terminal 2 - Frontend:
```bash
cd activity/frontend
npm run dev
```

### Verify Servers Running
- [ ] Backend: `http://localhost:8080` → Returns "Geminya Mini-Games API"
- [ ] Frontend: `http://localhost:5173` → Shows game selection screen
- [ ] API Docs: `http://localhost:8080/docs` → Shows Swagger UI
- [ ] Health Check: `http://localhost:8080/health` → Returns healthy status

## ☐ Discord Testing

### Open Activity in Discord
- [ ] Discord desktop app opened (recommended over web)
- [ ] Test URL pasted in any server/DM
- [ ] Activity iframe opened successfully
- [ ] DevTools opened (Ctrl+Shift+I) for debugging

### Test All Games
- [ ] **Anidle** - Starts and accepts guesses
- [ ] **Guess Anime** - Shows screenshots, accepts guesses
- [ ] **Guess Character** - Shows character, accepts dual input
- [ ] **Guess Opening** - Audio plays, video reveal works
- [ ] **Guess Ending** - Audio plays, video reveal works

### Specific Theme Game Tests
Guess Opening:
- [ ] Game starts with random anime opening
- [ ] Audio player loads and plays (Stage 1)
- [ ] "Show Video" button reveals full video (Stage 2)
- [ ] Anime search autocomplete works
- [ ] Correct guess shows success screen
- [ ] Wrong guess shows correct answer

Guess Ending:
- [ ] Game starts with random anime ending
- [ ] Audio player loads and plays (Stage 1)
- [ ] "Show Video" button reveals full video (Stage 2)
- [ ] Anime search autocomplete works
- [ ] Correct guess shows success screen
- [ ] Wrong guess shows correct answer

## ☐ Debug Common Issues

### "No themes found after 5 attempts"
Check backend logs for:
- [ ] `🎲 Attempt X: Trying <anime>` - Shows what's being tried
- [ ] `⚠️ MAL ID X: Not found in AnimeThemes` - Anime not in database
- [ ] API returning themes successfully

**Fix:** 
- Verify `theme_anime_selection` config in `config.yml`
- Popular anime (rank 1-2000) have better theme coverage
- Check AnimeThemes API is accessible: https://api.animethemes.moe/anime

### Video/Audio Not Playing
- [ ] Check browser console for CORS errors
- [ ] Verify video URL is accessible (check network tab)
- [ ] Try different anime (some videos may be unavailable)
- [ ] Check if AnimeThemes.moe is online

### Discord Activity Not Loading
- [ ] Both servers running (check terminals)
- [ ] URL mappings correct in Discord portal
- [ ] No CORS errors in browser console
- [ ] Refresh Discord (Ctrl+R)
- [ ] Try regenerating test link

### API Errors
- [ ] IDS_MOE_API_KEY set in `secrets.json`
- [ ] Backend logs show no errors
- [ ] Rate limits not exceeded (2.5s delay for AnimeThemes)
- [ ] External APIs (Jikan, AnimeThemes) are online

## ☐ Monitoring

### Backend Logs to Watch
```
✅ Loaded config from ...
✅ IDs.moe API configured
✅ Selected 'Anime Name' (rank #XXX)
✅ Found in AnimeThemes: Anime Name
🎲 Attempt X: Trying Anime Name
📊 Anime Name: X OPs, Y EDs
```

### Console Logs (Frontend)
- [ ] No CORS errors
- [ ] API responses successful (200 status)
- [ ] Discord SDK initialized properly
- [ ] Media elements loading

## ☐ Production Ready (Optional)

If deploying to production:

### Backend
- [ ] Environment variables configured
- [ ] CORS allowed origins updated
- [ ] Deployed to hosting (Railway/Heroku/VPS)
- [ ] Production URL obtained

### Frontend
- [ ] `npm run build` successful
- [ ] Deployed to hosting (Vercel/Netlify/Cloudflare)
- [ ] Production URL obtained

### Discord Portal
- [ ] URL mappings updated to production URLs
- [ ] Activity tested in production mode
- [ ] Application submitted for review (if public)

## ✅ Deployment Complete!

Your Guess Opening and Guess Ending games are now live on Discord Activities!

**Next steps:**
- Share with friends for testing
- Monitor backend logs for issues
- Gather feedback
- Consider adding leaderboards or stats
