#!/bin/bash
# LMBench "Gold Standard" Super-Robust Installer
# Optimized for clean VMs and modern Linux (PEP 668)

set -e

# --- Configuration ---
INSTALL_DIR="$HOME/.lmbench"
VENV_PATH="$INSTALL_DIR/venv"
BIN_NAME="lmbench"

# --- UI Helpers ---
BLUE='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

header() {
    clear
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}   LMBench - Professional Installer${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

step() { echo -ne "${YELLOW}➜ $1...${NC}"; }
success() { echo -e " ${GREEN}Done${NC}"; }
fail() { echo -e " ${RED}Failed${NC}"; echo -e "Error: $1"; exit 1; }

# --- Main ---
header

# 1. Cleanup
step "Cleaning existing installation"
rm -rf "$INSTALL_DIR"
success

# 2. Prerequisites (Aggressive)
step "Installing system prerequisites"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Use -n for non-interactive sudo if possible
    sudo -n apt-get update -y &>/dev/null || sudo apt-get update -y &>/dev/null
    sudo -n apt-get install -y python3 python3-venv python3-pip build-essential &>/dev/null || sudo apt-get install -y python3 python3-venv python3-pip build-essential &>/dev/null
elif [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v brew &> /dev/null; then
        echo -e "${RED}Homebrew missing. Please install it first.${NC}"
        exit 1
    fi
    brew install python &>/dev/null
fi
success

# 3. Create Venv
step "Creating isolated environment (PEP 668 fix)"
mkdir -p "$INSTALL_DIR"
python3 -m venv "$VENV_PATH" || fail "Could not create venv. Ensure python3-venv is installed."
success

# 4. Install LMBench
step "Installing LMBench core"
"$VENV_PATH/bin/python" -m pip install --upgrade pip &>/dev/null
"$VENV_PATH/bin/python" -m pip install -e . &>/dev/null
success

# 5. Global Shim
step "Configuring global access"
# Create a local bin in INSTALL_DIR
mkdir -p "$INSTALL_DIR/bin"
cat <<EOF > "$INSTALL_DIR/bin/$BIN_NAME"
#!/bin/bash
"$VENV_PATH/bin/python" -m lmbench "\$@"
EOF
chmod +x "$INSTALL_DIR/bin/$BIN_NAME"

# Try to link to /usr/local/bin if writable
if [ -w /usr/local/bin ]; then
    ln -sf "$INSTALL_DIR/bin/$BIN_NAME" "/usr/local/bin/$BIN_NAME"
    success "(Linked to /usr/local/bin)"
else
    # Fallback: Add to .bashrc
    if [[ ":$PATH:" != ":$INSTALL_DIR/bin:"* ]]; then
        echo "export PATH=\"
$PATH:$INSTALL_DIR/bin\"" >> "$HOME/.bashrc"
        success "(Added to ~/.bashrc)"
    else
        success
    fi
fi

# 6. Final Instructions
VERSION=$(grep -oP '__version__ = "\K[^"]+' src/lmbench/__init__.py || echo "1.9.0")
echo -e "\n${GREEN}✔ LMBench v$VERSION is ready!${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e " ${BLUE}USAGE:${NC}"
echo -e " Close and reopen your terminal OR run: ${YELLOW}source ~/.bashrc${NC}"
echo -e " Then run: ${GREEN}lmbench run --suite${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"