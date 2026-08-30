# WebClerk Backend Naming & Structure Plan

**Date:** 2026-08-27
**Status:** Deferred — execute before first customer

No users. No backwards compatibility burden. Fix everything now.

---

## Principles

1. **Name says what it does** — action + subject. `journalize_transactions.py` not `journalize.py`.
2. **One file, one concern** — no catch-all `*_services.py` with 400 lines of unrelated ops.
3. **Group by behavioral domain** — subdirectories when 3+ files share a domain.
4. **Consistent suffixes** — `_view.py` for views, `_serializer.py` for serializers. Services get no suffix (they ARE the domain).
5. **No duplicates** — one serializer class per model, in one file.
6. **Package not flat** — every app uses `models/`, `services/`, `serializers/`, `views/`. Kill the flat files.

---

## Structural Fixes (do first)

### Ghost files — delete
```
core/views/schema_fields_view 2.py     ← space-in-name duplicate
core/views/system_dispatch 2.py        ← space-in-name duplicate
```

### Flat/package collisions — pick one (package wins)
```
accounts/models.py    ← delete if empty, merge if not
products/models.py    ← delete if empty, merge if not
products/views.py     ← move into views/
products/serializers.py ← move into serializers/
orgs/models.py        ← delete if empty, merge if not
docs/models.py        ← delete if empty, merge if not
docs/views.py         ← move into views/
docs/views_qa.py      ← move to views/qa_view.py
docs/views_readme.py  ← move to views/readme_view.py
docs/views_stats.py   ← move to views/stats_view.py
docs/views_tag.py     ← move to views/tag_view.py
docs/views_upload.py  ← move to views/upload_view.py
transactions/views.py ← move into views/
transactions/aggregation.py ← move to services/ or views/
transactions/flow.py  ← move to services/
sync/views.py         ← move into views/
ai_assistant/models_alice.py ← merge into models/ package
```

---

## Service Naming Plan

### Behavioral categories

Every service file falls into one of these:

| Category | Pattern | Example |
|----------|---------|---------|
| **Transform** (A→B) | `convert_{source}_to_{target}.py` | `convert_order_to_invoice.py` |
| **Lifecycle** (create/update/manage) | `{subject}_{verb}.py` | `payment_apply.py`, `serial_receive.py` |
| **Query/Report** | `{subject}_{output}.py` | `sales_pipeline.py`, `customer_health.py` |
| **Validate** | `validate_{subject}.py` | `validate_transaction.py`, `validate_credit.py` |
| **Integration** | `{provider}_{protocol}.py` | `spreedly_gateway.py`, `google_calendar.py` |
| **Infrastructure** | descriptive noun | `cache.py`, `vector_store.py` |

### `transactions/services/` — rename map

**Transforms (conversion pipeline):**
```
conversion.py                    → convert.py  (public API — delegates)
transfer.py                      → convert_engine.py
transfer_utils.py                → convert_utils.py
order_to_invoice.py              → convert_order_to_invoice.py
order_to_purchase.py             → convert_order_to_purchase.py
proposal_to_order.py             → convert_proposal_to_order.py
proposal_to_purchase.py          → convert_proposal_to_purchase.py
purchase_to_invoice.py           → convert_purchase_to_invoice.py
purchase_to_order.py             → convert_purchase_to_order.py
purchase_to_proposal.py          → convert_purchase_to_proposal.py
invoice_to_purchase.py           → convert_invoice_to_purchase.py
```
→ Move all into `services/convert/`

**Payment cluster:**
```
payment_application.py           → payment_apply.py
payment_gateways.py              → spreedly_gateway.py
payment_pending.py               → payment_pending.py  (keep)
```
→ Move into `services/payment/`

**Fulfillment cluster:**
```
shipping.py                      → fulfillment_ship.py
freight_estimation.py            → fulfillment_freight.py
backorder.py                     → fulfillment_backorder.py
split_by_vendor.py               → fulfillment_split.py
carriers/                        → carriers/  (keep — already clustered)
```
→ Move into `services/fulfillment/`

**Pricing/cost cluster:**
```
landed_cost.py                   → cost_landed.py
tax_lookup.py                    → tax_resolve.py
totals.py                        → totals_compute.py
commission.py                    → commission_compute.py
```
→ Move into `services/pricing/`

**Lifecycle (transaction-level):**
```
status_guard.py                  → validate_status.py
validation.py                    → validate_transaction.py
transaction_save.py              → transaction_save.py  (keep)
flow.py                          → transaction_flow.py
line_item_service.py             → line_manage.py
inventory_flow.py                → inventory_flow.py  (keep)
pending_inventory_processor.py   → inventory_pending_process.py
```
→ Stay in `services/` root

**Query/report:**
```
sales_pipeline.py                → pipeline_report.py
campaign_roi.py                  → campaign_report.py
```

