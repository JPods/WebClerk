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
PID_DIR="$SCRIPT_DIR/.pids"
DJANGO_PID_FILE="$PID_DIR/django.pid"
VITE_PID_FILE="$PID_DIR/vite.pid"
SYNC_STATUS_FILE="$SCRIPT_DIR/.sync_status.json"
RESTART_REQUEST_FILE="$SCRIPT_DIR/.restart_django"
FRONTEND_WAS_RUNNING=""

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

ensure_pid_dir() {
    mkdir -p "$PID_DIR"
}

write_pid_file() {
    local file="$1"
    local pid="$2"
    ensure_pid_dir
    echo "$pid" > "$file"
}

read_pid_file() {
    local file="$1"
    if [ -f "$file" ]; then
        cat "$file" 2>/dev/null || true
    fi
}

is_pid_running() {
    local pid="$1"
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

pid_command_line() {
    local pid="$1"
    ps -p "$pid" -o command= 2>/dev/null || true
}

pid_matches() {
    local pid="$1"
    local pattern="$2"
    local cmd
    cmd=$(pid_command_line "$pid")
    [[ -n "$cmd" ]] && [[ "$cmd" == *"$pattern"* ]]
}

capture_running_pids() {
    local django_pid vite_pid
    django_pid=$(lsof -ti:8000 2>/dev/null | head -n 1 || true)
    vite_pid=$(lsof -ti:5173 2>/dev/null | head -n 1 || true)

    if is_pid_running "$django_pid"; then
        write_pid_file "$DJANGO_PID_FILE" "$django_pid"
        print_status "Tracked Django PID: $django_pid"
    fi

    if is_pid_running "$vite_pid"; then
        write_pid_file "$VITE_PID_FILE" "$vite_pid"
        print_status "Tracked Vite PID: $vite_pid"
    fi
}

get_frontend_pid() {
    local vite_pid

    vite_pid=$(read_pid_file "$VITE_PID_FILE")
    if is_pid_running "$vite_pid" && (pid_matches "$vite_pid" "vite" || pid_matches "$vite_pid" "npm run dev"); then
        echo "$vite_pid"
        return
    fi

    vite_pid=$(lsof -ti:5173 2>/dev/null | head -n 1 || true)
    if is_pid_running "$vite_pid"; then
        echo "$vite_pid"
        return
    fi

    vite_pid=$(pgrep -f "[v]ite" | head -n 1 || true)
    if is_pid_running "$vite_pid"; then
        echo "$vite_pid"
        return
    fi

    vite_pid=$(pgrep -f "npm run dev" | head -n 1 || true)
    if is_pid_running "$vite_pid"; then
        echo "$vite_pid"
        return
    fi

    echo ""
}

stop_tracked_processes() {
    local django_pid vite_pid
    django_pid=$(read_pid_file "$DJANGO_PID_FILE")
    vite_pid=$(read_pid_file "$VITE_PID_FILE")

    if is_pid_running "$django_pid" && pid_matches "$django_pid" "manage.py runserver"; then
        kill -TERM "$django_pid" 2>/dev/null || true
        print_status "Stopped tracked Django PID: $django_pid"
    elif [ -n "$django_pid" ]; then
        print_warning "Ignoring stale/unmatched Django PID file: $django_pid"
    fi

    if is_pid_running "$vite_pid" && (pid_matches "$vite_pid" "vite" || pid_matches "$vite_pid" "npm run dev"); then
        kill -TERM "$vite_pid" 2>/dev/null || true
        print_status "Stopped tracked Vite PID: $vite_pid"
    elif [ -n "$vite_pid" ]; then
        print_warning "Ignoring stale/unmatched Vite PID file: $vite_pid"
    fi

    # Fallback by ports for cases where PID files were missing/stale.
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true
}

stop_backend_process() {
    local django_pid
    django_pid=$(read_pid_file "$DJANGO_PID_FILE")

    if is_pid_running "$django_pid" && pid_matches "$django_pid" "manage.py runserver"; then
        kill -TERM "$django_pid" 2>/dev/null || true
        sleep 1
        is_pid_running "$django_pid" && kill -KILL "$django_pid" 2>/dev/null || true
        print_status "Stopped tracked Django PID: $django_pid"
    elif [ -n "$django_pid" ]; then
        print_warning "Ignoring stale/unmatched Django PID file: $django_pid"
    fi

    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
}

request_same_console_django_restart() {
    local django_pids django_pid
    django_pids=$(lsof -ti:8000 2>/dev/null || true)

    if [ -n "$django_pids" ]; then
        django_pid=$(echo "$django_pids" | head -n 1)
        write_pid_file "$DJANGO_PID_FILE" "$django_pid"
        ensure_pid_dir
        echo "1" > "$RESTART_REQUEST_FILE"
        echo "$django_pids" | xargs kill -INT 2>/dev/null || true
        print_status "Requested same-terminal Django restart (port 8000 PIDs: $django_pids)."
        print_status "If using ./runserver.sh, Django will auto-restart in this terminal."
    else
        print_warning "No active Django runserver found on port 8000 for same-terminal restart."
    fi
}

start_backend_background() {
    cd "$WC3_DIR"
    local py_bin="$WC3_DIR/bin/python"
    if [ ! -x "$py_bin" ]; then
        py_bin="python"
    fi

    ensure_pid_dir
    nohup "$py_bin" manage.py runserver --noreload > "$PID_DIR/django.log" 2>&1 &
    local new_pid=$!
    write_pid_file "$DJANGO_PID_FILE" "$new_pid"
    print_status "Django restart launched (PID: $new_pid)"

    local attempts=0
    local max_attempts=20
    while [ $attempts -lt $max_attempts ]; do
        if ! is_pid_running "$new_pid"; then
            print_error "Django process exited during startup. See $PID_DIR/django.log"
            return 1
        fi

        if lsof -ti:8000 >/dev/null 2>&1; then
            print_status "Django is live on http://localhost:8000"
            return 0
        fi

        sleep 1
        attempts=$((attempts + 1))
    done

    print_error "Django did not become live on port 8000 within ${max_attempts}s"
    return 1
}

start_frontend_background() {
    cd "$R25_DIR"
    ensure_pid_dir
    nohup npm run dev > "$PID_DIR/vite.log" 2>&1 &
    local new_pid=$!
    write_pid_file "$VITE_PID_FILE" "$new_pid"
    print_warning "Frontend was down after switch; restarted Vite in background (PID: $new_pid)."
}

capture_frontend_state() {
    FRONTEND_WAS_RUNNING=$(get_frontend_pid)
    if [ -n "$FRONTEND_WAS_RUNNING" ]; then
        write_pid_file "$VITE_PID_FILE" "$FRONTEND_WAS_RUNNING"
    fi
}

ensure_frontend_alive_if_needed() {
    if [ -z "$FRONTEND_WAS_RUNNING" ]; then
        return
    fi

    local frontend_now
    frontend_now=$(get_frontend_pid)
    if [ -n "$frontend_now" ]; then
        return
    fi

    start_frontend_background
}

schedule_frontend_watchdog() {
    if [ -z "$FRONTEND_WAS_RUNNING" ]; then
        return
    fi

    (
        sleep 6
        local frontend_now
        frontend_now=$(get_frontend_pid)
        if [ -z "$frontend_now" ]; then
            start_frontend_background
        fi
    ) >/dev/null 2>&1 &
}

get_env_var() {
    local key="$1"
    local default_value="$2"
    local env_file="$WC3_DIR/.env"

    if [ ! -f "$env_file" ]; then
        echo "$default_value"
        return
    fi

    local value
    value=$(grep -E "^${key}=" "$env_file" | tail -n 1 | cut -d'=' -f2-)
    value=$(echo "$value" | sed 's/[[:space:]]*$//')

    if [ -z "$value" ]; then
        echo "$default_value"
    else
        echo "$value"
    fi
}

sync_remote_to_local() {
    print_warning "Switch target is LOCAL. Attempting force sync from REMOTE..."

    local py_bin="$WC3_DIR/bin/python"
    if [ ! -x "$py_bin" ]; then
        py_bin="python"
    fi

    if "$py_bin" "$SCRIPT_DIR/sync_remote_to_local.py" --status-file "$SYNC_STATUS_FILE"; then
        print_status "Remote data forcefully synced into local database."
    else
        print_error "Remote→local sync failed. Aborting switch to prevent stale local data."
        return 1
    fi
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

        print_warning "Stopping existing servers..."
        capture_running_pids

        # Headless mode is used by API calls. Do not spawn detached background processes.
        # In headless mode, restart backend only and keep frontend running.
        if [ "${SWITCH_HEADLESS:-0}" = "1" ]; then
            print_warning "Headless switch mode detected (API-triggered)."
            print_status "Restarting Django only; frontend is left running."
            stop_backend_process
            sleep 1
            start_backend_background
            return
        fi

        stop_tracked_processes
    
    sleep 1
    
    # Start Django in background
    print_status "Starting webClerk3 (Django)..."
    cd "$WC3_DIR"
    source bin/activate 2>/dev/null || source venv312/bin/activate 2>/dev/null || true
    python manage.py runserver &
    WC3_PID=$!
    write_pid_file "$DJANGO_PID_FILE" "$WC3_PID"
    
    sleep 2
    
    # Start Vite in background
    print_status "Starting React2025 (Vite)..."
    cd "$R25_DIR"
    npm run dev &
    R25_PID=$!
    write_pid_file "$VITE_PID_FILE" "$R25_PID"
    
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

capture_frontend_state

CURRENT_MODE=$(get_current_mode)

# Update configuration files
update_env_file "$WC3_DIR/.env" "$MODE"
update_dev_config "$MODE"

print_status "Configuration updated!"
echo ""

if [ "$MODE" = "local" ]; then
    SHOULD_SYNC=0
    if [ "$CURRENT_MODE" != "local" ]; then
        SHOULD_SYNC=1
    fi
    if [ "${FORCE_LOCAL_SYNC:-0}" = "1" ]; then
        SHOULD_SYNC=1
    fi
    if [ "${SKIP_LOCAL_SYNC:-0}" = "1" ]; then
        SHOULD_SYNC=0
    fi

    if [ "$SHOULD_SYNC" = "1" ]; then
        if ! sync_remote_to_local; then
            # Revert config back to previous mode when force-sync fails.
            update_env_file "$WC3_DIR/.env" "$CURRENT_MODE"
            update_dev_config "$CURRENT_MODE"
            exit 1
        fi
    else
        print_status "Skipping remote→local sync (already in local mode)."
    fi

    echo ""
fi

if [ "$MODE" = "remote" ]; then
    print_status "Remote mode selected. No local→remote data sync is performed."

    echo ""
fi

# Ask about restarting servers (can be skipped for same-console workflow)
if [ "${SKIP_RESTART:-0}" = "1" ]; then
    if [ "${REQUEST_CONSOLE_RESTART:-0}" = "1" ]; then
        request_same_console_django_restart
    else
        print_warning "Restart skipped by flag. Restart Django/Vite manually in your own terminal(s)."
    fi
elif [ "${SWITCH_HEADLESS:-0}" = "1" ]; then
    restart_servers
else
    read -p "Restart servers now? [Y/n] " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        restart_servers
    else
        print_warning "Remember to restart servers manually for changes to take effect."
    fi
fi

ensure_frontend_alive_if_needed
schedule_frontend_watchdog

echo -e "${GREEN}Done!${NC}"
echo ""
