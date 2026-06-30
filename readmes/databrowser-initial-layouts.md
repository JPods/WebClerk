# DataBrowser — Initial Layouts & Seed Data

**Created:** 2026-06-28
**Command:** `./bin/python manage.py seed_databrowser`

## Purpose

Every model in WebClerk3 gets a curated "initial" layout for the DataBrowser — a default set of list columns and detail fields, chosen in a deliberate order. This serves three purposes:

1. **Users see useful data immediately** — not raw field dumps. A new user opening the Customer model sees display_name, status, email, phone — not id, uuid, dt_created, version.

2. **Alice has a baseline** — when users submit their own layouts for bonus credit, Alice can compare against the initial layout to see what experienced users prioritize differently. Divergence from the initial layout is a signal about what matters in practice.

3. **Every table has at least one record** — fake records (marked `metadata.health = "fake"`, prefixed with "zz") let users explore the DataBrowser without needing real data. They sort to the bottom, they're filterable, and they're deletable.

## Usage

```bash
# Seed both layouts and fake records
./bin/python manage.py seed_databrowser

# Layouts only
./bin/python manage.py seed_databrowser --layouts

# Fake records only
./bin/python manage.py seed_databrowser --fakes

# Overwrite existing layouts with fresh initial versions
./bin/python manage.py seed_databrowser --layouts --force
```

## How Layouts Are Stored

Each model gets one `Setting` record:
- `purpose = "workbench_fields"`
- `parent_model = "<model_key>"` (e.g., "customer", "gl_account")
- `data` contains:
  - `list: string[]` — fields shown in the list table, in order
  - `detail: string[]` — fields shown in the detail pane, in order
  - `views: [{ name, list, detail, listWidths }]` — named saved layouts

The "initial" view is saved as a named layout inside `views[]` so it can always be loaded back even after a user customizes their current view.

## Layout Design Principles

**List view (5-8 fields):**
- Start with `id` — always need a reference
- Then the most identifying field: `display_name`, `name`, `email`, `account_number`
- Then status — users scan for active/inactive
- Then 2-3 business-critical fields per model type
- End with a date if space permits

**Detail view (12-20 fields):**
- All list fields plus deeper context
- Business fields before system fields
- JSON envelope fields (price, cost, totals) included for power users
- System fields (dt_created, dt_modified) at the end

**Field order matters:**
- Users scan left-to-right in lists, top-to-bottom in details
- The first field after `id` is the one they'll use to find what they need
- Group related fields (all contact info together, all financial together)

## Curated Layouts by Category

### Orgs (Customer, Vendor, Manufacturer, Employee, Rep)
**List:** id, display_name, status, email, phone, address_full, price_level
**Rationale:** Who are they, how do I reach them, what pricing tier. All orgs share the same OrgBase model so layouts are consistent.

### Transactions (Invoice, Order, Proposal, Purchase, WorkOrder)
**List:** id, ida, status, total, balance, dt_created, priority
**Rationale:** Where is it in the workflow, how much, when. Balance only on invoices.

### Products (Item)
**List:** id, ida, name, kind, status, uom, dt_created
**Rationale:** What is it, what type, is it active, how is it measured.

### Core (Contact)
**List:** id, email, name_first, name_last, company, title, role, phone
**Rationale:** People-first — email is the key identifier, then name, then affiliation.

### Core (Action)
**List:** id, ida, status, kanban_column, priority, percent_complete, project_name, dt_deadline
**Rationale:** Task management view — where is it, how urgent, when is it due.

### Accounts (GL Account)
**List:** id, account_number, name, type, category, division, used_for
**Rationale:** Chart of accounts browsing — number is the key, then classification.

### Accounts (Ledger)
**List:** id, value_original, value_available, dt_due, is_settled, source, model_name
**Rationale:** Aging view — how much, when due, is it paid.

## Fake Records

Fake records are created with:
- `ida` prefixed with `zz-fake-`
- `name` / `display_name` prefixed with `zz Fake`
- `metadata.health = "fake"`
- `email` using `@example.com` domain
- Minimal valid data (status=active, version=1, etc.)

The "zz" prefix ensures fakes sort to the bottom of alphabetical lists. Query `metadata__health='fake'` to find or delete them.

Line items (InvoiceLine, OrderLine, etc.) are skipped because they require parent FK references.

## Alice's Role

When users submit layouts via sync:
1. Alice compares the submitted layout against the "initial" layout for that model
2. Fields the user added that aren't in the initial layout → things we may have undervalued
3. Fields the user removed → things we may have overvalued
4. Field order changes → what users actually scan for first
5. Adoption rate of submitted layouts → democratic signal about what works

This is the same bottom-up signal loop as Small-Stings: users tell us what matters by what they choose, not by what they say.
