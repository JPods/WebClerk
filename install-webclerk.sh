#!/bin/bash
# install-webclerk.sh — Install WebClerk3 on Mac or Linux
#
# Usage:
#   curl -sL webclerk.com/download/install-webclerk.sh | bash
#   or
#   git clone https://github.com/JPods/webClerk3.git && cd webClerk3 && bash install-webclerk.sh
#
# What it does:
#   1. Checks for Python 3.11+, PostgreSQL, Redis, Node.js
#   2. Installs missing dependencies via Homebrew (Mac) or apt (Linux)
#   3. Creates PostgreSQL database
#   4. Creates Python venv, installs requirements
#   5. Builds React frontend
#   6. Copies .env from template
#   7. Runs first-run entrypoint (migrate, seed, optional demo data)
#   8. Writes run-webclerk.sh convenience script
#
# The result: a working WebClerk3 at http://localhost:8000
set -e

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║         WebClerk3 Installer              ║"
echo "║   Open Source Commerce — Desktop First   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

WC3_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WC3_DIR"

OS="$(uname -s)"
ERRORS=()

# ── Colors ──────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; ERRORS+=("$1"); }

# ── Step 1: Check dependencies ──────────────────────────────────
echo "Checking dependencies..."

# Python
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
        ok "Python $PY_VER"
    else
        fail "Python $PY_VER found — need 3.11+"
    fi
else
    fail "Python 3 not found"
fi

# PostgreSQL
if command -v psql &>/dev/null; then
    PG_VER=$(psql --version | head -1)
    ok "$PG_VER"
else
    fail "PostgreSQL not found"
fi

# Check PostgreSQL is running
if pg_isready &>/dev/null; then
    ok "PostgreSQL is running"
else
    fail "PostgreSQL is not running"
fi

# Redis
if command -v redis-cli &>/dev/null; then
    ok "Redis installed"
else
    warn "Redis not found — Celery background tasks won't work"
    warn "Install later: brew install redis (Mac) or apt install redis-server (Linux)"
fi

# Node.js (for React build)
if command -v node &>/dev/null; then
    NODE_VER=$(node --version)
    ok "Node.js $NODE_VER"
else
    fail "Node.js not found — needed to build frontend"
fi

