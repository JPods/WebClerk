# 71 — Advance Chimney WC2→WC3 Conversion
**Created:** 2026-08-21
**Status:** In progress — testing week, cutover 2026-08-28
**Owner:** Bill James
**Participants:** Claude Code, Allie, Alice

---

## Objective

Convert Advance Chimney's WC2 (4D) production database to WC3 (Django/PostgreSQL).
Deploy at `advchm.webclerk.com` on Andi for testing this week.
Fresh dump and real cutover on Friday 2026-08-28.

---

## Timeline

| Date | What |
|------|------|
| 2026-08-21 | Dumps received, audit baselines computed, conversion project started |
| 2026-08-21 → 08-27 | Testing week — Advance Chimney staff test at advchm.webclerk.com (READ_ONLY_MODE) |
| 2026-08-28 (Friday) | Bill runs fresh `19Convert_ExportAllData()` on WC2, hands dump to Claude, final conversion + deploy |

---

## Data Dumps

Three WC2 dumps at `~/Allie/conversions/wc2_dump/`:

| Dump | Tables | Records | Pattern |
|------|--------|---------|---------|
| `jit/` | 140 | ~1.4M | Distributor — 5,541 customers, few transactions |
| `demo/` | 140 | ~105K | Training — 37 customers, complete transaction cycles |
| `advchm/` | 140 | 1.97M | **Production — 29,124 customers, $25M revenue, $78M proposal pipeline** |

All three share identical table names and field schemas. One converter handles all.

### Technical facts about the dumps

- **UTF-8 BOM** on every JSON file — 4D's export adds it. Must use `encoding='utf-8-sig'` in Python.
- **Plural→singular table name change** — Bill warned about this. Visible in the Ledger table:
  - `tableName='Invoice'` (5,987 entries, $13,832.35 unapplied) — current/active
  - `tableName='Invoices'` (22,234 entries, $714.33 unapplied) — legacy, mostly closed
  - `tableName='Payment'` (31,859 entries) — current
  - `tableName='Payments'` (18,037 entries) — legacy
  - Converter must normalize both to singular.
- **41 Ledger entries with tableName `00/00/00`** — garbage data, zero balance, skip.
- **Export method:** `19Convert_ExportAllData()` in 4D — one click, all tables as JSON arrays. See `readmes/56-wc2-data-export.md`.

---

## advchm Audit Baseline

These numbers are the conversion acceptance test. After conversion to WC3, the same sums must hold.

```
OPEN ORDERS
  Total orders:            37,617
  Open orders (backlog>0):    292
  Open order total:      $    525,291.98
  Open backlog amount:   $    471,557.24
  Lines with backlog:       7,428  (qty: 31,526.24)

UNPAID INVOICES
  Total invoices:          29,077
  Unpaid (balanceDue!=0):      62
  Unpaid balance:        $     13,832.35
  All invoices total:    $ 24,536,092.34

UNAPPLIED PAYMENTS
  Total payments:          31,842
  With unapplied amt:         407
  Unapplied total:       $    390,302.41
  All payments total:    $ 25,414,260.40

UNRECEIVED PURCHASE ORDERS
  Total POs:                7,188
  Open POs (backlog>0):     1,021
  Open PO total:         $    541,634.79
  Open PO backlog:       $    513,894.51
  Lines unreceived:         7,339  (qty: 12,737.55)

INVENTORY LEVELS (from Item)
  Total items:             36,788
  Items with qty on hand:   1,305
  Total on hand:              -5,342.00  (negative = adjustments/returns)
  Total on sales order:       -2,367.57
  Total on PO:                 5,201.35

LEDGER CROSS-CHECK
  Total ledger entries:    78,158
  Ledger unapplied total: $   -448,697.14  (net credit position)

RECONCILIATION
  Invoice.balanceDue:        $     13,832.35
  Payment.amountAvailable:   $    390,302.41
  Net AR (inv - pay):        $   -376,470.06
```

