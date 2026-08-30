# WC3 Flowcharts — Training Reference

33 charts documenting the complete WC3/R25 commerce system. Originally derived from the WC2 `WebClerkComExFlowCharts.pdf` (86 pages) and Miro boards, updated with WC3 model names, architecture, and Alice integration.

**Alice Dashboard:** These charts are listed in the Alice Dashboard Training tab with clickable PDF links at `/static/training/flowcharts/`.

All charts are Graphviz DOT source files. Render with: `dot -Tpdf <file>.dot -o <file>.pdf`

Render all: `for f in *.dot; do dot -Tpdf "$f" -o "${f%.dot}.pdf"; done`

## Chart Index

### Core Commerce Flow

| # | Chart | File | Description |
|---|-------|------|-------------|
| 1 | Master Commerce Flow | [wc3-master-flow](wc3-master-flow.pdf) | Top-level: Market → Contact → Proposal → Order → Invoice → Payment → GL |
| 2 | Big 4 Transactions | [wc3-big4-transactions](wc3-big4-transactions.pdf) | Proposal/Order/Purchase/Invoice line quantities and pending inventory |
| 3 | Order to Invoice | [wc3-order-to-invoice](wc3-order-to-invoice.pdf) | Customer → verify → order → production → workflow → backorder/invoice |
| 4 | Customer-Centered Sales | [wc3-customer-centered-sales](wc3-customer-centered-sales.pdf) | Commerce from the customer's perspective: cloud of options, competitors |

### Inventory & Purchasing

| # | Chart | File | Description |
|---|-------|------|-------------|
| 5 | Inventory Buckets | [wc3-inventory-buckets](wc3-inventory-buckets.pdf) | Quantity math: on_hand, on_so, on_po, on_wo → available |
| 6 | Inventory Costing | [wc3-inventory-costing](wc3-inventory-costing.pdf) | Layer-based cost: LIFO / FIFO / Weighted Average evaluation |
| 7 | Inventory Adjustment | [wc3-inventory-adjustment](wc3-inventory-adjustment.pdf) | Physical count → variance → adjustment → audit trail |
| 8 | PO Receipt Flow | [wc3-po-receipt](wc3-po-receipt.pdf) | Purchase → receive → inventory layers → serials → GL |
| 9 | Forecast & Purchasing | [wc3-forecast-purchasing](wc3-forecast-purchasing.pdf) | Replenishment loop: demand signals → forecast → PO → receive |
| 10 | Requisition Management | [wc3-requisition-management](wc3-requisition-management.pdf) | Internal procurement: request → approve → purchase order |
| 11 | Bill of Materials | [wc3-bom](wc3-bom.pdf) | Assembly tree: expand, build, cost rollup, where-used |

### Sales & Marketing

| # | Chart | File | Description |
|---|-------|------|-------------|
| 12 | Sales Management | [wc3-sales-management](wc3-sales-management.pdf) | Full sales module: pipeline, activity tracking, performance evaluation |
| 13 | Lead Qualification | [wc3-lead-qualification](wc3-lead-qualification.pdf) | Marketing effort → leads → qualify → commit or disqualify |
| 14 | Ad Source Tracking | [wc3-ad-source-tracking](wc3-ad-source-tracking.pdf) | Campaign ROI: source → lead → customer → revenue measurement |
| 15 | Territory Assignment | [wc3-territory-assignment](wc3-territory-assignment.pdf) | Auto-assign rep & sales ID by zip code geography |
| 16 | Commission Calculation | [wc3-commission-calculation](wc3-commission-calculation.pdf) | Line-item controlled: rep rate × item commissionableness |
| 17 | Price Cascade | [wc3-price-cascade](wc3-price-cascade.pdf) | First-match-wins: item → level → customer → final price |

### Support & Service

