# DataBrowser Discipline — Why Polish Matters More Than Features

**Created:** 2026-07-11
**Owner:** Bill James

---

## The Principle

Every tool gap is an invitation to bypass the system. If the DataBrowser can't do something a user needs, they will find another way — pgAdmin, raw SQL, direct database edits. The damage from those workarounds is invisible until it isn't.

**What direct database edits bypass:**

| Protection | What it does | Skipped by psql |
|---|---|---|
| RBAC | Controls who sees and changes what | Yes |
| Audit trail | Records who changed what and when | Yes |
| Backend recalculation | Ensures totals, margins, balances are correct | Yes |
| Alice observation | Learns from user behavior to improve the system | Yes |
| WCHQ pattern learning | Community benefits from usage patterns | Yes |
| zz/qq exclusion | Keeps training data out of reports and decisions | Yes |
| Athena review | Validates calculated functions and security | Yes |
| Validation rules | Prevents bad data from entering the system | Yes |
| Pending queue | Stages changes for deferred processing | Yes |
| Refs/links integrity | Maintains relationship graph between records | Yes |

One raw SQL UPDATE can silently break an invoice balance, corrupt an inventory count, or expose data that RBAC was hiding. No log, no alert, no recovery path.

---

## The Rule

**Polish DataBrowser until there is no reason to use psql for data operations.**

Every feature gap in DataBrowser is a security risk, a data integrity risk, and a learning gap. The priority is not building new programs — it is making the one tool that touches all data so good that nobody needs to go around it.

This is not about preventing access. Admins will always have database access. It is about making the right path easier than the wrong path. If DataBrowser can search, filter, edit, export, inspect JSON, run saved queries, and show calculated columns — there is no reason to open pgAdmin except for schema changes and emergency recovery.

---

## What DataBrowser Must Do Well

### List (already working)
- Search by keyword
- Sort by any column
- Paginate
- Column show/hide/reorder
- Saved layouts per model
- CSV/Excel export
- Saved search presets

### BrowserDetail (needs polish)
- All fields editable with proper widgets
- JSON fields inspectable via floating viewer
- JSON editing gated by authority (read-only default, unlock with permission)
- Related records visible (subforms via Setting config)
- Calculated columns with instant feedback (JS display, backend saves)
- Print from detail view

### Subforms (to build)
- Five types: flat table, JSON, BOM/tree, grouped, calculated columns
- Filtered by parent record (e.g., order lines on order detail)
- Configured by Setting record per model
- Same DataBrowser engine, embedded mode

### Authority Controls
- field_access Settings control visibility per role
- JSON edit requires explicit permission
- Calculated functions approved by Athena
- Front-back mismatch is a FAULT — Alice and Athena alert immediately
- Monthly WCHQ settings review with admin approval

---

## The Analogy

This is the same argument as JPods vs highways. Build the good alternative and the bad behavior becomes unnecessary. You don't stop people from driving — you make the better option so convenient that driving becomes the harder choice.

DataBrowser is the JPods of data management. psql is the highway. Every feature we add to DataBrowser is a station that makes the highway less necessary.

---

## Hard Rules

1. **No ModelList.tsx** — DataBrowser at `/db/:model` is the only list engine
2. **BrowserDetail is read-only by default** — authority-gated unlock for editing
3. **JSON viewer is read-only by default** — unlock requires field_access + Setting permission
4. **JS calculated columns are display-only** — backend recalculates on save, backend wins
5. **Front-back mismatch is a FAULT** — Alice logs, Athena flags, admin alerted, WCHQ notified
6. **zz/qq records never tally** — excluded from all reports, GL, dashboards, decisions
7. **All CRUD through wcapi** — no direct model access, every operation audited
8. **One save path** — no two windows editing the same record simultaneously
