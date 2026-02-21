#!/usr/bin/env bash
# tools/check_renamed_models.sh
# ------------------------------------------------------------------
# Guard against reintroduction of legacy model names that were
# renamed during the Feb 2026 cleanup:
#   SalesOrder  → Order
#   PurchaseOrder → Purchase
#   Location (comm model) → Address
#
# Run:  bash tools/check_renamed_models.sh
# Exit: 0 = clean, 1 = violations found
#
# See readmes/model-rename-guard.md for full context.
# ------------------------------------------------------------------

set -eo pipefail

WC3_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
R25_ROOT="$(cd "$WC3_ROOT/../React2025" 2>/dev/null && pwd)" || R25_ROOT=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

VIOLATIONS=0

# ── helpers ────────────────────────────────────────────────────────

scan() {
    local label="$1"
    local pattern="$2"
    local root="$3"
    shift 3
    local extra_excludes=("$@")

    local exclude_args=(
        --exclude-dir=__pycache__
        --exclude-dir=node_modules
        --exclude-dir=.git
        --exclude-dir=venv
        --exclude-dir=venv312
        --exclude-dir=lib
        --exclude-dir=bin
        --exclude-dir=include
        --exclude-dir=.hypothesis
        --exclude-dir=media
        --exclude-dir=static
        --exclude-dir=uploads
        --exclude-dir=logs
        --exclude-dir=dist
        --exclude-dir=build
        --exclude='*.pyc'
        --exclude='*.min.js'
        --exclude='*.min.css'
        --exclude='package-lock.json'
        --exclude='yarn.lock'
    )

    for ex in "${extra_excludes[@]}"; do
        exclude_args+=(--exclude-dir="$ex")
    done

    local hits
    hits=$(grep -rn \
        "${exclude_args[@]}" \
        --include='*.py' \
        --include='*.ts' \
        --include='*.tsx' \
        --include='*.md' \
        --include='*.json' \
        --include='*.js' \
        -E "$pattern" "$root" 2>/dev/null \
        | grep -v 'migration' \
        | grep -v '_archive/session-notes/' \
        | grep -v 'model-rename-guard.md' \
        | grep -v 'check_renamed_models.sh' \
        | grep -v 'db_table' \
        | grep -v 'full_location' \
        | grep -v '_compute_display_location' \
        | grep -v 'OpenApiParameter' \
        | grep -v 'location\.state' \
        | grep -v 'location\.pathname' \
        | grep -v 'location\.href' \
        | grep -v 'useLocation' \
        | grep -v 'window\.location' \
        | grep -v 'Warehouse.*location' \
        | grep -v 'warehouse.*location' \
        | grep -v 'aisle.*location\|shelf.*location\|bin.*location' \
        | grep -v 'location.*aisle\|location.*shelf\|location.*bin' \
        | grep -v 'site.location\|geo.location\|Geolocation\|geolocation' \
        | grep -v 'Sub-account/Location' \
        | grep -v 'inventory.*location\|location.*inventory' \
        | grep -v 'File Location\|file location\|Documentation Location\|Output location' \
        | grep -v 'DOCUMENTS LOCATION\|Document.*Location' \
        | grep -v 'location\.ts:' \
        | grep -v 'allocation\|Allocation' \
        | grep -v 'package-lock\.json\|yarn\.lock' \
        | grep -v '(not .*)' \
        | grep -v 'not .*salesOrder\|not .*purchaseOrder\|not .*sales_order\|not .*purchase_order' \
        | grep -v 'compare_lines\.py' \
        || true)

    if [[ -n "$hits" ]]; then
        echo -e "${RED}✗ $label${NC}"
        echo "$hits" | head -20
        local count
        count=$(echo "$hits" | wc -l | tr -d ' ')
        if (( count > 20 )); then
            echo "  ... and $((count - 20)) more"
        fi
        echo ""
        VIOLATIONS=$((VIOLATIONS + 1))
    else
        echo -e "${GREEN}✓ $label${NC}"
    fi
}

# ── checks ─────────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Model Rename Guard — checking for regressions"
echo "═══════════════════════════════════════════════════"
echo ""

# --- SalesOrder / sales_order ---

echo -e "${YELLOW}── SalesOrder → Order ──${NC}"

scan "No 'sales_order' model key in wc3" \
    "'sales_order'|\"sales_order\"" \
    "$WC3_ROOT"

scan "No SalesOrder class reference in wc3" \
    '\bSalesOrder\b' \
    "$WC3_ROOT"

if [[ -n "$R25_ROOT" ]]; then
    scan "No 'sales_order' model key in R25" \
        "'sales_order'|\"sales_order\"|salesOrder" \
        "$R25_ROOT"

    scan "No SalesOrder class reference in R25" \
        '\bSalesOrder\b' \
        "$R25_ROOT"
fi

# --- PurchaseOrder / purchase_order ---

echo ""
echo -e "${YELLOW}── PurchaseOrder → Purchase ──${NC}"

scan "No 'purchase_order' model key in wc3" \
    "'purchase_order'|\"purchase_order\"" \
    "$WC3_ROOT"

scan "No PurchaseOrder class reference in wc3" \
    '\bPurchaseOrder\b' \
    "$WC3_ROOT"

if [[ -n "$R25_ROOT" ]]; then
    scan "No 'purchase_order' model key in R25" \
        "'purchase_order'|\"purchase_order\"|purchaseOrder" \
        "$R25_ROOT"

    scan "No PurchaseOrder class reference in R25" \
        '\bPurchaseOrder\b' \
        "$R25_ROOT"
fi

# --- Location → Address (comm model only) ---

echo ""
echo -e "${YELLOW}── Location → Address (comm model) ──${NC}"

scan "No Location=Address alias in wc3" \
    'Location\s*=\s*Address|from.*models.*import.*Location' \
    "$WC3_ROOT"

scan "No location_verification connection type in wc3" \
    'location_verification|validate_location_osm|verify_location_via_connection' \
    "$WC3_ROOT"

scan "No 'location' model key in resolver/registry/settings" \
    "'location'\s*:" \
    "$WC3_ROOT"

if [[ -n "$R25_ROOT" ]]; then
    scan "No location model key in R25 api layer" \
        "location.*:.*['\"]address['\"]|'communications/location'" \
        "$R25_ROOT/src/api"
fi

# ── summary ────────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════════"
if (( VIOLATIONS > 0 )); then
    echo -e "  ${RED}FAILED: $VIOLATIONS violation(s) found${NC}"
    echo "  Fix the above before merging."
else
    echo -e "  ${GREEN}PASSED: No rename regressions detected${NC}"
fi
echo "═══════════════════════════════════════════════════"
echo ""

exit $((VIOLATIONS > 0 ? 1 : 0))