**Customer/defaults:**
```
customer_defaults.py             → customer_defaults.py  (keep)
credit_check.py                  → validate_credit.py
```

**Integration:**
```
email_notifications.py           → notify_email.py
```

**Production:**
```
order_production.py              → production_fulfill.py
training_flow.py                 → training_flow.py  (keep)
```

**Dev tools:**
```
trace_debug.py                   → trace_debug.py  (keep — but move to mgmt commands?)
```

**Denormalization:**
```
denormalize_org_links.py         → denormalize_org_links.py  (keep)
```

### `core/services/` — rename map

**Action cluster:**
```
action_service.py                → action_links.py  (it appends contact links)
action_summary.py                → action_report.py
action_horizon.py                → action_horizon.py  (keep — distinct)
lifecycle.py                     → action_lifecycle.py
burndown.py                      → action_burndown.py
```

**Contact cluster:**
```
contact_communications_maintenance.py → contact_maintenance.py
contact_health.py                → contact_health.py  (keep)
vcard_service.py                 → contact_vcard.py
```

**Settings cluster:**
```
setting_resolver.py              → setting_resolve.py
settings_bootstrap.py            → setting_bootstrap.py
settings_health.py               → setting_health.py
```

**Dashboard/summary cluster:**
```
commerce_dashboard.py            → dashboard_commerce.py
dashboard_counts.py              → dashboard_counts.py  (keep)
customer_summary.py              → dashboard_customer.py
vendor_summary.py                → dashboard_vendor.py
item_summary.py                  → dashboard_item.py
rep_summary.py                   → dashboard_rep.py
pending_summary.py               → dashboard_pending.py
dbsr_health.py                   → dashboard_dbsr.py
```
→ Move into `services/dashboard/`

**Data ops:**
```
clone.py                         → record_clone.py
dedup.py                         → record_dedup.py
json_field_ops.py                → json_ops.py
keywords.py                      → record_keywords.py
field_behaviors.py               → field_behaviors.py  (keep)
field_projection.py              → field_projection.py  (keep)
orphan_detection.py              → record_orphans.py
schema_compliance.py             → schema_validate.py
```

**Integration/infrastructure:**
```
cache_service.py                 → cache.py
wcapi.py                         → record_serialize.py  (that's what it does)
agent_bus_bridge.py              → agent_bus.py
alice_denormalize.py             → alice_denormalize.py  (keep)
```

**Formatting:**
```
address_formatter.py             → format_address.py
phone_normalizer.py              → format_phone.py
template_resolver.py             → format_template.py
report_renderer.py               → render_report.py
image_library.py                 → resolve_image.py
```

**Config:**
```
role_defaults.py                 → role_defaults.py  (keep)
role_filter.py                   → role_filter.py  (keep)
link_defaults.py                 → link_defaults.py  (keep)
ui_config.py                     → ui_config.py  (keep)
app_bootstrap.py                 → app_bootstrap.py  (keep)
architecture.py                  → codemap.py
```

**Reports:**
```
tally_registry.py                → tally_registry.py  (keep)
tally_reports.py                 → tally_reports.py  (keep)
parade_of_reports.py             → report_parade.py
```

### `products/services/` — rename map

**Inventory cluster:**
```
inventory_services.py            → inventory_layers.py  (layer costing, movement)
inventory_stacks.py              → inventory_stacks.py  (keep — FIFO/LIFO)
inventory_availability.py        → inventory_available.py
inventory_reservations.py        → inventory_reserve.py
inventory_velocity.py            → inventory_velocity.py  (keep)
inventory_metrics.py             → inventory_metrics.py  (keep)
inventory_bounds.py              → inventory_bounds.py  (keep)
inventory_flight_sim.py          → inventory_flight_sim.py  (keep)
```
→ Move into `services/inventory/`

**Serial cluster:**
```
serial_services.py               → serial_ops.py
serial_lifecycle.py              → serial_lifecycle.py  (keep)
serial_bulk.py                   → serial_bulk.py  (keep)
serial_trends.py                 → serial_trends.py  (keep)
```
→ Move into `services/serial/`

**Pricing:**
```
price_resolver.py                → price_resolve.py  (keep as canonical)
pricing.py                       → DELETE (legacy — merge anything missing into price_resolve.py)
map_enforcement.py               → price_map_enforce.py
```

**Other:**
```
bom_services.py                  → bom_ops.py
xref_lookup.py                   → xref_lookup.py  (keep)
suggest_purchase.py              → suggest_purchase.py  (keep)
onboarding_flight_sim.py         → onboarding_flight_sim.py  (keep)
purchasing_dashboard.py          → dashboard_purchasing.py
sales_dashboard.py               → dashboard_sales.py
```

