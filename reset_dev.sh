#!/usr/bin/env bash
set -euo pipefail
"$(cd "$(dirname "$0")" && pwd)"/Scripts/rebaseline.sh "$@"

