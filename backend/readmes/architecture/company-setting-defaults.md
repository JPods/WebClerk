# Company Setting Defaults

**Setting record:** id=438, purpose=`company_profile`, parent_model=`setting`

This is the single source of truth for company-wide defaults. Every WC3 installation
has exactly one. Alice reviews these during onboarding — each section affects how
the system behaves from day one.

## How It Works

The Setting record holds a JSON `config` object with 15 sections. Code reads these
at runtime — no restart needed after changes. The cascade:

1. **Per-record override** (e.g., item.config.costing_method) — wins if set
2. **Company default** (this Setting) — fallback
3. **Hardcoded default** — final fallback if neither exists

Edit in databrowser: `/db/setting?id=438`

---

## Sections

### company

Who you are. Prints on every document.

| Key | Type | Default | What it controls |
|-----|------|---------|-----------------|
| `name` | string | "" | Company name on documents, emails, headers |
| `legal_name` | string | "" | Legal entity name (contracts, tax forms) |
| `email` | string | "" | Primary contact email |
| `phone` | string | "" | Primary phone |
| `fax` | string | "" | Fax number (legacy, still on some POs) |
| `website` | string | "" | Company website URL |
| `tax_id` | string | "" | Tax ID / EIN |
| `registration_number` | string | "" | Business registration (non-US) |
| `tagline` | string | "" | Tagline on documents |
| `address.street1` | string | "" | Street address line 1 |
| `address.street2` | string | "" | Street address line 2 |
| `address.city` | string | "" | City |
| `address.state` | string | "" | State/province |
| `address.zip` | string | "" | Postal code |
| `address.country` | string | "US" | Country code |

**Alice onboarding:** Verify all fields are filled. Missing phone or email = broken
documents. Missing tax_id = broken tax reports.

---

### inventory

How inventory is valued and tracked. **This is structural — set before any stock moves.**

| Key | Type | Default | What it controls |
|-----|------|---------|-----------------|
| `costing_method` | string | "average" | Company default: `fifo`, `lifo`, `average`, or `last`. Items can override in `item.config.costing_method`. |
| `costing_method_options` | array | ["fifo","lifo","average","last"] | Valid choices (for UI dropdowns) |
| `track_inventory` | bool | true | Whether to track on-hand quantities |
| `track_serial_numbers` | bool | true | Whether to track serial numbers on items |
| `unit_cost_precision` | int | 5 | Decimal places for unit cost (5 = $1.23456) |
| `item_qty_precision` | int | 0 | Decimal places for quantities (0 = whole units) |

**Alice onboarding:** Ask the customer which costing method their accountant requires.
This determines how BOM builds, shipments, and adjustments calculate cost. Changing
it after transactions exist is an accounting event — flag it.

**How costing_method flows:**
- `_get_costing_method(item)` checks item.config first, then this setting
- `consume_by_item_method()` dispatches to fifo/lifo based on the result
- BOM builds use this to drain child component layers and calculate build cost
- The build cost receipts into the parent item's inventory as a new layer
- `recalc_average_cost()` weighted-averages it into existing inventory

---

### pricing

How prices display and calculate.

| Key | Type | Default | What it controls |
|-----|------|---------|-----------------|
| `unit_price_precision` | int | 2 | Decimal places for unit prices |
| `total_precision` | int | 2 | Decimal places for line/order totals |
| `minimum_margin` | decimal | 0 | Floor margin % — warns if a line falls below this |
| `use_price_matrix` | bool | true | Enable price matrix (customer-specific pricing) |
| `price_levels.A` | string | "Retail" | Name for price level A |
| `price_levels.B` | string | "Wholesale" | Name for price level B |
| `price_levels.C` | string | "Distributor" | Name for price level C |
| `price_levels.D` | string | "Sample" | Name for price level D |

**Alice onboarding:** Confirm price level names match the customer's terminology.
These labels appear in dropdowns, reports, and on printed documents. WC2 origin:
APriceName, BPriceName, CPriceName, DPriceName.

