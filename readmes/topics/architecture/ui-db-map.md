# UI / DB Model Map

Every model, every rendering path. A model can appear in multiple columns —
these are WHERE the model is used, not exclusive assignments.

- **ui.json** — JSON-driven detail layout with Design Mode, widgets, print
- **db.json** — DataBrowser list + detail (admin, config, browse)
- **ui.tsx** — Custom React component (interaction-heavy)

## Transactions App

| Model | ui.json uses | db.json uses | ui.tsx uses |
|-------|-------------|-------------|------------|
| order | Order detail form, print, customer card | Order list browse, admin | Kanban (by status) |
| order_line | Line card inside order | Line export, admin | — |
| invoice | Invoice detail form, print | Invoice list, AR aging | — |
| invoice_line | Line card inside invoice | Line export | — |
| proposal | Proposal detail form, print | Proposal list, pipeline | Gantt (by project) |
| proposal_line | Line card inside proposal | — | — |
| purchase | PO detail form, print | PO list, AP aging | — |
| purchase_line | Line card inside purchase | Line export | — |
| work_order | WO detail form, print | WO list | Gantt (by project) |
| work_order_line | Line card inside WO | — | — |
| receipt | Receipt detail form | Receipt list | — |
| receipt_line | Line card inside receipt | — | — |
| requisition | Requisition detail form | Requisition list | — |
| requisition_line | Line card inside requisition | — | — |
| payment | Payment detail form | Payment list, journal | Apply Payments (drag) |
| payment_application | — | Application list | Apply Payments (drag) |
| project | — | Project list, admin | Kanban, Gantt |
| statement_line | — | Statement list | — |

## Core App

| Model | ui.json uses | db.json uses | ui.tsx uses |
|-------|-------------|-------------|------------|
| contact | Contact detail form (3-col + 7 tabs) | Contact list browse | — |
| action | Action detail form (2-col) | Action list | Kanban (cards), Gantt (bars) |
| document | Document detail form (2-col) | Document list, admin | — |
| report | Report detail form (2-col) | Report list, admin | — |
| question_answer | QA detail form | QA list | — |
| setting | — | Setting list, admin | — |
| template | — | Template list, admin | — |
| notification | — | Notification list | — |
| pending | — | Pending queue, admin | — |

## Communications App

| Model | ui.json uses | db.json uses | ui.tsx uses |
|-------|-------------|-------------|------------|
| email | Email card (in contact, order) | Email list, admin | — |
| phone | Phone card (in contact, order) | Phone list, admin | — |
| address | Address card (in contact, order) | Address list, admin | — |
| domain | Domain card (in contact) | Domain list, admin | — |

## Organizations App

| Model | ui.json uses | db.json uses | ui.tsx uses |
|-------|-------------|-------------|------------|
| customer | Customer detail form (3-col + 7 tabs) | Customer list browse | — |
| vendor | Vendor detail form (3-col + 7 tabs) | Vendor list browse | — |
| manufacturer | Manufacturer detail form | Manufacturer list | — |
| employee | Employee detail form | Employee list | — |
| rep | Rep detail form | Rep list | — |

## Products App

| Model | ui.json uses | db.json uses | ui.tsx uses |
|-------|-------------|-------------|------------|
| item | Item detail form (3-col + 8 tabs) | Item list browse, price list | — |
| serial | Serial detail form (2-col) | Serial list, tracking | — |
| specification | Spec detail form | Spec list | — |
| bill_of_material | BOM card in Item tabs | BOM list, admin | BOM tree (future) |
| catalog | — | Catalog list, admin | — |
| item_xref | XRef card in Item tabs | XRef list, admin | — |
| org_item | — | Org-Item links, admin | — |
| service | — | Service list | — |
| variant | — | Variant list | — |
| warehouse | — | Warehouse list, admin | Inventory Dashboard |
| usage | — | Usage tracking | — |
| matrics | — | Metrics, system | — |

## Accounts App

| Model | ui.json uses | db.json uses | ui.tsx uses |
|-------|-------------|-------------|------------|
| gl_account | — | Chart of accounts | — |
| gl_journal | — | Journal entries | — |
| ledger | — | Ledger records | — |
| tax_jurisdiction | — | Tax rates, admin | — |
| term | — | Payment terms, admin | — |
| currency | — | Currency codes, admin | — |
| exchange_rate | — | FX rates, admin | — |
| exchange_transaction | — | FX transactions | — |
| audit | — | Audit log, system | — |
| tally_summary | — | Aggregations, system | — |
| sales_dimension_tally | — | Analytics, system | — |
| inventory_usage_tally | — | Analytics, system | — |
| tally_registry | — | Tally config, admin | — |

## Docs App

| Model | ui.json uses | db.json uses | ui.tsx uses |
|-------|-------------|-------------|------------|
| document | Document detail form | Document list | — |
| question_answer | QA detail form | QA list | — |
| tag | — | Tag list, admin | — |
| linkage | — | Linkage list, system | — |

## Sync App

| Model | ui.json uses | db.json uses | ui.tsx uses |
|-------|-------------|-------------|------------|
| connection | — | Connection config, admin | — |
| bundle | — | Bundle list, system | — |

## Support App

| Model | ui.json uses | db.json uses | ui.tsx uses |
|-------|-------------|-------------|------------|
| All support models | — | Scheduler, tasks, admin | — |

## AI Assistant App

| Model | ui.json uses | db.json uses | ui.tsx uses |
|-------|-------------|-------------|------------|
| alice_observation | — | Observation list | Alice Dashboard |
| alice_preset | — | Preset list, admin | — |
| alice_coaching_log | — | Coaching log | — |

## JPods App (to be removed)

| Model | ui.json uses | db.json uses | ui.tsx uses |
|-------|-------------|-------------|------------|
| All jpods models | Should be standard WC3 item/order flow | — | — |

---

## Summary

| Path | Model Count | Primary Use |
|------|-------------|-------------|
| ui.json | ~35 | User workflow: data entry, forms, cards, print |
| db.json | ~60+ | All models for list/admin + config-only models |
| ui.tsx | ~8 | Kanban, Gantt, Apply Payments, Inventory, BOM tree |

**Every model appears in db.json** — DataBrowser can browse anything.
**Workflow models also appear in ui.json** — dedicated forms for daily use.
**Interaction-heavy views appear in ui.tsx** — drag, timeline, real-time.
