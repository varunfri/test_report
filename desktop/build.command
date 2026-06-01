#!/bin/bash

# Change directory to the folder where this script is located
cd "$(dirname "$0")"

echo "=================================================="
echo "Compiling Standalone Offline Desktop Application..."
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
    echo "Setting up a private environment (.venv)..."
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
echo "Installing requirements and build dependencies..."
pip install --upgrade pip
pip install -r ../requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install required packages."
    echo "Press Enter to exit..."
    read -r
    exit 1
fi

# Run the build script
python3 build_exe.py
if [ $? -ne 0 ]; then
    echo "Error: Standalone compilation failed."
    echo "Press Enter to exit..."
    read -r
    exit 1
fi

echo "=================================================="
echo "Compilation successful!"
echo "Zip the 'dist/ReportConsolidationTool' folder and share."
echo "=================================================="
echo "Press Enter to exit..."
read -r