---

### order_defaults

Defaults applied to new transactions.

| Key | Type | Default | What it controls |
|-----|------|---------|-----------------|
| `terms` | string | "n30" | Default payment terms for new orders |
| `price_level` | string | "wholesale" | Default price level for new orders |
| `days_to_ship` | int | 5 | Default estimated shipping days |
| `default_warehouse` | string | "" | Default warehouse for inventory operations |
| `require_po_number` | bool | false | Require PO number on orders |

**Alice onboarding:** These populate every new order. Wrong defaults = manual correction
on every transaction.

---

### shipping

Shipping behavior.

| Key | Type | Default | What it controls |
|-----|------|---------|-----------------|
| `default_carrier` | string | "UPS" | Default carrier for new shipments |
| `fob` | string | "" | Default FOB point (prints on POs and orders) |
| `auto_calc_freight` | bool | true | Auto-calculate freight on orders |
| `no_weekend_ship` | bool | false | Suppress shipping on weekends |
| `ship_condition` | string | "" | Default shipping condition text |

---

### commission

How sales commission calculates.

| Key | Type | Default | What it controls |
|-----|------|---------|-----------------|
| `commission_on_margin` | bool | true | Calculate commission on margin (sale - cost) |
| `commission_on_amount` | bool | false | Calculate commission on sale amount (ignores cost) |

**Alice onboarding:** One or the other, not both. Margin-based is more common.
The rep's rate × the basis (margin or amount) × any level factor = commission per line.

---

### ar_aging

Accounts receivable aging periods and statement messaging.

| Key | Type | Default | What it controls |
|-----|------|---------|-----------------|
| `grace_period_1` | int | 35 | Days before first aging bucket |
| `grace_period_2` | int | 65 | Days before second aging bucket |
| `grace_period_3` | int | 95 | Days before third aging bucket |
| `late_followup_days` | int | 10 | Days between follow-up actions on late invoices |
| `finance_charge_pct` | decimal | 1.1 | Monthly finance charge percentage |
| `heading_period_1` | string | (see below) | Statement heading for 30-day past due |
| `closing_period_1` | string | (see below) | Statement closing for 30-day past due |
| `heading_period_2` | string | (see below) | Statement heading for 60-day past due |
| `closing_period_2` | string | (see below) | Statement closing for 60-day past due |
| `heading_period_3` | string | (see below) | Statement heading for 90-day past due |
| `closing_period_3` | string | (see below) | Statement closing for 90-day past due |

**Statement text defaults:**
- Period 1: "Our records show that we have not received payments for the invoice(s) listed below."
- Period 2: "These invoices are past due. No further orders will be shipped until we receive payment in full."
- Period 3: "These invoices are critically overdue. Immediate payment is required."

**Alice onboarding:** Review the tone. Some customers want softer language. The grace
periods should match the customer's actual terms — if they sell Net 30, period 1
should be 30-35 days, not 60.

---

### currency

Currency display.

| Key | Type | Default | What it controls |
|-----|------|---------|-----------------|
| `code` | string | "USD" | ISO 4217 currency code |
| `locale` | string | "en-US" | Locale for number formatting |
| `symbol` | string | "$" | Currency symbol for display |
| `decimal_places` | int | 2 | Decimal places for currency display |

---

### accounting

Accounting integration.

| Key | Type | Default | What it controls |
|-----|------|---------|-----------------|
| `package` | string | "" | Accounting package name (QuickBooks, Sage, etc.) |
| `export_format` | string | "csv" | Export format for GL journal entries |
| `default_division` | string | "" | Default division for GL coding |
| `fiscal_year_end_day` | int | 31 | Fiscal year end day |
| `fiscal_year_end_month` | int | 12 | Fiscal year end month |

---

### leads

Lead management timing.

| Key | Type | Default | What it controls |
|-----|------|---------|-----------------|
| `lead_response_days` | int | 20 | Target days to respond to a new lead |
| `recent_days` | int | 730 | How many days back counts as "recent" activity |

