#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# setup_ai.sh — One-command setup for the CommerceExpert AI Assistant
#
# Usage:
#   ./tools/setup_ai.sh           # full setup
#   ./tools/setup_ai.sh --check   # check prerequisites only
#   ./tools/setup_ai.sh --index   # re-index docs only
#   ./tools/setup_ai.sh --hooks   # install git hooks for auto-reindex
# ──────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OLLAMA_MODEL="${OLLAMA_MODEL:-deepseek-r1:8b}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERR]${NC}  $*"; }

# ── Check prerequisites ──────────────────────────────────────────

check_prereqs() {
    local ok=true

    echo ""
    echo "═══════════════════════════════════════════"
    echo "  AI Assistant — Prerequisite Check"
    echo "═══════════════════════════════════════════"
    echo ""

    # Python
    if command -v python3 &>/dev/null; then
        success "Python: $(python3 --version)"
    else
        error "Python 3 not found"
        ok=false
    fi

    # Ollama
    if command -v ollama &>/dev/null; then
        success "Ollama: $(ollama --version 2>/dev/null || echo 'installed')"
    else
        error "Ollama not installed"
        echo "       Install: https://ollama.ai or 'brew install ollama'"
        ok=false
    fi

    # Ollama running?
    if curl -s http://localhost:11434/api/tags &>/dev/null; then
        success "Ollama server: running"
        # Check for model
        if curl -s http://localhost:11434/api/tags | python3 -c "
import sys, json
models = [m['name'] for m in json.load(sys.stdin).get('models', [])]
if any('$OLLAMA_MODEL' in m for m in models):
    print('found')
else:
    sys.exit(1)
" &>/dev/null; then
            success "Model '$OLLAMA_MODEL': available"
        else
            warn "Model '$OLLAMA_MODEL': not pulled yet"
        fi
    else
        warn "Ollama server: not running (start with 'ollama serve')"
    fi

    # Django setup
    if [[ -f "$PROJECT_DIR/manage.py" ]]; then
        success "Django project: found"
    else
        error "Django project not found at $PROJECT_DIR"
        ok=false
    fi

    # Python packages
    cd "$PROJECT_DIR"
    for pkg in chromadb sentence_transformers httpx; do
        if python3 -c "import $pkg" 2>/dev/null; then
            success "Package '$pkg': installed"
        else
            warn "Package '$pkg': not installed"
        fi
    done

    echo ""
    if $ok; then
        success "All critical prerequisites met!"
    else
        error "Some prerequisites missing — see above"
    fi
}

# ── Install dependencies ─────────────────────────────────────────

install_deps() {
    info "Installing Python packages..."
    cd "$PROJECT_DIR"

    if [[ -f "bin/activate" ]]; then
        source bin/activate
    elif [[ -f "venv312/bin/activate" ]]; then
        source venv312/bin/activate
    fi

    pip install -q chromadb sentence-transformers httpx
    success "Python packages installed"
}

# ── Install & pull Ollama model ──────────────────────────────────

setup_ollama() {
    # Install Ollama if not present
    if ! command -v ollama &>/dev/null; then
        info "Installing Ollama..."
        if [[ "$(uname)" == "Darwin" ]]; then
            brew install ollama 2>/dev/null || {
                error "Couldn't install Ollama via brew. Install manually: https://ollama.ai"
                return 1
            }
        else
            curl -fsSL https://ollama.ai/install.sh | sh
        fi
        success "Ollama installed"
    fi

    # Start Ollama if not running
    if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
        info "Starting Ollama server..."
        ollama serve &>/dev/null &
        sleep 3
        if curl -s http://localhost:11434/api/tags &>/dev/null; then
            success "Ollama server started"
        else
            warn "Ollama may need a moment to start. Check 'ollama serve' manually."
        fi
    fi

    # Pull the model
    info "Pulling model '$OLLAMA_MODEL' (this may take a while on first run)..."
    ollama pull "$OLLAMA_MODEL"
    success "Model '$OLLAMA_MODEL' ready"
}

