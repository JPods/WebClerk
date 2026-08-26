# WC3 Project Management — Comparison with Dedicated PM Tools

## What WC3 Is Not

WC3 is a commerce platform with project tracking built in. It is not a dedicated PM tool.
The project model exists to connect work to transactions — not to replace MS Project.

## Feature Comparison

| Capability | MS Project | Smartsheet | Asana | Trello | WC3 |
|-----------|-----------|-----------|-------|--------|-----|
| **Planning** | | | | | |
| Gantt with auto-scheduling | Yes | Yes | Yes | No | No |
| Critical path calculation | Yes | Yes | No | No | **Yes** |
| Resource leveling | Yes | Yes | Limited | No | No |
| Earned value management | Yes | No | No | No | No |
| Multiple baselines | Yes | Yes | No | No | No |
| Lag/lead time on deps | Yes | Yes | No | No | No |
| Recurring tasks | Yes | Yes | Yes | Yes | No |
| Dependency tracking | Yes | Yes | Yes | Limited | **Yes** |
| **Views** | | | | | |
| Gantt timeline | Yes | Yes | Yes | No | **Yes** |
| Kanban board | No | Yes | Yes | Yes | **Yes** |
| List/table | Yes | Yes | Yes | Yes | **Yes** |
| Calendar | Yes | Yes | Yes | Yes | No |
| Timeline/roadmap | Yes | Yes | Yes | Yes | No |
| **Collaboration** | | | | | |
| Comments/notes | Limited | Yes | Yes | Yes | **Yes** |
| Assignees | Yes | Yes | Yes | Yes | **Yes** |
| Automation rules | Limited | Yes | Yes | Yes | **Alice** |
| Templates | Yes | Yes | Yes | Yes | **bundle.json** |
| **Resource Mgmt** | | | | | |
| Resource pool | Yes | Yes | Yes | No | No |
| Workload view | Yes | Yes | Yes | No | No |
| Cost per task | Yes | Yes | No | No | No |

## What WC3 Does That None of Them Do

The gap PM tools cannot fill: connecting work to money.

| Capability | MS Project | Smartsheet | Asana | Trello | WC3 |
|-----------|-----------|-----------|-------|--------|-----|
| **Commerce Chain** | | | | | |
| Action → Invoice → Payment | No | No | No | No | **Yes** |
| Action → Purchase Order | No | No | No | No | **Yes** |
| Project → Customer contact | No | Limited | No | No | **Yes** |
| Project → Vendor contact | No | No | No | No | **Yes** |
| **Documents** | | | | | |
| Confidentiality tagging | No | No | No | No | **Yes** |
| Version-tracked data room | No | Limited | No | No | **Yes** |
| Access counting | No | No | No | No | **Yes** |
| Retention periods | No | No | No | No | **Yes** |
| **Quality** | | | | | |
| NCR/CAR as action types | No | No | No | No | **Yes** |
| ISO 9001 integration | No | No | No | No | **Yes** |
| Retrospection per action | No | No | No | No | **Yes** |
| Impact tracking (predicted vs actual) | No | No | No | No | **Yes** |
| **Intelligence** | | | | | |
| Alice pattern recognition | No | No | No | No | **Yes** |
| Small-Stings (customer fines) | No | No | No | No | **Yes** |
| Portable project plans (bundle.json) | XML | Limited | No | JSON | **Yes** |
| Project Scanner import tool | No | No | CSV | JSON | **Yes** |
| **Transactions** | | | | | |
| Orders (sales) | No | No | No | No | **Yes** |
| Proposals/quotes | No | No | No | No | **Yes** |
| Invoices (AR) | No | No | No | No | **Yes** |
| Purchases (AP) | No | No | No | No | **Yes** |
| Payments (received + made) | No | No | No | No | **Yes** |
| Inventory tracking | No | No | No | No | **Yes** |
| GL/ledger entries | No | No | No | No | **Yes** |
| Price levels + terms | No | No | No | No | **Yes** |
| Tax calculation | No | No | No | No | **Yes** |
| Commission tracking | No | No | No | No | **Yes** |

## WC3 Transaction Models

Every transaction type in WC3 can link to project actions:

| Model | What It Does | Links To |
|-------|-------------|----------|
| **Proposal** | Quote/estimate for customer | Customer, Contact, Lines, Actions |
| **Order** | Confirmed sale | Customer, Contact, Lines, Invoice, Actions |
| **Invoice** | Bill to customer (AR) | Customer, Order, Lines, Payments, Ledger |
| **Purchase** | Buy from vendor (AP) | Vendor, Contact, Lines, Payments, Ledger |
| **Payment** | Money in or out | Invoice, Purchase, Contact, Ledger |
| **Ledger** | GL journal entry | Invoice (AR), Purchase (AP), Payment |
| **Item** | Product/service | Lines, Inventory, BOM, Specs, XRefs |
| **Inventory** | Stock tracking | Item, Warehouse, Layers |

### The Chain PM Tools Cannot Complete

A typical project action flow in WC3:

```
Action: "Order steel for station structure"
  → creates Purchase (vendor: steel supplier, lines: beam specs)
    → Purchase triggers Inventory (incoming stock)
      → when delivered, Payment created (AP)
        → Payment posts to Ledger (GL)
          → Ledger rolls up to project profit tracking

Action: "Invoice customer for Phase 1 milestone"
  → creates Invoice (customer: city transit authority)
    → Invoice triggers Ledger (AR)
      → when paid, Payment created
        → Payment posts to Ledger
          → Project profit_velocity updates
```

PM tools stop at "task done." WC3 carries the action through to the transaction,
the ledger, and the profit report.

## What WC3 Should Add (80% Coverage)

Three additions that cover 80% of what people actually use MS Project for:

1. **Gantt view** — visual timeline from dt_start/dt_deadline (built 2026-08-24, ProjectActionGantt.tsx)
2. **Dependency arrows** — visual links in action list + Gantt SVG overlay (built 2026-08-24)
3. **Critical path highlighting** — forward/backward pass, zero-slack = critical (built 2026-08-24)

The remaining 20% (resource leveling, earned value, multiple baselines) is enterprise PM
that WC3 users do not need. If they need it, they use MS Project and import via
the Project Scanner (webclerk.com/project_planner).

## The Project Scanner Bridge

Users plan in whatever tool they prefer. The Project Scanner
(webclerk.com/project_planner) imports CSV/XLSX into bundle.json:

```
Any PM tool → Export CSV → Project Scanner → bundle.json → WC3 Import
                                              ↓
                                           plan.svg (visual)
                                              ↓
                                           clean CSV (normalized)
```

WC3 does not need to be the planning tool. It needs to be where plans become transactions.

## Template Library

Pre-built bundle.json templates at ~/Allie/knowledge/projects/:

| Template | Actions | Status |
|----------|---------|--------|
| Due Diligence Data Room | 23 | Done |
| ISO 9001 QMS Implementation | 25 | Done |
| JPods Build — Full Installation | 104 (13 sub-projects) | Done |
| Product Launch | ~20 | Planned |
| Employee Onboarding | ~15 | Planned |
| Vendor Evaluation | ~12 | Planned |
| + 12 more | — | Planned |

Full list: ~/Allie/knowledge/projects/project-plan-library.md
