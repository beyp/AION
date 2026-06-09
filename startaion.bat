@echo off
title AION Launcher
echo.
echo  ========================================
echo   AION - AI Agent Orchestrator Node
echo  ========================================
echo.

cd /d C:\code\python\AION
call .venv\Scripts\activate

echo  [1/2] Demarrage du Dashboard...
start "AION Dashboard" /min cmd /c ".venv\Scripts\python.exe -m uvicorn aion.dashboard.server:app --host 127.0.0.1 --port 8000"

timeout /t 2 /nobreak >nul

echo  [2/2] Demarrage d AION...
start "AION Console" cmd /c ".venv\Scripts\python.exe main.py"

echo.
echo  Dashboard : http://127.0.0.1:8000/dashboard
echo  Console   : voir la fenetre AION
echo.
pause
