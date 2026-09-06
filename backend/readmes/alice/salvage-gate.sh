#!/bin/bash
# salvage-gate.sh — Friction script for archived codebases on 5TB
#
# Place this at the root of any archived project directory.
# Running it acknowledges "just for salvage" before opening the folder.
#
# Usage: bash /Volumes/2022-5T/archive/CommerceExpert/salvage-gate.sh
#
# Why this exists: CommerceExpert was the source of scars #70 and #81.
# Claude Code, Bill, and team members repeatedly edited the wrong codebase
# because it lived next to the active WebClerk project. It was moved to
# 5TB on 2026-09-04 to eliminate that trap. This gate ensures anyone
# accessing it knows they are touching dead code.

ARCHIVE_DIR="$(cd "$(dirname "$0")" && pwd)"
ARCHIVE_NAME="$(basename "$ARCHIVE_DIR")"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG_FILE="$ARCHIVE_DIR/.salvage-access.log"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ARCHIVED CODEBASE: $ARCHIVE_NAME"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "  This project was archived on 2026-09-04."
echo "  The active codebase is: ~/Documents/WebClerk/"
echo ""
echo "  Scars #70 and #81: editing the wrong codebase."
echo "  Do not copy files back. Salvage data only."
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""
read -p "  Type 'just for salvage' to continue: " RESPONSE

if [ "$RESPONSE" = "just for salvage" ]; then
    echo "$TIMESTAMP — accessed by $(whoami) — acknowledged salvage-only" >> "$LOG_FILE"
    echo ""
    echo "  Access granted. Opening $ARCHIVE_DIR"
    echo "  Remember: ~/Documents/WebClerk/ is the active project."
    echo ""
    open "$ARCHIVE_DIR"
else
    echo ""
    echo "  Access denied. Use ~/Documents/WebClerk/ instead."
    echo ""
    exit 1
fi