---

## Core Conversion Tables

These WC2 tables map to WC3 models:

| WC2 Table | Records | WC3 Target | Notes |
|-----------|---------|------------|-------|
| Customer | 29,124 | Contact + Organization | 155 fields; `customerID` is natural key |
| Contact | 16,195 | Contact (linked to org) | |
| Vendor | 67 | Organization (type=vendor) | |
| Item | 36,788 | Item + ItemVariant | 142 fields; `itemNum` is natural key |
| ItemSpec | 23,648 | Item metadata/config | |
| ItemPriceMatrix | 918 | pricing tiers | |
| ItemXRef | 3,459 | cross-references | |
| Order | 37,617 | Order | `idNum` is document number |
| OrderLine | 192,378 | OrderLine | `idNumOrder` links to parent |
| Invoice | 29,077 | Invoice | |
| InvoiceLine | 152,673 | InvoiceLine | |
| Proposal | 21,152 | Proposal | |
| ProposalLine | 200,851 | ProposalLine | |
| PO | 7,188 | Purchase | |
| POLine | 25,851 | PurchaseLine | |
| POReceipt | 1,883 | receiving records | |
| Payment | 31,842 | Payment | |
| Ledger | 78,158 | LedgerEntry | Audit checksum source |
| GLAccount | 25 | GLAccount | |
| BOM / BOMD | 16 / ? | BillOfMaterials | |
| InventoryD | 148,247 | inventory levels | |
| Rep | ? | Contact (role=rep) | |
| Employee | 2,447 | Contact (role=employee) | |

### Tables to skip (scrub)

| Table | Records | Why skip |
|-------|---------|----------|
| TallyResult | 16,081 | Reporting cache — WC3 recomputes |
| TallyChange | 57,798 | Change tracking — WC3 has its own |
| TallySummary/Master | varies | Reporting cache |
| zzzWord | 538,422 | Keyword index — WC3 rebuilds |
| CashD / CashJournal | 31,898 / 11,790 | Cash register detail — derive from Payment |
| SalesJournal / PurchaseJournal | 23,403 / ? | Journal entries — derive from Ledger |
| EventLog | 89,019 | System log — no conversion value |
| All zzz-prefixed tables | varies | System/utility — WC3 has its own |
| Counter/CounterPending | varies | Sequence generators — WC3 uses Django |
| FC | 8,475 | Form configurations — WC3 uses Settings |
| Archive | 3,708 | Archived records — evaluate separately |

---

## Deployment on Andi

Following the pattern of `webclerk3-demo.service` (port 8001, commerce_demo DB):

| Setting | Value |
|---------|-------|
| Subdomain | `advchm.webclerk.com` |
| Database | `commerce_advchm` on Andi PostgreSQL |
| Service | `webclerk3-advchm.service` (Gunicorn on new port, e.g. 8002) |
| .env | Same as production but `LOCAL_DATABASE_NAME=commerce_advchm`, `READ_ONLY_MODE=True` |
| Nginx | New `server` block or `location` for advchm subdomain → proxy to :8002 |
| Cloudflare | CNAME `advchm` → Andi's CF tunnel or IP |
| Credentials | Advance Chimney staff get UserProfile records with appropriate permissions |
| READ_ONLY_MODE | True during testing week, False after Friday cutover |

### Deploy steps

1. Create `commerce_advchm` database on Andi
2. Copy code directory from webclerk3 to webclerk3-advchm
3. Create `.env` with advchm database credentials
4. Run migrations on `commerce_advchm`
5. Create `webclerk3-advchm.service` (Gunicorn on port 8002)
6. Add Nginx server block for `advchm.webclerk.com`
7. Add Cloudflare DNS CNAME `advchm` → andi-tunnel UUID
8. Update cloudflared config: `advchm.webclerk.com` → `localhost:8002` (BEFORE wildcard rule)
9. Run `import_wc2 import --fast` to load WC2 data
10. **Copy Settings from Mac** (85 records — layouts, panels, views, print templates)
11. **Copy Reports from Mac** (57 records — report definitions)
12. Create user accounts for Advance Chimney staff
13. Restart services, verify

