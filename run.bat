@echo off
title GitHub AI Assistant
echo ===================================================
echo     Launching GitHub AI Assistant (FastAPI + RAG)
echo ===================================================
cd /d "%~dp0backend"
echo Starting FastAPI server at http://127.0.0.1:8000 ...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
