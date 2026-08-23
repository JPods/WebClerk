# WC2 → WC3 Translation Plan
**Created:** 2026-06-27
**Status:** Draft — pending team review
**Owner:** Bill James
**Participants:** Claude Code, Allie, Alice (action records)

---

## Approach

Focus on **end-to-end data workflows**, not method-by-method translation from 4D.

WC2 had ~250 tables, ~460 methods. Most methods were UI rendering (HTML, popups, print templates, query utilities) that React and Django handle natively. The valuable core is the **data flow and business rules** — what happens when a user creates a customer, enters an order, invoices it, and collects payment.

WC3 already has 74+ models across 8 Django apps with a normalized JSON envelope architecture (refs, prefs, metadata, comments, actions). Many wc2 denormalized columns are absorbed into these envelopes. The translation work is completing the **behavioral layer** — the rules, validations, conversions, and calculations that make the data flow correct.

### What we're dropping

| Category | Count | Why |
|----------|-------|-----|
| Qx query utilities | 158 | Django ORM replaces all of this |
| HTTP/HTML methods | 156 | React renders UI; Django serves JSON |
| Print methods | 17 | Browser print + PDF generation |
| zzz deprecated tables | 37 | Dead in wc2 itself |
| EDI methods | 20 | Dead technology for a new platform |
| CMA import methods | 17 | Replaced by management commands + Celery |
| MRP/forecasting | — | Aspirational, not v1 |
| Territory/Maps | — | Nice-to-have, not load-bearing |

**Total dropped:** ~405 of ~460 methods. The remaining ~55 contain the actual business logic.

### What we're keeping and translating

The work organizes into **four production workflows** plus **two support layers**.

---

## Workflow 1: Customer → Order → Invoice → Payment

The core commerce cycle. Everything else is secondary until this works end-to-end.

### Tasks

| # | Task | Difficulty | Status | Unit Tests |
|---|------|-----------|--------|------------|
| 1.1 | **Customer creation + org linking** — Create Contact, link to Customer org, auto-populate refs.email/phone/address | 2/5 | Partial — models exist, refs linking works | `test_create_customer_with_contact`, `test_customer_refs_populated`, `test_customer_org_type_correct` |
| 1.2 | **Order entry with line items** — Create Order header, add OrderLines with item lookup, quantity, pricing; auto-calculate line extensions and order totals | 3/5 | Partial — models + totals service exist | `test_create_order_with_lines`, `test_order_totals_correct`, `test_line_price_extension`, `test_order_status_transitions` |
| 1.3 | **Inventory reservation on order** — OrderLine save triggers InventoryReservation for the item/warehouse; reservation expires if order cancelled | 3/5 | Exists — InventoryReservation + reserve endpoint | `test_order_reserves_inventory`, `test_cancel_releases_reservation`, `test_reservation_expiry` |
| 1.4 | **Order → Invoice conversion** — Convert Order to Invoice, copy lines, update statuses, preserve lineage in metadata | 3/5 | Exists — convert_to_invoice endpoint | `test_order_to_invoice_creates_invoice`, `test_invoice_lines_match_order`, `test_order_status_after_conversion`, `test_lineage_tracked` |
| 1.5 | **Invoice totals + tax calculation** — Invoice totals aggregate from lines; tax calculated per TaxJurisdiction | 3/5 | Partial — totals exist, tax service exists | `test_invoice_totals_correct`, `test_tax_applied_by_jurisdiction`, `test_tax_zero_for_exempt` |
| 1.6 | **Payment recording** — Create Payment record, link to Invoice via PaymentApplication, update Invoice balance | 3/5 | Partial — Payment model + application model exist | `test_record_payment`, `test_payment_applies_to_invoice`, `test_invoice_balance_after_payment`, `test_overpayment_rejected` |
| 1.7 | **Payment → GL posting** — Payment triggers GL journal entries (debit cash, credit AR) | 4/5 | Partial — GL models exist, posting logic unclear | `test_payment_creates_gl_entries`, `test_gl_entries_balance`, `test_ledger_updated` |
| 1.8 | **Invoice aging** — Background task calculates current/30/60/90 day aging buckets per customer | 3/5 | Not implemented | `test_aging_buckets_calculated`, `test_aging_updates_on_payment`, `test_aging_by_customer` |
| 1.9 | **React25: Order entry page end-to-end** — Verify OrderDetail page creates/saves/loads orders with lines through wcapi | 3/5 | Unknown — needs audit | `test_react_order_save_roundtrip` (integration) |
| 1.10 | **React25: Invoice page end-to-end** — Verify InvoiceDetail page works with conversion from order | 3/5 | Unknown — needs audit | `test_react_invoice_from_order` (integration) |
| 1.11 | **React25: Payment recording page** — Verify PaymentDetailPage applies payment to invoice | 3/5 | Unknown — needs audit | `test_react_payment_apply` (integration) |

