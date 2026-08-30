# Shipping & Fulfillment Architecture

**Decision date:** 2026-08-25
**Status:** JSON envelope added; services and UI pending
**Industry gap:** #3 from industry-comparison.md

## WC2 Lineage

WC2 used two relational tables for pack-and-ship:

| Table | WC2 Name | Purpose |
|-------|----------|---------|
| **LoadTag** (Table 88) | Container record | One per box, pallet, or container. Carried tracking number, carrier, costs, weight, status, dates. Pallets pointed to child boxes via `idUniqueSuperior`. |
| **LoadItem** (Table 87) | Item-in-container | One per item packed in a specific box. Linked to order line and invoice. Carried qty, unit weight, extended weight, hazmat class, dunnage flag. |

**WC2 packing workflow:**
1. Load order → lock it
2. Scan/select items → `PKLineIntoBox()` creates LoadItem in current box
3. Scale validates weight (serial scale polling, tare capture, deviation check)
4. Finalize box → LoadTag created (containerType=1)
5. Optionally palletize → pallet LoadTag (containerType=2), boxes assigned via `idUniqueSuperior`
6. Invoice from packed items → `PKOrder2Invoice()` creates invoice, stamps LoadItems/LoadTags with invoice number
7. Shipping cost calculated per LoadTag from carrier zone/weight tables

**Key WC2 concepts preserved in WC3:**
- Container hierarchy (item → box → pallet)
- Dunnage as a flagged item (not a separate entity)
- Weight tracking (gross, tare, per-item unit weight)
- Carrier cost breakdown (freight, fuel surcharge, insurance, handling)
- Declared value for insurance
- Tracking number per package

## WC3 Design: shipping JSON Envelope

Instead of two relational tables, WC3 uses a single `shipping` JSONField on the transaction header. This follows the PJPV principle — the envelope is the source of truth.

### Where It Lives

`TransactionBaseModel.shipping` — available on all transaction types:
- **Invoice** — primary: fulfillment shipments to customers
- **WorkOrder** — production shipments, inter-facility moves
- **Order** — drop-ship tracking (vendor ships direct to customer)
- **Purchase** — inbound receiving (vendor ships to warehouse)

### Structure

```json
{
  "status": "shipped",
  "carrier": "UPS",
  "carrier_account": "",
  "service": "Ground",
  "ship_to": {
    "company": "Acme Inc.",
    "attention": "John Smith",
    "address1": "123 Main St",
    "city": "Springfield",
    "state": "IL",
    "zip": "62701",
    "country": "US"
  },
  "packages": [
    {
      "id": "PKG-001",
      "type": "box",
      "parent_id": "",
      "tracking": "1Z999AA10123456784",
      "status": "shipped",
      "weight": {
        "gross": 12.5,
        "tare": 1.2,
        "unit": "lbs"
      },
      "dimensions": {
        "length": 18.0, "width": 12.0, "height": 8.0, "unit": "in"
      },
      "value": 250.00,
      "insured": true,
      "costs": {
        "freight": 8.50,
        "fuel_surcharge": 1.20,
        "insurance": 2.00,
        "handling": 0.00,
        "total": 11.70
      },
      "dt_packed": "2026-08-25T14:30:00Z",
      "dt_shipped": "2026-08-25T16:00:00Z",
      "items": [
        {
          "line_number": 10,
          "item_id": 42,
          "item_ida": "WIDGET-100",
          "description": "Blue Widget",
          "qty": 6,
          "unit_weight": 1.5,
          "extended_weight": 9.0,
          "is_dunnage": false,
          "hazmat_class": ""
        },
        {
          "line_number": 0,
          "item_id": 99,
          "item_ida": "DUNNAGE-BUBBLE",
          "description": "Bubble wrap",
          "qty": 1,
          "unit_weight": 0.3,
          "extended_weight": 0.3,
          "is_dunnage": true,
          "hazmat_class": ""
        }
      ],
      "child_ids": []
    }
  ],
  "costs": {
    "freight": 8.50,
    "fuel_surcharge": 1.20,
    "insurance": 2.00,
    "handling": 0.00,
    "estimated": 12.00,
    "actual": 11.70
  },
  "weight": {
    "gross": 12.5,
    "unit": "lbs"
  },
  "package_count": 1,
  "dt_shipped": "2026-08-25T16:00:00Z",
  "dt_delivered": "",
  "notes": ""
}
```

### Container Hierarchy

Same as WC2 — three levels:

```
Pallet (package with type="pallet")
├── child_ids: ["PKG-001", "PKG-002"]     ← box package IDs
├── Box (package with type="box")
│   ├── items: [{line_number, qty, ...}]   ← what's in this box
│   └── parent_id: "PALLET-001"            ← which pallet it's on
└── Box (package with type="box")
    ├── items: [...]
    └── parent_id: "PALLET-001"
```

Pallets carry `child_ids[]` pointing to box package IDs. Boxes carry `parent_id` pointing back. Weight rolls up from items → box → pallet.

### How It Connects to Existing Models

| WC3 Element | Role in Shipping |
|-------------|-----------------|
| `shipping.packages[].items[].line_number` | Links to InvoiceLine/OrderLine.line_number |
| `line.quantity.active` | IS the shipped qty (invoice's verb) |
| `order_line.quantity.remaining` | Backlog — qty not yet invoiced/shipped |
| `line.physical` | Item weight, dimensions, hazmat (exists already) |
| `header.ship_via` | Carrier name (existing field, now also in `shipping.carrier`) |
| `header.totals.shipping` | Customer-facing shipping charge (existing) |
| `shipping.costs` | Actual shipping cost breakdown (new — distinct from customer charge) |

### Partial Fulfillment

An order with 10 units can ship in two invoices:
- Invoice A: `quantity.active = 6`, shipping envelope has 1 package with 6 units
- Invoice B: `quantity.active = 4`, shipping envelope has 1 package with 4 units
- Order line: `quantity.remaining = 0` after both invoices

Each invoice's shipping envelope is independent — its own packages, tracking numbers, costs.

### Shipping Status

| Status | Meaning |
|--------|---------|
| `""` (empty) | Not yet packed |
| `partial` | Some packages shipped, some still packing |
| `shipped` | All packages have tracking and ship date |
| `delivered` | Carrier confirmed delivery |

### What's NOT in This Envelope

- **Carrier rate tables** — separate concern (carrier config/service)
- **Scale integration** — hardware interface, not data model
- **Packing slip PDF** — document generation from shipping data
- **Return tracking** — belongs on CreditMemo (Gap #2)

### Future: Services to Build

| Service | Purpose |
|---------|---------|
| `add_package()` | Create a package in the shipping envelope |
| `pack_items()` | Add items to a package (validates against line qty) |
| `ship_package()` | Set tracking number, ship date, calculate costs |
| `shipping_summary()` | Roll up costs/weight from packages to header |
| `carrier_rate_query()` | Call carrier stubs for rate estimates |

### File Locations

| What | Where |
|------|-------|
| JSON envelope default | `apps/transactions/models/base_transaction_model.py` → `default_shipping()` |
| Field declaration | `TransactionBaseModel.shipping` |
| Carrier stubs | `apps/transactions/services/carriers/` (FedEx, UPS, USPS) |
| Physical line data | `apps/transactions/models/base_line_model.py` → `default_physical()` |
| Freight estimation | `apps/transactions/services/freight_estimation.py` |
