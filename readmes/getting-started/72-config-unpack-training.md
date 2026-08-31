# 72 — Config Unpack: Finding Your Data in WebClerk 3
**Created:** 2026-08-21
**Status:** Training script for video
**Owner:** Bill James
**Audience:** WC2→WC3 conversion customers

---

## What This Feature Does

When data is converted from WC2 (4D) to WC3, every field from the old system is
preserved in `config.original` on every record. Known-useful fields are automatically
extracted to named keys (like `config.rep`, `config.division`). But users will
discover they need fields that weren't pre-extracted.

The config_unpack tool lets users (or Alice) promote any field from `config.original`
to a named config key — instantly searchable, filterable, and visible in the databrowser.

**The learning loop:**
1. Import puts everything in `config.original` — nothing lost
2. Known-useful fields extracted at import time
3. Users discover they need more — ask Alice
4. Alice promotes on demand
5. Over time, useful fields float to the top, junk stays buried
6. Next import for the same source adds the useful ones automatically

---

## Training Video Script

**Title:** "Finding Your Data in WebClerk 3"
**Length:** ~2.5 minutes
**Setup:** Terminal with WC3 virtualenv active. Databrowser open in browser.

---

### Scene 1: "Your data is all here" (30 sec)

Show an Item record in the databrowser. Point to the `config` field. Expand it.
Show `config.original` — all 142 WC2 fields are right there.

> "Everything from WebClerk 2 came over. Nothing was lost. It's all in
> config.original on every record."

---

### Scene 2: "What's available?" (30 sec)

```bash
python manage.py config_unpack list item
```

Shows a table:

```
Field                          Count   Type      Sample
──────────────────────────────────────────────────────────────────────────────────────────
itemNum                         3315   str       ABC-123
description                     3315   str       Widget Assembly
barCode                         1200   str       0-12345-67890
mfrItemNum                      2800   str       MFR-456 ✓
vendorItemNum                   1900   str       V-789
...
```

> "This shows every field from your old system, how many records have it,
> and a sample value. The checkmark means it's already been promoted."

---

### Scene 3: "I need barCode visible" (30 sec)

```bash
python manage.py config_unpack promote item barCode --as bar_code
```

Output:
```
barCode → config.bar_code: 1200 updated, 0 skipped, 2115 empty
```

> "Now bar_code is a named field on every item that had one. You can search it,
> filter it, see it in the databrowser."

Switch to browser — refresh the Item record — show `config.bar_code` now visible
at the top level of config.

---

### Scene 4: "I want several fields" (20 sec)

```bash
python manage.py config_unpack promote item barCode ean warrantyDays
```

> "You can do several at once."

---

### Scene 5: "That field is junk, take it back" (20 sec)

```bash
python manage.py config_unpack demote item bar_code
```

Output:
```
config.bar_code: 1200 removed
```

> "The value is still safe in config.original. We just removed the shortcut."

---

### Scene 6: "Dry run first" (15 sec)

```bash
python manage.py config_unpack promote item barCode --as bar_code --dry-run
```

> "Add --dry-run to see what would happen without changing anything."

---

### Closing (15 sec)

> "Your old data is never lost. Tell Alice what you need, she promotes it.
> If it turns out to be junk, she demotes it. Over time, the useful fields
> float to the top and the noise stays buried."

---

## Commands Reference

| Command | What it does |
|---------|-------------|
| `config_unpack list <model>` | Show all fields in config.original with counts and samples |
| `config_unpack promote <model> <field> [--as key]` | Copy field from config.original to config.{key} |
| `config_unpack promote <model> <field1> <field2> ...` | Promote multiple fields at once |
| `config_unpack demote <model> <key>` | Remove a named config key (value stays in original) |
| Add `--dry-run` to any promote/demote | See what would happen without writing |

**Available models:** item, customer, vendor, contact, order, invoice, proposal,
purchase, payment, order_line, invoice_line, proposal_line, purchase_line

---

## How Alice Uses This

Alice can call the service directly from Python:

```python
from apps.conversion.services.config_unpack import (
    list_original_fields,
    unpack_field,
    unpack_fields,
    demote_field,
)

# See what's available
fields = list_original_fields('item', sample_size=200)

# Promote one field
result = unpack_field('item', 'barCode', config_key='bar_code')

# Promote several
result = unpack_fields('item', {
    'barCode': 'bar_code',
    'ean': 'ean',
    'warrantyDays': 'warranty_days',
})

# Demote junk
result = demote_field('item', 'bar_code')
```

Alice should track which fields get promoted across installations. Fields promoted
by 3+ customers become candidates for the import-time EXTRACT dicts (added to
CUSTOMER_EXTRACT, ITEM_EXTRACT, etc. in `import_wc2.py`).

---

## Config Structure

After import, every record's config looks like:

```json
{
    "profiles": {"1": "CSS-CUSTOMER", "2": "East"},
    "rep": "JM",
    "division": "East",
    "zone": "5",
    "bar_code": "0-12345-67890",
    "original": {
        "customerID": "ACME001",
        "company": "Acme Corp",
        "barCode": "0-12345-67890",
        "profile1": "CSS-CUSTOMER",
        "... all 155 WC2 fields ..."
    }
}
```

- **Named keys** (rep, division, bar_code) — searchable, filterable, visible
- **profiles** — user-defined classification fields from WC2
- **original** — complete WC2 record, always preserved until all kinks are worked out

---

## Technical Files

| File | What it does |
|------|-------------|
| `apps/conversion/services/config_unpack.py` | Service: list, unpack, demote |
| `apps/conversion/management/commands/config_unpack.py` | CLI command |
| `apps/conversion/management/commands/import_wc2.py` | WC2 importer with EXTRACT dicts |
| `readmes/flowcharts/wc2-customer-to-orgbase.svg` | Visual: Customer field packing |
| `readmes/flowcharts/wc2-item-to-item.svg` | Visual: Item field packing |
| `readmes/flowcharts/wc2-transaction-packing.svg` | Visual: Transaction field packing |
