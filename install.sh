#!/bin/bash
# LMBench "Gold Standard" Installer (v2.7.0)
# Optimized for professional deployment on clean VMs

set -e

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

REAL_USER=${SUDO_USER:-$USER}
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
INSTALL_DIR="$REAL_HOME/.lmbench"
VENV_PATH="$INSTALL_DIR/venv"
BIN_DIR="$INSTALL_DIR/bin"
BIN_NAME="lmbench"

# --- UI Colors ---
BLUE='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

# --- UI Helpers ---
draw_progress_bar() {
    local percent=$1
    local task=$2
    local filled_chars=$(( percent / 4 ))
    local empty_chars=$(( 25 - filled_chars ))
    printf "\r\033[K%b➜ Installing: [" "${YELLOW}"
    printf "%b" "${GREEN}"
    for ((i=0; i<filled_chars; i++)); do printf "█"; done
    printf "%b" "${NC}"
    for ((i=0; i<empty_chars; i++)); do printf "-"; done
    printf "] %d%% %b(%s)%b" "$percent" "${BLUE}" "$task" "${NC}"
}

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   LMBench - Professional Deployment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 1. Early Sudo Validation
if [ "$EUID" -ne 0 ]; then
    sudo -v || { echo -e "${RED}Error: Sudo permissions required.${NC}"; exit 1; }
fi

# 2. Cleanup
rm -rf "$INSTALL_DIR"

steps=5
current=0
update_progress() {
    current=$((current + 1))
    local task=$1
    percent=$((current * 100 / steps))
    draw_progress_bar $percent "$task"
}

# Step 1: System Packages
update_progress "System Environment"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo apt-get update -y &>/dev/null
    sudo apt-get install -y python3 python3-venv python3-pip build-essential &>/dev/null
fi

# Step 2: Virtual Environment
update_progress "Isolated Python Sandbox"
mkdir -p "$INSTALL_DIR"
chown "$REAL_USER:$REAL_USER" "$INSTALL_DIR"
sudo -u "$REAL_USER" python3 -m venv "$VENV_PATH" &>/dev/null

# Step 3: Core Dependencies
update_progress "LMBench Engine & Core"
sudo -u "$REAL_USER" "$VENV_PATH/bin/python3" -m pip install --upgrade pip &>/dev/null
sudo -u "$REAL_USER" "$VENV_PATH/bin/python3" -m pip install -e . &>/dev/null

# Step 4: Command Shim
update_progress "Global Entrypoint"
mkdir -p "$BIN_DIR"
cat <<EOF > "$BIN_DIR/$BIN_NAME"
#!/bin/bash
"$VENV_PATH/bin/python3" -m lmbench "\$@"
EOF
chmod +x "$BIN_DIR/$BIN_NAME"
chown "$REAL_USER:$REAL_USER" "$BIN_DIR/$BIN_NAME"

# Step 5: Path Configuration
update_progress "System Integration"
if [ -d "/usr/local/bin" ] && [ -w "/usr/local/bin" ]; then
    sudo ln -sf "$BIN_DIR/$BIN_NAME" "/usr/local/bin/$BIN_NAME" &>/dev/null
fi
if ! grep -q "$BIN_DIR" "$REAL_HOME/.bashrc"; then
    echo "export PATH=\"
$PATH:$BIN_DIR\"" >> "$REAL_HOME/.bashrc"
fi

# Finalize
echo -e "\n\n${GREEN}✔ LMBench v2.7.0 is now ready!${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e " [white]The 'lmbench' command has been added to your environment.[/white]"
echo -e " [white]If it's not found, run: [bold cyan]source ~/.bashrc[/bold cyan][/white]\n"
echo -e " Run benchmark now:  ${GREEN}lmbench run --suite${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

# Clean temporary repo files if requested or just finish
# We don't delete the current dir as the user might be in it,
# but we've cleaned the internal install dir.
