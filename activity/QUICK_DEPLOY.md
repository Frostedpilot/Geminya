# 🚀 Quick Deploy Reference

## One-Page Production Deployment Guide

### Prerequisites
- Discord Application ID
- IDs.moe API key
- Cloudflare account (free)
- Vercel account (free)

---

## Step 1: Start Backend

```bash
cd activity/backend
venv\Scripts\activate
uvicorn main:app --port 8080 --host 0.0.0.0
```

Keep running ✅

---

## Step 2: Expose Backend

**New terminal:**
```bash
cloudflared tunnel --url http://localhost:8080
```

Copy the HTTPS URL shown (e.g., `https://abc-123.trycloudflare.com`)

Keep running ✅

---

## Step 3: Deploy Frontend

```bash
cd activity/frontend

# Set environment
echo VITE_DISCORD_CLIENT_ID=your_app_id_here > .env.production

# Deploy
vercel --prod
```

Copy the URL shown (e.g., `https://geminya-activity.vercel.app`)

---

## Step 4: Configure Discord

**Go to:** Discord Developer Portal → Your App → Activities → URL Mappings

**Add mappings:**

| Prefix | Target |
|--------|--------|
| `/.proxy/api` | Your backend URL from Step 2 |
| `/` | Your frontend URL from Step 3 |

**Example:**
```
/.proxy/api  →  https://abc-123.trycloudflare.com
/            →  https://geminya-activity.vercel.app
```

---

## Step 5: Test

1. Get test URL from Discord Portal
2. Paste in Discord
3. Click to open activity
4. Test all 5 games

---

## Troubleshooting

**Activity won't load?**
- Check both terminals are running
- Verify URL mappings are exact (no typos, no trailing slashes)
- Test backend URL in browser: `https://your-backend-url/health`

**Games not working?**
- Open DevTools in Discord (Ctrl+Shift+I)
- Check Network tab for failed API calls
- Check Console for errors

**Need to restart?**
- Backend: Ctrl+C in backend terminal, then `uvicorn main:app --port 8080 --host 0.0.0.0`
- Tunnel: Ctrl+C in tunnel terminal, then `cloudflared tunnel --url http://localhost:8080`
- Frontend: Just redeploy with `vercel --prod`

---

## Keep Running

**Two terminals must stay open:**
1. Backend: `uvicorn main:app...`
2. Tunnel: `cloudflared tunnel...`

**To keep running 24/7:**
- Use Windows scheduled task
- Or deploy backend to Railway/Heroku
- Or use `nssm` to run as Windows service

---

## URLs to Save

**Backend local:** http://localhost:8080  
**Backend public:** https://________________.trycloudflare.com  
**Frontend:** https://________________.vercel.app  
**Discord Activity:** https://discord.com/activities/YOUR_APP_ID/LAUNCH_ID

---

## Files Checklist

- [x] `secrets.json` - IDS_MOE_API_KEY
- [x] `activity/frontend/.env.production` - VITE_DISCORD_CLIENT_ID
- [x] Discord URL mappings configured
- [x] Both servers running

---

## Full Guide

See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) for complete instructions.
