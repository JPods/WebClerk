#!/bin/bash
# Commit tracked changes and push.
# Deliberately NOT `git add .` — that is how data dumps and credentials got
# committed (2026-09-15 incident). New files must be added by name:
#     git add path/to/new_file && ./push.sh "message"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <commit message>"
    exit 1
fi

# Stage modifications/deletions of already-tracked files only
git add -u

# Refuse to commit anything that looks like data or credentials
BLOCKED=$(git diff --cached --name-only | grep -Ei '(^|/)(\.env($|\.)|save_env|backups?/|statements?/|conversions/)|\.(dump|sql\.gz|sqlite3|pem|key)$|_full_|_backup_')
if [ -n "$BLOCKED" ]; then
    echo "Refusing to commit files that look like data or credentials:"
    echo "$BLOCKED"
    exit 1
fi

# Secret scan when gitleaks is installed
if command -v gitleaks >/dev/null 2>&1; then
    gitleaks git --staged --no-banner --redact || { echo "gitleaks found secrets — commit aborted"; exit 1; }
fi

git commit -m "$1" && git push
