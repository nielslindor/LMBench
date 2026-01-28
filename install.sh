#!/bin/bash
# LMBench High-Fidelity Installer for Linux/macOS

set -e

# --- Configuration ---
INSTALL_DIR="$HOME/.lmbench"
VENV_PATH="$INSTALL_DIR/venv"
BIN_LINK="/usr/local/bin/lmbench"

# --- UI Helpers ---
BLUE='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}   LMBench Installer${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# --- Main Script ---
clear
header

# 1. Environment Prep
echo -ne "${YELLOW}Preparing environment...${NC}"
mkdir -p "$INSTALL_DIR"
echo -e " ${GREEN}Done${NC}"

# 2. Check for Python 3 & Venv
if ! command -v python3 &> /dev/null; then
    echo -ne "${YELLOW}Installing Python 3...${NC}"
    (sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip) &> /dev/null &
    spinner $!
    echo -e " ${GREEN}Installed${NC}"
else
    # Ensure venv module is present (common issue on Ubuntu)
    if ! python3 -m venv --help &> /dev/null; then
        echo -ne "${YELLOW}Installing missing venv module...${NC}"
        (sudo apt-get update && sudo apt-get install -y python3-venv) &> /dev/null &
        spinner $!
        echo -e " ${GREEN}Installed${NC}"
    fi
fi

# 3. Create Virtual Environment (PEP 668 Fix)
echo -ne "${YELLOW}Creating secure virtual environment...${NC}"
(python3 -m venv "$VENV_PATH") &> /dev/null &
spinner $!
echo -e " ${GREEN}Created${NC}"

# 4. Install LMBench
echo -ne "${YELLOW}Installing LMBench core & dependencies...${NC}"
("$VENV_PATH/bin/python" -m pip install --upgrade pip) &> /dev/null
("$VENV_PATH/bin/python" -m pip install -e .) &> /dev/null &
spinner $!
echo -e " ${GREEN}Success${NC}"

# 5. Create Command Link
echo -ne "${YELLOW}Linking global command...${NC}"
cat <<EOF > "$INSTALL_DIR/lmbench_shim"
#!/bin/bash
"$VENV_PATH/bin/python" -m lmbench "\$@"
EOF
chmod +x "$INSTALL_DIR/lmbench_shim"

if sudo ln -sf "$INSTALL_DIR/lmbench_shim" "$BIN_LINK" &> /dev/null; then
    echo -e " ${GREEN}Linked to $BIN_LINK${NC}"
else
    # Fallback if sudo link fails
    echo -e " ${YELLOW}Manual link needed${NC}"
    echo -e " [dim]Run: alias lmbench='$INSTALL_DIR/lmbench_shim'[/dim]"
fi

# 6. Final Instructions
echo -e "\n${GREEN}✔ LMBench v$(cat src/lmbench/__init__.py | grep -oP '\d+\.\d+\.\d+') is ready!${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e " ${BLUE}HOW TO RUN:${NC}"
echo -e " 1. Start a benchmark:  ${GREEN}lmbench run --suite${NC}"
echo -e " 2. Check system:       ${GREEN}lmbench doctor${NC}"
echo -e " 3. Get suggestions:    ${GREEN}lmbench recommend${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
