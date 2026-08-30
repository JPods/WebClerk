# Frontend Documentation

> Frontend for WebClerk. See also: [backend readmes](../../backend/readmes/alice/00-ai-agreement.md)

---

## 📚 Reading Order

| # | File | Description |
|---|------|-------------|
| 00 | `00-index.md` | **Start here** |
| 01 | `01-architecture.md` | Project structure, apps, naming conventions |
| 02 | `02-env-setup.md` | Environment variables |
| 03 | `03-api-integration.md` | Connecting to wc3 wcapi |

## Security & Permissions

- `rbac-frontend.md` - Role-based access control in React (context, hooks, guards)

## Transaction Topics (`topics/`)

> **Quantity semantics, line models, and DB-level concerns live in wc3:**
> `backend/readmes/topics/transactions/transactions-totals.md`
> R25 is UI only — wc3 is the source of truth for all quantity, transfer, and totals logic.

- `transaction-services.md` - **Single Point of Authority services** (lines, tax, shipping, commissions, etc.)
- `transaction-calculations.md` - Frontend calculation logic (optimistic; backend is authoritative)
- `TransactionModelsAlignment.md` - wc3 ↔ r25 model mapping
- `payments.md` - **Payment module** — list, detail, panel, dialog, apply-payments, legacy crosswalk

## Additional Topics (`topics/`)

- `components.md` - **Component & file inventory** — every .tsx/.ts by area, qqq-flagged dead code catalog
- `config-defaults.md` - **Defaults by table** — modelDefaults, fieldDefaults, select lists
- `admin-workbench.md` - Admin panel features
- `admin-window.md` - Admin window component
- `offline-optimistic-updates.md` - Offline-first patterns
- `refs.md` - refs JSON field usage
- `unsaved-changes-guard.md` - Prevent data loss with navigation/action guards
- `whitelist.md` - Schema whitelist testing
- `git.md` - Git workflow

## DataBrowser

- `databrowser-discipline.md` - **Why polish matters** — every tool gap is a security risk
- `sow-detail-field-grouping.md` - **Field grouping SOW** — completed 2026-08-05; collapsible sections, data-driven groups
- `layout-maintenance.md` - Layout file inventory and status tracking

## Archived (`_archive/`)

Legacy migration and comparison docs.
