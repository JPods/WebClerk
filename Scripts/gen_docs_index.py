#!/usr/bin/env python3
"""Generate a lightweight JSON search index for markdown docs under readmes/.

Output: docs_index.json at repo root containing list[ {slug, title, headings, path, tags} ]
Heuristics:
- slug derived from filename (without extension)
- title = first H1 (# ...) or filename
- headings: collect H2/H3 text values (without #)
- tags: simple keywords extracted (split words, lowercase) excluding common stopwords
- For quick fuzzy search client-side
"""
from __future__ import annotations
from pathlib import Path
import json, re
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
READMES = ROOT / 'readmes'
OUT = ROOT / 'docs_index.json'
STOP = { 'the','a','an','and','or','of','to','for','in','on','with','by','at','is','be','this','that','it','as','if','are','was','were','from','via','vs','into','your','our','their','after','before','about','per' }
HEADING_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
WORD_RE = re.compile(r'[A-Za-z0-9]{3,}')


def process(md: Path):
    text = md.read_text(encoding='utf-8', errors='ignore')
    lines = text.splitlines()
    title = None
    h2h3 = []
    for line in lines:
        m = HEADING_RE.match(line)
        if not m:
            continue
        level = len(m.group(1))
        name = m.group(2).strip()
        if level == 1 and title is None:
            title = name
        elif level in (2,3):
            h2h3.append(name)
    if title is None:
        title = md.stem.replace('-', ' ').title()
    # Keyword extraction across whole file
    words = [w.lower() for w in WORD_RE.findall(text)]
    words = [w for w in words if w not in STOP]
    top = [w for w,_ in Counter(words).most_common(30)]
    return {
        'slug': md.stem,
        'title': title,
        'headings': h2h3,
        'path': str(md.relative_to(ROOT)),
        'tags': top,
    }


def main():
    docs = []
    for md in sorted(READMES.glob('*.md')):
        if md.name.startswith('_'):
            continue
        docs.append(process(md))
    OUT.write_text(json.dumps(docs, indent=2), encoding='utf-8')
    print(f'Wrote index: {OUT} ({len(docs)} docs)')

if __name__ == '__main__':
    main()
