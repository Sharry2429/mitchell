#!/usr/bin/env bash
# Mitchell Universal 1-Click Installer for Linux, macOS & WSL2
# Usage: bash scripts/install.sh

set -e

echo "=================================================="
echo "  Mitchell Autonomous Multi-Agent Hive Installer  "
echo "=================================================="

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3.10+ is required but not found."
    exit 1
fi

# 2. Virtual Environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment in ./venv..."
    python3 -m venv venv
fi

# 3. Activate and Install
echo "Installing dependencies..."
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -e ".[dev]"

# 4. Playwright Browsers
echo "Installing Playwright Chromium..."
./venv/bin/python -m playwright install chromium || true

# 5. Initialize .env
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "Created default .env from .env.example"
fi

echo "=================================================="
echo "  Mitchell Installation Complete!                 "
echo "  Run './venv/bin/mitchell studio' to start.      "
echo "=================================================="