### WC2 behaviors to preserve
- **Credit limit check** on order entry (wc2: Customers.CreditLimit vs BalanceDue) → wc3: check in Order pre_save_hook
- **Payment terms defaulting** from Customer to Order to Invoice (wc2: Customers.Terms) → wc3: Customer.prefs or OrgTypeFinancialMixin
- **Aging bucket calculation** (wc2: Customers.BalanceCurrent/BalPastPeriod1/2/3) → wc3: Celery task writing to Customer.metadata or Ledger

---

## Workflow 2: Product Lookup → Pricing → Inventory

### Tasks

| # | Task | Difficulty | Status | Unit Tests |
|---|------|-----------|--------|------------|
| 2.1 | **Item search with keywords** — Full-text search across Item name, SKU, description, keywords | 2/5 | Exists — keyword service + search | `test_item_search_by_name`, `test_item_search_by_sku`, `test_search_returns_pricing` |
| 2.2 | **Price tier resolution** — Resolve correct price for a customer based on their org type, quantity breaks, and item pricing tiers | 4/5 | Partial — Item has retail/wholesale/sample prices, but no multi-tier matrix | `test_retail_price_for_retail_customer`, `test_wholesale_price_for_wholesale`, `test_quantity_break_applied` |
| 2.3 | **Inventory availability check** — Query InventoryLayer for on_hand - reserved = available, by warehouse | 2/5 | Exists — InventoryLayer model | `test_available_calculation`, `test_available_by_warehouse`, `test_reserved_reduces_available` |
| 2.4 | **BOM cost rollup** — BillOfMaterial cost calculated from component items, recursive for sub-assemblies | 3/5 | Exists — BOM recalc endpoint | `test_bom_cost_from_components`, `test_recursive_bom`, `test_bom_cost_updates_parent` |
| 2.5 | **Item cross-reference lookup** — Find Item by barcode, GTIN, manufacturer SKU via ItemXRef | 2/5 | Exists — ItemXRef model | `test_lookup_by_barcode`, `test_lookup_by_mfr_sku` |
| 2.6 | **React25: Product list + detail pages** — Verify ItemList search works, ItemDetail shows pricing + inventory | 3/5 | Unknown — needs audit | `test_react_item_search`, `test_react_item_detail_shows_stock` (integration) |

### WC2 behaviors to preserve
- **Price matrix** (wc2: PriceMatrix table — customer type × quantity × item) → wc3: needs design decision. Options: (a) OrgItem.prefs pricing overrides, (b) dedicated PriceRule model, (c) Item.metadata.pricing_tiers
- **Item discount rules** (wc2: ItemDiscounts, SpecialDiscounts) → wc3: fold into pricing tier resolution or OrgItem

---

## Workflow 3: Proposal → Order → Invoice Conversion Chain

### Tasks

