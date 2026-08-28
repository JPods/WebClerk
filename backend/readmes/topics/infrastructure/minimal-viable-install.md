# Minimal Viable Installation — WebClerk3

**Created:** 2026-08-09
**Audience:** New WebClerk deployers (open source)

---

## Overview

A minimal viable WebClerk3 installation requires three layers:
1. **System configuration** — Settings, RBAC, reports, UI layouts
2. **Accounting foundation** — GL accounts, payment terms, currencies
3. **Demo data** (optional) — contacts, items, and complete transaction cycles

This document lists exactly what `seed_freshstart` and `seed_demo` create, so you know what's in the box.

---

## Layer 1: Fresh Start (`python manage.py seed_freshstart`)

This is the required foundation. Run it once on a new database after `migrate`.

| Seed Command | What It Creates | Why It's Needed |
|-------------|----------------|-----------------|
| `seed_field_access` | One Setting per model controlling which fields each role can see/edit | Without this, RBAC silently denies all access |
| `seed_company_settings` | Company-wide defaults: name, currency, tax, date format | Header info on every transaction and report |
| `seed_rbac_roles` | Role definitions: admin, manager, sales, warehouse, customer, vendor | Users need roles to access anything |
| `seed_gl_accounts` | Chart of accounts: assets (1000s), liabilities (2000s), equity (3000s), revenue (4000s), expenses (5000s) | Every invoice and payment needs GL accounts to post against |
| `seed_terms` | Payment terms: Net 10, Net 30, 2%10 Net 30, COD, Prepaid | Transactions need terms for aging and due dates |
| `seed_reports` | Report definitions: sales reports, aging, inventory, commissions | The reporting engine needs these definitions |
| `seed_databrowser` | DataBrowser layouts for all 61 models | The data browser needs initial column layouts |
| `seed_column_widths` | Default column widths for list views | Without these, all columns default to equal width |
| `seed_search_presets` | Saved searches: open orders, overdue invoices, active customers | Pre-built searches users expect |
| `seed_alice_layouts` | Alice's dashboard layouts and coaching cards | Alice needs these to function |
| `seed_select_lists` | Dropdown lists: states, countries, ship methods, UOM | Forms need these select options |
| `seed_qa_templates` | QA question templates for customer surveys | Quality module needs question structure |
| `seed_connections` | Agent communication channels, deploy targets | Sync and agent infrastructure |
| `seed_coaching` | Alice coaching content: help text, tooltips | In-app help system |
| `seed_wchq_settings` | WC_HQ data service configuration | DynamicCatalogs integration |
| `seed_collaborate_settings` | Multi-company collaboration defaults | Sync between WebClerk instances |
| `seed_model_definitions` | Consolidated model config: schemas, behaviors, layouts, select lists | Validation, API docs, form generation |
| `seed_serial_settings` | Serial number tracking configuration | Serial/lot tracking module |
| `seed_status_guards` | Transaction status transitions + journalized locks | Prevents illegal status changes (e.g., editing a posted invoice) |
| `seed_receivables_layouts` | Aged receivables report + customer statement print | AR reporting and statements |
| `seed_gl_defaults` | GL account mappings into items, orgs, payment methods | Auto-posting to correct accounts |

**After `seed_freshstart`, the database is ready for a company to enter their own data.**

---

## Layer 2: GL Accounts (created by `seed_gl_accounts`)

These are the minimum accounts needed for the full transaction cycle:

| Account | Type | Category | Used For |
|---------|------|----------|----------|
| 1000-Cash | Asset | cash | Payment receipts and disbursements |
| 1200-AR | Asset | receivables | Accounts receivable from invoices |
| 1300-Inventory | Asset | inventory | Inventory on hand |
| 2000-AP | Liability | payables | Accounts payable to vendors |
| 2100-SalesTaxPayable | Liability | payables | Sales tax collected from customers |
| 3000-Equity | Equity | equity | Owner's equity |
| 4000-Sales | Revenue | sales | Revenue from invoiced sales |
| 5000-COGS | Expense | cogs | Cost of goods sold |
| 5100-Expenses | Expense | expense | General operating expenses |

The actual `seed_gl_accounts` command creates a fuller chart — these are the load-bearing accounts that the transaction cycle requires.

---

## Layer 3: Demo Data (optional)

Two commands create a complete, realistic demo:

### `python manage.py seed_demo`

Creates the catalog and business entities:

