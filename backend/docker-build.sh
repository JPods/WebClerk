#!/bin/bash
# Build WebClerk3 Docker image — handles React2025 as separate repo
set -e

WC3_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
R25_DIR="$WC3_DIR/../React2025"

# Step 1: Build React frontend
if [ -d "$R25_DIR" ]; then
    echo "Building React frontend..."
    cd "$R25_DIR"
    npm install --silent 2>/dev/null
    npm run build
    mkdir -p "$WC3_DIR/media/static"
    cp -r dist/* "$WC3_DIR/media/static/"
    echo "Frontend built and copied."
    cd "$WC3_DIR"
else
    echo "Warning: React2025 not found at $R25_DIR"
    echo "Clone it: git clone https://github.com/JPods/React2025.git $R25_DIR"
    echo "Continuing without frontend..."
fi

# Step 2: Build Docker image
echo "Building Docker image..."
docker compose build

echo ""
echo "Done. Start with: docker compose up"