| # | Task | Difficulty | Status | Unit Tests |
|---|------|-----------|--------|------------|
| 3.1 | **Proposal creation with lines** — Mirror of order entry but with proposal-specific status flow | 2/5 | Exists — Proposal + ProposalLine models | `test_create_proposal`, `test_proposal_totals` |
| 3.2 | **Proposal → Order conversion** — Copy proposal lines to order, update statuses, track lineage | 3/5 | Exists — convert_to_order endpoint | `test_proposal_to_order`, `test_lines_copied`, `test_proposal_status_after_convert` |
| 3.3 | **Order → Purchase Order conversion** — For drop-ship or procurement: convert order lines to PO lines for vendor | 3/5 | Exists — convert_to_purchase endpoint | `test_order_to_purchase`, `test_po_vendor_set`, `test_po_lines_match_order` |
| 3.4 | **Bulk conversion** — Convert multiple proposals to orders, multiple orders to invoices in one operation | 3/5 | Exists — bulk transfer endpoints | `test_bulk_proposals_to_orders`, `test_bulk_orders_to_invoices` |
| 3.5 | **Conversion validation** — Prevent double-conversion, ensure all lines have items, check inventory before commit | 3/5 | Partial — validate_transfer endpoint exists | `test_no_double_conversion`, `test_validate_missing_items`, `test_validate_insufficient_stock` |
| 3.6 | **React25: Proposal detail + conversion flow** — User creates proposal, clicks convert, sees order created | 3/5 | Unknown — needs audit | `test_react_proposal_convert_flow` (integration) |

### WC2 behaviors to preserve
- **Proposal cloning** (wc2: duplicate proposal for new customer) → wc3: needs explicit clone endpoint or wcapi save with copy flag
- **Partial conversion** (wc2: convert selected lines, not entire proposal) → wc3: check if bulk transfer supports line selection

---

## Workflow 4: React25 Page Audit

Before building new features, verify what actually works.

### Tasks

| # | Task | Difficulty | Status | Unit Tests |
|---|------|-----------|--------|------------|
| 4.1 | **Audit all React25 list pages** — For each model route, verify: loads data from wcapi, displays results, pagination works, search/filter works | 3/5 | Not done | Checklist per page (pass/fail) |
| 4.2 | **Audit all React25 detail pages** — For each model, verify: loads single record, edits save via wcapi, validation errors display, new record creation works | 4/5 | Not done | Checklist per page (pass/fail) |
| 4.3 | **Audit transaction detail pages** — Orders, Invoices, Proposals, Purchases: verify line item add/edit/delete, totals recalculate, status transitions work | 4/5 | Not done | Checklist per transaction type |
| 4.4 | **Identify dead pages** — Routes that exist but render nothing or error | 2/5 | Not done | List of dead routes |
| 4.5 | **Identify missing wcapi wiring** — Pages that render UI but don't call wcapi (hardcoded data, empty state) | 3/5 | Not done | List of unwired pages |

---

## Support Layer A: Financial Accounting

### Tasks

| # | Task | Difficulty | Status | Unit Tests |
|---|------|-----------|--------|------------|
| A.1 | **Chart of accounts seeding** — Ensure default GL accounts exist for AR, AP, Cash, Sales, COGS, Inventory | 2/5 | Exists — seed_gl_defaults command | `test_gl_defaults_created`, `test_no_duplicate_accounts` |
| A.2 | **Transaction → GL posting rules** — Define which transactions create which journal entries (invoice → debit AR/credit Sales; payment → debit Cash/credit AR) | 4/5 | Partial — GL models exist, posting rules unclear | `test_invoice_gl_entries`, `test_payment_gl_entries`, `test_gl_always_balances` |
| A.3 | **Ledger balance verification** — Ledger balances reconcile with sum of journal entries | 3/5 | Exists — reconcile_financials command | `test_ledger_balances_match_journals` |
| A.4 | **Multi-currency support** — Transactions in foreign currency convert to base at ExchangeRate; GL entries in base currency | 4/5 | Partial — Currency + ExchangeRate models exist | `test_foreign_currency_order`, `test_exchange_rate_applied`, `test_gl_in_base_currency` |
| A.5 | **Payment terms enforcement** — Net30/Net60/COD terms on customer default to orders/invoices; due date calculated from terms | 2/5 | Exists — Term model + OrgTypeFinancialMixin | `test_terms_default_from_customer`, `test_due_date_from_terms` |

---

## Support Layer B: Data Integrity & Operations

### Tasks

