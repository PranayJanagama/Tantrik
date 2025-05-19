#!/bin/bash

set -e

echo "Setting up Python virtual environment..."

cd /home/tele/Music/Tantrik_Testcenter\

# Create and activate the virtual environment
source .venv/bin/activate

# Upgrade pip and install requirements
pip install --upgrade pip
pip install -r requirements.txt

echo "Virtual environment setup complete."