#!/bin/bash

# Change directory to the folder where this script is located
cd "$(dirname "$0")"

echo "=================================================="
echo "Starting Offline Desktop Report Generator Client..."
echo "=================================================="

# Check if Python 3 is installed
if ! command -v python3 &>/dev/null; then
    echo "Error: Python 3 is not installed on this Mac."
    echo "Please download and install Python from: https://www.python.org/downloads/"
    echo "Press Enter to exit..."
    read -r
    exit 1
fi

# Create virtual environment in parent directory if it does not exist
if [ ! -d "../.venv" ]; then
    echo "Setting up a private environment (.venv) in parent folder..."
    python3 -m venv ../.venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment."
        echo "Press Enter to exit..."
        read -r
        exit 1
    fi
fi

# Activate the virtual environment
source ../.venv/bin/activate

# Install/update dependencies
echo "Verifying and installing required packages (pywebview, pandas, openpyxl)..."
pip install --upgrade pip
pip install -r ../requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install packages from requirements.txt."
    echo "Press Enter to exit..."
    read -r
    exit 1
fi

echo "=================================================="
echo "Launching Standalone Desktop App..."
echo "=================================================="

python3 desktop.py