| # | Task | Difficulty | Status | Unit Tests |
|---|------|-----------|--------|------------|
| B.1 | **Refs consistency check** — Verify refs.links match FK relationships (refs audit already exists as management command) | 2/5 | Exists — audit_fk_values, refs_mismatch_log | `test_refs_match_fks` |
| B.2 | **Keyword indexing** — All models have search keywords generated and refreshed | 2/5 | Exists — update_keywords command + Celery task | `test_keywords_generated_on_save`, `test_keyword_search_finds_record` |
| B.3 | **Soft delete consistency** — Deleted records excluded from all queries except explicit .deleted() | 2/5 | Exists — LifecycleMixin + FullManager | `test_soft_delete_excludes_from_default`, `test_deleted_accessible_via_deleted()` |
| B.4 | **Version conflict detection** — Optimistic concurrency prevents lost updates | 2/5 | Exists — CoreModel.optimistic_save | `test_version_conflict_raises`, `test_concurrent_saves_one_wins` |
| B.5 | **Data export/import cycle** — Export full dataset, import to fresh database, verify integrity | 4/5 | Partial — export_data + restore_data_smart commands | `test_export_import_roundtrip`, `test_record_counts_match`, `test_fk_integrity_after_import` |

---

## Difficulty Scale

| Weight | Meaning | Typical effort |
|--------|---------|---------------|
| 1/5 | Configuration or seed data | < 1 hour |
| 2/5 | Single model/endpoint, clear requirements | 2–4 hours |
| 3/5 | Multi-model interaction, business rules | 4–8 hours |
| 4/5 | Complex logic, multiple services, edge cases | 1–2 days |
| 5/5 | Architectural decision + implementation | 2–5 days |

---

## Execution Order

**Phase 1 — Verify what works (Workflow 4)**
Audit React25 pages before building anything new. No point adding features to broken plumbing.

**Phase 2 — Complete the core cycle (Workflow 1)**
Customer → Order → Invoice → Payment, end-to-end, with tests. This is the minimum viable product.

**Phase 3 — Product & pricing (Workflow 2)**
Item search, pricing tiers, inventory checks. Required for real order entry.

**Phase 4 — Conversion chain (Workflow 3)**
Proposal → Order → Invoice conversions. High-value but depends on Phase 2 working.

**Phase 5 — Financial layer (Support Layer A)**
GL posting, aging, multi-currency. Required for real accounting but can run parallel to Phase 3.

**Phase 6 — Operations hardening (Support Layer B)**
Data integrity, export/import, monitoring. Pre-production checklist.

---

## What this plan does NOT cover (deferred)

- Sales rep quotas and commission tracking
- Call reports and CRM-style activity logging
- Delivery route management
- Service order management (beyond basic work orders)
- Barcode/label generation
- B2B sync automation
- Statistical reporting (Tally system)
- Campaign management

- **System health dashboard for administrators** — single page showing vital signs. Transaction volume by type per period, unapplied Pending count + age, locked record delays, RefsMismatchLog trend, inventory anomalies (negative on_hand/available), GL imbalance detection. Data sources already exist (APILog, UserDailyLog, Pending, RefsMismatchLog, InventoryLayer, GlJournal). Audit task frequency should be adaptive: normal=nightly, elevated=hourly, critical=every 5 min — driven by error rate, not fixed schedule. Django admin + psql cover ad-hoc investigation; this dashboard covers pattern detection.
- **Field publication control (wc3 → R25)** — admin-configurable declaration of which fields each model publishes to React. Currently spread across schema_whitelist.py, ModelRoleConfig view/edit field lists, and serializer field declarations. Need a single source: Setting or ModelRoleConfig record per model that declares published fields, field order, and role-based visibility. React reads this on page load to know what to render. Cost fields hidden from non-staff. Sensitive fields (password, security_level) never published. This is the server-side complement to configurable list layouts per role.
- **Staff authority rules (RBAC)** — three operations require staff-level authority, enforced via ModelRoleConfig:
  - Negative quantity on lines (returns) — staff only; prevents unauthorized returns
  - Changing price_level on a line — staff only; prevents unauthorized discounting
  - Viewing cost data (Item.cost, line.cost) — staff only; cost is confidential
  These are configuration, not code — seed via `seed_rbac_roles` management command.
- **Configurable list layouts per role** — list pages should support different column sets, field order, and default sort per user role/job function. Architecture: Setting records with `purpose: "list_layout"` per model+role, React reads on page load, user can override locally. AdvancedDataTable already has `storageKey` for column persistence. Currently each model has a single list page — that's correct for v1; role-based layouts layer on top later.

