import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
targets = list((ROOT / "apps" / "docs" / "tests").rglob("test_*.py"))

replacements = [
    # linkage
    (re.compile(r"reverse\(\s*['\"]linkage-list['\"]\s*\)"), "'/linkage/'"),
    (re.compile(r"reverse\(\s*['\"]linkage-detail['\"]\s*,\s*args=\[\s*(\w+)\s*\]\s*\)"), r"f'/linkage/{\1}/'"),
    (re.compile(r"reverse\(\s*['\"]linkage-detail['\"]\s*,\s*kwargs=\{\s*['\"]pk['\"]\s*:\s*(\w+)\s*\}\s*\)"), r"f'/linkage/{\1}/'"),
    # document
    (re.compile(r"reverse\(\s*['\"]document-list['\"]\s*\)"), "'/document/'"),
    (re.compile(r"reverse\(\s*['\"]document-detail['\"]\s*,\s*args=\[\s*(\w+)\s*\]\s*\)"), r"f'/document/{\1}/'"),
    (re.compile(r"reverse\(\s*['\"]document-detail['\"]\s*,\s*kwargs=\{\s*['\"]pk['\"]\s*:\s*(\w+)\s*\}\s*\)"), r"f'/document/{\1}/'"),
]

def rewrite(p: Path):
    s = p.read_text()
    orig = s
    for rx, repl in replacements:
        s = rx.sub(repl, s)
    if s != orig:
        p.write_text(s)
        return True
    return False

def main():
    changed = sum(rewrite(p) for p in targets)
    print(f"Rewrote {changed} docs test files")

if __name__ == "__main__":
    main()