| What | Count | Details |
|------|-------|---------|
| **Items** | 12 | Baseball equipment: bats, balls, gloves, bags, training aids, 1 kit with BOM |
| **Customers** | 5 | Retail store, academy, little league, dealer, school — each with different price levels (A/B/C) and terms |
| **Vendor** | 1 | National Baseball Supply |
| **Contacts** | 7 | One per customer + 2 at vendor |
| **BOM** | 4 entries | Little League Starter Kit → bat + glove + batting gloves + balls |

All ida values use `qqdemo-` prefix for easy identification and cleanup.

### `python manage.py seed_demo_transactions`

Creates 3 complete transaction cycles flowing through the entire system:

| Cycle | Customer | What They Bought | Total | Payment |
|-------|----------|-----------------|-------|---------|
| 1 | Riverside Sports (B) | 2 bats, 1 bag, 2dz balls | ~$528 | Full — check |
| 2 | Metro Baseball Academy (A) | 3 screens, 6 trainers, 3 gloves | ~$701 | Split 60/40 — Visa |
| 3 | Eastside Little League (C) | 12 starter kits, 6dz balls | ~$710 | Full — check |

Each cycle creates:
```
Proposal (status: complete)
  → Order (parent: proposal, status: released)
    → Invoice (parent: order, type: invoice, status: released)
      → Payment(s) (type: received, status: completed)
        → GL Journal entries (AR ↔ Sales, Cash ↔ AR)
```

**GL entries per cycle:**
- Invoice posted: debit 1200-AR / credit 4000-Sales (full amount)
- Each payment: debit 1000-Cash / credit 1200-AR (payment amount)
- Entries are batched (SJ-DEMO-01, -02, -03) and marked `is_posted=True`

---

## Complete Installation Sequence

```bash
# 1. Apply migrations
python manage.py migrate

# 2. Create superuser
python manage.py createsuperuser

# 3. Seed system configuration (required)
python manage.py seed_freshstart

# 4. Seed demo catalog data (optional)
python manage.py seed_demo

# 5. Seed demo transactions (optional — requires seed_demo first)
python manage.py seed_demo_transactions

# 6. Collect static files (production only)
python manage.py collectstatic --noinput
```

### Resetting Demo Data

```bash
# Remove demo transactions only (keeps items, contacts, orgs)
python manage.py seed_demo_transactions --force

# Remove all demo data (items, contacts, orgs, transactions)
python manage.py seed_demo --force
python manage.py seed_demo_transactions --force

# Nuclear option — full database reset and re-seed
python manage.py reset_database
python manage.py migrate
python manage.py seed_freshstart
python manage.py seed_demo
python manage.py seed_demo_transactions
```

---

## Downloadable Base Data Structure

For deployers who want to start fresh without running seed commands, a pg_dump of the seeded database is available:

```bash
# Create the base dump (on a seeded database)
pg_dump -Fc commerce_expert -f webclerk3-base-install.dump

# Restore on a new server
sudo -u postgres createdb commerce_expert
sudo -u postgres pg_restore -d commerce_expert webclerk3-base-install.dump
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE commerce_expert TO webclerk;"
sudo -u postgres psql -d commerce_expert -c \
  "GRANT ALL ON ALL TABLES IN SCHEMA public TO webclerk; \
   GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO webclerk;"
```

---

## What You Get After Installation

| Feature | Ready? | Notes |
|---------|--------|-------|
| Contact management | Yes | Create, edit, search contacts and organizations |
| Item catalog | Yes | Products with multi-level pricing, cost tracking |
| Proposals | Yes | Create, price, send proposals |
| Orders | Yes | Convert proposals to orders |
| Invoices | Yes | Generate invoices from orders |
| Payments | Yes | Record payments against invoices |
| GL journals | Yes | Automatic journal entries on invoice/payment |
| Aged receivables | Yes | AR aging report |
| DataBrowser | Yes | Browse and edit any model's data |
| Alice (AI assistant) | Yes | In-app help, pattern recognition |
| RBAC | Yes | Role-based field access control |
| Sync | Configured | Connection model ready, no active connections |
| Serial tracking | Configured | Enabled, no serial data |
| BOM / Work orders | Configured | Structure ready, demo kit shows BOM |

---

## See Also

- [Production Deployment](production-deployment.md) — Gunicorn + Nginx setup
- [Production Database](production-db.md) — database configuration
- [Dev Setup](../../02-dev-setup.md) — local development environment
