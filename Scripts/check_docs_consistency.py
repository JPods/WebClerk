#!/usr/bin/env python3
"""Fail CI if docs index or TOCs are stale.

Process:
1. Snapshot current docs_index.json content (if exists)
2. Run gen_docs_index.py (import module) and re-read output
3. If changed -> print diff summary and exit non-zero
4. Run gen_readmes_toc.py then git diff readmes/*.md; if any changes -> fail

Intended for CI workflow job.
"""
from __future__ import annotations
import json, subprocess, sys, difflib, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC_INDEX = ROOT / 'docs_index.json'


def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        sys.exit(r.returncode)
    return r.stdout


def main():
    orig_index = DOC_INDEX.read_text(encoding='utf-8') if DOC_INDEX.exists() else ''
    # Rebuild index
    run([sys.executable, 'Scripts/gen_docs_index.py'])
    new_index = DOC_INDEX.read_text(encoding='utf-8') if DOC_INDEX.exists() else ''
    if orig_index != new_index:
        print('ERROR: docs_index.json is stale. Run: python Scripts/gen_docs_index.py')
        for line in difflib.unified_diff(orig_index.splitlines(), new_index.splitlines(), fromfile='before/docs_index.json', tofile='after/docs_index.json', lineterm=''):
            print(line)
        stale_index = True
    else:
        stale_index = False

    # Rebuild TOCs
    # Get git status before
    before = run(['git', 'diff', '--name-only', 'readmes'])
    run([sys.executable, 'Scripts/gen_readmes_toc.py'])
    after_diff = run(['git', 'diff', '--name-only', 'readmes'])
    toc_changed = bool(after_diff.strip())
    if toc_changed:
        print('ERROR: One or more readmes missing updated TOC. Run: python Scripts/gen_readmes_toc.py')
        print(after_diff)

    if stale_index or toc_changed:
        sys.exit(1)
    print('Docs consistency check passed.')

if __name__ == '__main__':
    main()
