# Transaction JSONB Management and Best Practices

> **Last updated:** 2026-02-19

## Overview

All transaction models in WebClerk3 (Proposal, Order, Invoice, Purchase, WorkOrder) use PostgreSQL JSONB fields to store structured, extensible, and queryable data for totals, cost, sell, finance, flow, source, and actions. Proper management of these JSONB fields is critical for data integrity, performance, and future schema evolution.

## Key JSONB Fields

- `totals`: Header-level rollup (see `default_totals()` in `base_transaction_model.py`)
- `cost`: Aggregated cost details (see `default_cost()`)
- `sell`: Aggregated sell-side details (for sell-side docs)
- `finance`: Tax, payment, and financial metadata
- `flow`: Transaction lineage and children
- `source`: Campaign, catalog, vendor, manufacturer references
- `actions`: Next action metadata

## Best Practices

1. **Always use factory functions** (`default_totals`, `default_cost`, etc.) to seed new records and ensure all expected keys are present.
2. **Never store null or missing keys** in JSONB fields. Use zero or empty values as appropriate for each key.
3. **Normalize on save**: All line and header saves should call normalization helpers (e.g., `normalize_cost_map`, `normalize_price_map`) to fill in missing keys and fix nulls.
4. **Atomic updates**: Always update JSONB fields in a single transaction to avoid partial writes.
5. **Schema evolution**: When adding new keys, update the factory functions and normalization logic. Old records will be backfilled on next save.
6. **Indexing**: Use GIN indexes for JSONB fields that are queried frequently (e.g., totals.total, totals.balance).
7. **Validation**: Validate JSONB payloads before save. Skip or log corrupted fields, never overwrite with invalid data.
8. **Audit trail**: Preserve original values in `metadata.history` for traceability.

## Example: `default_totals()`

```python
def default_totals() -> Dict[str, Any]:
    return {
        "subtotal": 0,
        "discount": 0,
        "taxable": 0,
        "tax": 0,
        "shipping": 0,
        "other": 0,
        "total": 0,
        "cost": 0,
        "margin": 0,
        "margin_pc": 0,
        "received": 0,
        "balance": 0,
    }
```

## Save Workflow

- On every transaction or line save:
  - Call `ensure_json_defaults()` to seed all JSONB fields.
  - Normalize with `normalize_cost_map`, `normalize_price_map`.
  - Validate and skip corrupted JSON fields.
  - Use atomic transactions for all updates.

## Error Handling

- Corrupted or missing JSON fields are logged and skipped, not overwritten.
- All saves are wrapped in atomic transactions; partial failures roll back changes.

## Related Documents
- [transactions-totals.md](transactions-totals.md)
- [transaction_flows.md](transaction_flows.md)
- [transaction_line_save.md](transaction_line_save.md)
- [08-transaction-calculations.md](../../08-transaction-calculations.md)

---

**Summary:**

Proper JSONB management is essential for transaction integrity, queryability, and future-proofing. Always use the provided factory and normalization functions, validate on save, and never allow partial or corrupted JSONB writes.
