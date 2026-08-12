# CodeMap — Live Architecture Maps

## What It Is

CodeMap makes .dot flowcharts into live, clickable architecture maps. Every
node in a diagram links to the actual code that implements it — functions,
JSON schemas, models, tests. Click a node, see the code. One source of truth.

## Three Layers

### Layer 1: Enrichment Script
```bash
python3 ~/Allie/scripts/codemap_enrich.py --all --render
```
Reads .dot files + `codemap.json`, adds `URL` and `tooltip` attributes,
renders clickable SVGs. Idempotent — run anytime.

### Layer 2: React Page
Navigate to `/codemap` in Alice Commerce (port 5176). Card grid with SVG
thumbnails organized by category. Click a card → full-size diagram with
clickable nodes. Detail panel shows functions, file:line, pending deltas,
GL impact, schema fields. Print current or print all.

### Layer 3: Architecture API
```
POST /wcapi/manage/
{ "action": "get_architecture_node", "params": { "node": "pending" } }
{ "action": "get_architecture_map", "params": { "flowchart": "wc3-inventory-buckets" } }
{ "action": "get_architecture_svg", "params": { "flowchart": "wc3-inventory-buckets" } }
{ "action": "list_architecture_flowcharts", "params": {} }
```
Fuzzy matching on node names. Alice uses these to answer architecture questions.

## Source of Truth

One JSON mapping file powers everything:
```
~/Allie/readmes/flowcharts/codemap.json
```
Maps node names → file:line, functions, pending deltas, GL impact, schemas.
All three layers read it. Edit once, regenerate, all consumers update.

## Standard Style

Defined in `~/Allie/readmes/flowcharts/codemap-style.dot`, injected
automatically by the enrichment script:
- 2px edge lines, 200% arrowheads
- 10pt labels on nodes and edges
- Helvetica Neue, rounded nodes, 0.75 aspect ratio
- Consistent across all 34 flowcharts

Bill designs polished versions in Affinity Designer. Graphviz for drafts.

## Flowchart Categories

| Category | Count | Examples |
|----------|-------|---------|
| Core Transactions | 7 | master-flow, big4, inventory-buckets, payment-gl |
| Products & Serial | 3 | items, serial-tracking, serial-actions |
| Contacts & Sales | 3 | contact, customer-centered-sales, signin |
| Connections | 10 | accounting, banking, shipping, tax, payment |
| Projects & QA | 6 | project, action, action-documents, action-touches, qa |
| Data & Infrastructure | 5 | data-conversion, document-library, celery, security |

## WC3 Document Records

Every flowchart has a Document record with `purpose="codemap-guru"` tracking
revision number, node count, coverage percentage, and SVG availability.

Update after changes:
```bash
# Uses WC3 venv
python3 ~/Allie/scripts/codemap_seed_documents.py --apply --re-enrich
```

## Key Files

| What | Where |
|------|-------|
| Mapping file | `~/Allie/readmes/flowcharts/codemap.json` |
| Enrichment script | `~/Allie/scripts/codemap_enrich.py` |
| Document seeder | `~/Allie/scripts/codemap_seed_documents.py` |
| Viewer server | `~/Allie/scripts/codemap_serve.py` |
| Style template | `~/Allie/readmes/flowcharts/codemap-style.dot` |
| Architecture API | `apps/core/services/architecture.py` |
| React page | `react-alice/src/pages/CodeMap.tsx` |
| Site | `~/Allie/sites/codemap/index.html` |
| VS Code tasks | `~/Allie/.vscode/tasks.json` |

## Design Decisions

- **No new FKs for touches**: contact_id is the identity. Roles (customer,
  vendor, employee) are on Contact, not Action. Org is via Contact.org FK.
  assigned_to is the toucher. refs is cache, not authority.
- **Graphviz for drafts, Affinity for polish**: Standard style makes Graphviz
  output consistent. Bill uses Affinity Designer for presentation-quality SVGs.
- **codemap.json is sovereign**: One file, three consumers. No drift.
