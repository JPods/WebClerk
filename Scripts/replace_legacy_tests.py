import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_DIRS = [
    ROOT / "tests",
    ROOT / "apps",
]

REPLACERS = [
    # tx/ prefix to root model routes (GET cases)
    (re.compile(r"['\"]/tx/([a-z0-9_]+)/(\d+)/?['\"]"), r"'/\1/\2/'"),
    (re.compile(r"['\"]/tx/([a-z0-9_]+)/?['\"]"), r"'/\1/'"),
    # wcapi get/query/save/delete old paths with tx/
    (re.compile(r"['\"]/tx/wcapi/save/?['\"]"), r"'/wcapi/save'"),
    (re.compile(r"['\"]/tx/wcapi/query/?['\"]"), r"'/wcapi/query'"),
    (re.compile(r"['\"]/tx/wcapi/delete/?['\"]"), r"'/wcapi/delete'"),
    # table_name -> model in payloads and queries
    (re.compile(r'"table_name"\s*:'), r'"model":'),
    # dotted model in payloads -> remove (assume canonical key used elsewhere)
    # reverse('namespace:name...') -> leave to manual if complex; common patterns below:
    (re.compile(r"reverse\(['\"][a-z0-9_]+:[a-z0-9_-]+['\"].*?\)"), r"'/domain/'"),  # safe default; adjust per-test if needed
]

def should_rewrite(path: Path) -> bool:
    if not path.is_file():
        return False
    if not path.suffix in ('.py',):
        return False
    # Only test files
    return "tests" in path.parts and path.name.startswith("test_")

def rewrite_file(path: Path) -> bool:
    original = text = path.read_text()
    for rx, repl in REPLACERS:
        text = rx.sub(repl, text)
    if text != original:
        path.write_text(text)
        return True
    return False

def main():
    changed = 0
    for base in TEST_DIRS:
        if not base.exists():
            continue
        for p in base.rglob("test_*.py"):
            if should_rewrite(p):
                if rewrite_file(p):
                    changed += 1
    print(f"Rewrote {changed} test files")

if __name__ == "__main__":
    main()