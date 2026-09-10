# Time & Billing Integration Plan for WebClerk

**Date:** 2026-09-08
**Status:** Draft — candidates identified, ready for evaluation
**Principle:** Time/billing is a specialty function, like accounting and HR. WebClerk spawns work orders and tracks tasks. The billing of time is administrative — it belongs in a dedicated tool.

---

## The Principle

This follows the same Divided philosophy as accounting:

| Domain | Operational (WebClerk) | Administrative (Dedicated) |
|--------|------------------------|---------------------------|
| **Finance** | Sales → GL journals | P&L, BS, AP payments, bank rec |
| **HR** | Not WC3's domain | Payroll, leave, benefits |
| **Time/Billing** | Spawn work orders, track tasks | Timesheets, billable hours, T&M invoicing, profitability |

WebClerk knows *what* needs to be done (Projects, Actions, Work Orders). The billing tool knows *how long it took* and *what to charge*.

---

## The Boundary

```
                 WEBCLERK (operations)
 ┌─────────────────────────────────────────┐
 │ Projects · Actions · Work Orders        │
 │ Customer / Contact records              │
 │ Rates (via Catalog / price levels)      │
 └───────────────────┬─────────────────────┘
                     │
              ┌──────▼──────┐
              │ Project/Task │  WC3 pushes project + task +
              │ Definitions  │  customer definitions via API
              └──────┬──────┘
                     │
              TIME & BILLING SYSTEM
 ┌─────────────────────────────────────────┐
 │ Timesheets (clock in/out, manual entry) │
 │ Billable vs Non-Billable classification │
 │ T&M / Fixed Price / Milestone billing   │
 │ Invoice generation from logged time     │
 │ Resource allocation / utilization       │
 │ Project profitability reporting         │
 └───────────────────┬─────────────────────┘
                     │
              ┌──────▼──────┐
              │ Billing      │  Billing summaries flow back
              │ Summaries    │  to WC3 for GL journalization
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │ GL Journals  │  → Accounting System
              └──────────────┘
```

---

## Candidate Comparison

| Tool | License | Stack | Time Tracking | Invoicing | Project Billing | API | Self-Hosted | Integration Fit |
|------|---------|-------|--------------|-----------|----------------|-----|-------------|----------------|
| **Kimai** | AGPL-3.0 | PHP/Symfony/MariaDB | Full (punch, manual, bulk) | Yes (PDF, DOCX, e-invoice) | T&M native; fixed via plugin | REST + OpenAPI | Docker | **Best today** |
| **Solidtime** | AGPL-3.0 | PHP/Laravel/Vue | Full (timer, manual) | Yes (PDF, e-invoice) | T&M via billable rates | OpenAPI (partial) | Docker | Strong but API immature |
| **AlgaPSA** | AGPL-3.0 | TS/Next.js/PostgreSQL | Full | Yes (drag-drop PDF) | T&M, fixed, quotes | REST + Extension SDK | Docker | Most complete; 137 stars — immature |
| **Ever Gauzy** | AGPL-3.0 | TS/NestJS/Angular/PG | Full | Yes | Claims full billing | REST (poorly documented) | Docker | Risky — claims > docs |
| **OpenProject** | GPL-3.0 | Ruby/Rails/Angular/PG | Log time on work packages | No | No (cost tracking only) | REST (HAL+JSON) | Docker/packages | PM only, no billing |
| **Leantime** | AGPL-3.0 | PHP/MySQL | Yes | No | No | JSON-RPC | Docker | PM only, no billing |

### Excluded
- **Invoice Ninja** — Elastic License (not truly open source)
- **Traggo** — Tag-based only, no project/task model
- **Taiga/Plane** — No time tracking or billing
- **Redmine** — Time tracking but no billing; dated
- **ERPNext** — Full ERP; can't isolate timesheet module; duplicates WC3

---

## Assessment

### 1. Kimai — Recommended First Evaluation

**Why:** Most mature dedicated time-tracking-with-invoicing in open source. REST API with OpenAPI spec — full CRUD on customers, projects, activities, time entries. Production-grade (5,000+ stars, active maintenance).

