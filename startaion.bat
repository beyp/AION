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
REM 0.0.0.0 = accessible depuis tout le reseau WiFi (iPhone, tablette, etc.)
start "AION Dashboard" /min cmd /c ".venv\Scripts\python.exe -m uvicorn aion.dashboard.server:app --host 0.0.0.0 --port 8000"

timeout /t 2 /nobreak >nul

echo [3/3] Demarrage AION...
start "AION Console" cmd /c ".venv\Scripts\python.exe main.py"

echo.
echo  ========================================
echo   AION demarre !
echo  ========================================
echo.
echo  Dashboard local : http://localhost:8000/dashboard
echo  API Docs        : http://localhost:8000/docs
echo.
echo  Pour acceder depuis l iPhone :
echo    1. Trouve ton IP locale :
FOR /F "tokens=2 delims=:" %%i IN ('ipconfig ^| findstr /i "IPv4"') DO (
    SET IP=%%i
    SET IP=!IP: =!
    echo    2. URL iPhone : http://!IP!:8000/api/voice
)
echo.
pause
