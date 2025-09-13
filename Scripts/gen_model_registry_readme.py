#!/usr/bin/env python3
"""Generate a README documenting the canonical MODEL_REGISTRY.

Outputs readmes/model-registry.md with:
- Alphabetical list of model keys (A→Z) with app, endpoint, and kind
- Grouped-by-app view (A→Z within each app)
- Mermaid diagram (flowchart with subgraphs per app)

This is derived from apps.core.constants.model_registry.MODEL_REGISTRY to avoid drift.
"""
from __future__ import annotations

from pathlib import Path
import sys
import csv
import json
import inspect
from typing import Dict, List, Tuple
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'readmes' / 'model-registry.md'
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
JSON_OUT = ROOT / 'readmes' / 'model-registry.json'
CSV_OUT = ROOT / 'readmes' / 'model-registry.csv'


def _get_registry():
    # Import locally to avoid import costs when unused
    from apps.core.constants.model_registry import MODEL_REGISTRY
    return MODEL_REGISTRY


def _extract_app(model_path: str) -> str:
    # e.g. 'apps.transactions.models.line_variants.SalesOrder' -> 'transactions'
    parts = model_path.split('.')
    try:
        i = parts.index('apps')
        return parts[i + 1]
    except Exception:
        # Fallback: best-effort second segment
        return parts[1] if len(parts) > 1 else 'unknown'


def _alphabetical_list(reg) -> List[Tuple[str, str, str, str, List[str]]]:
    rows: List[Tuple[str, str, str, str, List[str]]] = []  # (key, app, endpoint, kind, aliases)
    for key, meta in reg.items():
        app = _extract_app(meta.model)
        rows.append((key, app, meta.endpoint, meta.kind, list(meta.aliases)))
    rows.sort(key=lambda r: (r[0]))
    return rows


def _group_by_app(reg) -> Dict[str, List[str]]:
    groups: Dict[str, List[str]] = defaultdict(list)
    for key, meta in reg.items():
        app = _extract_app(meta.model)
        groups[app].append(key)
    for app in groups:
        groups[app].sort(key=lambda k: k)
    return dict(sorted(groups.items(), key=lambda kv: kv[0]))


def _render_mermaid(groups: Dict[str, List[str]], reg) -> str:
    lines = []
    lines.append('```mermaid')
    lines.append('flowchart LR')
    # Styles
    lines.append('  classDef app fill:#f6f8fa,stroke:#bbb,stroke-width:1px;')
    lines.append('  classDef header fill:#e3f2fd,stroke:#64b5f6,stroke-width:1px;')
    lines.append('  classDef line fill:#fff3e0,stroke:#ffb74d,stroke-width:1px;')
    lines.append('  classDef support fill:#e8f5e9,stroke:#81c784,stroke-width:1px;')
    for app, keys in groups.items():
        title = app.capitalize()
        app_id = f'app_{app}'.replace('-', '_').replace(' ', '_')
        lines.append(f'  subgraph {title}')
        lines.append('    direction TB')
        # App node inside subgraph
        lines.append(f'    {app_id}(["{app}"])')
        lines.append(f'    class {app_id} app')
        for k in keys:
            safe_id = k.replace('-', '_').replace(' ', '_')
            lines.append(f'    {safe_id}["{k}"]')
            # Edge from app to model node
            lines.append(f'    {app_id} --> {safe_id}')
            # Apply class by kind if known
            kind = getattr(reg[k], 'kind', 'support') or 'support'
            if kind in ('header', 'line', 'support'):
                lines.append(f'    class {safe_id} {kind}')
        lines.append('  end')
    lines.append('```')
    return '\n'.join(lines)
def _try_model_source_path(meta) -> str | None:
    try:
        model_cls = meta.import_model()
        file = inspect.getsourcefile(model_cls) or inspect.getfile(model_cls)
        if not file:
            return None
        p = Path(file)
        try:
            rel = p.relative_to(ROOT)
        except ValueError:
            # Not under ROOT
            return None
        return str(rel)
    except Exception:
        return None


