#!/bin/bash
# LMBench "Gold Standard" Installer (v2.8.0)
# Optimized for high-fidelity terminal feedback

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
DIM='\033[2m'
NC='\033[0m'

# --- State ---
CURRENT_STEP=0
TOTAL_STEPS=5
LAST_LOG=""

# --- UI Helpers ---
spinner() {
    local pid=$1
    local task=$2
    local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local i=0
    while kill -0 $pid 2>/dev/null; do
        local percent=$(( (CURRENT_STEP * 100) / TOTAL_STEPS ))
        local filled=$(( percent / 4 ))
        local empty=$(( 25 - filled ))
        
        # Build progress bar
        local bar=""
        for ((j=0; j<filled; j++)); do bar+="█"; done
        for ((j=0; j<empty; j++)); do bar+="░"; done
        
        # Get last line of log
        if [ -f /tmp/lmbench_install.log ]; then
            LAST_LOG=$(tail -n 1 /tmp/lmbench_install.log | cut -c1-50)
        fi

        printf "\r${YELLOW}%s${NC} Installing: [${GREEN}%s${NC}] %d%% (%s) ${DIM}%s...${NC}\033[K" \
            "${spin:i++%${#spin}:1}" "$bar" "$percent" "$task" "$LAST_LOG"
        sleep 0.1
    done
}

run_task() {
    local task_name=$1
    local cmd=$2
    CURRENT_STEP=$((CURRENT_STEP + 1))
    
    # Run command in background, redirecting to log
    eval "$cmd" > /tmp/lmbench_install.log 2>&1 & 
    spinner $! "$task_name"
    wait $!
}

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   LMBench - High-Fidelity Deployment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 1. Early Sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}➜ Authenticating sudo...${NC}"
    sudo -v
fi

# 2. Cleanup
rm -rf "$INSTALL_DIR"
rm -f /tmp/lmbench_install.log

# 3. Tasks
run_task "System Environment" "sudo apt-get update -y && sudo apt-get install -y python3 python3-venv python3-pip build-essential"
run_task "Python Sandbox" "mkdir -p $INSTALL_DIR && chown $REAL_USER:$REAL_USER $INSTALL_DIR && sudo -u $REAL_USER python3 -m venv $VENV_PATH"
run_task "LMBench Core" "sudo -u $REAL_USER $VENV_PATH/bin/python3 -m pip install --upgrade pip && sudo -u $REAL_USER $VENV_PATH/bin/python3 -m pip install -e ."
run_task "Command Shim" "mkdir -p $BIN_DIR && echo '#!/bin/bash' > $BIN_DIR/$BIN_NAME && echo '$VENV_PATH/bin/python3 -m lmbench \"\$@\"' >> $BIN_DIR/$BIN_NAME && chmod +x $BIN_DIR/$BIN_NAME && chown $REAL_USER:$REAL_USER $BIN_DIR/$BIN_NAME"
run_task "System Integration" "if [ -d /usr/local/bin ] && [ -w /usr/local/bin ]; then sudo ln -sf $BIN_DIR/$BIN_NAME /usr/local/bin/$BIN_NAME; fi && if ! grep -q '$BIN_DIR' '$REAL_HOME/.bashrc'; then echo 'export PATH="\$PATH:$BIN_DIR"' >> '$REAL_HOME/.bashrc'; fi"

# Finalize
printf "\r${GREEN}✔${NC} Installation Complete: [${GREEN}█████████████████████████${NC}] 100%% (Ready) \033[K\n"
echo -e "\n${GREEN}LMBench v2.8.0 successfully deployed!${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e " ${WHITE}To start immediately, run:${NC}"
echo -e " ${CYAN}export PATH=\"\$PATH:$BIN_DIR\" && lmbench run --suite${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"