### `accounts/services/` — mostly good

```
eom.py                           → period_close.py  (abbreviation → descriptive)
erosion.py                       → value_erosion.py  (distinguish from model)
```

### `ai_assistant/services/` — rename map

```
alice_inbox.py                   → inbox.py
alice_notes.py                   → notes.py
alice_qa.py                      → qa.py
to_alice_overrides.py            → setting_overrides.py
dedup_service.py                 → dedup.py
rag_service.py                   → rag.py
coding_journal.py                → journal.py
code_standards.py                → watch_code.py
git_observer.py                  → watch_git.py
accounting_watchdog.py           → watch_accounting.py
inventory_watchdog.py            → watch_inventory.py
layout_drift_detector.py         → watch_layouts.py
schema_drift_detector.py         → watch_schemas.py
schema_audit.py                  → watch_envelopes.py
```

---

## Serializer Plan

### Rule: one serializer per model, one file, suffix `_serializer.py`

**transactions/serializers/ — current mess:**
- `transaction_serializers.py` defines serializers for Proposal, Order, Purchase, Invoice, Payment, StatementLine — a mega-file
- `invoice_serializers.py`, `order_serializers.py`, `payment_serializers.py` duplicate classes from the mega-file
- `line_serializers.py` has a misplaced `ProjectSerializer`

**Target state:**
```
transactions/serializers/
  proposal_serializer.py          ← ProposalSerializer, ProposalLineSerializer
  order_serializer.py             ← OrderSerializer, OrderLineSerializer
  invoice_serializer.py           ← InvoiceSerializer, InvoiceLineSerializer
  purchase_serializer.py          ← PurchaseSerializer, PurchaseLineSerializer
  payment_serializer.py           ← PaymentSerializer, PaymentTermSerializer, PaymentMethodSerializer
  payment_application_serializer.py ← PaymentApplicationSerializer
  workorder_serializer.py         ← WorkOrderSerializer, WorkOrderLineSerializer
  requisition_serializer.py       ← RequisitionSerializer, RequisitionLineSerializer
  project_serializer.py           ← ProjectSerializer
  statement_serializer.py         ← StatementLineSerializer
  transfer_serializer.py          ← TransferRequestSerializer, etc.
  convert_serializer.py           ← ConvertRequestSerializer, TransitionRequestSerializer
  cost_validators.py              ← keep (not a serializer — move to services/pricing/?)
```

**Other apps — fix suffixes:**
```
docs/serializers/linkage_entry.py      → linkage_entry_serializer.py
docs/serializers/question_answer.py    → question_answer_serializer.py
sync/serializers/connection.py         → connection_serializer.py
transactions/serializers/requisition.py → requisition_serializer.py
transactions/serializers/actions.py    → convert_serializer.py
```

---

## View Plan

### Rule: suffix `_view.py`, one file per resource or cluster

Kill all flat view files at app root. Move into `views/` package.

**docs/ — move and rename:**
```
docs/views.py          → docs/views/document_view.py
docs/views_qa.py       → docs/views/qa_view.py
docs/views_readme.py   → docs/views/readme_view.py
docs/views_stats.py    → docs/views/stats_view.py
docs/views_tag.py      → docs/views/tag_view.py
docs/views_upload.py   → docs/views/upload_view.py
```

**transactions/ — move flat files:**
```
transactions/views.py        → merge into views/ or delete if dead
transactions/aggregation.py  → views/aggregation_view.py
```

**products/ — move flat file:**
```
products/views.py → merge into views/ or delete if dead
```

**Fix missing `_view` suffixes:**
```
transactions/views/requisition.py → requisition_view.py
products/views/inventory.py       → inventory_view.py
```

**ai_assistant/ — split flat views.py:**
```
ai_assistant/views.py → ai_assistant/views/
  chat_view.py        ← AskView, FeedbackView, HistoryView
  health_view.py      ← HealthView, DiagnoseView, DeviceStatusView
  admin_view.py       ← ReviewView, GenerateView, ReindexView, DebugView, ModesView
  note_view.py        ← NoteView, ReportView, SearchFeedbackView
```

---

## Execution Order

1. **Ghost files** — delete the space-in-name duplicates
2. **Flat/package collisions** — merge or delete the flat files
3. **Duplicate serializer classes** — pick one definition, delete the other
4. **Rename services** — one app at a time, update all imports
5. **Create subdirectories** — `convert/`, `payment/`, `fulfillment/`, `pricing/`, `dashboard/`, `inventory/`, `serial/`
6. **Rename serializers** — add `_serializer` suffix
7. **Rename views** — add `_view` suffix, move flat files
8. **Update all imports** — grep for every old path, fix
9. **Run tests** — verify nothing broke
10. **Commit per app** — one commit per app so git blame stays useful
