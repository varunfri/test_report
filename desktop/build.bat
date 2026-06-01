@echo off
cd /d "%~dp0"

echo ==================================================
echo Compiling Standalone Offline Desktop Application...
echo ==================================================

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not added to your PATH.
    echo Please install Python and check the box "Add Python to PATH".
    pause
    exit /b 1
)

:: Create virtual environment in parent directory if it does not exist
if not exist "..\.venv" (
    echo Setting up a private environment (.venv)...
    python -m venv ..\.venv
    if %errorlevel% neq 0 (
        echo Error: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Activate virtual environment
call ..\.venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Error: Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Install dependencies
echo Installing requirements and build dependencies...
python -m pip install --upgrade pip
pip install -r ..\requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install packages.
    pause
    exit /b 1
)

:: Run build script
python build_exe.py
if %errorlevel% neq 0 (
    echo Error: Standalone compilation failed.
    pause
    exit /b 1
)

echo ==================================================
echo Compilation successful!
echo Zip the 'dist\ReportConsolidationTool' folder and share.
echo ==================================================
pause
