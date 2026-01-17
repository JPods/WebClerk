#!/bin/bash
# =============================================================================
# Data Set Switcher
# =============================================================================
# Usage: ./switch-dataset.sh [remote|local]
# 
# Switches the database mode and restarts both wc3 and r25 servers.
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WC3_DIR="$(dirname "$SCRIPT_DIR")"
R25_DIR="$(dirname "$WC3_DIR")/React2025"
DEV_CONFIG="$SCRIPT_DIR/dev-config.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Data Set Switcher${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

get_current_mode() {
    if [ -f "$DEV_CONFIG" ]; then
        grep -o '"db_mode": *"[^"]*"' "$DEV_CONFIG" | cut -d'"' -f4
    else
        grep "^DB_MODE=" "$WC3_DIR/.env" | cut -d'=' -f2
    fi
}

show_current_status() {
    local current_mode=$(get_current_mode)
    echo -e "Current mode: ${YELLOW}${current_mode}${NC}"
    echo ""
}

update_env_file() {
    local file=$1
    local mode=$2
    
    if [ -f "$file" ]; then
        # Update DB_MODE in backend .env
        if grep -q "^DB_MODE=" "$file"; then
            sed -i '' "s/^DB_MODE=.*/DB_MODE=$mode/" "$file"
            print_status "Updated $file"
        fi
    fi
}

update_dev_config() {
    local mode=$1
    
    if [ -f "$DEV_CONFIG" ]; then
        # Use Python for reliable JSON update
        python3 << EOF
import json
with open("$DEV_CONFIG", "r") as f:
    config = json.load(f)
config["db_mode"] = "$mode"
with open("$DEV_CONFIG", "w") as f:
    json.dump(config, f, indent=2)
EOF
        print_status "Updated dev-config.json"
    fi
}

restart_servers() {
    echo ""
    echo -e "${BLUE}Restarting servers...${NC}"
    echo ""
    
    # Kill existing processes on ports 8000 and 5173
    print_warning "Stopping existing servers..."
    
    # Kill Django (port 8000)
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    
    # Kill Vite (port 5173)
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true
    
    sleep 1
    
    # Start Django in background
    print_status "Starting webClerk3 (Django)..."
    cd "$WC3_DIR"
    source bin/activate 2>/dev/null || source venv312/bin/activate 2>/dev/null || true
    python manage.py runserver &
    WC3_PID=$!
    
    sleep 2
    
    # Start Vite in background
    print_status "Starting React2025 (Vite)..."
    cd "$R25_DIR"
    npm run dev &
    R25_PID=$!
    
    echo ""
    print_status "Servers started!"
    echo ""
    echo -e "  Django:  ${GREEN}http://localhost:8000${NC} (PID: $WC3_PID)"
    echo -e "  Vite:    ${GREEN}http://localhost:5173${NC} (PID: $R25_PID)"
    echo ""
}

# Main
print_header

MODE=${1:-""}

if [ -z "$MODE" ]; then
    echo "Usage: ./switch-dataset.sh [remote|local|status]"
    echo ""
    show_current_status
    echo "Options:"
    echo -e "  ${GREEN}remote${NC}  - Use shared database (team collaboration)"
    echo -e "  ${GREEN}local${NC}   - Use local database (debugging)"
    echo -e "  ${GREEN}status${NC}  - Show current mode without changing"
    echo ""
    exit 0
fi

if [ "$MODE" = "status" ]; then
    show_current_status
    exit 0
fi

if [ "$MODE" != "remote" ] && [ "$MODE" != "local" ]; then
    print_error "Invalid mode: $MODE"
    echo "Valid options: remote, local, status"
    exit 1
fi

echo -e "Switching to: ${GREEN}${MODE}${NC}"
echo ""

# Update configuration files
update_env_file "$WC3_DIR/.env" "$MODE"
update_dev_config "$MODE"

print_status "Configuration updated!"
echo ""

# Ask about restarting servers
read -p "Restart servers now? [Y/n] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    restart_servers
else
    print_warning "Remember to restart servers manually for changes to take effect."
fi

echo -e "${GREEN}Done!${NC}"
echo ""