### Settings and Reports — Copy from Mac (not Andi main)

The authoritative Settings and Reports are on Bill's Mac (`commerce_expert`), not
on Andi's main database (which accumulates junk). Always copy from Mac.

```bash
# Settings (85 records — layouts, views, panels, print templates, keyword configs)
COLS=$(psql -d commerce_expert -t -A -c "
  SELECT string_agg(column_name, ', ' ORDER BY ordinal_position)
  FROM information_schema.columns
  WHERE table_name = 'settings' AND table_schema = 'public';
")
psql -d commerce_expert -c "COPY (SELECT $COLS FROM settings) TO '/tmp/settings_mac.csv' WITH CSV HEADER"
rsync -avz /tmp/settings_mac.csv andi@192.168.1.114:/tmp/settings_mac.csv

ssh andi@192.168.1.114 "sudo -u postgres psql -d commerce_advchm -c '
  TRUNCATE settings CASCADE;
  ALTER TABLE settings DISABLE TRIGGER ALL;
' && \
sudo -u postgres psql -d commerce_advchm -c \"COPY settings FROM '/tmp/settings_mac.csv' WITH CSV HEADER\" && \
sudo -u postgres psql -d commerce_advchm -c '
  ALTER TABLE settings ENABLE TRIGGER ALL;
  SELECT setval($$settings_id_seq$$, (SELECT MAX(id) FROM settings));
'"

# Reports (57 records — report definitions)
COLS=$(psql -d commerce_expert -t -A -c "
  SELECT string_agg(column_name, ', ' ORDER BY ordinal_position)
  FROM information_schema.columns
  WHERE table_name = 'reports' AND table_schema = 'public';
")
psql -d commerce_expert -c "COPY (SELECT $COLS FROM reports) TO '/tmp/reports_mac.csv' WITH CSV HEADER"
rsync -avz /tmp/reports_mac.csv andi@192.168.1.114:/tmp/reports_mac.csv

ssh andi@192.168.1.114 "sudo -u postgres psql -d commerce_advchm -c '
  TRUNCATE reports CASCADE;
  ALTER TABLE reports DISABLE TRIGGER ALL;
' && \
sudo -u postgres psql -d commerce_advchm -c \"COPY reports FROM '/tmp/reports_mac.csv' WITH CSV HEADER\" && \
sudo -u postgres psql -d commerce_advchm -c '
  ALTER TABLE reports ENABLE TRIGGER ALL;
  SELECT setval($$reports_id_seq$$, (SELECT MAX(id) FROM reports));
'"
```

**Why Mac, not Andi main:**
- Mac has 85 curated Settings; Andi main had 503 (accumulated junk)
- Settings and Reports define the application behavior — they must come from the development source
- This applies to every new customer instance, not just advchm

### Company Profile — Populate from WC2 Default Record

The `company-profile` Setting (purpose=`wc:company_profile`) must be populated with
data from the WC2 `Default.json` record. This is the company identity — name, address,
phone, tax ID, default terms, shipping, aging periods.

```bash
# 1. Read Default.json from dump
# 2. Map WC2 fields to config.company structure:
#    company → company.name / company.legal_name
#    address1/2, city, state, zip → company.address.street1/2, city, state, zip
#    phone, fax → company.phone, company.fax
#    taxID → company.tax_id
#    terms → terms.default_terms
#    shipVia1 → shipping.default_ship_via
#    fob → shipping.default_fob
#    gracePrd1/2/3 → aging.grace_period_1/2/3
#    lateFreq → aging.late_notice_frequency
#    typeSale → pricing.default_price_level
# 3. Build JSON, write to file, update via pg_read_file
```