# ── Django setup ─────────────────────────────────────────────────

setup_django() {
    cd "$PROJECT_DIR"
    if [[ -f "bin/activate" ]]; then
        source bin/activate
    elif [[ -f "venv312/bin/activate" ]]; then
        source venv312/bin/activate
    fi

    info "Running Django migrations..."
    python manage.py migrate ai_assistant
    success "Migrations applied"

    info "Indexing documentation..."
    python manage.py index_docs
    success "Documentation indexed"

    info "Running health check..."
    python manage.py ai_health
}

# ── Main ─────────────────────────────────────────────────────────

install_hooks() {
    info "Installing git hooks for auto-reindex..."
    local hooks_src="$SCRIPT_DIR/hooks"
    local hooks_dst

    # wc3 repo
    if [[ -d "$PROJECT_DIR/.git/hooks" ]]; then
        hooks_dst="$PROJECT_DIR/.git/hooks"
        if [[ -f "$hooks_src/post-commit" ]]; then
            cp "$hooks_src/post-commit" "$hooks_dst/post-commit"
            chmod +x "$hooks_dst/post-commit"
            success "Installed post-commit hook for wc3"
        fi
    fi

    # r25 repo
    local r25_dir="$(dirname "$PROJECT_DIR")/React2025"
    if [[ -d "$r25_dir/.git/hooks" ]]; then
        hooks_dst="$r25_dir/.git/hooks"
        if [[ -f "$hooks_src/post-commit" ]]; then
            cp "$hooks_src/post-commit" "$hooks_dst/post-commit"
            chmod +x "$hooks_dst/post-commit"
            success "Installed post-commit hook for r25"
        fi
    fi

    success "Git hooks installed — docs auto-reindex on commit"
}

case "${1:-full}" in
    --check|-c)
        check_prereqs
        ;;
    --index|-i)
        cd "$PROJECT_DIR"
        if [[ -f "bin/activate" ]]; then source bin/activate; fi
        python manage.py index_docs "$@"
        ;;
    --reset)
        cd "$PROJECT_DIR"
        if [[ -f "bin/activate" ]]; then source bin/activate; fi
        python manage.py index_docs --reset
        ;;
    --hooks)
        install_hooks
        ;;
    full|--full)
        echo ""
        echo "═══════════════════════════════════════════"
        echo "  CommerceExpert AI Assistant Setup"
        echo "═══════════════════════════════════════════"
        echo ""
        check_prereqs
        echo ""
        install_deps
        setup_ollama
        setup_django
        install_hooks
        echo ""
        echo "═══════════════════════════════════════════"
        success "AI Assistant setup complete!"
        echo ""
        echo "  Modes available:"
        echo "    general      — Conversational help"
        echo "    developer    — Code-aware with file paths & conventions"
        echo "    debugger     — Error analysis & fix suggestions"
        echo "    user_support — Plain-language help for end users"
        echo "    code_review  — Convention compliance review"
        echo "    test_writer  — Generate tests with project patterns"
        echo ""
        echo "  Try it:"
        echo "    curl -X POST http://localhost:8000/wcapi/ai/ask/ \\"
        echo "      -H 'Content-Type: application/json' \\"
        echo "      -H 'Authorization: Bearer <your-token>' \\"
        echo "      -d '{\"question\": \"How do I create an order?\", \"mode\": \"developer\"}'"
        echo ""
        echo "  New endpoints:"
        echo "    POST /wcapi/ai/debug/    — paste a traceback for diagnosis"
        echo "    POST /wcapi/ai/review/   — submit code for review"
        echo "    POST /wcapi/ai/generate/ — generate code or tests"
        echo "    GET  /wcapi/ai/modes/    — list available modes"
        echo "    POST /wcapi/ai/reindex/  — trigger reindex (staff only)"
        echo ""
        echo "═══════════════════════════════════════════"
        ;;
    *)
        echo "Usage: $0 [--check|--index|--reset|--hooks|--full]"
        exit 1
        ;;
esac
