#!/bin/bash

# --- Color Definitions for UI ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=================================================${NC}"
echo -e "${CYAN}   🚀 Initializing Lab Submission Server...      ${NC}"
echo -e "${CYAN}=================================================${NC}\n"

# --- Helper Function: Auto-Installer ---
prompt_install() {
    local package_name=$1
    local apt_package=$2
    
    echo -e "${YELLOW}⚠️ Missing required dependency: ${package_name}${NC}"
    
    # Check if the system uses 'apt' (Ubuntu/Debian)
    if command -v apt &> /dev/null; then
        read -p "Would you like to install it now using apt? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${GREEN}Installing ${package_name}...${NC}"
            sudo apt update && sudo apt install -y $apt_package
        else
            echo -e "${RED}❌ Cannot continue without ${package_name}. Exiting.${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ Cannot auto-install on this OS.${NC}"
        echo -e "💡 Please install '${package_name}' using your system's package manager, then run this script again."
        exit 1
    fi
}

# --- 1. System Checks ---
echo -e "🔍 Checking system dependencies..."

# Check Python 3
if ! command -v python3 &> /dev/null; then
    prompt_install "Python 3" "python3"
fi

# Check Python Virtual Environment module (often separated in Ubuntu)
if ! python3 -m venv -h &> /dev/null; then
    prompt_install "Python 3 venv module" "python3-venv"
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    prompt_install "Docker" "docker.io"
fi

echo -e "${GREEN}✅ All core dependencies installed.${NC}\n"

# --- 2. Docker Permissions Check ---
echo -e "🐳 Verifying Docker daemon access..."
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Error: Cannot connect to Docker, or you lack permissions.${NC}"

    # Check if the user is running WSL
    if grep -qEi "(Microsoft|WSL)" /proc/version &> /dev/null; then
        echo -e "${YELLOW}💡 WSL Environment Detected! Your Docker daemon is likely turned off.${NC}"
        echo -e "   Run this command to force it online in the background:"
        echo -e "   ${CYAN}sudo dockerd &${NC}"
        echo -e "   (Press Enter if the text keeps scrolling, then run ./start.sh again)"
    else
        echo -e "${YELLOW}💡 Standard Linux Detected! You likely need to fix user permissions.${NC}"
        echo -e "   Run these two commands to grant your user access:"
        echo -e "   ${CYAN}sudo usermod -aG docker \$USER${NC}"
        echo -e "   ${CYAN}newgrp docker${NC}"
        echo -e "   Then run ./start.sh again."
    fi
    exit 1
fi
echo -e "${GREEN}✅ Docker daemon connected successfully.${NC}\n"

# --- 3. Build Docker Sandbox ---
if [[ "$(docker images -q lab_sandbox 2> /dev/null)" == "" ]]; then
    echo -e "📦 ${YELLOW}Building the secure lab_sandbox Docker image (this takes a minute)...${NC}"
    docker build -t lab_sandbox -f Dockerfile.eval .
    echo -e "${GREEN}✅ Sandbox built successfully.${NC}\n"
else
    echo -e "${GREEN}✅ lab_sandbox Docker image is already built.${NC}\n"
fi

# --- 4. Python Environment Setup ---
if [ ! -d "venv" ]; then
    echo -e "🐍 ${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

echo -e "📥 Activating environment and verifying Python packages..."
source venv/bin/activate
pip install -q -r requirements.txt
echo -e "${GREEN}✅ Python environment ready.${NC}\n"

# --- 4.5 Configuration Wizard ---
echo -e "⚙️ Checking server configuration..."

# If the config still has the default secret key, force the setup wizard
if grep -q "super-secret-persistent-key-change-this" config.json; then
    echo -e "${YELLOW}⚠️ First-time setup detected. Launching Configuration Wizard...${NC}"
    python3 configure_lab.py
else
    # For subsequent runs, ask if they want to update settings
    read -p "Would you like to run the Configuration Wizard? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 configure_lab.py
    fi
fi

# --- 5. Start Server ---
echo -e "${CYAN}=================================================${NC}"
echo -e "${GREEN}🌟 Starting Flask Server on http://0.0.0.0:5000${NC}"
echo -e "${CYAN}=================================================${NC}"
python3 run.py
