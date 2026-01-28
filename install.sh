#!/bin/bash
# LMBench One-Command Installer for Linux/macOS

set -e

echo -e "\033[0;36m🚀 Starting LMBench Installation...\033[0m"

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "\033[0;33mPython 3 not found. Attempting to install...\033[0m"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y python3 python3-pip
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install python
        else
            echo -e "\033[0;31m❌ Homebrew not found. Please install Python 3 manually.\033[0m"
            exit 1
        fi
    fi
fi

# 2. Install LMBench
echo -e "\n\033[0;34mInstalling LMBench dependencies...\033[0m"
python3 -m pip install --upgrade pip
python3 -m pip install -e .

echo -e "\n\033[0;32m✅ Installation Complete!\033[0m"
echo -e "You can now run LMBench using: \033[0;36mlmbench --help\033[0m"
