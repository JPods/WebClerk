# Model UI Map — SUPERSEDED

**Superseded by:** `model-layout-map.md` (2026-08-18)
**Reason:** Terms changed — `ui.json`→form, `db.json`→detail. Content consolidated into one file.

---

*Original content below preserved for reference only.*

# Model UI Map — Which Models Get What (OLD)

## The Three UI Paths

| Path | What renders it | When to use |
|------|----------------|-------------|
| **ui.json** | Custom layout renderer (FieldRow, HeaderRenderer, Design Mode) | User touches it during business |
| **ui.tsx** | Custom React component | Complex interaction (drag, timeline, real-time) |
| **db.json** | databrowser (db.list + db.detail) | Admin/config, structured data, no workflow |

Every model is exactly one of these three. No ambiguity.

## ui.json Models — Custom Detail Layout

These get `detail_layout` Settings, Design Mode, print templates, widget actions.

### Transactions (family: sell/exec)
| Model | Layout | Family | Status |
|-------|--------|--------|--------|
| order | 3-col: Customer \| Ship To \| Order | sell | Done |
| proposal | 3-col: Customer \| Ship To \| Proposal | sell | Done |
| invoice | 3-col: Customer \| Ship To \| Invoice | sell | Done |
| purchase | 3-col: Vendor \| Receive At \| Purchase | exec | Done |
| work_order | 3-col: Customer \| Location \| Work Order | exec | Pending |
| receipt | 2-col: Vendor \| Receipt | exec | Pending |
| requisition | 2-col: Requestor \| Requisition | exec | Pending |
| payment | 2-col: Payer \| Payment | special | Pending |

### Transaction Lines (family: sell/exec — rendered inside parent line card)
| Model | Parent | Family | Status |
|-------|--------|--------|--------|
| order_line | order | sell | Done (via useLineCard) |
| proposal_line | proposal | sell | Done |
| invoice_line | invoice | sell | Done |
| purchase_line | purchase | exec | Done |
| work_order_line | work_order | exec | Pending |
| receipt_line | receipt | exec | Pending |
| requisition_line | requisition | exec | Pending |

### Communications (family: comm)
| Model | Layout | Status |
|-------|--------|--------|
| email | single-col | Seeded |
| phone | single-col | Seeded |
| address | single-col | Seeded |
| domain | single-col | Seeded |

### Core (family: core)
| Model | Layout | Status |
|-------|--------|--------|
| contact | 3-col: Contact \| Address \| Profile + 7 tabs | Seeded |
| action | 2-col: Action \| Assignment | Seeded |
| document | 2-col: Document \| Attachment | Seeded |
| question_answer | single-col | Seeded |
| report | 2-col: Report \| Settings | Seeded |

### Organizations (family: org)
| Model | Layout | Status |
|-------|--------|--------|
| customer | 3-col: Company \| Primary Contact \| Account | Pending |
| vendor | 3-col: Company \| Primary Contact \| Account | Pending |
| manufacturer | 2-col: Company \| Contact | Pending |
| employee | 2-col: Person \| Employment | Pending |
| rep | 2-col: Person \| Territory | Pending |

### Products (family: product)
| Model | Layout | Status |
|-------|--------|--------|
| item | 3-col: Item \| Pricing \| Inventory + tabs | Pending |

## ui.tsx Models — Custom React Components

These are interaction-heavy — drag, drop, timeline, real-time updates. JSON drives the data, .tsx owns the interaction.

| Component | What it does | Models involved |
|-----------|-------------|-----------------|
| KanbanBoardPage | Drag cards between columns | action, project |
| UnifiedGantt | Timeline with drag resize | action, project |
| ApplyPayments | Drag payments to invoices | payment, invoice |
| ShoppingCart | Cart with qty, checkout | item, order |
| InventoryDashboard | Receive, adjust, reconcile | item, warehouse, serial |

## db.json Models — databrowser Only

These use db.list and db.detail. No custom layout. No Design Mode.

### Accounts
| Model | Why databrowser |
|-------|----------------|
| gl_account | Chart of accounts — admin setup |
| gl_journal | Journal entries — accounting |
| ledger | Ledger records — accounting |
| tax_jurisdiction | Tax rates — admin config |
| term | Payment terms — admin config |
| currency | Currency codes — admin config |
| exchange_rate | FX rates — admin config |
| exchange_transaction | FX transactions — accounting |
| audit | Audit log — system records |
| tally_summary | Aggregations — system computed |
| sales_dimension_tally | Analytics — system computed |
| inventory_usage_tally | Analytics — system computed |
| tally_registry | Tally config — admin |

### Core Config
| Model | Why databrowser |
|-------|----------------|
| setting | System config — admin |
| template | Document templates — admin |
| notification | System notifications — admin |
| pending | Queue records — system |

### Docs Config
| Model | Why databrowser |
|-------|----------------|
| linkage | Linkage entries — system |
| tag | Tags — admin |

### Products — ui.json
| Model | Layout | Status |
|-------|--------|--------|
| item | 3-col: Item \| Pricing \| Inventory + 8 tabs (BOM tab = embedded db.list) | Seeded |
| serial | 2-col: Serial \| Assignment | Seeded |
| specification | single-col | Seeded |

### Products — db.json
| Model | Why databrowser |
|-------|----------------|
| bill_of_material | BOM records — db.json standalone, embedded as card in Item BOM tab |
| catalog | Catalog config — admin |
| item_xref | Cross-references — admin |
| org_item | Org-item links — admin |
| service | Service records — admin |
| variant | Variants — admin |
| warehouse | Warehouse config — admin |
| usage | Usage tracking — system |
| matrics | Metrics — system |

### Support — db.json
| Model | Why databrowser |
|-------|----------------|
| All support models | Scheduler, tasks — admin/system |

### Sync
| Model | Why databrowser |
|-------|----------------|
| connection | Sync config — admin |
| bundle | Sync bundles — system |

## How to Add a New Model

1. Decide: workflow or admin? (Does a user touch it during business?)
2. If workflow: create a `detail_layout` Setting via `seed_comm_layouts` or similar
3. If admin: databrowser handles it — add to `workbench_fields` if custom column layout needed
4. Add to this map

## Future: Universal Detail Renderer

The goal is one renderer component that reads any `detail_layout` Setting and renders the form.
TransactionDetail already does this for transactions. A `RecordDetail` component would do the
same for contacts, items, orgs — any model with a layout Setting.

The difference from TransactionDetail: no line card, no transaction-specific toolbar.
The renderer reads the `family` field to know what features to enable:
- `sell`/`exec` → line card, transaction toolbar, print
- `comm` → single-column card, widget actions
- `core` → flexible layout, tabs
- `org` → three-column with contact panels
- `product` → tabs with inventory, pricing, BOM
