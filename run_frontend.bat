@echo off
title GitHub AI Assistant - Frontend (Port 5000)
echo ===================================================
echo   Launching GitHub AI Assistant Frontend on Port 5000
echo ===================================================

cd /d "%~dp0"

where npm >nul 2>nul
if %errorlevel% equ 0 (
    echo Node.js/npm detected. Checking Vite frontend...
    cd frontend
    if not exist node_modules (
        echo Installing dependencies...
        call npm install
    )
    echo Starting Vite frontend on http://localhost:5000 ...
    npm run dev
) else (
    echo Node.js not detected. Running high-performance frontend server via Python...
    echo Frontend will be accessible at: http://localhost:5000
    echo (Proxying all API calls to FastAPI backend at http://127.0.0.1:8000)
    python frontend_server.py
)
pause
