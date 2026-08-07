# UI / DB Model Map

Every model has db.json access (databrowser) for administration. That's universal — not listed per model.

This map shows which models ALSO get:
- **ui.json** — JSON-driven detail layout with Design Mode, widgets, print
- **ui.tsx** — Custom React component (interaction-heavy)

If a model has no ui.json or ui.tsx entry, it's db.json only.

---

## MVP Status — ui.json models

Only ui.json models tracked here. db.json is universal (always available). ui.tsx is per-component.

| Model | App | Layout | MVP Date |
|-------|-----|--------|----------|
| order | transactions | 3-col + lines | 2026-08-02 |
| order_line | transactions | Line card | 2026-08-02 |
| proposal | transactions | 3-col + lines | 2026-08-02 |
| proposal_line | transactions | Line card | 2026-08-02 |
| invoice | transactions | 3-col + lines | 2026-08-02 |
| invoice_line | transactions | Line card | 2026-08-02 |
| purchase | transactions | 3-col + lines | 2026-08-02 |
| purchase_line | transactions | Line card | 2026-08-02 |
| work_order | transactions | 3-col + lines | — |
| work_order_line | transactions | Line card | — |
| receipt | transactions | 2-col + lines | — |
| receipt_line | transactions | Line card | — |
| requisition | transactions | 2-col + lines | — |
| requisition_line | transactions | Line card | — |
| payment | transactions | 2-col | — |
| email | communications | single-col card | — |
| phone | communications | single-col card | — |
| address | communications | single-col card | — |
| domain | communications | single-col card | — |
| contact | core | 3-col + 7 tabs | — |
| action | core | 2-col | — |
| document | docs | 2-col | — |
| question_answer | docs | single-col | — |
| report | core | 2-col | — |
| customer | orgs | 3-col + 7 tabs | — |
| vendor | orgs | 3-col + 7 tabs | — |
| manufacturer | orgs | 2-col | — |
| employee | orgs | 2-col | — |
| rep | orgs | 2-col | — |
| item | products | 3-col + 8 tabs | — |
| serial | products | 2-col | — |
| specification | products | single-col | — |
| bill_of_material | products | BOM card in Item | — |
| item_xref | products | XRef card in Item | — |

---

## By App

### accounts
| Model | ui.json | ui.tsx |
|-------|---------|--------|
| Audit | — | — |
| Currency | — | — |
| Erosion | — | — |
| ExchangeRate | — | — |
| ExchangeTransaction | — | — |
| GlAccount | — | — |
| GlJournal | — | — |
| Ledger | — | — |
| TaxJurisdiction | — | — |
| Term | — | — |

### ai_assistant
| Model | ui.json | ui.tsx |
|-------|---------|--------|
| AliceCoachingLog | — | — |
| AliceInsight | — | — |
| AliceObservation | — | Alice Dashboard |
| AlicePreset | — | — |
| CodingSession | — | — |
| Conversation | — | — |
| ErrorPattern | — | — |
| GitEvent | — | — |
| InventoryEvent | — | — |
| Message | — | — |
| SchemaDrift | — | — |

### communications
| Model | ui.json | ui.tsx |
|-------|---------|--------|
| Address | Address card (contact, order, org) | — |
| Domain | Domain card (contact) | — |
| Email | Email card (contact, order, org) | — |
| Phone | Phone card (contact, order, org) | — |

### core
| Model | ui.json | ui.tsx |
|-------|---------|--------|
| APILog | — | — |
| Action | Action detail (2-col) | Kanban (cards), Gantt (bars) |
| AuditLog | — | — |
| Contact | Contact detail (3-col + 7 tabs) | — |
| ModelLinkConfig | — | — |
| ModelRoleConfig | — | — |
| Notification | — | — |
| Pending | — | — |
| RefsMismatchLog | — | — |
| Report | Report detail (2-col) | — |
| RoleConfig | — | — |
| Setting | — | — |
| SoftDeleteLedger | — | — |
| Template | — | — |
| UserDailyLog | — | — |
| UserProfile | — | — |

### docs
| Model | ui.json | ui.tsx |
|-------|---------|--------|
| Document | Document detail (2-col) | — |
| LinkageEntry | — | — |
| QuestionAnswer | QA detail | — |
| Tag | — | — |

### orgs
| Model | ui.json | ui.tsx |
|-------|---------|--------|
| Customer | Customer detail (3-col + 7 tabs) | — |
| Employee | Employee detail (2-col) | — |
| Manufacturer | Manufacturer detail (2-col) | — |
| OrgBase | — | — |
| Rep | Rep detail (2-col) | — |
| Vendor | Vendor detail (3-col + 7 tabs) | — |