**The full chain for every WC2→WC3 conversion:**

1. **Default.json → `company-profile` Setting `config.company`** — company name, address, phone, tax ID
2. **Default.json → `company-profile` Setting `config.original`** — preserve the entire Default record
3. **Default.json → `config.terms`, `config.shipping`, `config.aging`, `config.pricing`** — business defaults
4. **Match the self-customer OrgBase** — find or create the OrgBase record where `display_name` matches the company name, `org_type='customer'`
5. **Link `company-profile` Setting → self-customer** via `org_id`
6. **Create an Employee OrgBase** — `org_type='employee'`, linked to the company
7. **WC2 Employee records → Contact records** — all linked to the self-customer OrgBase via `customer_id` and to the Employee OrgBase via `employee_id`
8. **WC2 Contact records already imported** — verify they are linked to the correct customer OrgBase via `customerID` → `customer_id` FK

**Schema note:** If Mac has columns that Andi doesn't (or vice versa due to migration timing),
set defaults on missing columns before COPY:
```sql
ALTER TABLE settings ALTER COLUMN explanation SET DEFAULT '';
ALTER TABLE settings ALTER COLUMN paths SET DEFAULT '{}';
```

---

## Conversion Pipeline

```
advchm/*.json (UTF-8 BOM)
    │
    ▼
Read with utf-8-sig → normalize table names (plural→singular)
    │
    ▼
Skip scrub tables (tally, zzz, journals, logs)
    │
    ▼
Map WC2 fields → WC3 schema per table
    │
    ▼
Compute audit baseline from raw data
    │
    ▼
Assemble bundle.json (WC3 schema, natural keys, UTC datetimes)
    │
    ▼
Verify: bundle audit sums == raw data audit sums
    │
    ▼
Apply to commerce_advchm on Andi
```

No separate metric files needed — the audit baseline is computed directly from the dump JSON.

---

## Running the Audit

```python
# From any session — run against any dump folder:
python3 -c "
import json
folder = '/Users/williamjames/Allie/conversions/wc2_dump/advchm'
# ... (audit script computes open orders, unpaid invoices,
#      unapplied payments, unreceived POs, inventory levels,
#      ledger cross-check, reconciliation)
"
```

The full audit script was run interactively on 2026-08-21. Build a permanent version
in `~/Allie/conversions/scripts/audit_dump.py`.

---

## Key Relationships in WC2 Data

- `customerID` — natural key linking Customer, Contact, Order, Invoice, Payment, Ledger
- `idNum` — document number on transactions (Order, Invoice, PO, Payment)
- `idNumOrder` — links OrderLine→Order, Invoice→Order, PO→Order
- `idNumInvoice` — links InvoiceLine→Invoice, Payment→Invoice
- `idNumPO` — links POLine→PO
- `itemNum` — links OrderLine/InvoiceLine/POLine→Item, InventoryD→Item
- `vendorID` — links PO→Vendor
- `repID` — links Order/Invoice→Rep

---

## WC2 Field → WC3 JSON Packing Map

This is the critical section — WC2 has ~155 flat fields per table that pack into
WC3's structured JSON envelopes. Bill proofs this.

### Customer (WC2) → OrgBase (WC3, org_type='customer')

**Scalar fields (direct mapping):**

| WC2 Field | WC3 Field | Notes |
|-----------|-----------|-------|
| customerID | ida | Natural key — used for all FK lookups |
| company | display_name | Also accessible as `.company` property |
| phone | phone | |
| email | email | |
| address1 + address2 + city + state + zip | address_full | Concatenated for display |
| domain | domain | |
| terms | terms | |
| typeSale | price_level | A, B, C, D pricing tier |
| dateRetired | status, is_active | retired → status='retired', is_active=False |
| taxExemptid | tax_exempt_code | |

**Packed into `financial` JSON:**