**Data model maps cleanly:**
- WebClerk `Project` → Kimai `Project`
- WebClerk `Action` → Kimai `Activity`
- WebClerk `Contact` → Kimai `Customer`

**Integration pattern:**
1. WC3 creates Kimai project + activities via API when Action/Project created
2. Workers log time in Kimai (Kimai owns the timesheet UX)
3. WC3 pulls time entries and invoice data via API for profitability + GL

**Gaps:** No milestone billing. No webhooks (must poll or batch). Budget/expense plugins are paid (EUR 99 each).

### 2. Solidtime — Watch Closely

**Why:** Modern UI, solid fundamentals, growing fast (8,900 stars). Billable rates at project/member/org levels. Recently added invoicing.

**Gap:** API only covers projects and time entries — no endpoints for tasks, clients, or invoices yet. Cannot programmatically read invoice data back. Blocker today; may resolve soon.

### 3. AlgaPSA — Long-Term Play

**Why:** Only true open-source PSA tool. Full lifecycle: time tracking, billing cycles, invoicing with PDF designer, quoting, contract POs, tax. REST API + Extension SDK. PostgreSQL (same as WC3).

**Concern:** 137 stars, early-stage. Enterprise features behind commercial license. Not production-ready for critical billing pipeline today. Worth revisiting in 6-12 months.

---

## TimeAdapter Interface

Following the AccountingAdapter pattern:

```python
class TimeAdapter:
    """Base interface for time/billing system integrations."""

    # --- Outbound (WC3 → Time System) ---
    def push_project(self, project_data):
        """Create/update project in time system."""

    def push_task(self, action_data):
        """Create/update task/activity in time system."""

    def push_customer(self, contact_data):
        """Create/update customer in time system."""

    # --- Inbound (Time System → WC3) ---
    def pull_time_entries(self, project_id=None, since=None):
        """Pull logged time entries for profitability."""

    def pull_billing_summary(self, project_id=None, period=None):
        """Pull billing totals for GL journalization."""

    def pull_invoices(self, since=None):
        """Pull generated invoices for reconciliation."""
```

Implementations:
```
KimaiAdapter       ← REST API, OpenAPI spec
SolidtimeAdapter   ← when API matures
AlgaPSAAdapter     ← when project matures
GenericCSVAdapter   ← flat file fallback
```

---

## Implementation Phases

### Phase 1: Manual Export (now)
- Workers log time in whatever tool they use
- Export CSV/PDF, attach to WC3 Project as Document
- Manual GL journal entry for billable time

### Phase 2: Kimai Integration (evaluate + build)
- Install Kimai locally (Docker)
- Map WC3 Projects/Actions → Kimai Projects/Activities
- Build `KimaiAdapter` — push project defs, pull time entries
- Test round-trip: WC3 work order → Kimai time logging → billing summary → GL journal

### Phase 3: Profitability Dashboard
- Pull Kimai data into WC3 Project profitability fields
- Budget vs actual hours
- Billable utilization rate
- Alice watches for projects burning faster than estimated

### Phase 4: Invoice Flow
- Kimai generates time-based invoices
- WC3 pulls invoice summaries
- GL journalization: Dr AR / Cr Service Revenue

---

## Design Rules

1. **WebClerk is source of truth for projects and customers.** The time system receives definitions; it does not create them independently.
2. **The time system is source of truth for hours logged.** WC3 never captures timesheets — that UX belongs to the dedicated tool.
3. **Billing summaries flow through GL.** Time-based invoices produce GL journal entries through the same AccountingAdapter pipeline as sales invoices.
4. **The adapter is the only boundary.** All time system communication goes through the TimeAdapter. No direct database reads.
5. **GenericCSV is always available.** Even without an adapter, workers can export time and attach it to WC3 Projects.
6. **Each company tunes to its needs.** A consulting firm needs T&M. A distributor needs none. A manufacturer needs labor tracking. The adapter makes this the customer's choice, not WC3's assumption.