# ── Offer to install missing deps ───────────────────────────────
if [ ${#ERRORS[@]} -gt 0 ]; then
    echo ""
    echo "Missing dependencies:"
    for e in "${ERRORS[@]}"; do
        echo "  - $e"
    done

    if [ "$OS" = "Darwin" ] && command -v brew &>/dev/null; then
        echo ""
        read -p "Install missing dependencies via Homebrew? [y/N] " INSTALL
        if [[ "$INSTALL" =~ ^[Yy] ]]; then
            command -v python3 &>/dev/null || brew install python@3.13
            command -v psql &>/dev/null    || brew install postgresql@16
            command -v node &>/dev/null    || brew install node
            pg_isready &>/dev/null         || brew services start postgresql@16
            echo ""
            ok "Dependencies installed"
        else
            echo "Install the missing dependencies and run this script again."
            exit 1
        fi
    elif [ "$OS" = "Linux" ]; then
        echo ""
        read -p "Install missing dependencies via apt? [y/N] " INSTALL
        if [[ "$INSTALL" =~ ^[Yy] ]]; then
            sudo apt update
            command -v python3 &>/dev/null || sudo apt install -y python3 python3-venv python3-pip
            command -v psql &>/dev/null    || sudo apt install -y postgresql postgresql-contrib
            command -v node &>/dev/null    || sudo apt install -y nodejs npm
            sudo systemctl start postgresql 2>/dev/null || true
            echo ""
            ok "Dependencies installed"
        else
            echo "Install the missing dependencies and run this script again."
            exit 1
        fi
    else
        echo ""
        echo "Please install the missing dependencies and run this script again."
        exit 1
    fi
fi

# ── Step 2: Create database ─────────────────────────────────────
echo ""
echo "Setting up database..."

DB_NAME="commerce_expert"
DB_USER="$(whoami)"

if psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    ok "Database '$DB_NAME' exists"
else
    createdb "$DB_NAME" 2>/dev/null && ok "Created database '$DB_NAME'" || {
        # Try as postgres user
        sudo -u postgres createdb -O "$DB_USER" "$DB_NAME" 2>/dev/null && ok "Created database '$DB_NAME'" || {
            fail "Could not create database '$DB_NAME'"
            echo "Create it manually: createdb $DB_NAME"
            exit 1
        }
    }
fi

# ── Step 3: Python venv ─────────────────────────────────────────
echo ""
echo "Setting up Python environment..."

if [ ! -d "$WC3_DIR/venv" ]; then
    python3 -m venv "$WC3_DIR/venv"
    ok "Created venv"
else
    ok "venv exists"
fi

"$WC3_DIR/venv/bin/pip" install --upgrade pip -q
"$WC3_DIR/venv/bin/pip" install -r "$WC3_DIR/requirements.txt" -q
ok "Python dependencies installed"

# ── Step 4: React frontend ──────────────────────────────────────
echo ""
echo "Building frontend..."

R25_DIR=""
if [ -d "$WC3_DIR/../React2025" ]; then
    R25_DIR="$WC3_DIR/../React2025"
elif [ -d "$WC3_DIR/React2025" ]; then
    R25_DIR="$WC3_DIR/React2025"
fi

if [ -n "$R25_DIR" ]; then
    cd "$R25_DIR"
    npm install --silent 2>/dev/null
    npm run build 2>/dev/null
    ok "React frontend built"
    cd "$WC3_DIR"
else
    warn "React2025 not found — frontend not built"
    warn "Clone it: git clone https://github.com/JPods/React2025.git ../React2025"
fi

# ── Step 5: Environment file ────────────────────────────────────
echo ""
echo "Configuring environment..."

if [ ! -f "$WC3_DIR/.env" ]; then
    cp "$WC3_DIR/.env.template" "$WC3_DIR/.env"
    # Set DB user to current user
    if [ "$OS" = "Darwin" ]; then
        sed -i '' "s/LOCAL_DATABASE_USER=postgres/LOCAL_DATABASE_USER=$DB_USER/" "$WC3_DIR/.env"
        sed -i '' "s/LOCAL_DATABASE_PASS=/LOCAL_DATABASE_PASS=/" "$WC3_DIR/.env"
    else
        sed -i "s/LOCAL_DATABASE_USER=postgres/LOCAL_DATABASE_USER=$DB_USER/" "$WC3_DIR/.env"
    fi
    ok "Created .env from template"
else
    ok ".env exists"
fi

# ── Step 6: First-run setup ─────────────────────────────────────
echo ""
echo "Running first-time setup..."

export LOAD_DEMO_DATA=1
bash "$WC3_DIR/tools/webclerk-entrypoint.sh" echo "setup complete"

# ── Step 7: Collect static files ────────────────────────────────
"$WC3_DIR/venv/bin/python" manage.py collectstatic --no-input -q 2>/dev/null || true
ok "Static files collected"

# ── Step 8: Write run script ────────────────────────────────────
cat > "$WC3_DIR/run-webclerk.sh" << 'RUNEOF'
#!/bin/bash
# Start WebClerk3
cd "$(dirname "${BASH_SOURCE[0]}")"
echo "Starting WebClerk3 at http://localhost:8000"
echo "Press Ctrl+C to stop."
./venv/bin/python manage.py runserver 0.0.0.0:8000
RUNEOF
chmod +x "$WC3_DIR/run-webclerk.sh"

# ── Done ────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║       WebClerk3 installed!               ║"
echo "╠══════════════════════════════════════════╣"
echo "║                                          ║"
echo "║  Start:  ./run-webclerk.sh               ║"
echo "║  Open:   http://localhost:8000            ║"
echo "║                                          ║"
echo "║  Demo data included. Remove it anytime:  ║"
echo "║  ./venv/bin/python manage.py              ║"
echo "║      remove_demo_data                    ║"
echo "║                                          ║"
echo "╚══════════════════════════════════════════╝"
echo ""
