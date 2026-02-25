@echo off
title SkillVerse

REM Move to the project root folder (wherever this .bat file is)
cd /d "%~dp0"

echo ========================================
echo   SkillVerse - Starting Application
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.x from python.org
    pause
    exit /b 1
)

REM Always install/update all packages from requirements.txt
echo Installing dependencies...
pip install -r requirements.txt --quiet
echo Dependencies ready.
echo.

echo Starting SkillVerse...
echo.
echo  URL:      http://localhost:5000
echo  Admin:    admin@skillverse.com
echo  Password: admin123
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

REM Open browser after 3 seconds
start "" cmd /c "timeout /t 3 >nul && start http://localhost:5000"

REM Run the app
python run.py

pause