### products
| Model | ui.json | ui.tsx |
|-------|---------|--------|
| BillOfMaterial | BOM card in Item tabs | BOM tree (future) |
| Catalog | — | — |
| CatalogLine | — | — |
| DeliveryLine | — | — |
| DeliveryVisit | — | — |
| InventoryAdjustmentProcessorRun | — | — |
| InventoryCheck | — | Inventory Dashboard |
| InventoryCheckLine | — | Inventory Dashboard |
| InventoryLayer | — | — |
| InventoryMetricsSnapshot | — | — |
| InventoryMovement | — | — |
| InventoryReservation | — | — |
| Item | Item detail (3-col + 8 tabs) | — |
| ItemUsage | — | — |
| ItemXRef | XRef card in Item tabs | — |
| OrgItem | — | — |
| PendingInventoryAdjustment | — | — |
| Serial | Serial detail (2-col) | — |
| SerialLog | — | — |
| Service | — | — |
| SiteInventory | — | — |
| Specification | Spec detail | — |
| Variant | — | — |
| Warehouse | — | Inventory Dashboard |

### sync
| Model | ui.json | ui.tsx |
|-------|---------|--------|
| Bundle | — | — |
| Connection | — | — |

### transactions
| Model | ui.json | ui.tsx |
|-------|---------|--------|
| Invoice | Invoice detail (3-col), print | — |
| InvoiceLine | Line card inside invoice | — |
| Order | Order detail (3-col), print | Kanban (by status) |
| OrderLine | Line card inside order | — |
| Payment | Payment detail (2-col) | Apply Payments |
| PaymentApplication | — | Apply Payments |
| PaymentMethod | — | — |
| PaymentTerm | — | — |
| PendingPaymentApplication | — | — |
| Project | — | Kanban, Gantt |
| Proposal | Proposal detail (3-col), print | Gantt |
| ProposalLine | Line card inside proposal | — |
| Purchase | Purchase detail (3-col), print | — |
| PurchaseLine | Line card inside purchase | — |
| Receipt | Receipt detail | — |
| ReceiptLine | Line card inside receipt | — |
| Requisition | Requisition detail | — |
| RequisitionLine | Line card inside requisition | — |
| StatementLine | — | — |
| WorkOrder | WO detail (3-col), print | Gantt |
| WorkOrderLine | Line card inside WO | — |

---

## Alphabetical (all models)

