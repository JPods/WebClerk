from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def rewrite(path: Path) -> bool:
    src = path.read_text(encoding="utf-8")
    if "from django.contrib.auth.models import User" not in src:
        return False

    lines = src.splitlines()
    out = []
    injected_assignment = False
    for i, line in enumerate(lines):
        if line.strip().startswith("from django.contrib.auth.models import User"):
            # Replace import with get_user_model alias
            out.append("from django.contrib.auth import get_user_model as _dj_get_user_model")
            # We’ll add User = get_user_model() right here
            out.append("User = _dj_get_user_model()")
            injected_assignment = True
            continue
        out.append(line)

    # If file already had get_user_model import under another name, we still rely on our alias above.
    new = "\n".join(out)
    if new != src:
        path.write_text(new, encoding="utf-8")
        return True
    return False

def main() -> int:
    changed = 0
    targets = []
    # Limit to repo tests folders (top-level tests/ and apps/*/tests/)
    for pat in ("tests", "apps"):
        p = ROOT / pat
        if not p.exists():
            continue
        for file in p.rglob("*.py"):
            # Only test modules
            if "tests" not in file.parts:
                continue
            if rewrite(file):
                changed += 1
                targets.append(str(file.relative_to(ROOT)))
    print(f"Patched {changed} files.")
    for t in targets:
        print(f"  - {t}")
    return 0

if __name__ == "__main__":
    sys.exit(main())