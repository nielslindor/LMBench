#!/bin/bash
# LMBench High-Fidelity Installer
# Optimized for professional deployment on clean VMs

set -e

# --- Configuration ---
INSTALL_DIR="$HOME/.lmbench"
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
    local width=40
    local filled=$(( percent * width / 100 ))
    local empty=$(( width - filled ))
    printf "\r${YELLOW}Installing: [${GREEN}"
    printf "%${filled}s" | tr ' ' '█'
    printf "${NC}"
    printf "%${empty}s" | tr ' ' '░'
    printf "] ${percent}%"
}

header() {
    clear
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}   LMBench - Professional Standard Installer${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# --- Initialization ---
header

# 1. Early Sudo Validation
echo -e "${YELLOW}➜ Validating permissions...${NC}"
sudo -v || { echo -e "${RED}Error: Sudo permissions required for system prerequisites.${NC}"; exit 1; }

# 2. Cleanup
echo -ne "${YELLOW}➜ Preparing clean slate...${NC}"
rm -rf "$INSTALL_DIR"
echo -e " ${GREEN}Done${NC}"

# 3. Installation Flow with Progress
steps=5
current=0

update_progress() {
    current=$((current + 1))
    percent=$((current * 100 / steps))
    draw_progress_bar $percent
}

# Step 1: System Packages
update_progress
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo apt-get update -y &>/dev/null
    sudo apt-get install -y python3 python3-venv python3-pip build-essential &>/dev/null
fi

# Step 2: Virtual Environment
update_progress
mkdir -p "$INSTALL_DIR"
python3 -m venv "$VENV_PATH" &>/dev/null

# Step 3: Core Dependencies
update_progress
"$VENV_PATH/bin/python" -m pip install --upgrade pip &>/dev/null
"$VENV_PATH/bin/python" -m pip install -e . &>/dev/null

# Step 4: Command Shim
update_progress
mkdir -p "$BIN_DIR"
cat <<EOF > "$BIN_DIR/$BIN_NAME"
#!/bin/bash
"$VENV_PATH/bin/python" -m lmbench "\$@"
EOF
chmod +x "$BIN_DIR/$BIN_NAME"

# Step 5: Path Configuration
update_progress
if [ -w /usr/local/bin ]; then
    sudo ln -sf "$BIN_DIR/$BIN_NAME" "/usr/local/bin/$BIN_NAME" &>/dev/null
else
    if [[ ":$PATH:" != ":$BIN_DIR:"* ]]; then
        echo "export PATH=\"
$PATH:$BIN_DIR\"" >> "$HOME/.bashrc"
    fi
fi

# Finalize
echo -e "\n\n${GREEN}✔ LMBench installation successful!${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e " ${BLUE}GETTING STARTED:${NC}"
echo -e " 1. Reload Path:      ${YELLOW}source ~/.bashrc${NC}"
echo -e " 2. Run Benchmark:    ${GREEN}lmbench run --suite${NC}"
echo -e " 3. Diagnostics:      ${GREEN}lmbench doctor${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