These are all real features but none are required for a first production deployment. They become Phase 7+ after the core works.

### Stubbed for future — will impact React layout

| Feature | Why deferred | Stub action | React impact |
|---------|-------------|-------------|-------------|
| **Forecasting / demand planning** | Requires historical transaction data that doesn't exist yet | TODO comment in Item detail + Order analytics pages | Will add forecasting panel to product and order pages |
| **Currency exchange UI** | Multi-currency GL posting (Task A.4) comes first; UI is secondary | TODO comment in Invoice/Payment detail pages | Will add currency selector and live rate display |

When these are implemented, the React pages they affect are: ItemDetail, OrderDetail, InvoiceDetail, PaymentDetailPage. Add `{/* TODO: [feature] — see wc2-wc3-translation-plan.md */}` comments in those components now so future developers know where the panels go.

### Data architecture decisions

**Import = "External Mandated"**
wc3 does NOT carry import-specific code. External conversion scripts (per data source, outside the wc3 codebase) transform source data to match wcapi's save contract exactly, then POST to `/wcapi/save/`. The conversion script is the importer's responsibility. wc3 defines the contract; importers conform.

- No field-mapping code in wc3
- No source-specific parsing in wc3
- No data cleanup logic in wc3
- The wcapi save endpoint IS the import endpoint

**Admin operations = Django admin + psql directly**
Administrators use Django admin (`/admin/`) and PostgreSQL (`psql`) for data inspection, bulk corrections, user management, and ad-hoc queries. We do not build admin UI in React for operations that these tools already handle. One warning applies: **changes made outside wc3 (direct SQL, Django admin) bypass save hooks, version bumps, refs maintenance, keyword indexing, and audit logging.** Administrators accept that risk. Document this in the admin onboarding guide.

Admin tool summary for onboarding:

| Tool | What it does | When to use |
|------|-------------|-------------|
| **Django admin** (`/admin/`) | Browse/edit any model, filter/search, bulk actions, user management, permissions | Day-to-day record inspection, one-off fixes, user account management, toggling is_active/is_staff |
| **Django shell** (`manage.py shell_plus`) | Python REPL with all models loaded — run queries, fix data, test logic | Scripted bulk corrections, data investigation, testing business rules interactively |
| **Management commands** (`manage.py <cmd>`) | Purpose-built operations: `update_keywords`, `reconcile_financials`, `seed_gl_defaults`, `export_data`, `restore_data_smart`, etc. | Scheduled maintenance, seeding, data migration, health checks |
| **psql** (PostgreSQL CLI) | Direct SQL — queries, indexes, `EXPLAIN` plans, table stats, vacuum | Performance investigation, bulk UPDATE/DELETE, schema inspection, backup/restore |
| **pg_dump / pg_restore** | Full database backup and restore | Disaster recovery, environment cloning, pre-migration snapshots |
| **Celery Flower** (`localhost:5555`) | Monitor background task queue — active/pending/failed tasks | Debugging stuck tasks, checking inventory processing, keyword refresh status |

**Bypass warning:** Django admin's `save()` does run model-level hooks (version bump, timestamps). Direct SQL and `psql` bypass everything. Django shell runs whatever you tell it — hooks fire if you call `.save()`, not if you use `.update()`.

**Sync as user-facing change request channel**
Users and external systems post data and feature requests through the sync app (`apps/sync/`). Connection defines the partner or channel (API, webhook, manual, internal). Bundle carries each exchange — payload in, response out, with conflict detection and transformation rules.

This means:
- **User change requests** can arrive as Bundle payloads via an internal Connection — wc3 processes them through the same pipeline as external data
- **Code changes triggered by sync** — a Bundle can carry configuration changes, feature flag updates, or data corrections that wc3 applies via its save hooks (preserving audit trail)
- **External partners** post structured data through their Connection; wc3 validates against its contract and applies or rejects

The sync pipeline preserves what direct admin access skips: audit logging, conflict tracking, transformation rules, and the full Bundle history. For changes that need an audit trail, prefer sync over direct SQL.

