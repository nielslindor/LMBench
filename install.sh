#!/bin/bash
# LMBench "Gold Standard" Installer (v3.4.0)
# Optimized for high-fidelity granular feedback

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname \"$0\")" && pwd)"
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
TOTAL_STEPS=15 # Increased granularity
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
        local bar=""
        for ((j=0; j<filled; j++)); do bar+="█"; done
        for ((j=0; j<empty; j++)); do bar+="░"; done
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
    eval "$cmd" >> /tmp/lmbench_install.log 2>&1 &
    local pid=$!
    spinner $pid "$task_name"
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

# 3. Tasks - HIGH GRANULARITY
run_task "Syncing Time" "sudo date -s \"\
$(curl -s --head http://google.com | grep ^Date: | sed 's/Date: //g')\" || true"
run_task "Updating Apt" "sudo apt-get update -y"
run_task "Base Tools" "sudo apt-get install -y build-essential curl git"
run_task "Python Core" "sudo apt-get install -y python3"
run_task "Python Venv" "sudo apt-get install -y python3-venv"
run_task "Python Pip" "sudo apt-get install -y python3-pip"
run_task "Sandbox Dir" "mkdir -p $INSTALL_DIR && chown $REAL_USER:$REAL_USER $INSTALL_DIR"
run_task "Virtual Env" "sudo -u $REAL_USER python3 -m venv $VENV_PATH"
run_task "Pip Upgrade" "sudo -u $REAL_USER $VENV_PATH/bin/python3 -m pip install --upgrade pip"
run_task "Dependencies" "sudo -u $REAL_USER $VENV_PATH/bin/python3 -m pip install typer rich httpx pydantic psutil platformdirs py-cpuinfo nvidia-ml-py"
run_task "Core Logic" "sudo -u $REAL_USER $VENV_PATH/bin/python3 -m pip install -e '$SCRIPT_DIR'"
run_task "Import Check" "sudo -u $REAL_USER $VENV_PATH/bin/python3 -c 'import lmbench'"
run_task "Command Shim" "mkdir -p $BIN_DIR && echo '#!/bin/bash' > $BIN_DIR/$BIN_NAME && echo 'export PYTHONPATH="$SCRIPT_DIR/src:
$PYTHONPATH"' >> $BIN_DIR/$BIN_NAME && echo '$VENV_PATH/bin/python3 -m lmbench "\$@"' >> $BIN_DIR/$BIN_NAME && chmod +x $BIN_DIR/$BIN_NAME && chown $REAL_USER:$REAL_USER $BIN_DIR/$BIN_NAME"
run_task "Path Link" "if [ -d /usr/local/bin ] && [ -w /usr/local/bin ]; then sudo ln -sf $BIN_DIR/$BIN_NAME /usr/local/bin/$BIN_NAME; fi"
run_task "RC Integration" "if ! grep -q '$BIN_DIR' '$REAL_HOME/.bashrc'; then echo 'export PATH="\$PATH:$BIN_DIR"' >> '$REAL_HOME/.bashrc'; fi"

# Finalize
printf "\r${GREEN}✔${NC} Deployment Complete: [${GREEN}█████████████████████████${NC}] 100%% (Success) \033[K\n"
echo -e "${GREEN}LMBench successfully deployed!${NC}\n"

export PATH="$PATH:$BIN_DIR"
rm -f /tmp/lmbench_install.log

# Interactive Flow
echo -e "Running LMBench in suite mode."
echo -ne "Press any key to choose flags or cancel (5s)... "
KEY_PRESSED=""
for i in {5..1}; do
    echo -ne "\rPress any key to choose flags or cancel (${i}s)... "
    read -t 1 -n 1 input && { KEY_PRESSED=$input; break; }
done

if [ -n "$KEY_PRESSED" ]; then
    echo -e "\n\n${WHITE}[ LMBench Launch Menu ]${NC}"
    echo -e " 1. ${RED}Cancel and return to terminal${NC}"
    echo -e " 2. Run standard suite (Default)"
    echo -e " 3. Run intensive deep suite"
    echo -e " 4. Run system doctor"
    echo -e " 5. Get model recommendations"
    echo -ne "\nSelect option [1-5]: "
    read -n 1 choice
    echo -e "\n"
    case $choice in
        1) echo "Exiting..."; exit 0 ;; 
        3) lmbench run --deep --rounds 2 --intent G ;; 
        4) lmbench doctor ;; 
        5) lmbench recommend ;; 
        *) lmbench run --suite --intent G ;; 
    esac
else
    echo -e "\n\n${BLUE}➜ Executing suite...${NC}"
    lmbench run --suite --intent G
fi