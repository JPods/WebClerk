#!/usr/bin/env python3
"""Publish a flowchart (and its written framework) to webclerk.com/flowcharts/.

The site is static: a `flowcharts.json` manifest plus `svg/` and `docs/` folders under
/var/www/webclerk-static/flowcharts/ on Andi. Until now the 45 charts there were placed
by hand — this script exists because "we create" is a recurring act, not a one-off
(Bill, 2026-09-17).

Usage
-----
    # what would change, and nothing else
    python tools/publish_flowcharts.py --chart replenishment-framework \\
        --category Products --title "Replenishment Framework" \\
        --doc readmes/products/replenishment-framework.md --dry-run

    # then, to actually publish
    python tools/publish_flowcharts.py ... --publish

It refuses to publish without --publish. A dry run prints the diff of the manifest and
the files it would copy, and touches nothing.

The .md becomes a plain HTML page under docs/ (the site has no markdown renderer, and
Andi has no markdown module — the conversion happens here, where it does).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FLOWCHARTS = BACKEND / 'readmes' / 'flowcharts'
HOST = 'andi'
REMOTE = '/var/www/webclerk-static/flowcharts'


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def fetch_manifest() -> dict:
    result = run(['ssh', HOST, f'cat {REMOTE}/flowcharts.json'])
    if result.returncode != 0:
        sys.exit(f'could not read the manifest: {result.stderr.strip()}')
    return json.loads(result.stdout)


def md_to_html(md_text: str, title: str) -> str:
    """The written framework as a page that matches the site's plain style."""
    try:
        import markdown  # local venv has it; Andi does not, which is why this runs here
        body = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])
    except ImportError:
        body = '<pre>' + html.escape(md_text) + '</pre>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} &mdash; WebClerk</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 16px/1.6 -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif;
         max-width: 46rem; margin: 0 auto; padding: 2rem 1rem 4rem; }}
  h1, h2, h3 {{ line-height: 1.25; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid #ccc; padding: .4rem .6rem; text-align: left; vertical-align: top; }}
  code, pre {{ font-family: ui-monospace, Menlo, Consolas, monospace; font-size: .9em; }}
  pre {{ background: #f6f6f6; padding: .8rem; overflow-x: auto; }}
  blockquote {{ margin: 1rem 0; padding-left: 1rem; border-left: 3px solid #ccc; color: #555; }}
  .back {{ display: inline-block; margin-bottom: 1.5rem; }}
</style>
</head>
<body>
<a class="back" href="/flowcharts/">&larr; Flowcharts</a>
{body}
</body>
</html>
"""


def slug_title(chart_id: str) -> str:
    return chart_id.replace('-', ' ').replace('_', ' ').title()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--chart', required=True,
                    help='svg basename in readmes/flowcharts (without .svg)')
    ap.add_argument('--category', required=True, help='manifest category, e.g. Products')
    ap.add_argument('--title', help='display title (default: from the chart name)')
    ap.add_argument('--description', default='', help='one line under the title')
    ap.add_argument('--doc', help='path to the .md that explains it, relative to backend/')
    ap.add_argument('--publish', action='store_true', help='actually copy and update')
    ap.add_argument('--dry-run', action='store_true', help='print what would happen')
    args = ap.parse_args()

    svg = FLOWCHARTS / f'{args.chart}.svg'
    if not svg.exists():
        sys.exit(f'no such chart: {svg}')
    doc = (BACKEND / args.doc) if args.doc else None
    if doc and not doc.exists():
        sys.exit(f'no such doc: {doc}')

    title = args.title or slug_title(args.chart)
    manifest = fetch_manifest()
    categories = manifest.get('categories') or []
    names = [c.get('name') for c in categories]
    if args.category not in names:
        sys.exit(f'unknown category {args.category!r}. One of: {", ".join(map(str, names))}')

    entry = {
        'title': title,
        'src': f'svg/{args.chart}.svg',
        'id': args.chart,
        'description': args.description or title,
        'search': re.sub(r'\s+', ' ', ' '.join(
            re.findall(r'>([^<>]{2,})<', svg.read_text()))).strip()[:4000],
    }
    if doc:
        entry['doc'] = f'docs/{args.chart}.html'

    category = categories[names.index(args.category)]
    charts = category.setdefault('charts', [])
    existing = next((i for i, c in enumerate(charts) if c.get('id') == args.chart), None)
    action = 'replace' if existing is not None else 'add'
    if existing is not None:
        charts[existing] = entry
    else:
        charts.append(entry)

    print(f'{action} "{title}" in category {args.category}')
    print(f'  svg  readmes/flowcharts/{args.chart}.svg -> {REMOTE}/svg/{args.chart}.svg')
    if doc:
        print(f'  doc  {args.doc} -> {REMOTE}/docs/{args.chart}.html')
    print(f'  manifest: {sum(len(c.get("charts", [])) for c in categories)} charts total')

    if not args.publish:
        print('\ndry run — nothing sent. Add --publish to do it.')
        return 0

    # The site directory is owned by www-data. The house method is sudo cp + chown
    # (that is how every other chart got there) — scp as andi cannot write it.
    #
    # Another machine publishes to this same folder, so the manifest is re-read here,
    # immediately before writing, and the chart is re-applied to that fresh copy. A
    # concurrent publish that landed in between is kept, not overwritten.
    fresh = fetch_manifest()
    fresh_categories = fresh.get('categories') or []
    fresh_names = [c.get('name') for c in fresh_categories]
    if args.category not in fresh_names:
        sys.exit(f'category {args.category!r} vanished from the live manifest — nothing sent')
    fresh_category = fresh_categories[fresh_names.index(args.category)]
    fresh_charts = fresh_category.setdefault('charts', [])
    at = next((i for i, c in enumerate(fresh_charts) if c.get('id') == args.chart), None)
    if at is not None:
        fresh_charts[at] = entry
    else:
        fresh_charts.append(entry)
    live_total = sum(len(c.get('charts', [])) for c in fresh_categories)

    tmp = Path('/tmp/flowcharts.json')
    tmp.write_text(json.dumps(fresh, indent=2, ensure_ascii=False) + '\n')

    stamp = run(['ssh', HOST, 'date -u +%Y%m%dT%H%M%S']).stdout.strip()
    backup = run(['ssh', HOST,
                  f'sudo -n cp {REMOTE}/flowcharts.json /home/andi/flowcharts.json.{stamp}.bak'])
    if backup.returncode != 0:
        sys.exit(f'backup failed, nothing changed: {backup.stderr.strip()}')
    print(f'  backup: ~andi/flowcharts.json.{stamp}.bak')

    staged = [(svg, f'svg/{args.chart}.svg')]
    if doc:
        page = Path(f'/tmp/{args.chart}.html')
        page.write_text(md_to_html(doc.read_text(), title))
        staged.append((page, f'docs/{args.chart}.html'))
    staged.append((tmp, 'flowcharts.json'))

    steps = [(['ssh', HOST, f'sudo -n mkdir -p {REMOTE}/svg {REMOTE}/docs'], 'make folders')]
    for local, remote_rel in staged:
        scratch = f'/tmp/publish-{Path(remote_rel).name}'
        steps.append((['scp', '-q', str(local), f'{HOST}:{scratch}'], f'stage {remote_rel}'))
        steps.append((['ssh', HOST,
                       f'sudo -n cp {scratch} {REMOTE}/{remote_rel} && '
                       f'sudo -n chown www-data:www-data {REMOTE}/{remote_rel} && '
                       f'rm -f {scratch}'], f'install {remote_rel}'))

    for cmd, what in steps:
        result = run(cmd)
        if result.returncode != 0:
            sys.exit(f'{what} failed: {result.stderr.strip()}')
        print(f'  ok: {what}')

    check = run(['ssh', HOST, f'grep -c \'"id": "{args.chart}"\' {REMOTE}/flowcharts.json'])
    if check.stdout.strip() not in ('1',):
        print(f'  WARNING: the live manifest does not list {args.chart} — check for a '
              f'concurrent publish')
    else:
        print(f'  verified live: {live_total} charts in the manifest')

    print(f'\nhttps://www.webclerk.com/flowcharts/ — {title} published')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
