#!/usr/bin/env python3
"""Quick start script for Geminya Activity development."""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start both backend and frontend servers."""
    
    # Get activity root directory
    activity_root = Path(__file__).parent
    backend_dir = activity_root / "backend"
    frontend_dir = activity_root / "frontend"
    
    print("🚀 Starting Geminya Activity Servers...\n")
    
    # Check if virtual environment exists
    venv_dir = backend_dir / "venv"
    if not venv_dir.exists():
        print("❌ Backend virtual environment not found!")
        print("   Run: cd activity/backend && python -m venv venv && pip install -r requirements.txt")
        return 1
    
    # Check if node_modules exists
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("❌ Frontend node_modules not found!")
        print("   Run: cd activity/frontend && npm install")
        return 1
    
    # Check if .env exists
    env_file = frontend_dir / ".env"
    if not env_file.exists():
        print("⚠️  Frontend .env not found!")
        print("   Run: cd activity/frontend && cp .env.example .env")
        print("   Then edit .env and add your Discord Client ID")
        return 1
    
    # Determine Python/venv command based on OS
    if sys.platform == "win32":
        python_exe = venv_dir / "Scripts" / "python.exe"
        uvicorn_exe = venv_dir / "Scripts" / "uvicorn.exe"
    else:
        python_exe = venv_dir / "bin" / "python"
        uvicorn_exe = venv_dir / "bin" / "uvicorn"
    
    print("✅ All dependencies found!\n")
    print("📡 Starting Backend Server (port 8080)...")
    print("📱 Starting Frontend Server (port 5173)...\n")
    print("=" * 60)
    print("Backend:  http://localhost:8080")
    print("Frontend: http://localhost:5173")
    print("API Docs: http://localhost:8080/docs")
    print("=" * 60)
    print("\n⚠️  Keep this terminal open - both servers running")
    print("   Press Ctrl+C to stop both servers\n")
    
    try:
        # Start backend
        backend_process = subprocess.Popen(
            [str(uvicorn_exe), "main:app", "--reload", "--port", "8080", "--host", "0.0.0.0"],
            cwd=backend_dir
        )
        
        # Start frontend
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            shell=True if sys.platform == "win32" else False
        )
        
        # Wait for both processes
        backend_process.wait()
        frontend_process.wait()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down servers...")
        backend_process.terminate()
        frontend_process.terminate()
        backend_process.wait()
        frontend_process.wait()
        print("✅ Servers stopped")
        return 0
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
