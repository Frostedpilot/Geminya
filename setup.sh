#!/bin/bash

set -e  # Exit on any error

echo "Setting up Geminya environment..."

# Check if Python 3.12 is available
if ! command -v python3.12 &> /dev/null; then
    echo "Error: Python 3.12 is not installed or not in PATH"
    echo "Please install Python 3.12 first"
    exit 1
fi

echo "Found Python 3.12: $(python3.12 --version)"

# Create virtual environment named .venv
if [ -d ".venv" ]; then
    echo "Virtual environment .venv already exists"
else
    echo "Creating virtual environment .venv with Python 3.12..."
    python3.12 -m venv .venv
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Verify we're using the correct Python version
echo "Using Python: $(python --version)"
echo "Python location: $(which python)"

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "Warning: requirements.txt not found"
    exit 0
fi

# Install packages line by line from requirements.txt
echo "Installing packages from requirements.txt line by line..."
while IFS= read -r line; do
    # Skip empty lines and comments
    if [[ -z "$line" || "$line" == \#* ]]; then
        continue
    fi
    
    echo "Installing: $line"
    pip install "$line"
    
    if [ $? -ne 0 ]; then
        echo "Failed to install: $line"
        echo "Continuing with next package..."
    fi
done < requirements.txt

echo "Setup complete!"
echo "To activate the environment in the future, run: source .venv/bin/activate"
