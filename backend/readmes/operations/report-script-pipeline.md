# Report Script Pipeline — Before / During / After

**Established:** 2026-08-09
**Applies to:** All WC3 Report records (category: report, tally, dashboard, summary, export, utility)

---

## The Three Phases

When a Report processes a group of records, three script fields execute in sequence:

| Phase | Field | Runs | Purpose |
|-------|-------|------|---------|
| **Before** | `script_before` | Once, before the first record | Initialize accumulators, open connections, apply filters, establish the working set |
| **During** | `script_during` | Once per record in the set | Business logic — line extensions, bucket assignments, GL accumulation, formatting |
| **After** | `script_after` | Once, after the last record | Write results, format output, send notifications, close connections, update records |

```
┌─────────────────────────────────────────────────────┐
│  User selects records → clicks Report               │
│                                                     │
│  ┌──────────────┐                                   │
│  │ script_before │  ← runs ONCE                     │
│  │  • zero accumulators                             │
│  │  • open output stream                            │
│  │  • apply filters / establish selection            │
│  └──────┬───────┘                                   │
│         │                                           │
│         ▼         ┌─────── loop ───────┐            │
│  ┌──────────────┐ │                    │            │
│  │ script_during │ │  ← once per record │            │
│  │  • read record (read_only if no changes)         │
│  │  • calculate / accumulate                        │
│  │  • UNLOAD record when done                       │
│  └──────┬───────┘ │                    │            │
│         │         └────────────────────┘            │
│         ▼                                           │
│  ┌──────────────┐                                   │
│  │ script_after  │  ← runs ONCE                     │
│  │  • write totals / summary                        │
│  │  • format final output                           │
│  │  • send notifications                            │
│  │  • close streams                                 │
│  └──────────────┘                                   │
└─────────────────────────────────────────────────────┘
```

---

## Two Critical Rules

### 1. Unload Records After Processing

Each record must be **unloaded** after `script_during` completes for that record. Holding all records in memory while iterating defeats the purpose of record-at-a-time processing. The pattern:

```
load record → process → accumulate results → unload record → next
```

Not:

```
load all records → process all → (memory exhaustion on large sets)
```

This applies to printing 10 invoices or processing 10,000 inventory adjustments. The discipline is the same.

### 2. Read-Only Access When Records Are Not Changed

If `script_during` only reads data (totals, reports, analysis, exports), the record must be accessed **read_only**. This:

- Prevents accidental writes during report runs
- Allows concurrent report execution without locking
- Makes the report's intent explicit — read vs. read-write

Only reports that intentionally modify records (tally calculations written back, status updates, batch operations) should open records for write.

---

## How Users Configure Report Scripts

Report scripts are stored in the `reports` table as Report records. Users interact with them through:

1. **Alice Dashboard → Reports tab** — browse available reports per model
2. **databrowser detail view** — edit `script_before`, `script_during`, `script_after` fields directly
3. **Report menu on any model page** — click Reports button, select a report, run it against the current selection

### Built-in vs. User Reports

Built-in reports (shipped with WC3 or synced from WC_HQ) can **lock** `script_before` and `script_after` — the setup and teardown are protected. Users customize only `script_during` — the business logic phase. This prevents users from breaking the report's infrastructure while giving them full control over what happens to each record.

| Field | Built-in (locked) | User report |
|-------|--------------------|-------------|
| `script_before` | Protected — setup logic | Fully editable |
| `script_during` | **Open to user** | Fully editable |
| `script_after` | Protected — output logic | Fully editable |

### Report Record Fields

| Field | Purpose |
|-------|---------|
| `name` | Display name in report menu |
| `model_name` | Which model this report applies to (contact, order, invoice, etc.) |
| `category` | Menu grouping: report, tally, dashboard, summary, export, utility |
| `output_type` | What it produces: print, screen, email, api, json, export, label, merge |
| `script_before` | Pre-processing setup (TextField) |
| `script_during` | Per-record business logic (TextField) |
| `script_after` | Post-processing output (TextField) |
| `config` | Extended config JSON: endpoint_url, template, parameters |
| `role_required` | RBAC — which roles can see/run this report |
| `security_level` | 0 = unrestricted, higher = more restricted |

---

## Examples

### Tally Report (read-only, accumulate, write summary)

```
script_before:  total = 0; count = 0; open output
script_during:  read_only; total += record.amount; count += 1; unload record
script_after:   write "Total: {total}, Count: {count}, Avg: {total/count}"; close output
```

### Batch Status Update (read-write)

```
script_before:  updated = 0; errors = []
script_during:  record.status = 'archived'; save; updated += 1; unload record
script_after:   write "Updated {updated} records, {len(errors)} errors"; notify admin
```

### Statement of Account (read-only, grouped output)

```
script_before:  current_customer = None; page_break = False; open PDF
script_during:  read_only; if customer changed: write subtotal, page break; 
                accumulate line; unload record
script_after:   write final subtotal; close PDF; return document
```

---

## Flowchart

See `readmes/charts/flowcharts/wc3-report-script-pipeline.dot` for the visual.

---

## Related

- `readmes/topics/reports-and-dashboards.md` — full report library (35 standard reports, 7 dashboards)
- `readmes/charts/flowcharts/wc3-report-output.dot` — document routing (PDF/email/API/sync)
- `readmes/charts/flowcharts/wc3-document-template.dot` — template-driven save with scriptBefore/scriptAfter
- `apps/core/models/report.py` — Report model definition
- `apps/core/services/parade_of_reports.py` — Alice's report onboarding parade
