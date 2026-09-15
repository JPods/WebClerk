# Done — React2025 Frontend

What's built, tested, and working. Updated 2026-08-05.

---

## DataBrowser
- Two-pane dark/light browser at `/db/:model`
- 61 models seeded with initial layouts
- Field grouping with collapsible sections
- Detail field groups ordered by user priority (Communication 2nd, FK IDs in System)
- Saved views (list + detail layouts)
- Row color rules
- Markdown template dialog (merge reports open MarkdownEditor)
- Cmd+P = primary print, Cmd+Opt+P = report selector
- Universal print wired via ReportsDialog
- Edit Layout button opens print_layout Setting
- Flat view seeded

## Transaction Detail
- JSON-driven `TransactionDetail` renders all transaction types
- `LineCardRenderer` — line items with price/cost/qty columns
- `DetailToolbar` — single toolbar (archived TransactionToolbar)
- Balance display (red when > 0)
- Commission columns (C toggle, staff-only)
- `line_type` field on all 7 line models (product/tax/shipping/discount)
- `applyCustomerDefaults.ts` — tax jurisdiction + exemption flow from customer

## Packing
- `PackingPanel` — 3-step pick/pack/ship workflow
- Step 1 Pick: checklist sorted by warehouse/bin, checkbox all
- Step 2 Pack: multi-box, weight per box, editable qty, ScaleBar
- Step 3 Ship: carrier/tracking/date/freight cost → invoice creation
- Ship Order button in ManageActionPanel opens PackingPanel
- `ScaleBar` — live weight, status dot, tare/read/disconnect buttons

## Scale Integration
- `useScale` hook — Web Serial API, WC2 PkScaleProcess algorithm port
- Continuous polling, dither filter, stability detection (6 readings)
- Deviation calc: expected + tare - scale, with allowed variance %
- Per-item delta check (weight change after scan vs expected)
- Status: ok (green), mismatch (red), negative_tare (red), no_reading (amber)
- Configurable: baud rate, data bits, parity, weight command, poll interval

## Markdown Templates
- `MarkdownEditor` — view/edit toggle, split preview
- `{{field.path}}` and `{{field.path|format}}` token syntax
- `{{#each lines}}...{{/each}}` list iteration
- Token picker dropdown (filter + insert from available fields)
- Submit to WC_HQ button (Action record for upstream contribution)
- `resolveTokens()` exported for standalone use
- Wired to Reports: `output_type='merge'` opens MarkdownEditor
- List context passes all records, detail context passes selected record

## Printing
- 13 print document components (order, invoice, proposal, purchase, work order, receipt, requisition, tax report, commission report, etc.)
- `UniversalPrint.ts` — JSON-driven HTML renderer
- `printLayoutTypes.ts` — TypeScript interfaces
- `usePrintLayout.ts` — fetch print_layout Setting with fallback
- `useReportShortcuts` — Cmd+P and Cmd+Opt+P
- Alice drafts layouts from PDF/image uploads

## Contact Detail
- `ContactDetailJson` — JSON-driven from detail_layout Setting
- 3-column header with field groups
- Tabs: Communications, Actions, Kanban, Gantt, Documents, Notes, QA, History
- `CommPanel` — emails, phones, addresses, domains
- `ProjectKanbanPanel` — drag-and-drop project board filtered by contact
- `ProjectGanttPanel` — pure CSS timeline with today marker, month headers, progress fill

## Inventory
- `InventoryAdjust.tsx` — search items, warehouse select, qty +/-, reason, Apply
- `CycleCountMobile.tsx` — phone-sized, barcode/QR camera scan, expected vs actual
- `CycleCountPanel` — desktop, on Item dashboard Counts tab
- `InventoryLayersPanel` — FIFO/LIFO cost layers by warehouse

## Serial Tracker
- `SerialCard`, `SerialDetailCard`, `SerialSelectPanel`, `SerialPanel`
- Multi-context: item/customer/vendor/manufacturer
- 9 statuses, lifecycle actions, SerialLog display

## Kanban & Gantt (standalone)
- `KanbanBoardPage` — full drag-and-drop board with contact filtering
- `UnifiedGantt` — `@svar-ui/react-gantt` with project selector
- Both at `/kanban` and `/gantt` routes

## Dashboards
- `Dashboard` — main landing page
- `CommerceDashboard` — commerce overview
- `SupportDashboard` — combined Support + Accounting (actions, quality, documents, connections, bundles, journal status, GL balance, aging, pending inventory)
- `ProductsDashboard`, `TransactionsDashboard`, `OrgsDashboard`
- `AliceDashboard`, `TeamDashboard`, `InventoryDashboard`

## Layout
- `AppSidebar` — prefs-driven nav (models + dashboards)
- `MacTopBar` — window tabs, dev indicator
- Default dashboards: dashboard, products, transactions, orgs, support, kanban, gantt, alice, databrowser, json

## Security (frontend)
- `is_staff`/`is_superuser` on auth user
- Commission columns/totals/panels hidden for non-staff
- Commission auto-populate gated to staff
- Commission reports require `role_required: 'admin'`
- Gateway fields stripped from payment display for non-staff

## ManageActionPanel
- Config-driven action buttons per model
- Order: Convert to Invoice, Convert to PO, Create Work Order, Ship Order, Complete, Clone, Link Campaign
- Invoice: Journalize, Ship (Consume Inventory), Assign Serial, Clone, Link Campaign
- Purchase: Receive Goods, Create Serial
- Proposal: Convert to Order, Convert to Invoice, Clone, Link Campaign
- Ship Order opens PackingPanel (full workflow)

---

*Verified by code audit 2026-08-05. Each section maps to files in the `src/` tree.*
