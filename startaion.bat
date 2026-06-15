@echo off
title AION Launcher
echo.
echo  ========================================
echo   AION - AI Agent Orchestrator Node
echo  ========================================
echo.

cd /d C:\code\python\AION
call .venv\Scripts\activate

echo [1/3] Demarrage Ollama...
start "" /min "C:\Users\%USERNAME%\AppData\Local\Programs\Ollama\ollama.exe" serve
timeout /t 3 /nobreak >nul

echo [2/3] Demarrage Dashboard...
start "AION Dashboard" /min cmd /c ".venv\Scripts\python.exe -m uvicorn aion.dashboard.server:app --host 127.0.0.1 --port 8000"

timeout /t 2 /nobreak >nul

echo [3/3] Demarrage AION...
start "AION Console" cmd /c ".venv\Scripts\python.exe main.py"

echo.
echo  Dashboard : http://127.0.0.1:8000/dashboard
echo  Console   : voir la fenetre AION
echo.
pause
