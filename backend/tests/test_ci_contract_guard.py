import os
import re
from pathlib import Path

# Simple hygiene/contract guard.
# Fails fast if absolute user paths or legacy header markers reappear.
# Extendable for future envelope smoke calls.

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_PATTERNS = [
    re.compile(r"/Users/"),
    re.compile(r"^#\s*filepath:", re.MULTILINE),
]

ALLOWLIST_DIR_NAMES = {
    'bin', 'lib', 'include', 'Scripts', '__pycache__', '.hypothesis', '.git',
    'logs',         # log files contain runtime absolute paths
    '.claude',      # Claude Code local settings
    'readmes',      # documentation legitimately references /Users/ paths as examples
    'git_bypass',   # local-only editor config notes
    'archive',      # archived code not in active use
    'junkdrawer',   # notes and scratch files
}

SKIP_EXTENSIONS = {
    '.pyc', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.db', '.sqlite3', '.rdb',
    '.log', '.txt', '.yml', '.yaml',
}

SKIP_FILE_NAMES = {
    'dump.rdb',
    'README_INPROCESS.md',  # documentation can mention /Users/ illustratively
    'test_ci_contract_guard.py',  # don't scan self to avoid false positives
    'pyvenv.cfg',  # virtualenv metadata contains absolute paths
    '.coverage',   # coverage data contains absolute paths
    'django.yml',  # CI config with example paths
    # Standalone utility scripts with local default paths (not deployed code)
    'convert_price_tiers.py',
    'check_inventory.py',
    'fetch_order.py',
    # Management commands use local defaults for dev convenience — not production paths
    'seed_jpods_demo.py',
    'code_standards.py',
    'index_docs.py',
    'alice_deliberate.py',
    'dedup.py',
    'load_qa.py',
    'load_bom.py',
    'export_data.py',
    'restore_data.py',
    'restore_data_smart.py',
}

def iter_text_files():
    for path in ROOT.rglob('*'):
        if not path.is_file():
            continue
        name = path.name
        if name in SKIP_FILE_NAMES:
            continue
        if path.suffix in SKIP_EXTENSIONS:
            continue
        # Skip virtualenv / dependency directories / non-source dirs
        if any(part in ALLOWLIST_DIR_NAMES for part in path.parts if part != ''):
            continue
        # Only scan reasonably sized text files (< 500KB)
        try:
            if path.stat().st_size > 500_000:
                continue
            text = path.read_text(errors='ignore')
        except Exception:
            continue
        yield path, text


def test_no_forbidden_path_markers():
    violations = []
    for path, text in iter_text_files():
        for pat in FORBIDDEN_PATTERNS:
            if pat.search(text):
                violations.append(f"Pattern '{pat.pattern}' found in {path.relative_to(ROOT)}")
    if violations:
        msg = "\n".join(violations[:50])  # cap output
        raise AssertionError(f"Forbidden path/header markers detected (showing up to 50):\n{msg}")


def test_readme_s_deprecation():
    legacy_dir = ROOT / 'README_s'
    if legacy_dir.exists():
        # Allow only placeholder files (<= 25 lines each)
        offenders = []
        for f in legacy_dir.glob('README*.md'):
            try:
                lines = f.read_text().strip().splitlines()
            except Exception:
                continue
            if len(lines) > 25:
                offenders.append(f"{f.name} has {len(lines)} lines (expected placeholder <=25)")
        if offenders:
            raise AssertionError("Deprecated README_s/ contains non-placeholder files after consolidation:\n" + "\n".join(offenders))

# Placeholder for future dynamic envelope smoke tests.
# def test_envelope_smoke():
#     from django.test import Client
#     c = Client()
#     for url in ['/wcapi/modelinfo/', '/wcapi/get/']:
#         resp = c.get(url)
#         if resp.status_code == 200:
#             body = resp.json()
#             for key in ['status','code','message','data','error']:
#                 assert key in body, f"Missing '{key}' in envelope for {url}"
