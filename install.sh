#!/bin/bash
# LMBench "Gold Standard" Installer (v3.5.0)
# Optimized for high-fidelity terminal feedback and professional lifecycle

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
WHITE='\033[1;37m'
NC='\033[0m'

# --- State ---
CURRENT_STEP=0
TOTAL_STEPS=15
LAST_LOG=""

# --- UI Helpers ---
draw_progress_bar() {
    local percent=$1
    local task=$2
    local filled_chars=$(( percent / 4 ))
    local empty_chars=$(( 25 - filled_chars ))
    local bar=""
    for ((j=0; j<filled_chars; j++)); do bar+="█"; done
    for ((j=0; j<empty_chars; j++)); do bar+="░"; done
    if [ -f /tmp/lmbench_install.log ]; then
        LAST_LOG=$(tail -n 1 /tmp/lmbench_install.log | cut -c1-50)
    fi
    printf "\r\033[K${YELLOW}⠋${NC} Installing: [${GREEN}%s${NC}] %d%% (%s) ${DIM}%s...${NC}" \
        "$bar" "$percent" "$task" "$LAST_LOG"
}

run_task() {
    local task_name=$1
    local cmd=$2
    CURRENT_STEP=$((CURRENT_STEP + 1))
    eval "$cmd" >> /tmp/lmbench_install.log 2>&1 &
    local pid=$!
    while kill -0 $pid 2>/dev/null; do
        draw_progress_bar $(( (CURRENT_STEP * 100) / TOTAL_STEPS )) "$task_name"
        sleep 0.1
    done
    wait $pid
}

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   LMBench - Benchmark Tool Installer${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 1. Early Sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}➜ Authenticating sudo...${NC}"
    sudo -v
fi

# 2. Cleanup
rm -rf "$INSTALL_DIR"
rm -f /tmp/lmbench_install.log
touch /tmp/lmbench_install.log

# 3. Tasks
run_task "System Environment" "sudo apt-get update -y && sudo apt-get install -y python3 python3-venv python3-pip build-essential"
run_task "Sandbox Directory" "mkdir -p $INSTALL_DIR && chown $REAL_USER:$REAL_USER $INSTALL_DIR"
run_task "Python Sandbox" "sudo -u $REAL_USER python3 -m venv $VENV_PATH"
run_task "Core Engine" "sudo -u $REAL_USER $VENV_PATH/bin/python3 -m pip install --upgrade pip && sudo -u $REAL_USER $VENV_PATH/bin/python3 -m pip install -e '$SCRIPT_DIR'"
run_task "Global Link" "mkdir -p $BIN_DIR && printf '#!/bin/bash\nexport PYTHONPATH=\"$SCRIPT_DIR/src:\\$PYTHONPATH\"\n\"$VENV_PATH/bin/python3\" -m lmbench \"\$@\"' > $BIN_DIR/$BIN_NAME && chmod +x $BIN_DIR/$BIN_NAME && chown $REAL_USER:$REAL_USER $BIN_DIR/$BIN_NAME"
run_task "System Integration" "if [ -d /usr/local/bin ] && [ -w /usr/local/bin ]; then sudo ln -sf $BIN_DIR/$BIN_NAME /usr/local/bin/$BIN_NAME; fi && if ! grep -q '$BIN_DIR' '$REAL_HOME/.bashrc'; then echo 'export PATH=\"\$PATH:$BIN_DIR\"' >> '$REAL_HOME/.bashrc'; fi"

# Finalize
printf "\r${GREEN}✔${NC} Deployment Complete: [${GREEN}█████████████████████████${NC}] 100%% (Success) \033[K\n"
echo -e "${GREEN}LMBench successfully deployed!${NC}\n"

export PATH="$PATH:$BIN_DIR"
rm -f /tmp/lmbench_install.log

# 4. Interactive Execution Flow
echo -e "LMBench is ready."
echo -ne "Press any key to change suite flags or cancel (5s)... "
KEY_PRESSED=""
for i in {5..1}; do
    echo -ne "\rPress any key to change suite flags or cancel (${i}s)... "
    read -t 1 -n 1 input && { KEY_PRESSED=$input; break; }
done

if [ -n "$KEY_PRESSED" ]; then
    echo -e "\n\n${WHITE}[ LMBench Launch Menu ]${NC}"
    echo -e " 1. ${RED}Exit to terminal${NC}"
    echo -e " 2. Run standard suite (Default)"
    echo -e " 3. Run intensive deep suite"
    echo -e " 4. Run system doctor"
    echo -e " 5. Get model recommendations"
    echo -ne "\nSelect option [1-5]: "
    read -n 1 choice
    echo -e "\n"
    case $choice in
        1) exit 0 ;;
        3) "$BIN_DIR/$BIN_NAME" run --deep --rounds 2 --intent G ;; 
        4) "$BIN_DIR/$BIN_NAME" doctor ;; 
        5) "$BIN_DIR/$BIN_NAME" recommend ;; 
        *) "$BIN_DIR/$BIN_NAME" run --suite --intent G ;; 
    esac
else
    echo -e "\n\n${BLUE}➜ Executing suite...${NC}"
    "$BIN_DIR/$BIN_NAME" run --suite --intent G
fi