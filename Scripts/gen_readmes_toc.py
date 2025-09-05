#!/usr/bin/env python3
"""Generate or update Table of Contents blocks for all markdown files in readmes/.

Rules:
- Inserts/updates between markers: <!-- TOC START --> and <!-- TOC END -->
- Placed immediately after the first top-level heading (# ...) if present, else at file top.
- Includes heading levels 1..4 (H1-H4). Skips the TOC markers themselves.
- Skips files starting with '_' (templates) and non .md endings.
- Safe id slugs approximating GitHub algorithm (lowercase, spaces->-, strip invalid chars).
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
READMES = ROOT / "readmes"
TOC_START = "<!-- TOC START -->"
TOC_END = "<!-- TOC END -->"
MAX_DEPTH = 4

HEADING_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*$')


def slug(text: str) -> str:
    # Remove markdown code ticks and trailing punctuation typical for headings
    t = text.strip().strip('#').strip()
    t = re.sub(r'`+', '', t)
    # Remove inline code/backticks still lingering or trailing symbols
    t = re.sub(r'[^0-9A-Za-z\s\-]', '', t)
    t = t.lower()
    t = re.sub(r'\s+', '-', t)
    t = re.sub(r'-+', '-', t)
    return t.strip('-')


def build_toc(headings):
    lines = [TOC_START, '', '## Table of Contents', '']
    for level, text in headings:
        if level > MAX_DEPTH:
            continue
        anchor = slug(text)
        indent = '  ' * (level - 1)
        lines.append(f"{indent}- [{text}](#{anchor})")
    lines.append('')
    lines.append(TOC_END)
    lines.append('')
    return '\n'.join(lines)


def extract_headings(lines):
    headings = []
    for line in lines:
        m = HEADING_RE.match(line)
        if not m:
            continue
        hashes, title = m.groups()
        level = len(hashes)
        headings.append((level, title.strip()))
    return headings


def insert_or_replace_toc(text: str) -> str:
    lines = text.splitlines()
    headings = extract_headings(lines)
    if not headings:
        return text  # nothing to do
    toc_block = build_toc(headings)

    # Find existing TOC markers if present
    try:
        start_idx = next(i for i,l in enumerate(lines) if l.strip() == TOC_START)
        end_idx = next(i for i,l in enumerate(lines) if l.strip() == TOC_END)
        # Replace existing
        new_lines = lines[:start_idx] + toc_block.splitlines() + lines[end_idx+1:]
        return '\n'.join(new_lines) + ('\n' if text.endswith('\n') else '')
    except StopIteration:
        pass

    # Insert after first H1 if present
    first_h1_idx = None
    for i, (lvl, _) in enumerate(headings):
        if lvl == 1:
            # locate actual line index in file
            # search again in lines starting at 0
            count = 0
            for j, l in enumerate(lines):
                if HEADING_RE.match(l):
                    if count == i:
                        first_h1_idx = j
                        break
                    count += 1
            break
    if first_h1_idx is None:
        # prepend at top
        return toc_block + '\n' + text
    insert_at = first_h1_idx + 1
    # Skip blank lines just after H1
    while insert_at < len(lines) and lines[insert_at].strip() == '':
        insert_at += 1
    new_lines = lines[:insert_at] + [''] + toc_block.splitlines() + [''] + lines[insert_at:]
    return '\n'.join(new_lines) + ('\n' if text.endswith('\n') else '')


def process_file(path: Path):
    original = path.read_text(encoding='utf-8')
    updated = insert_or_replace_toc(original)
    if updated != original:
        path.write_text(updated, encoding='utf-8')
        print(f"[TOC] Updated: {path.name}")
    else:
        print(f"[TOC] Skipped (no change): {path.name}")


def main():
    if not READMES.exists():
        raise SystemExit("readmes/ directory not found")
    for md in sorted(READMES.glob("*.md")):
        if md.name.startswith('_'):
            continue
        process_file(md)

if __name__ == "__main__":
    main()