---

### logos

Company logos for documents and UI.

| Key | Type | Default | What it controls |
|-----|------|---------|-----------------|
| `primary` | string | "" | Primary logo (documents, headers) |
| `icon` | string | "" | Favicon / small icon |
| `watermark` | string | "" | Watermark for printed documents |
| `dark_theme` | string | "" | Logo variant for dark backgrounds |
| `email_banner` | string | "" | Banner image for email templates |

---

### print_defaults

Default print formatting.

| Key | Type | Default | What it controls |
|-----|------|---------|-----------------|
| `paper_size` | string | "letter" | Paper size (letter, A4) |
| `font_family` | string | "Helvetica" | Default font |
| `font_size` | int | 10 | Default font size |
| `margin_top/bottom/left/right` | decimal | 0.75-1.0 | Page margins in inches |
| `show_logo` | bool | true | Print company logo |
| `show_address` | bool | true | Print company address |
| `show_phone` | bool | true | Print phone number |
| `show_email` | bool | true | Print email |
| `show_website` | bool | true | Print website |
| `show_tax_id` | bool | false | Print tax ID on documents |
| `footer_text` | string | "" | Custom footer text |

---

### documents

Document template references.

| Key | Type | Default | What it controls |
|-----|------|---------|-----------------|
| `invoice_template` | string | "" | Default invoice print template |
| `proposal_template` | string | "" | Default proposal print template |
| `po_template` | string | "" | Default PO print template |
| `statement_template` | string | "" | Default statement print template |
| `packing_slip_template` | string | "" | Default packing slip template |
| `letterhead_template` | string | "" | Default letterhead template |

---

### alice_coaching

Alice's relationship with WC_HQ.

| Key | Type | Default | What it controls |
|-----|------|---------|-----------------|
| `wchq_level` | string | "receive_only" | Data sharing level with WC_HQ |
| `manufacturer_reporting` | string | "none" | Manufacturer reporting level |

---

### paths

File system paths.

| Key | Type | Default | What it controls |
|-----|------|---------|-----------------|
| `bundles.posted` | string | "bundles/posted/" | Path for posted bundle files |
| `bundles.unposted` | string | "bundles/unposted/" | Path for unposted bundle files |

---

### certificates

Placeholder for business certificates (insurance, licenses, compliance).

---

## Alice Onboarding Checklist

When Alice onboards a new WC3 customer, she reviews Setting 438 in this order:

1. **company** — Fill every field. This prints on everything.
2. **inventory.costing_method** — Ask the accountant. Set before any stock moves.
3. **pricing.price_levels** — Match the customer's language.
4. **order_defaults** — Match the customer's standard terms and warehouse.
5. **ar_aging** — Match grace periods to actual payment terms.
6. **commission** — Margin or amount? One or the other.
7. **currency** — Confirm locale and code.
8. **accounting** — Fiscal year end, export format for their accounting package.
9. **logos** — Upload before first document prints.
10. **print_defaults** — Paper size, margins, what to show.
11. **shipping** — Default carrier and FOB.
12. **leads** — Response target.

**What NOT to change after go-live without accounting review:**
- `inventory.costing_method` — changes how all future costs calculate
- `pricing.price_levels` — renames affect all existing records
- `accounting.fiscal_year_end_*` — affects year-end processing
- `ar_aging.grace_period_*` — changes which invoices appear in which aging bucket

---

## WC2 Origin

These defaults migrated from WC2's single Company record (Table 15, `[Company]`).
WC2 had ~150 fields in a flat record. WC3 organizes them into sections.

Skipped from WC2 (obsolete):
- Apple Events, modem dialing, 4D networking, CC hardware, window sizing,
  help paths, barcode preambles, cash drawer, memory allocation, ITK licenses,
  share paths, process delays, AuthNet test mode

Full WC2 field mapping preserved in Allie's session records for reference.

---

*Created 2026-08-06. Setting 438 in commerce_expert database.*