| WC2 Field | JSON path | Notes |
|-----------|-----------|-------|
| creditLimit | financial.credit.limit | |
| highCredit | financial.credit.used | |
| creditApproval | financial.credit.approved | |
| balanceCurrent | financial.aging.current | Aging snapshot |
| balPastPeriod1 | financial.aging.period_1 | |
| balPastPeriod2 | financial.aging.period_2 | |
| balPastPeriod3 | financial.aging.period_3 | |
| balanceDue | financial.aging.balance_due | |
| futureDue | financial.aging.future_due | |
| salesMTD | financial.sales.mtd | |
| salesYTD | financial.sales.ytd | |
| salesLastYr | financial.sales.last_yr | |
| salesAllTime | financial.sales.all_time | |
| lastSaleDate | financial.sales.last_date | |
| lastSaleAmount | financial.sales.last_amount | |
| lastPayDate | financial.payments.last_date | |
| lastPayAmount | financial.payments.last_amount | |
| daysAvgPaid | financial.payments.days_avg_paid | |
| costsMTD | financial.costs.mtd | |
| costsYTD | financial.costs.ytd | |
| costsAllTime | financial.costs.all_time | |

**Packed into `config.original`:** All remaining WC2 fields preserved as-is.

**Not mapped (available in config.original if needed):**
- profile1-7 — user-defined fields
- o-suffix fields (generalo, historyo, etc.) — mostly empty; generalo has keyTags UUID
- shipTo, shipVia, shipInstruct — shipping defaults
- repID, salesNameID — need FK resolution to rep OrgBase
- adSource, zone, territory — marketing/geography

---

### Item (WC2) → Item (WC3)

**Scalar fields:**

| WC2 Field | WC3 Field | Notes |
|-----------|-----------|-------|
| itemNum | sku | Natural key (case-insensitive unique) |
| description | name | Truncated to 160 chars |
| descriptionDetail | description | Full text description |
| unitOfMeasure | uom | |
| vendorID | vendor_id | FK to OrgBase via lookup |
| mfrID | manufacturer_id | FK to OrgBase via lookup |
| retired | is_active | inverted: retired=True → is_active=False |

**Packed into `price` JSON:**

| WC2 Field | JSON path | Notes |
|-----------|-----------|-------|
| priceA | price.base, price.retail | Same value — price level A = retail |
| priceMSR | price.msrp | |
| priceB | price.wholesale | Price level B |
| priceC | price.distributor | Price level C |
| priceD | price.sample | Price level D |

**Packed into `cost` JSON:**

| WC2 Field | JSON path | Notes |
|-----------|-----------|-------|
| costLastInShip | cost.last | Last receipt cost |
| costAverage | cost.avg | Moving average cost |

**Packed into `quantity` JSON:**

| WC2 Field | JSON path | Notes |
|-----------|-----------|-------|
| qtyOnHand | quantity.on_hand | |
| qtyOnSalesOrder | quantity.on_so | |
| qtyOnPo | quantity.on_po | |
| qtyAllocated | quantity.allocated | |
| qtyAvailable | quantity.available | |
| qtyOnWO | quantity.on_wo | Work order qty |

**Packed into `flags` JSON:**

| WC2 Field | JSON path | Notes |
|-----------|-----------|-------|
| backOrder | flags.back_order_allowed | |
| discountable | flags.discountable | |
| linked | flags.linked | |
| notTracked | flags.not_tracked | |
| pacing | flags.pacing | |
| printNot | flags.print_suppressed | |
| serialized | flags.serialized | |
| tallyByType | flags.tally_by_type | |

**Packed into `gls` JSON:**

| WC2 Field | JSON path | Notes |
|-----------|-----------|-------|
| salesGlAccount | gls.revenue | |
| costGLAccount | gls.cogs | |
| inventoryGlAccount | gls.inventory | |

---

### Transaction Headers (Order, Invoice, Proposal, PO) → WC3 equivalents

All transaction headers use the same packing pattern:

