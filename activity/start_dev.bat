@echo off
REM Quick start script for Geminya Activity (Windows)

echo.
echo ========================================
echo   Geminya Activity - Development Mode
echo ========================================
echo.

REM Check if backend venv exists
if not exist "backend\venv\" (
    echo [ERROR] Backend virtual environment not found!
    echo Please run: cd activity\backend
    echo              python -m venv venv
    echo              venv\Scripts\activate
    echo              pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check if frontend node_modules exists
if not exist "frontend\node_modules\" (
    echo [ERROR] Frontend node_modules not found!
    echo Please run: cd activity\frontend
    echo              npm install
    pause
    exit /b 1
)

REM Check if .env exists
if not exist "frontend\.env" (
    echo [WARNING] Frontend .env not found!
    echo Please run: cd activity\frontend
    echo              copy .env.example .env
    echo Then edit .env and add your Discord Client ID
    pause
    exit /b 1
)

echo [OK] All dependencies found!
echo.
echo Starting servers...
echo   Backend:  http://localhost:8080
echo   Frontend: http://localhost:5173
echo   API Docs: http://localhost:8080/docs
echo.
echo Keep this window open. Press Ctrl+C to stop servers.
echo.

REM Start backend in new window
start "Geminya Backend" cmd /k "cd backend && venv\Scripts\activate && uvicorn main:app --reload --port 8080 --host 0.0.0.0"

REM Wait a moment for backend to start
timeout /t 2 /nobreak > nul

REM Start frontend in new window
start "Geminya Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo [OK] Servers started in separate windows
echo      Close those windows to stop the servers
echo.
pause