**Trading partner exchange and compliance:** Sync is the compliance boundary for B2B data exchange. Trading partners never touch wc3 directly. Their data arrives through a Connection, is scrubbed for compliance (transformation rules, field validation, agreement enforcement), and enters wc3 as an audited Bundle. Every exchange is logged — payload, response, conflicts, duration. This is the DynamicCatalogs pattern: upstream data is normalized against distribution agreements before it enters the retailer's system. The Connection.rules and Bundle.maps fields carry the compliance logic; the Bundle history is the audit trail.

**User-defined executables on new/save (TallyMaster replacement)**
wc2 stored user-defined executables in TallyMaster — custom logic that fired on new record creation and post-save. wc3 already has this: **Save Hooks** stored in Setting records with `purpose: "save_pre_post"`. Full documentation: `readmes/topics/api/save-hooks.md`.

| Hook | When it fires | Use case |
|------|--------------|----------|
| `save_pre` | Before save, synchronous | Validation, field defaulting, compliance checks |
| `save_post` | After save, synchronous | Denormalized counter updates, notification triggers |
| `save_async` | After save, via Celery | Email sends, external API calls, heavy computation |

Hooks are per-model, stored in the database (not code), toggled via `is_active`, and survive application upgrades. Administrators create them through Django admin or wcapi — no code deployment required. This is the same pattern as Salesforce triggers, NetSuite custom scripts, and SAP user exits.

**Hook & script library (WC-support)**
Hooks are not only local customizations — WC-support maintains a library of pre-built scripts:
- **React25 form scripts** — client-side form behaviors, validation, field logic
- **wc3 save hooks** — server-side pre/post/async hooks per model

Customers check the scripts they need into their local wc instance from the WC-support library. Scripts can also be custom-written per deployment.

**Athena approval (blockchain-signed)**
Every hook or script that enters a local instance must carry an Athena approval tag — blockchain-signed for provenance and tamper detection. No unsigned code executes in the hook pipeline. This applies to:
- Save hooks checked out from WC-support library
- Custom hooks written for a specific deployment
- React25 form scripts that modify data behavior

**Athena enforcement modes**
- **Scripts/hooks: blocking.** No unsigned code executes. Exception: admin explicitly assigns `yolo` override — accepted risk, admin's name on it, override logged and auditable. Yolo is not a bypass; it's an acknowledged exception with provenance.
- **Sync Bundles: flagging with quarantine.** Unapproved data enters Pending (holding state), queued for admin review and release. If Athena is down, data queues instead of being rejected — no single point of failure stops data flow. Admin reviews and releases from Pending.

**Sync corruption guard**
All sync Bundle records flow through Athena approval for corruption detection. Trading partner data is validated for format (Connection.rules) AND flagged for integrity (Athena signature). Unapproved Bundles land in Pending until an admin releases them. This closes the loop: external data can't reach live records without both contract compliance and integrity verification.

**JPods is customer zero**
We use these mechanisms ourselves. JPods trip pricing, Alice's ticket sales, station data, Small-Stings accounting — all run through the same save hooks, sync pipeline, and Athena approval that any WC customer would use. Problems we find building JPods become fixes for every future deployment.

**Export = external consumer via API (formatted) + management command (bulk)**
- **Formatted exports** (CSV, partner feeds, reports): External scripts call `/wcapi/get/` with filters, format output to recipient's needs. Export formatting code lives outside wc3.
- **Bulk database dumps** (backup, migration): Keep `export_data` / `restore_data_smart` management commands. These are operational, not business logic. Direct DB read is required for performance at scale.

---

## Unit Test Strategy

**Framework:** Django's TestCase + pytest
**Database:** Use test database (not mocks — per Bill's established rule)
**Coverage target:** Every task above defines its own tests. No task is complete without passing tests.
**Integration tests:** React25 pages get Playwright or Cypress tests for the critical workflows (order entry, invoice, payment).

**Test organization:**
```
tests/
  test_workflow_1_order_cycle.py
  test_workflow_2_product_pricing.py
  test_workflow_3_conversions.py
  test_support_a_accounting.py
  test_support_b_integrity.py
```

---

## Next Steps

1. **Bill reviews this plan** — adjust scope, reorder priorities
2. **Alice creates action records** — one action per task, linked to weekly project
3. **Phase 1 begins** — React25 page audit (Workflow 4)
4. **Each completed task** gets a retrospection entry with lessons for Allie
