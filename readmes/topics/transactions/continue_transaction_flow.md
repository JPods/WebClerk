# Continue: Transaction Flow Cleanup

## Last Session (Feb 16, 2026)

### 1. Sequence Rename

Renamed 4 legacy PostgreSQL sequences to match current table names:

| Before | After |
|---|---|
| `orders_id_seq` | `orders_id_seq` |
| `purchases_id_seq` | `purchases_id_seq` |
| `order_lines_id_seq` | `order_lines_id_seq` |
| `purchase_lines_id_seq` | `purchase_lines_id_seq` |

All 12 transaction tables verified OK via `tools/check_all_sequences.py`.

### 2. ida Standardization

Updated all ida values across all transaction tables (headers + lines) to `"ida-{id}"` format. Fixed 38 rows of stale data (bare ids, `ida-` prefixes on wrong ranges, faker lorem text). Script: `tools/fix_ida_values.py`.

### 3. CoreModel.save() Updated

`common/models.py` line ~450 now generates `ida = f"ida-{self.pk}"` instead of `str(self.pk)` for all new records.

---

## Ready to Pick Up: Transaction Flow Cleanup

Current transaction docs are in `readmes/topics/transactions/`. Key known issues from `readmes/topics/transactions/00_instructions.md`:

- §11 lists open issues: quantity key mismatch between line save and calc (`qty` vs `quantity`), header totals signal gap (line saves don't trigger header recalc)
- Transaction flow calc plan needs implementation alignment
- The file currently open is `apps/transactions/models/invoice.py`

Please review the transaction flow and let's address the next priority items.
