#!/bin/bash

# Change directory to the folder where this script is located
cd "$(dirname "$0")"

echo "=================================================="
echo "Starting NA, Blocked Consolidation Tool..."
echo "=================================================="

# Check if Python 3 is installed
if ! command -v python3 &>/dev/null; then
    echo "Error: Python 3 is not installed."
    echo "Please install Python 3 using your system package manager."
    echo "Press Enter to exit..."
    read -r
    exit 1
fi

# Create virtual environment if it does not exist
if [ ! -d ".venv" ]; then
    echo "Setting up a private environment (.venv) for dependencies..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment."
        echo "Press Enter to exit..."
        read -r
        exit 1
    fi
fi

# Activate the virtual environment
source .venv/bin/activate

# Install/update dependencies
echo "Verifying and installing required packages (this may take a minute on the first run)..."
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install packages from requirements.txt."
    echo "Press Enter to exit..."
    read -r
    exit 1
fi

echo "=================================================="
echo "Setup complete. Launching the web application..."
echo "=================================================="

# Run the Streamlit application
streamlit run app.py
