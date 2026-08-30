# Item-Linked Models — Why Each Earns Its Table

All models below inherit from `ItemLinkedBase` (FK to Item + BaseModel envelopes).
The question for each: does this belong in its own table, or could it be JSON on Item?

**The rule:** A satellite model earns its own table when it has an independent lifecycle,
multiple rows per item, or requires reverse lookups. If it's 1:1 with no independent
lifecycle, it belongs in `item.config` (see: Service model deletion, 2026-08-27).

---

## Models That Earn Their Tables

### InventoryLayer
FIFO/LIFO cost layers. Many rows per item — one per receipt. Each layer has its own
quantity, cost basis, and depletion state. Queried independently for costing decisions.
GL journal entries post per layer. Cannot be JSON.

### SiteInventory
Per-warehouse quantity summary. Many rows per item × warehouse. Queried by warehouse
for availability checks. Aggregated across warehouses for total on-hand. Cannot be JSON.

### InventoryMovement
Append-only audit trail. Many rows per item over time. Queried by date range for
activity reports. Regulatory requirement for inventory audit. Cannot be JSON.

### InventoryReservation
Soft holds with TTL. Many concurrent rows per item (one per order line). Expire
independently. Released on invoice creation. Queried for available-to-promise.
Cannot be JSON.

### Serial
Individual serial numbers. Each has its own lifecycle — received, in-stock, sold,
warranty, returned. Assigned to specific customers. Queried by serial number for
warranty lookup, by customer for service history. Cannot be JSON.

### OrgItem
Customer/vendor-specific pricing per item. Many-to-many relationship (item × org).
Queried from both sides: "what's this customer's price for item X" and "which
customers have negotiated prices for item X." Contains contract prices, MAP overrides,
vendor lead times. Cannot be JSON.

### ItemXRef
Cross-reference identifiers. Two distinct functions:

1. **Substitutes/alternatives** — "buy this instead of that." This is a relationship
   between items, not an attribute of one item. The xref table expresses the graph
   of substitution relationships. Reverse lookup: "what substitutes exist for item X?"

2. **Same item, different sourcing** — same physical product but different supplier
   SKUs, barcodes, or regulatory treatment. These carry source-specific context
   (different UPC, different lead time, different compliance status) that does not
   belong on the canonical item record. The item is the product; the xref is the
   context it lives in at a specific source.

Both functions require indexed reverse lookups (scan barcode → find item, search
MPN → find alternatives). Cannot be JSON.

### CatalogLine
Item placement in a catalog. Many-to-many (item × catalog). Each line carries
catalog-specific display data (position, featured flag, category within catalog).
Queried from catalog side for rendering. Cannot be JSON.

### Specification
Shared spec sheets. Many-to-many — multiple items share one specification record.
Contains attributes that define a product class (voltage, weight class, material).
Queried across items for filtering ("show all items with voltage=220V").
Absorbing into Item would duplicate spec data across every item sharing that spec.
Cannot be JSON.

### ItemUsage
Consumption/usage tracking. Time-series data — many rows per item over time.
Used for velocity calculations, reorder point computation, demand forecasting.
Cannot be JSON.

## The Model That Didn't Earn Its Table

### Service (deleted 2026-08-27)
Was 1:1 with Item. No independent lifecycle — a service billing config only existed
in the context of its parent item. No reverse lookups needed. No multiple rows.
Absorbed into `item.config.service` as a JSON dictionary. See `default_service_config()`
in `apps/products/models/item.py`.

**Two approaches for service items** (documented in schema):
- **Itemized** (recommended): separate Item records per cost type → correct GL journals
- **Composite**: single bundled item → simpler but lost-signal for GL accuracy

The `approach` field in `config.service` records the user's choice.
