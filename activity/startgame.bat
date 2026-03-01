@echo off
TITLE Geminya Server Controller
COLOR 0A

echo [1/2] Starting Backend API...
cd backend
:: Starts the Python server minimized
start /min "Geminya Backend" cmd /k "venv\Scripts\activate && uvicorn main:app --port 8080 --host 0.0.0.0"

echo [2/2] Starting Cloudflare Tunnel...
:: Starts the tunnel using the config.yml we just made
start /min "Cloudflare Tunnel" cmd /k "cloudflared tunnel run geminya"

echo.
echo ========================================================
echo   SERVER IS LIVE!
echo   Frontend: https://geminya-frontend.vercel.app
echo   Backend:  https://api.geminya.me
echo ========================================================
echo   Don't close this window, or the server stops.
echo.
pause