| # | Chart | File | Description |
|---|-------|------|-------------|
| 18 | Service & RMA | [wc3-service-rma](wc3-service-rma.pdf) | Support loop: track, route, resolve, learn (Pareto + Alice) |
| 19 | Returns & Credits | [wc3-returns-credits](wc3-returns-credits.pdf) | RMA → credit memo → inventory reversal → GL |
| 20 | QA Entity | [wc3-qa-entity](wc3-qa-entity.pdf) | Quality inspection, surveys, customer feedback via QAQuestion templates |
| 21 | Serial Tracking | [wc3-serial-tracking](wc3-serial-tracking.pdf) | Serial lifecycle: receive → reserve → ship → return; warranty |

### Financial

| # | Chart | File | Description |
|---|-------|------|-------------|
| 22 | Payment & GL | [wc3-payment-gl](wc3-payment-gl.pdf) | Payment → journals → general ledger; aging; erosion detection |
| 23 | Management Dashboard | [wc3-management-dashboard](wc3-management-dashboard.pdf) | Input efforts → evaluation → business results (cash flow, commissions) |

### Organization & Infrastructure

| # | Chart | File | Description |
|---|-------|------|-------------|
| 24 | Project | [wc3-project](wc3-project.pdf) | Project connects transactions; data layer with lines/items/serials |
| 25 | Action | [wc3-action](wc3-action.pdf) | Universal task model: Who/What/Why/When; references any record |
| 26 | Linkage | [wc3-linkage](wc3-linkage.pdf) | Data package: project inheritance, transaction chain, item families |
| 27 | Contact | [wc3-contact](wc3-contact.pdf) | Central identity: roles (customer/employee/rep/vendor); linkage |
| 28 | Sign-in / Register | [wc3-signin-register](wc3-signin-register.pdf) | Authentication + role assignment flow |
| 29 | RBAC & Field Access | [wc3-rbac-field-access](wc3-rbac-field-access.pdf) | Role → Setting → what each user sees and edits |
| 30 | Save Pipeline | [wc3-save-pipeline](wc3-save-pipeline.pdf) | Setting-driven hooks: pre → validate → save → post → async |
| 31 | Document Templates | [wc3-document-template](wc3-document-template.pdf) | Template-driven: role-based fields, scripts, denormalization |
| 32 | Report & Document Output | [wc3-report-output](wc3-report-output.pdf) | Document routing: PDF / email / API / webhook / sync bundle |
| 33 | Data Sync | [wc3-sync](wc3-sync.pdf) | Connection model: bundles, field maps, soft/hard match, conflict resolution |

### Deployment & Operations

| # | Chart | File | Description |
|---|-------|------|-------------|
| 34 | Deployment Architecture | [wc3-deployment](wc3-deployment.pdf) | Dev (runserver) vs production (Gunicorn + Nginx); rsync deploy; systemd services |

### Reference Documentation

| Document | Location | Description |
|----------|----------|-------------|
| Production Deployment | [topics/infrastructure/production-deployment.md](../../topics/infrastructure/production-deployment.md) | Dev vs production server; SSH/rsync setup; systemd services; Cloudflare SSL |
| Minimal Viable Install | [topics/infrastructure/minimal-viable-install.md](../../topics/infrastructure/minimal-viable-install.md) | All seed commands, required GL accounts, demo data, complete install sequence |
| READ_ONLY_MODE | [topics/infrastructure/read-only-mode.md](../../topics/infrastructure/read-only-mode.md) | Single .env setting locks any database to read-only; 4-layer enforcement; demos, archives, audits |

## Style

New charts (2026-08) use a cleaner visual style:
- Rounded boxes, subtle cluster backgrounds
- Consistent color palette (indigo/blue/green/amber/purple)
- Alice integration shown where she participates
- Helvetica Neue font throughout

Original 12 charts (2026-07) use the earlier style. Both render correctly.

## WC2 Source

Original WC2 flow charts: `allie/inbox/domains/jpods.com/public_html/software/WebClerkComExFlowCharts.pdf` (86 pages, ~2002)

Miro board exports: `allie/readmes/flowcharts/miro/` (12 PNG files — updated versions of core charts)
