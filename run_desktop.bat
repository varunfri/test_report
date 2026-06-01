@echo off
cd /d "%~dp0"

echo ==================================================
echo Starting Offline Desktop Report Generator Client...
echo ==================================================

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not added to your PATH.
    echo Please install Python and check the box "Add Python to PATH".
    pause
    exit /b 1
)

:: Create virtual environment if it does not exist
if not exist ".venv" (
    echo Setting up a private environment (.venv) for dependencies...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo Error: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Activate virtual environment
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Error: Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Install dependencies
echo Verifying and installing required packages (pywebview, pandas, openpyxl)...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install required packages.
    pause
    exit /b 1
)

echo ==================================================
echo Launching Standalone Desktop App...
echo ==================================================

python desktop.py