**Scalar fields:**

| WC2 Field | WC3 Field | Notes |
|-----------|-----------|-------|
| idNum | ida | Document number |
| customerID | customer_id | FK via lookup |
| company | company | |
| attention | attention | |
| address1+2+city+state+zip | address_full | |
| email | email | |
| phone | phone | |
| terms | terms | |
| shipVia | ship_via | |
| dateDocument | dt_created | Converted to epoch ms |
| total | total | Decimal field |
| balanceDue | balance | Decimal field |

**Packed into `totals` JSON:**

| WC2 Field | JSON path | Notes |
|-----------|-----------|-------|
| amount | totals.subtotal | Pre-tax subtotal |
| salesTax | totals.tax | |
| shipTotal / shipFreightCost | totals.shipping | |
| total | totals.total | |
| balanceDue | totals.balance | |
| totalCost | totals.cost | |
| (total - balanceDue) | totals.received | Computed |

---

### Transaction Lines (OrderLine, InvoiceLine, ProposalLine, POLine)

**Packed into `item` JSON:**

| WC2 Field | JSON path | Notes |
|-----------|-----------|-------|
| itemNum | item.ida_item | |
| (looked up) | item.item_id | FK to Item.pk |
| description | item.description | |
| unitOfMeasure | item.unit_measure | |
| lineNum | item.line_number | |

**Packed into `quantity` JSON:**

| WC2 Field | JSON path | Notes |
|-----------|-----------|-------|
| qty | quantity.active, quantity.staged | The verb of the document |
| qtyBackLogged / qtyRemain | quantity.remaining | |

**Packed into `price` JSON (sell-side lines only):**

| WC2 Field | JSON path | Notes |
|-----------|-----------|-------|
| unitPrice / price | price.unit, price.unit_base | |
| discount | price.discount_percent | |
| extendedSell / amount | price.extended | |

**Packed into `cost` JSON:**

| WC2 Field | JSON path | Notes |
|-----------|-----------|-------|
| unitCost / costEach | cost.unit, cost.unit_base | |
| extendedCost | cost.extended | |

---

### Payment (WC2) → Payment (WC3)

| WC2 Field | WC3 Field / JSON | Notes |
|-----------|-----------------|-------|
| idNum | ida | |
| customerID | customer_id | FK via lookup |
| amount | total | Decimal |
| amountAvailable | balance | Decimal — unapplied amount |
| complete | status | True→'complete', False→'released' |
| dateDocument | dt_created | Epoch ms |
| typePayment | config.payment_type | |
| checkNum | config.check_num | |
| bankDeposit | config.bank_deposit | |
| idNumInvoice | parent_id + parent_model='invoice' | FK link |
| idNumOrder | parent_id + parent_model='order' | Fallback FK link |

---

### Ledger (WC2) → LedgerEntry (WC3)

All ledger data goes into `config` JSON — the Ledger model is TBD (may need schema work):

| WC2 Field | JSON path | Notes |
|-----------|-----------|-------|
| tableName | config.wc2_table_name | Normalized: 'Invoices'→'Invoice' |
| tableNum | config.wc2_table_num | |
| docRefid | config.doc_ref | |
| terms | config.terms | |
| unAppliedValue | config.unapplied_value | **Audit checksum field** |
| origValue | config.original_value | |
| discntPotential | config.discount_potential | |

---

## Open Questions

- How to handle the `o`-suffix fields (`generalo`, `historyo`, `commo`, `shipo`, etc.) — likely 4D object fields (JSON blobs). Need to inspect structure and decide what maps to WC3 config/refs/metadata.
- Inventory negative on-hand (-5,342) — flag to Advance Chimney, not a conversion blocker.
- 155 fields on Customer → most map to WC3 `config.original` (preserve everything, map what matters).
- Customer aging fields (`balanceCurrent`, `balPastPeriod1-3`) — are these snapshots or should WC3 recompute from Ledger?
