# CodeMap (codemap.guru) — Live Architecture Tool

## What It Is

CodeMap makes .dot flowcharts into live, clickable architecture maps. Every
node in a diagram links to the actual code that implements it — functions,
JSON schemas, models, tests. The diagram IS the index into the codebase.

Click a node. See the code. Alice reads the same map to answer architecture
questions. One source of truth, three consumers.

## Why It Exists

Diagrams drift from code. Documentation says "pending records are created
when an order converts to invoice" but doesn't say WHERE in the code that
happens. CodeMap closes that gap permanently. The diagram links to
`order_to_invoice.py:332` — if the code moves, the mapping updates.

## The Three Layers

### Layer 1: Enrichment Script
```bash
python3 ~/Allie/scripts/codemap_enrich.py --all --render
```
Reads .dot files + `codemap.json`, adds `URL` and `tooltip` attributes,
renders clickable SVGs. Idempotent — run anytime. Graphviz renders clickable
SVG — clicking opens the file in VS Code at the right line.

### Layer 2: React Page
Navigate to `/codemap` in Alice Commerce (port 5176). Card grid with SVG
thumbnails organized by category. Click a card -> full-size diagram with
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
Fuzzy matching on node names. Alice uses this to answer "what
happens when I create an invoice?" by walking the graph. Users can query
it from the flight simulator to see deeper code context.

## The Source of Truth: Mapping File

One JSON file maps node names to code locations. All three layers read it.

```
readmes/flowcharts/codemap.json
```

Structure:
```json
{
  "nodes": {
    "pending": {
      "model": "apps/core/models/pending.py:6",
      "functions": [
        {"name": "Pending.objects.create", "file": "apps/transactions/services/order_to_invoice.py", "line": 332},
        {"name": "Pending.objects.create", "file": "apps/transactions/services/proposal_to_order.py", "line": 171},
        {"name": "Pending.objects.create", "file": "apps/transactions/services/flow.py", "line": 308}
      ],
      "schema": {
        "fields": ["model_name", "record_id", "purpose", "name", "dt_processed", "changes", "data"],
        "data_keys": ["item_id", "on_so", "on_po", "on_wo", "on_in", "on_r", "on_p", "on_hand"]
      },
      "tests": ["tests/test_pending.py"],
      "description": "Central hub for inventory quantity deltas"
    }
  }
}
```

Node names in the mapping match node IDs in the .dot files. The enrichment
script is idempotent — run it anytime, it overwrites URL/tooltip. The panel
watches the mapping file for changes.

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

## Existing Flowcharts

15 .dot files in `readmes/flowcharts/wc3-*.dot`:

| File | What it maps |
|------|-------------|
| `wc3-master-flow` | Complete commerce lifecycle |
| `wc3-big4-transactions` | Line quantity flow and pending |
| `wc3-customer-centered-sales` | Commerce from customer perspective |
| `wc3-order-to-invoice` | Fulfillment with inventory effects |
| `wc3-payment-gl` | Cash through GL posting |
| `wc3-inventory-buckets` | available = on_hand - allocated |
| `wc3-flight-sim-inventory` | 9-step training with GL impact |
| `wc3-impact-assessment-loop` | Alice auto-populate cycle |
| `wc3-action` | Universal task model |
| `wc3-project` | Project connects transactions |
| `wc3-contact` | Central identity |
| `wc3-serial-tracking` | Serial + SerialLog lifecycle |
| `wc3-print-system` | Print and report system |
| `wc3-qa-entity` | Quality inspection |
| `wc3-signin-register` | Authentication and roles |

Combined PDF with introduction: `wc3-all-flowcharts.pdf`

## Priority for Enrichment

1. `wc3-inventory-buckets` — most code references, most complex flows
2. `wc3-flight-sim-inventory` — 9 steps, each links to a service function
3. `wc3-big4-transactions` — core transaction lifecycle
4. `wc3-payment-gl` — cash flow through GL
5. `wc3-master-flow` — the big picture

## Known Gap

`order_to_purchase.py` does NOT create pending records for `+on_po`. The PO
line is created but no inventory delta is written. `receive_purchase` writes
`-on_po` on receipt, but nothing writes `+on_po` when the PO is created.
CodeMap will surface this — the node will have no function link for the
`+on_po` delta.

## WC3 Document Records

Every flowchart has a Document record with `purpose="codemap-guru"` tracking
revision number, node count, coverage percentage, and SVG availability.

Update after changes:
```bash
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

## Connection to the Ecosystem

CodeMap is the same idea expressed in a new domain: the developer is
sovereign over understanding the system. The diagram is locally owned,
locally rendered, locally queryable. Alice reads the same map — she is an
agent with limited, enumerated access to the architecture, not a black box
that "just knows."

This is Desktop Hosting applied to architecture documentation.

## Design Decisions

- **No new FKs for touches**: contact_id is the identity. Roles are on Contact, not Action.
- **Graphviz for drafts, Affinity for polish**: Standard style makes Graphviz output consistent.
- **codemap.json is sovereign**: One file, three consumers. No drift.