def _export_json(reg) -> None:
    payload = []
    for key in sorted(reg.keys()):
        meta = reg[key]
        payload.append({
            'key': key,
            'app': _extract_app(meta.model),
            'model': meta.model,
            'endpoint': meta.endpoint,
            'kind': meta.kind,
            'aliases': list(meta.aliases),
        })
    JSON_OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def _export_csv(reg) -> None:
    rows = []
    for key in sorted(reg.keys()):
        meta = reg[key]
        rows.append({
            'key': key,
            'app': _extract_app(meta.model),
            'model': meta.model,
            'endpoint': meta.endpoint,
            'kind': meta.kind,
            'aliases': ','.join(sorted(set(meta.aliases))) if meta.aliases else '',
        })
    with CSV_OUT.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['key','app','model','endpoint','kind','aliases'])
        writer.writeheader()
        writer.writerows(rows)



def build_markdown() -> str:
    reg = _get_registry()
    alpha = _alphabetical_list(reg)
    groups = _group_by_app(reg)

    lines: List[str] = []
    lines.append('# Model Registry')
    lines.append('')
    lines.append('Autogenerated reference derived from the canonical MODEL_REGISTRY.')
    lines.append('Do not edit by hand; run `bin/python Scripts/gen_model_registry_readme.py` to regenerate.')
    lines.append('')
    lines.append('## Migration note')
    lines.append('')
    lines.append('- Prefer `item` for product records. Use `model_name=item` (plural table key: `items`).')
    lines.append('- `org_item` refers to the Org↔Item association (assortment/carry relationship), not the product itself.')
    lines.append('- Existing clients that queried products with `org_item` should switch to `item` for product list/detail calls.')
    lines.append('- `org_item` remains available for association use cases (org assortment, thresholds, checks).')
    lines.append('')
    lines.append('## Alphabetical list (A→Z)')
    lines.append('')
    for key, app, endpoint, kind, aliases in alpha:
        alias_txt = f", aliases: {', '.join(sorted(set(aliases)))}" if aliases else ''
        # Attempt to link key to source file
        meta = reg[key]
        src = _try_model_source_path(meta)
        key_label = f'[{key}]({src})' if src else key
        lines.append(f'- {key_label} — app: `{app}`, endpoint: [`/wcapi/{endpoint}/`](/wcapi/{endpoint}/), kind: `{kind}`{alias_txt}')
    lines.append('')
    lines.append('## By app (A→Z)')
    lines.append('')
    for app, keys in groups.items():
        lines.append(f'### {app} ({len(keys)})')
        lines.append('')
        for k in keys:
            m = reg[k]
            alias_txt = f", aliases: {', '.join(sorted(set(m.aliases)))}" if m.aliases else ''
            src = _try_model_source_path(m)
            k_label = f'[{k}]({src})' if src else k
            lines.append(f'- {k_label} — endpoint: [`/wcapi/{m.endpoint}/`](/wcapi/{m.endpoint}/), kind: `{m.kind}`{alias_txt}')
        lines.append('')
    lines.append('## Diagram')
    lines.append('')
    # Legend for colors/kinds
    lines.append('Legend:')
    lines.append('- header: blue nodes (document headers like orders)')
    lines.append('- line: orange nodes (line items)')
    lines.append('- support: green nodes (supporting/reference data)')
    lines.append('')
    lines.append(_render_mermaid(groups, reg))
    lines.append('')
    lines.append('> Source of truth: `apps/core/constants/model_registry.py`.')
    return '\n'.join(lines)


def main():
    OUT.write_text(build_markdown(), encoding='utf-8')
    _export_json(_get_registry())
    _export_csv(_get_registry())
    print(f'Wrote: {OUT}')
    print(f'Wrote: {JSON_OUT}')
    print(f'Wrote: {CSV_OUT}')


if __name__ == '__main__':
    main()