| Model | App | ui.json | ui.tsx |
|-------|-----|---------|--------|
| Action | core | Action detail (2-col) | Kanban, Gantt |
| Address | communications | Address card | — |
| AliceCoachingLog | ai_assistant | — | — |
| AliceInsight | ai_assistant | — | — |
| AliceObservation | ai_assistant | — | Alice Dashboard |
| AlicePreset | ai_assistant | — | — |
| APILog | core | — | — |
| Audit | accounts | — | — |
| AuditLog | core | — | — |
| BillOfMaterial | products | BOM card in Item | BOM tree (future) |
| Bundle | sync | — | — |
| Catalog | products | — | — |
| CatalogLine | products | — | — |
| CodingSession | ai_assistant | — | — |
| Connection | sync | — | — |
| Contact | core | Contact detail (3-col + 7 tabs) | — |
| Conversation | ai_assistant | — | — |
| Currency | accounts | — | — |
| Customer | orgs | Customer detail (3-col + 7 tabs) | — |
| DeliveryLine | products | — | — |
| DeliveryVisit | products | — | — |
| Document | docs | Document detail (2-col) | — |
| Domain | communications | Domain card | — |
| Email | communications | Email card | — |
| Employee | orgs | Employee detail (2-col) | — |
| Erosion | accounts | — | — |
| ErrorPattern | ai_assistant | — | — |
| ExchangeRate | accounts | — | — |
| ExchangeTransaction | accounts | — | — |
| GitEvent | ai_assistant | — | — |
| GlAccount | accounts | — | — |
| GlJournal | accounts | — | — |
| InventoryAdjustmentProcessorRun | products | — | — |
| InventoryCheck | products | — | Inventory Dashboard |
| InventoryCheckLine | products | — | Inventory Dashboard |
| InventoryEvent | ai_assistant | — | — |
| InventoryLayer | products | — | — |
| InventoryMetricsSnapshot | products | — | — |
| InventoryMovement | products | — | — |
| InventoryReservation | products | — | — |
| Invoice | transactions | Invoice detail (3-col), print | — |
| InvoiceLine | transactions | Line card | — |
| Item | products | Item detail (3-col + 8 tabs) | — |
| ItemUsage | products | — | — |
| ItemXRef | products | XRef card in Item | — |
| Ledger | accounts | — | — |
| LinkageEntry | docs | — | — |
| Manufacturer | orgs | Manufacturer detail (2-col) | — |
| Message | ai_assistant | — | — |
| ModelLinkConfig | core | — | — |
| ModelRoleConfig | core | — | — |
| Notification | core | — | — |
| Order | transactions | Order detail (3-col), print | Kanban |
| OrderLine | transactions | Line card | — |
| OrgBase | orgs | — | — |
| OrgItem | products | — | — |
| Payment | transactions | Payment detail (2-col) | Apply Payments |
| PaymentApplication | transactions | — | Apply Payments |
| PaymentMethod | transactions | — | — |
| PaymentTerm | transactions | — | — |
| Pending | core | — | — |
| PendingInventoryAdjustment | products | — | — |
| PendingPaymentApplication | transactions | — | — |
| Phone | communications | Phone card | — |
| Project | transactions | — | Kanban, Gantt |
| Proposal | transactions | Proposal detail (3-col), print | Gantt |
| ProposalLine | transactions | Line card | — |
| Purchase | transactions | Purchase detail (3-col), print | — |
| PurchaseLine | transactions | Line card | — |
| QuestionAnswer | docs | QA detail | — |
| Receipt | transactions | Receipt detail | — |
| ReceiptLine | transactions | Line card | — |
| RefsMismatchLog | core | — | — |
| Rep | orgs | Rep detail (2-col) | — |
| Report | core | Report detail (2-col) | — |
| Requisition | transactions | Requisition detail | — |
| RequisitionLine | transactions | Line card | — |
| RoleConfig | core | — | — |
| SchemaDrift | ai_assistant | — | — |
| Serial | products | Serial detail (2-col) | — |
| SerialLog | products | — | — |
| Service | products | — | — |
| Setting | core | — | — |
| SiteInventory | products | — | — |
| SoftDeleteLedger | core | — | — |
| Specification | products | Spec detail | — |
| StatementLine | transactions | — | — |
| Tag | docs | — | — |
| TaxJurisdiction | accounts | — | — |
| Template | core | — | — |
| Term | accounts | — | — |
| UserDailyLog | core | — | — |
| UserProfile | core | — | — |
| Variant | products | — | — |
| Vendor | orgs | Vendor detail (3-col + 7 tabs) | — |
| Warehouse | products | — | Inventory Dashboard |
| WorkOrder | transactions | WO detail (3-col), print | Gantt |
| WorkOrderLine | transactions | Line card | — |

---

## Dashboards — ui.json + ui.tsx

Dashboards are panel layouts stored as Settings. The panel renderer reads the config
and renders the right component for each panel type.

| Dashboard | Panels | ui.json | ui.tsx |
|-----------|--------|---------|--------|
| Commerce | KPIs, orders, invoices, AR | db.list panels | Chart (sales trend) |
| Forecast | Running balance, pipeline, AR/AP | db.list panels | Area chart |
| Apply Payments | Customer search, invoice list, payment form | db.list + form | Drag-apply |
| Inventory | Receive, adjust, reconcile, warehouse | db.list panels | Count sheet |
| Script Editor | Prompt, code editor, output | Form + code | Console |
| Alice | Observations, insights, coaching | db.list panels | — |
| Team | Activity, performance | db.list panels | Chart |
| Accounting | GL, journals, aging | db.list panels | — |

## Printing — ui.json (mostly)

Print templates read from the same layout JSON as the working form.
The print renderer builds standalone HTML — no React, no app chrome.

| Output | Driven by | Notes |
|--------|-----------|-------|
| Standard document (order, invoice, etc.) | ui.json layout + record data | TransactionPrint.tsx |
| Pick list | ui.json + report config (no prices, show location) | Template variant |
| Packing slip | ui.json + report config (no prices, show shipped qty) | Template variant |
| Labels/barcodes | Report config + pdfme | ui.tsx (pdfme layout editor) |
| Statements | ui.json + aging calculation | Template variant |
| Letters/email | Report config + template merge | Template-driven |
| EDI/export | Report config + format spec | External convention may force ui.tsx |
| Custom reports | Report model config | User-defined via Report records |

**The rule:** if the output follows the document layout, ui.json drives it.
If the output requires a specialized renderer (barcode layout, EDI format), ui.tsx.

## Summary

- **All models**: db.json (databrowser) for administration — universal, not listed
- **~35 models**: ui.json — dedicated forms for daily workflow use
- **~8 models**: ui.tsx — interaction-heavy custom components
- **~50 models**: db.json only — config, system, admin, accounting
