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
python3 scripts/codemap_enrich.py readmes/flowcharts/wc3-inventory-buckets.dot
```
Reads the .dot file + a mapping JSON, adds `URL` and `tooltip` attributes
to every node, outputs an enriched .dot. Graphviz renders clickable SVG —
clicking opens the file in VS Code at the right line.

### Layer 2: VS Code Webview Panel
Click a node in the rendered diagram → right panel shows:
- Function signatures (parsed from actual source)
- JSON schema for data structures
- Example data (from the code's default factories)
- Links to service, model, and test files
- Updates when you save a .py file

### Layer 3: Architecture API
```
POST /wcapi/manage/
{ "action": "get_architecture_node", "params": { "node": "pending" } }
```
Returns the same data the panel shows. Alice uses this to answer "what
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

## Connection to the Ecosystem

CodeMap is the same idea expressed in a new domain: the developer is
sovereign over understanding the system. The diagram is locally owned,
locally rendered, locally queryable. Alice reads the same map — she is an
agent with limited, enumerated access to the architecture, not a black box
that "just knows."

This is Desktop Hosting applied to architecture documentation.
