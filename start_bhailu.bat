@echo off
echo ============================================
echo   B H A I L U  — AI Assistant
echo ============================================
echo.
python --version >nul 2>&1 || (echo [ERROR] Python not found && pause && exit /b 1)
echo [1/4] Installing dependencies...
pip install -r requirements.txt --quiet
echo [2/4] Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1 || echo [WARN] Ollama not running. Start it with: ollama serve
echo [3/4] Checking microphone...
python -c "import speech_recognition as sr; sr.Microphone()" 2>nul && echo [OK] Mic found || echo [WARN] Check mic settings
echo [4/4] Launching BHAILU...
python bhailu_dashboard.py
pause
