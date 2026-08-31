# Journal Formatter — GL Export Tool

> **Location**: `tools/journal_formatter.html`
> **Type**: Standalone HTML+JS — no server, works offline
> **Video**: (pending — Bill recording)

---

## What It Does

Takes a `bundle.json` from WebClerk's GL Journal Export and produces a
file formatted for your accounting program. Same idea as Statement Sorter
but in reverse:

| Tool | Direction | Consumes | Produces |
|------|-----------|----------|----------|
| **Statement Sorter** | Inbound | Bank CSV/OFX | WC3 JSON |
| **Journal Formatter** | Outbound | WC3 bundle.json | QB / Xero / Sage file |

---

## How to Use

1. In WebClerk, export your GL journals for the period → downloads `bundle.json`
2. Open `journal_formatter.html` in any browser
3. Drop `bundle.json` onto the page
4. See your company name, period, entry count, debit/credit totals, balanced status
5. Pick your accounting program (remembered for next time)
6. Click Download — get the formatted file
7. Import into your accounting program

---

## Supported Accounting Programs

| Format | Program | File |
|--------|---------|------|
| `quickbooks_iif` | QuickBooks Desktop | `.iif` |
| `quickbooks_csv` | QuickBooks Online | `.csv` |
| `xero_csv` | Xero | `.csv` |
| `sage_csv` | Sage 50 / 100 | `.csv` |
| `freshbooks_csv` | FreshBooks | `.csv` |
| `csv` | Generic (any program) | `.csv` |

---

## bundle.json Schema

Every bundle carries the same structure whether from a standalone business
or a location in a multi-company network. The `source` field identifies
which company produced the entries — linked to the UUID of the
`Setting(purpose='wc:company_profile')` record.

```json
{
  "type": "gl_journal",
  "version": "1.0",
  "source": {
    "uuid": "df4a906e-740e-4964-8a50-5cae6fd9128e",
    "name": "JPods LLC",
    "ida": "company-profile"
  },
  "period": "2026-08",
  "dt_built": 1725120000000,
  "entries": [
    {
      "id": 136,
      "ida": "SJ-DEV-107-ASSET-AR-000",
      "account": "ASSET-AR-000",
      "debit": 349.95,
      "credit": 0.0,
      "type": "sales",
      "source_model": "invoice",
      "source_id": 107,
      "division": "",
      "batch_id": "",
      "note": "",
      "dt_created": 1787426686184
    }
  ],
  "totals": {
    "entry_count": 10,
    "total_debits": 1200.00,
    "total_credits": 1200.00,
    "balanced": true
  }
}
```

---

## Two Destinations, One Format

The same `bundle.json` serves both paths:

```
GL Journals → build_gl_journal_bundle() → bundle.json
                                              │
                               ┌──────────────┼──────────────┐
                               ↓                              ↓
                     Journal Formatter            Upstream HQ
                     (local download →            (Bundle record —
                      accounting program)          consolidation)
```

- **Standalone business**: Export → Journal Formatter → QuickBooks
- **Multi-location**: Export → send upstream to HQ → HQ downloads all
  locations' bundles → Journal Formatter → consolidated accounting file

HQ never loads journals into its own GL tables. They stay as Bundle
records until formatted for the accounting program.

---

## Adding a New Format

Edit `tools/journal_formatter.html`:

1. Add an entry to the `FORMATS` array (key, name, desc, ext, mime)
2. Add a converter function in the `converters` object
3. The converter receives the full bundle and returns a string

The bundle schema is stable — new formats just read entries and write
the target program's columns.

---

## Where It Lives in WebClerk

| Component | Location |
|-----------|----------|
| Bundle builder | `apps/sync/services/gl_journal_bundle.py` |
| Formatter tool | `tools/journal_formatter.html` |
| Existing GL export | `apps/accounts/services/journalize.py:export_journals()` |
| Accounting Connection seeds | `seed_connections.py` (conn-acct-quickbooks, conn-acct-xero) |
| Company Setting (source UUID) | `Setting(purpose='wc:company_profile')` |

---

*Built 2026-08-31. The Journal Formatter is a free, standalone tool.*
